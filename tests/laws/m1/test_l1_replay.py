"""M1 law L1.15 — replay determinism. This is BRIEF §6's **L1**, at full scope.

FROZEN at m1-laws-freeze. M0's L0.8 was explicitly "L1's mechanism at M0 scope": one
subprocess, reproducing golden encodings. This is the real one — fixed inputs and
descriptors through the whole executor, in fresh interpreters with randomised hash seeds,
producing byte-identical output.

The fixture is chosen to make hash-order dependence REACHABLE rather than theoretical. It
runs under `ℤ × Why`, whose annotations are frozensets of frozensets: iteration order over
a set of strings varies with `PYTHONHASHSEED`, so any place the implementation lets set
order leak into bytes — a `Why` encoding, a row ordering, a canonical form — diverges here
and nowhere else. `Rel` also merges rows by canonical encoding, so dict ordering is in
scope too.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip(
    "tannen.executor",
    reason="M1 executor not implemented yet (law suite frozen ahead of Session B)",
)
pytest.importorskip("tannen.kernel.ops")

REPO_ROOT = Path(__file__).resolve().parents[3]
RUNS = 3

_REPLAY = r'''
import json, tempfile
from tannen.executor import AlwaysRebuild, Node, TraceStore
from tannen.kernel import ops
from tannen.kernel.rel import Rel
from tannen.kernel.semiring import Why
from tannen.store import Store
from tannen.transform import transform

REFS = [f"sha256:{c * 64}" for c in "0123456789ab"]


@transform(kind="derive", params={"threshold": 0})
def pipeline(left, right):
    joined = ops.join(left, right, ("k",))
    kept = ops.select(joined, lambda row: row["k"] >= 0)
    return ops.distinct(kept)


def why(*atoms):
    # Several support sets of several atoms: the frozenset iteration order this produces
    # is exactly what a randomised hash seed perturbs.
    return Why.of(*({REFS[i], REFS[j]} for i, j in atoms))


LEFT = Rel(
    ("k", "x"),
    [
        ({"k": 3, "x": "a"}, (2, why((0, 1), (2, 3), (4, 5)))),
        ({"k": -1, "x": "b"}, (1, why((1, 2)))),
        ({"k": 0, "x": "c"}, (4, why((5, 6), (7, 8), (9, 10), (0, 11)))),
        ({"k": 3, "x": "a"}, (1, why((6, 7)))),
    ],
)
RIGHT = Rel(
    ("k", "y"),
    [
        ({"k": 3, "y": 1}, (3, why((2, 4), (8, 9)))),
        ({"k": 0, "y": 2}, (1, why((3, 5), (1, 7), (0, 10)))),
    ],
)

with tempfile.TemporaryDirectory() as scratch:
    store = Store(scratch + "/store")
    traces = TraceStore(scratch + "/traces")
    inputs = (store.put_value(LEFT.to_value()), store.put_value(RIGHT.to_value()))
    built = AlwaysRebuild().build(Node(pipeline, inputs), store, traces)
    print(json.dumps({
        "descriptor": pipeline.descriptor_id,
        "code_hash": pipeline.code_hash,
        "params_hash": pipeline.params_hash,
        "inputs": list(inputs),
        "derivation_id": built.derivation_id,
        "output_ref": built.output_ref,
        "output_bytes": store.get_bytes(built.output_ref).decode("utf-8"),
    }, sort_keys=True))
'''


def _run() -> str:
    result = subprocess.run(
        [sys.executable, "-c", _REPLAY],
        cwd=REPO_ROOT,
        env={"PYTHONHASHSEED": "random", "PATH": ""},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_l1_15_fresh_interpreters_with_random_hash_seeds_agree_byte_for_byte() -> None:
    outputs = [_run() for _ in range(RUNS)]
    assert len(set(outputs)) == 1, (
        "replay diverged across interpreters with randomised hash seeds — some set or dict "
        f"iteration order is reaching the bytes:\n{outputs}"
    )


def test_l1_15_the_replayed_output_is_the_content_address_of_its_own_bytes() -> None:
    from tannen.kernel.refs import ref_for_bytes

    replayed = json.loads(_run())
    assert ref_for_bytes(replayed["output_bytes"].encode("utf-8")) == replayed["output_ref"]


def test_l1_15_descriptors_are_stable_across_interpreters() -> None:
    # "Fixed captures AND DESCRIPTORS": a descriptor that moved between runs would make
    # every evidence record's freshness claim meaningless.
    replayed = [json.loads(_run()) for _ in range(RUNS)]
    for key in ("descriptor", "code_hash", "params_hash", "derivation_id", "inputs"):
        assert len({json.dumps(run[key], sort_keys=True) for run in replayed}) == 1, key


def test_l1_15_the_join_actually_produced_rows() -> None:
    # A determinism law over an empty result would pass while proving nothing.
    replayed = json.loads(_run())
    assert '"rows":[[' in replayed["output_bytes"], replayed["output_bytes"]
