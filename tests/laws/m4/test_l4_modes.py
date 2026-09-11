"""M4 laws L4.4 and L4.8 — replay-only by default, and the clock as a captured value
(docs/specs/m4.md §4, §3; BRIEF §5.10, §5.7).

FROZEN at m4-laws-freeze.

L4.4. "`tannen run` is replay-only by default and refuses novel oracle invocations; `tannen
run --spend` engages SpendGuard against the budget file." The refusal comes BEFORE the
transport is touched and writes nothing — a refusal issued after the call has already
spent. The same holds at the command line: `tannen run MODULE:CALLABLE` without `--spend`
refuses; with `--spend` it asks SpendGuard, and a zero budget says no.

L4.8. "No wall clock ... the Clock oracle is the only source of time, so replay determinism
is not a discipline but a fact." A clock reading is a capture keyed by the label the caller
names; replaying the label returns the captured instant with no transport at all, and a new
label is a new reading that replay-only refuses.
"""

from __future__ import annotations

import importlib.util as _ilu
import json
import textwrap
from pathlib import Path as _Path

import pytest

pytest.importorskip("tannen.oracles", reason=(
    "M4 boundary not implemented yet (law suite frozen ahead of Session B); M4's laws go "
    "live together — docs/specs/m4.md §11"))

_spec = _ilu.spec_from_file_location("tannen_frozen_m4._frozen_bind",
                                     _Path(__file__).with_name("_frozen_bind.py"))
bind = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(bind)

M = bind.m4("_boundary_model")
TANNEN = bind.m4("_boundary_subject").make(M)

from tannen import cli  # noqa: E402

VALIDATED_BY = "tests/laws/m4/_boundary_model.py::check_modes"


@pytest.mark.parametrize("kind", ["fetch", "llm"])
def test_l4_4_replay_only_is_the_default_and_refuses_before_the_transport(kind) -> None:
    M.check_modes(TANNEN, kind, M.spec_for(kind, 0, 1))


_TARGET = textwrap.dedent('''
    from tannen.oracles import Clock

    CALLS = []


    def _transport(request):
        CALLS.append(request)
        return {"instant": "2026-09-11T00:00:00Z"}


    def pipeline(oracles):
        clock = Clock("m4-cli-clock", reproducibility="non-reproducible",
                      transport=_transport, unit="nano-usd", price=0)
        return oracles.invoke(clock, {"label": "cli"})
''')


def _target(tmp_path, monkeypatch, name: str):
    (tmp_path / f"{name}.py").write_text(_TARGET, encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    import importlib

    return importlib.import_module(name)


def _budget(tmp_path, ceiling: int) -> str:
    path = tmp_path / "budget.yaml"
    path.write_text(json.dumps({"scope": "M4", "unit": "nano-usd",
                                "ceilings": {"total": ceiling, "clock": ceiling}}),
                    encoding="utf-8")
    return str(path)


def test_l4_4_tannen_run_without_spend_refuses_a_novel_invocation(tmp_path, monkeypatch,
                                                                   capsys) -> None:
    module = _target(tmp_path, monkeypatch, "m4_l4_4_run_replay")
    code = cli.main(["run", "m4_l4_4_run_replay:pipeline", "--store", str(tmp_path / "s"),
                     "--budget", _budget(tmp_path, 10**6)])
    assert code == 1
    assert "NovelInvocationRefused" in capsys.readouterr().err
    assert module.CALLS == [], "`tannen run` reached the transport without --spend"


def test_l4_4_tannen_run_spend_with_a_zero_budget_is_denied(tmp_path, monkeypatch,
                                                            capsys) -> None:
    module = _target(tmp_path, monkeypatch, "m4_l4_4_run_zero")
    code = cli.main(["run", "m4_l4_4_run_zero:pipeline", "--store", str(tmp_path / "s"),
                     "--budget", _budget(tmp_path, 0), "--spend"])
    assert code == 1
    assert "SpendDenied" in capsys.readouterr().err
    assert module.CALLS == [], "a zero budget authorised a call"


def test_l4_4_tannen_run_spend_is_the_one_spelling_that_can_call(tmp_path, monkeypatch) -> None:
    module = _target(tmp_path, monkeypatch, "m4_l4_4_run_spend")
    args = ["run", "m4_l4_4_run_spend:pipeline", "--store", str(tmp_path / "s"),
            "--budget", _budget(tmp_path, 10**6)]
    assert cli.main(args + ["--spend"]) == 0
    assert len(module.CALLS) == 1
    assert cli.main(args) == 0, "a capture made under --spend did not replay without it"
    assert len(module.CALLS) == 1, "the replay reached the transport"


def test_l4_8_a_clock_reading_replays_its_instant_with_no_transport() -> None:
    M.check_modes(TANNEN, "clock", M.spec_for("clock"))


def test_l4_8_each_label_is_its_own_reading() -> None:
    spec = M.spec_for("clock")
    budget = {"scope": "M4", "unit": spec["unit"], "ceilings": {"total": 1, "clock": 1}}
    store = TANNEN.store_local()
    seeding = M.FakeTransport("clock")
    clock = TANNEN.oracle("clock", "m4-clock", spec, "non-reproducible", seeding)
    first = TANNEN.invoke(TANNEN.session(store, "spend", budget), clock, {"label": "noon"})
    silent = M.FakeTransport("clock")
    replayed = TANNEN.oracle("clock", "m4-clock", spec, "non-reproducible", silent)
    replay = TANNEN.session(store, None, None)
    assert TANNEN.invoke(replay, replayed, {"label": "noon"}) == first
    assert len(seeding.calls) == 1
    assert TANNEN.read(replay, first) == M.FakeTransport("clock")(seeding.calls[0]), \
        "the replayed instant is not the one the world reported"
    with pytest.raises(TANNEN.novel_refused):
        TANNEN.invoke(replay, replayed, {"label": "midnight"})
    assert silent.calls == [], "a clock replay asked the world what time it was"
