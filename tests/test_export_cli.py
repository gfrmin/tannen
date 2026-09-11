"""`tannen.export` and `tannen run` — what frozen L4.10 and L4.4 leave open (docs/specs/m4.md
§1, §7; decision D0237).

L4.10 drives the export door over the model's catalogue through `AlwaysRebuild`; L4.4 drives
`tannen run`'s three spellings. Decided here: that the two `Built`s with nothing honest to
say — a trace hit (nothing ran, so no layer) and a whole-node quarantine (no output) — are
refused rather than exported, and the command line's ergonomics: a malformed target is a
usage error, `--spend` with no budget authorises nothing, a returned capture ref is printed,
and a failure that is not one of the four named refusals is not swallowed into an exit code.

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


def test_spend_without_a_budget_authorises_nothing(tmp_path, monkeypatch, capsys) -> None:
    name = _target(tmp_path, monkeypatch, "cli_no_budget_target")
    assert cli.main(["run", f"{name}:read_the_clock", "--store", str(tmp_path / "s"),
                     "--spend"]) == 1
    assert "SpendDenied" in capsys.readouterr().err


def test_a_returned_capture_ref_is_printed(tmp_path, monkeypatch, capsys) -> None:
    name = _target(tmp_path, monkeypatch, "cli_printed_target")
    budget = tmp_path / "budget.yaml"
    budget.write_text(json.dumps({"scope": "M4", "unit": "nano-usd",
                                  "ceilings": {"total": 1, "clock": 1}}), encoding="utf-8")
    assert cli.main(["run", f"{name}:read_the_clock", "--store", str(tmp_path / "s"),
                     "--budget", str(budget), "--spend"]) == 0
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", capsys.readouterr().out.strip())


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
