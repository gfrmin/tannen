"""tannen on the stand — the IMPLEMENTATION half of M5's model-checked laws
(docs/specs/m5.md §10). FROZEN at m5-laws-freeze.

`_dogfood_model.py` holds the checks; this file puts the shipped package behind the same
interface. It is loaded by `_dogfood_bind.m5()` under a private name and handed the model by
`make(M)`. `TannenSubject` deliberately does NOT subclass the model's `Subject`: `make` checks
`REQUIRED` against this class's own `__dict__`, so a missing method is a hole here and never a
silent fallback to model code (the m2/m3/m4 rule, verbatim).

Every module new at M5 is importorskip'd, so a half-landed Session B sees skips, never a
collection error that aborts the run. The surface it pins is docs/specs/m5.md §1:

  tannen.cli       `tannen run MODULE:CALLABLE --store PATH [--budget PATH | --budget-override
                   PATH] [--spend]`, clamped to the checked-in budget.yaml at `find_root()`
  tannen.dogfood   select(measurement) -> source; SelectionRefused;
                   compare(store, corpus, outputs) -> [divergence/1 values]; IncompleteRun
"""

from __future__ import annotations

import atexit
import contextlib
import importlib
import io
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest

_SENTINEL = ("M5 dogfood not implemented yet (law suite frozen ahead of Session B); M5's laws "
             "go live together — docs/specs/m5.md §8")

dogfood = pytest.importorskip("tannen.dogfood", reason=_SENTINEL)
cli = pytest.importorskip("tannen.cli")
ops = pytest.importorskip("tannen.kernel.ops")
refs = pytest.importorskip("tannen.kernel.refs")
store_mod = pytest.importorskip("tannen.store")

_SCRATCH = tempfile.mkdtemp(prefix="tannen-m5-laws-")
atexit.register(shutil.rmtree, _SCRATCH, True)

_TARGET = '''
from tannen.oracles import Clock

CALLS = []


def _transport(request):
    CALLS.append(request)
    return {"instant": "2026-09-15T00:00:00Z"}


def pipeline(oracles):
    clock = Clock("m5-clamp-clock", reproducibility="non-reproducible",
                  transport=_transport, unit="nano-usd", price=0)
    return oracles.invoke(clock, {"label": "clamp"})
'''

_COUNTER = [0]


def _budget(path: Path, ceiling: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"scope": "M5", "unit": "nano-usd",
                                "ceilings": {"total": ceiling, "clock": ceiling}}),
                    encoding="utf-8")
    return path


def _main(argv: list[str], cwd: Path) -> tuple[int, str]:
    err = io.StringIO()
    here = os.getcwd()
    os.chdir(cwd)
    try:
        with contextlib.redirect_stderr(err):
            try:
                code = cli.main(argv)
            except SystemExit as exc:  # argparse's usage errors
                code = exc.code if isinstance(exc.code, int) else 2
    finally:
        os.chdir(here)
    return code, err.getvalue()


class TannenSubject:
    """The shipped package behind the model's `Subject` interface."""

    name = "tannen"
    selection_refused = dogfood.SelectionRefused
    incomplete_run = dogfood.IncompleteRun
    catalogue = ops.OPERATORS

    # -- the clamp (§6)
    def run_cli(self, spend: bool, flag: str | None, checked_in: int, other: int) -> list[dict]:
        """A throwaway repository root (MANIFEST.sha256 + a checked-in budget.yaml), a second
        budget file elsewhere, a pipeline module beside them, and `tannen run` from that root:
        the scenario, then a plain replay over the same store."""
        _COUNTER[0] += 1
        root = Path(tempfile.mkdtemp(dir=_SCRATCH))
        (root / "MANIFEST.sha256").write_text("", encoding="utf-8")
        checked = _budget(root / "budget.yaml", checked_in)
        elsewhere = _budget(root / "elsewhere" / "budget.yaml", other)
        module = f"m5_l5_1_clamp_{_COUNTER[0]}"
        (root / f"{module}.py").write_text(_TARGET, encoding="utf-8")
        store = root / "store"
        base = ["run", f"{module}:pipeline", "--store", str(store)]
        flags = {None: [], "budget-checked-in": ["--budget", str(checked)],
                 "budget-other": ["--budget", str(elsewhere)],
                 "override-other": ["--budget-override", str(elsewhere)],
                 "both": ["--budget", str(elsewhere), "--budget-override", str(elsewhere)]}[flag]
        sys.path.insert(0, str(root))
        try:
            outcomes = []
            for argv in (base + flags + (["--spend"] if spend else []), base):
                code, stderr = _main(argv, root)
                loaded = sys.modules.get(module)
                outcomes.append({
                    "code": code, "stderr": stderr,
                    "calls": len(loaded.CALLS) if loaded is not None else 0,
                    "wrote": store.exists() and any(p.is_file() for p in store.rglob("*")),
                })
            return outcomes
        finally:
            sys.path.remove(str(root))
            sys.modules.pop(module, None)
            importlib.invalidate_caches()

    # -- selection (§2)
    def select(self, measurement: dict) -> str:
        return dogfood.select(measurement)

    # -- the comparator (§4, §5)
    def ref_of(self, data: bytes) -> str:
        return refs.ref_for_bytes(data)

    def compare_cases(self, cases: list, omit: str | None = None) -> list[dict]:
        store = store_mod.Store(tempfile.mkdtemp(dir=_SCRATCH))
        items = []
        outputs = {}
        for item_id, production, tannen in cases:
            items.append({"id": item_id,
                          "input": store.put_bytes(b"input:" + item_id.encode()),
                          "production_output": store.put_bytes(production)})
            if item_id != omit:
                outputs[item_id] = store.put_bytes(tannen)
        corpus = {"tannen": "corpus/1", "vertical": "synthetic", "pipeline": "synthetic:run",
                  "authorisation": "decisions/0000-synthetic.yaml", "items": items}
        return list(dogfood.compare(store, corpus, outputs))


def make(model: Any) -> TannenSubject:
    """The tannen subject, checked against the model's `REQUIRED` list."""
    missing = [name for name in model.REQUIRED if name not in vars(TannenSubject)]
    assert not missing, (
        f"TannenSubject does not define {missing} — it does not inherit from the model's "
        "Subject on purpose, so a missing method is a hole here and never a silent fallback "
        "to the model")
    return TannenSubject()
