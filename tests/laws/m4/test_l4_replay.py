"""M4 law L4.12 — replay determinism at the boundary. BRIEF §6's L1, with the world in it
(docs/specs/m4.md §3; BRIEF P1, §5.7, §5.10).

FROZEN at m4-laws-freeze.

"Fixed captures + descriptors ⇒ byte-identical outputs, incl. fresh interpreter with
randomized hash seed." L1.15 proved it for a pipeline with no oracle; this is the claim the
boundary exists to make true for one that has three. A store is seeded once, in spend mode,
through fake transports; then fresh interpreters with randomised hash seeds — default mode,
every transport one that aborts the process if touched — replay every invocation, read
every value back, and derive a relation from what they read. Every run prints the same
bytes, the captures are the seeded ones, and a question nobody captured is refused because
replay-only is the default in a fresh interpreter too.
"""

from __future__ import annotations

import importlib.util as _ilu
import json
import subprocess
import sys
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

from tannen import oracles  # noqa: E402
from tannen.store import Store  # noqa: E402

REPO_ROOT = _Path(__file__).resolve().parents[3]
RUNS = 3

VALIDATION_REASON = (
    "replay across interpreters is machinery — the store, the codec and the process "
    "boundary — and a model of it would BE the implementation (the L1.15 and L2.8 "
    "precedent). The invocation policy it rests on is L4.2-L4.5's, model-checked."
)

PLAN = [[kind, M.spec_for(kind, 1, 1), [M.requests_for(kind, i) for i in range(2)]]
        for kind in M.KINDS]
BUDGET = {"scope": "M4", "unit": "nano-usd",
          "ceilings": {"total": 10**12, "fetch": 10**12, "llm": 10**12, "clock": 10**12}}
_CLASSES = {"fetch": oracles.Fetch, "llm": oracles.LLM, "clock": oracles.Clock}

_REPLAY = r'''
import json, sys
from tannen import oracles, sources
from tannen.kernel import ops
from tannen.store import Store

root, plan = sys.argv[1], json.loads(sys.argv[2])
CLASSES = {"fetch": oracles.Fetch, "llm": oracles.LLM, "clock": oracles.Clock}


def refuse(request):
    raise SystemExit("L4.12: a replay reached the transport")


store = Store(root)
context = oracles.Oracles(store)
refs, reads, rows = [], [], []
for kind, spec, requests in plan:
    oracle = CLASSES[kind]("m4-replay-" + kind, reproducibility="non-reproducible",
                           transport=refuse, **spec)
    for request in requests:
        ref = context.invoke(oracle, request)
        value = dict(context.read(ref))
        if isinstance(value.get("body"), bytes):
            value["body"] = value["body"].hex()
        refs.append(ref)
        reads.append(value)
        rows.append({"k": len(rows), "x": len(json.dumps(value, sort_keys=True))})
rel = sources.ingest(store, "sha256:" + "5a" * 32, ("k", "x"), rows)
derived = ops.select(rel, lambda row: row["x"] > 0).unwrap()
derived_ref = store.put_value(derived.to_value())
print(json.dumps({"refs": refs, "reads": reads, "derived": derived_ref,
                  "bytes": store.get_bytes(derived_ref).decode("utf-8")}, sort_keys=True))
'''


@pytest.fixture(scope="module")
def seeded(tmp_path_factory):
    root = tmp_path_factory.mktemp("m4-replay") / "store"
    store = Store(root)
    context = oracles.Oracles(store, mode=oracles.SPEND, budget=oracles.load_budget(BUDGET))
    refs = []
    for kind, spec, requests in PLAN:
        oracle = _CLASSES[kind]("m4-replay-" + kind, reproducibility="non-reproducible",
                                transport=M.FakeTransport(kind), **spec)
        refs.extend(context.invoke(oracle, request) for request in requests)
    return root, refs


def _run(root, plan) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", _REPLAY, str(root), json.dumps(plan)],
        cwd=REPO_ROOT, env={"PYTHONHASHSEED": "random", "PATH": ""},
        capture_output=True, text=True, check=False,
    )


def test_l4_12_fresh_interpreters_with_random_hash_seeds_replay_byte_for_byte(seeded) -> None:
    root, _ = seeded
    runs = [_run(root, PLAN) for _ in range(RUNS)]
    for run in runs:
        assert run.returncode == 0, run.stderr
    outputs = {run.stdout for run in runs}
    assert len(outputs) == 1, f"replay diverged across interpreters:\n{outputs}"


def test_l4_12_the_replay_serves_exactly_the_seeded_captures(seeded) -> None:
    root, refs = seeded
    run = _run(root, PLAN)
    assert run.returncode == 0, run.stderr
    assert json.loads(run.stdout)["refs"] == refs


def test_l4_12_a_fresh_interpreter_is_replay_only(seeded) -> None:
    root, _ = seeded
    novel = [[kind, spec, [M.requests_for(kind, 9)]] for kind, spec, _ in PLAN[:1]]
    run = _run(root, novel)
    assert run.returncode != 0
    assert "NovelInvocationRefused" in run.stderr, run.stderr
    assert "reached the transport" not in run.stderr, "the refusal came after the call"


def test_l4_12_the_derivation_actually_produced_rows(seeded) -> None:
    """A determinism law over an empty result would pass while proving nothing."""
    root, _ = seeded
    replayed = json.loads(_run(root, PLAN).stdout)
    assert '"rows":[[' in replayed["bytes"], replayed["bytes"]
