"""`tannen.export` and `tannen run` — what frozen L4.10 and L4.4 leave open (docs/specs/m4.md
§1, §7; decision D0237).

L4.10 drives the export door over the model's catalogue through `AlwaysRebuild`; L4.4 drives
`tannen run`'s three spellings. Decided here: that the two `Built`s with nothing honest to
say — a trace hit (nothing ran, so no layer) and a whole-node quarantine (no output) — are
refused rather than exported, and the command line's ergonomics: a malformed target is a
usage error, a returned capture ref is printed, and a failure that is not one of the four
named refusals is not swallowed into an exit code.

It also carries the CLAMP's live tests (D0263): L5.1 is the frozen judge of `tannen run`'s
budget rule, and it skips wherever no authorised M5 corpus exists (D0259) — which is
everywhere but the owner's machine. The section at the foot of this file is what still runs
the shipped `tannen.cli` against that rule at every commit.

Run with `TANNEN_NO_EVIDENCE=1` until M4's evidence refresh (D0227).
"""

from __future__ import annotations

import json
import re
import textwrap

import pytest

from tannen import cli
from tannen.executor import AlwaysRebuild, Built, Node, TraceStore, VerifyingTrace
from tannen.export import export
from tannen.kernel import ops
from tannen.kernel.layers import Layer, LayerError
from tannen.sources import ingest
from tannen.store import Store
from tannen.transform import transform

SOURCE = "sha256:" + "7e" * 32


def _k_positive(row) -> bool:
    return row["k"] > 0


@transform(kind="derive", params={"tests/test_export_cli": "select"})
def _served(rel):
    return ops.select(rel, _k_positive)


def _bench(tmp_path):
    store, traces = Store(tmp_path / "s"), TraceStore(tmp_path / "t")
    rel = ingest(store, SOURCE, ("k",), [{"k": 1}, {"k": -1}])
    return store, traces, Node(_served, (store.put_value(rel.to_value()),))


def test_a_serve_node_exports_exactly_its_output_bytes(tmp_path) -> None:
    store, traces, node = _bench(tmp_path)
    built = AlwaysRebuild().build(node, store, traces)
    assert built.layer is Layer.SERVE
    assert export(store, built) == store.get_bytes(built.output_ref)


def test_a_trace_hit_is_refused_because_nothing_ran(tmp_path) -> None:
    """A `VerifyingTrace` hit ran nothing, so its layer is unknown; exporting it would be
    trusting a layer nobody observed. Rebuild it to export it."""
    store, traces, node = _bench(tmp_path)
    AlwaysRebuild().build(node, store, traces)
    hit = VerifyingTrace().build(node, store, traces)
    assert hit.rebuilt is False and hit.layer is None
    with pytest.raises(LayerError, match="trace hit"):
        export(store, hit)


def test_a_node_that_quarantined_as_a_whole_is_refused(tmp_path) -> None:
    store, _, _ = _bench(tmp_path)
    quarantined = Built("sha256:" + "0" * 64, None, True, Layer.SERVE, frozenset({"select"}))
    with pytest.raises(LayerError, match="quarantined"):
        export(store, quarantined)


def test_export_takes_a_built(tmp_path) -> None:
    with pytest.raises(TypeError):
        export(Store(tmp_path / "s"), "sha256:" + "0" * 64)


# ------------------------------------------------------------------ tannen run

_TARGET = textwrap.dedent('''
    from tannen.oracles import Clock

    CALLS = []


    def _transport(request):
        CALLS.append(request)
        return {"instant": "2026-09-12T00:00:00Z"}


    def read_the_clock(oracles):
        clock = Clock("cli-clock", reproducibility="bit", transport=_transport,
                      unit="nano-usd", price=0)
        return oracles.invoke(clock, {"label": "cli"})


    def fail(oracles):
        raise RuntimeError("not one of the four refusals")
''')


def _target(tmp_path, monkeypatch, name: str) -> str:
    (tmp_path / f"{name}.py").write_text(_TARGET, encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    return name


def test_a_target_without_a_callable_is_a_usage_error(tmp_path, capsys) -> None:
    with pytest.raises(SystemExit) as exited:
        cli.main(["run", "a_module_only", "--store", str(tmp_path / "s")])
    assert exited.value.code == 2
    assert "MODULE:CALLABLE" in capsys.readouterr().err


def test_a_returned_capture_ref_is_printed(tmp_path, monkeypatch, capsys) -> None:
    """`--budget-override`, because the clamp (docs/specs/m5.md §6, D0263) made it the spelling
    for a budget the repository did not check in. The budget file was always incidental to this
    node's claim — that a returned capture ref reaches stdout — and only its spelling moved."""
    name = _target(tmp_path, monkeypatch, "cli_printed_target")
    budget = _elsewhere(tmp_path, 1)
    assert cli.main(["run", f"{name}:read_the_clock", "--store", str(tmp_path / "s"),
                     "--budget-override", str(budget), "--spend"]) == 0
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", capsys.readouterr().out.strip())


# ------------------------------------------------------------------ the clamp (L5.1, D0263)
#
# L5.1 is the frozen judge of this rule, and it SKIPS until an authorised corpus is present
# (D0259) — which, for the M5 dogfood, means on the owner's machine and never in CI. D0259
# stated that cost and named what holds the property meanwhile; what it named for the clamp is
# `tests/test_law_validation.py`'s model matrix, which runs the rule against the MODEL, and
# `tests/test_spend_preconditions.py`, which only asks whether the flag is DECLARED. Neither
# runs the shipped `tannen.cli`. These nodes do, at every commit, over a throwaway repository
# root — not a restatement of the frozen law but the part of it CI can still see.


def _repo_root(tmp_path, monkeypatch, ceiling: int):
    """A throwaway repository root: MANIFEST.sha256 is what `find_root` looks for, and
    budget.yaml beside it is the checked-in budget the clamp binds to."""
    root = tmp_path / "root"
    root.mkdir(exist_ok=True)
    (root / "MANIFEST.sha256").write_text("", encoding="utf-8")
    (root / "budget.yaml").write_text(
        json.dumps({"scope": "M5", "unit": "nano-usd",
                    "ceilings": {"total": ceiling, "clock": ceiling}}), encoding="utf-8")
    monkeypatch.chdir(root)
    return root


def _elsewhere(tmp_path, ceiling: int):
    """A budget file this repository did not check in."""
    path = tmp_path / "elsewhere" / "budget.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"scope": "M5", "unit": "nano-usd",
                                "ceilings": {"total": ceiling, "clock": ceiling}}),
                    encoding="utf-8")
    return path


def test_spend_with_no_flag_admits_against_the_checked_in_budget(tmp_path, monkeypatch,
                                                                 capsys) -> None:
    """`--spend` with no flag is no longer `--spend` with no budget: it is the repository's own
    budget.yaml at `find_root()`."""
    name = _target(tmp_path, monkeypatch, "cli_checked_in_target")
    _repo_root(tmp_path, monkeypatch, 10**6)
    assert cli.main(["run", f"{name}:read_the_clock", "--store", str(tmp_path / "s"),
                     "--spend"]) == 0
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", capsys.readouterr().out.strip())


def test_spend_against_a_zero_checked_in_budget_authorises_nothing(tmp_path, monkeypatch,
                                                                   capsys) -> None:
    """Admission is still L4.5's: a zero ceiling refuses even a zero-priced call. This is the
    state this repository is actually in — every ceiling in budget.yaml is zero — so it is the
    behaviour a `tannen run --spend` here gets today."""
    name = _target(tmp_path, monkeypatch, "cli_zero_checked_in_target")
    _repo_root(tmp_path, monkeypatch, 0)
    assert cli.main(["run", f"{name}:read_the_clock", "--store", str(tmp_path / "s"),
                     "--spend"]) == 1
    assert "SpendDenied" in capsys.readouterr().err


def test_a_budget_naming_another_file_is_refused_before_anything_is_touched(
        tmp_path, monkeypatch, capsys) -> None:
    """The clamp itself. The refusal names the flag that would have been legitimate, nothing is
    written, and the pipeline module is never even imported — which is what "before the
    transport" means when the transport lives in the caller's code."""
    import sys

    name = _target(tmp_path, monkeypatch, "cli_clamped_target")
    _repo_root(tmp_path, monkeypatch, 0)
    assert cli.main(["run", f"{name}:read_the_clock", "--store", str(tmp_path / "s"),
                     "--budget", str(_elsewhere(tmp_path, 10**6)), "--spend"]) == 1
    error = capsys.readouterr().err
    assert "SpendDenied" in error and "--budget-override" in error
    assert not (tmp_path / "s").exists(), "a refused run wrote to the store"
    assert name not in sys.modules, "a refused run imported the pipeline"


def test_the_checked_in_budget_may_be_named_explicitly(tmp_path, monkeypatch, capsys) -> None:
    """The clamp is about WHICH FILE, never about which spelling: `--budget` naming the
    checked-in file — here by a relative path, resolved — is the same admission as no flag."""
    name = _target(tmp_path, monkeypatch, "cli_named_checked_in_target")
    _repo_root(tmp_path, monkeypatch, 10**6)
    assert cli.main(["run", f"{name}:read_the_clock", "--store", str(tmp_path / "s"),
                     "--budget", "budget.yaml", "--spend"]) == 0
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", capsys.readouterr().out.strip())


def test_budget_override_spends_against_another_file_and_its_capture_replays(
        tmp_path, monkeypatch, capsys) -> None:
    """The claim L4.4's retired third node carried, under the spelling D0240 names: the
    checked-in budget authorises nothing, another file does, and what it captured replays with
    no `--spend` and no second call."""
    name = _target(tmp_path, monkeypatch, "cli_override_target")
    _repo_root(tmp_path, monkeypatch, 0)
    base = ["run", f"{name}:read_the_clock", "--store", str(tmp_path / "s")]
    assert cli.main(base + ["--budget-override", str(_elsewhere(tmp_path, 10**6)), "--spend"]) == 0
    first = capsys.readouterr().out.strip()
    assert cli.main(base) == 0, "a capture made under --spend did not replay without it"
    assert capsys.readouterr().out.strip() == first
    import sys

    assert len(sys.modules[name].CALLS) == 1, "the replay reached the transport"


def test_the_two_budget_flags_exclude_each_other(tmp_path, monkeypatch, capsys) -> None:
    name = _target(tmp_path, monkeypatch, "cli_both_flags_target")
    _repo_root(tmp_path, monkeypatch, 0)
    with pytest.raises(SystemExit) as exited:
        cli.main(["run", f"{name}:read_the_clock", "--store", str(tmp_path / "s"),
                  "--budget", "budget.yaml",
                  "--budget-override", str(_elsewhere(tmp_path, 1)), "--spend"])
    assert exited.value.code == 2
    assert "not allowed with" in capsys.readouterr().err


def test_without_spend_neither_budget_flag_is_consulted(tmp_path, monkeypatch, capsys) -> None:
    """A replay refuses a novel invocation whatever the flags name — including a `--budget` the
    clamp would refuse under `--spend`, and including one that does not exist. A clamp that
    fired here would turn every replay into a spend refusal."""
    name = _target(tmp_path, monkeypatch, "cli_replay_flags_target")
    _repo_root(tmp_path, monkeypatch, 0)
    assert cli.main(["run", f"{name}:read_the_clock", "--store", str(tmp_path / "s"),
                     "--budget", str(tmp_path / "no" / "such" / "budget.yaml")]) == 1
    assert "NovelInvocationRefused" in capsys.readouterr().err


def test_run_finds_a_module_in_the_working_directory(tmp_path, monkeypatch, capsys) -> None:
    """Run through the console script, sys.path[0] is the venv's bin directory; `tannen run
    pipeline:main` must still find the `pipeline.py` it is run beside (found in review)."""
    import sys

    (tmp_path / "cli_cwd_target.py").write_text(_TARGET, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "path", [p for p in sys.path if p not in ("", str(tmp_path))])
    assert cli.main(["run", "cli_cwd_target:read_the_clock", "--store", str(tmp_path / "s")]) == 1
    assert "NovelInvocationRefused" in capsys.readouterr().err


def test_a_failure_that_is_not_a_refusal_propagates(tmp_path, monkeypatch) -> None:
    name = _target(tmp_path, monkeypatch, "cli_failing_target")
    with pytest.raises(RuntimeError, match="not one of the four refusals"):
        cli.main(["run", f"{name}:fail", "--store", str(tmp_path / "s")])


def test_spend_outside_a_checkout_is_refused_even_with_a_budget_in_the_cwd(
        tmp_path, monkeypatch, capsys) -> None:
    """RT-M5-06: `find_root` falls back to the cwd, so outside a checkout the "checked-in"
    budget was whatever budget.yaml the cwd held, unreviewed and with no override flag."""
    name = _target(tmp_path, monkeypatch, "cli_outside_checkout_target")
    root = _repo_root(tmp_path, monkeypatch, 10**6)
    (root / "MANIFEST.sha256").unlink()
    assert cli.main(["run", f"{name}:read_the_clock", "--store", str(tmp_path / "s"),
                     "--spend"]) == 1
    assert "not inside a tannen checkout" in capsys.readouterr().err
    assert not (tmp_path / "s").exists(), "a refused run wrote to the store"
