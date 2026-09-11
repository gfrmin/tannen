"""M4 law L4.23 — a declared node names its code by content address (RT-M3-01;
docs/specs/m4.md §8; docs/specs/m3-corrections.md §1; BRIEF §5.1).

FROZEN at m4-laws-freeze.

RT-M3-01 (critical): a `DeltaNode` named its code by string, so two processes registering
different predicates under one name minted one descriptor and one `step_id`, and a trace
served the first's answer to the second with `rebuilt=False`. D0197 closed the predicate
half in unfrozen code; nothing frozen pinned it, and the map half is still open: a
`map_rows` node's registered OUT-SCHEMA is resolved from the registry at tick time and
appears in no descriptor (m3-corrections.md §1). The corrected rule is normative: the
declared form carries the content address of ANY code a parameter names — a predicate, a
map and the schema it declares, a monoid or group with its identity and witnesses — and a
callable with no addressable source is refused.

Same name, different code is only observable ACROSS interpreters — within one, re-registering
a name is refused outright — so the identity clauses run each variant in a fresh interpreter
(the L1.15 precedent) and compare the descriptors they print.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("tannen.oracles", reason=(
    "M4 boundary not implemented yet (law suite frozen ahead of Session B); M4's laws go "
    "live together — docs/specs/m4.md §11"))
incremental = pytest.importorskip("tannen.incremental")

from tannen.kernel.outcome import OperatorError  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]

VALIDATION_REASON = (
    "descriptor identity is machinery — the registry, the source hash and the declared "
    "form — and a model of it would BE the implementation (D0094 §3). What it protects is "
    "the one-derivation-one-output property L4.21 and L1.14 rest on."
)

_PROBE = r'''
import json, sys
from tannen.incremental import DeltaNode, register_map, register_monoid, register_predicate
from tannen.kernel.algebra import Monoid

variant = sys.argv[1]

if variant == "body":
    def l4_23_probe(row):
        return row["x"] > 1
else:
    def l4_23_probe(row):
        return row["x"] > 0


def l4_23_map(row):
    return {"k": row["k"]}


def l4_23_add(a, b):
    return a + b


register_predicate("l4-23-probe", l4_23_probe)
register_map("l4-23-map", l4_23_map, ("key",) if variant == "schema" else ("k",))
witnesses = tuple(range(-3, 4)) if variant == "witnesses" else tuple(range(-6, 7))
register_monoid("l4-23-sum", Monoid("l4-23-sum", l4_23_add, 0, witnesses=witnesses))
print(json.dumps({
    "select": DeltaNode("select", predicate_id="l4-23-probe").descriptor,
    "map_rows": DeltaNode("map_rows", map_id="l4-23-map").descriptor,
    "aggregate": DeltaNode("aggregate", by=("k",), column="x", into="s",
                           monoid_id="l4-23-sum").descriptor,
}, sort_keys=True))
'''


def _descriptors(variant: str) -> dict:
    result = subprocess.run(
        [sys.executable, "-c", _PROBE, variant], cwd=REPO_ROOT,
        env={"PYTHONHASHSEED": "random", "PATH": ""},
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_l4_23_the_same_declared_code_is_the_same_node_in_every_interpreter() -> None:
    assert _descriptors("base") == _descriptors("base")


def test_l4_23_a_different_predicate_under_one_name_is_a_different_node() -> None:
    base, moved = _descriptors("base"), _descriptors("body")
    assert moved["select"] != base["select"], (
        "two predicates with different bodies under one registered name minted one "
        "descriptor — RT-M3-01, the trace would serve one's answer to the other")
    assert moved["map_rows"] == base["map_rows"] and moved["aggregate"] == base["aggregate"]


def test_l4_23_a_different_map_out_schema_under_one_name_is_a_different_node() -> None:
    base, moved = _descriptors("base"), _descriptors("schema")
    assert moved["map_rows"] != base["map_rows"], (
        "one map body declared with two different out-schemas minted one descriptor — the "
        "schema is resolved from the registry at tick time and is in no descriptor "
        "(m3-corrections.md §1, the residue D0197 left open)")
    assert moved["select"] == base["select"]


def test_l4_23_a_different_fold_under_one_name_is_a_different_node() -> None:
    base, moved = _descriptors("base"), _descriptors("witnesses")
    assert moved["aggregate"] != base["aggregate"]
    assert moved["select"] == base["select"]


def test_l4_23_a_lambda_is_refused_at_registration() -> None:
    with pytest.raises(OperatorError):
        incremental.register_predicate("l4-23-lambda", lambda row: True)
    assert "l4-23-lambda" not in incremental.PREDICATES
