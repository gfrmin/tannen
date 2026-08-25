"""M1 law L1.11 — raising is safe (docs/specs/m1.md §5; BRIEF P3, §5.4).

FROZEN at m1-laws-freeze. BRIEF §5.4's claim is that the LAZY path is the correct path: a
transform that just raises produces a quarantined row with provenance, and crashing the
pipeline is what requires an opt-out. This law is what makes that claim checkable.

The three edges that matter, and each has a plausible wrong answer:
  * a row-wise failure quarantines THE ROW, not the node;
  * a node that quarantines EVERY row is still `Ok` with an empty Rel — "empty" is a
    declared, distinguishable outcome (P3), not a failure;
  * `BaseException` is NOT caught, or a KeyboardInterrupt inside a transform would make
    the process unkillable.
"""

from __future__ import annotations

import operator

import pytest
from hypothesis import given, strategies as st

outcome_mod = pytest.importorskip(
    "tannen.kernel.outcome",
    reason="M1 outcome types not implemented yet (law suite frozen ahead of Session B)",
)
ops = pytest.importorskip("tannen.kernel.ops")
rel_mod = pytest.importorskip("tannen.kernel.rel")
semiring = pytest.importorskip("tannen.kernel.semiring")
algebra = pytest.importorskip("tannen.kernel.algebra")

Rel = rel_mod.Rel
Z = semiring.Z
WHY = "law fixture"
SUM_INT = algebra.Monoid("sum-int", operator.add, 0, (-3, -1, 0, 1, 2, 5))

QUARANTINE_SCHEMA = ("detail", "operator", "reason", "row")


def rel(pairs):
    return Rel(("k",), [({"k": k}, n) for k, n in pairs], annotations=Z, annotations_reason=WHY)


def boom(row):
    raise ValueError(f"no good: {row}")


def test_l1_11_the_quarantine_schema_is_the_pinned_one() -> None:
    assert outcome_mod.QUARANTINE_SCHEMA == QUARANTINE_SCHEMA


@given(st.sets(st.integers(min_value=0, max_value=6)), st.sets(st.integers(min_value=0, max_value=6)))
def test_l1_11_a_row_wise_failure_quarantines_the_row_not_the_node(keys, poisoned) -> None:
    source = rel([(k, 1) for k in sorted(keys)])
    doomed = keys & poisoned

    result = ops.select(source, lambda r: boom(r) if r["k"] in doomed else True)

    assert isinstance(result, outcome_mod.Ok), "a row-wise failure is not a node failure"
    assert {row["k"] for row, _ in result.rel} == keys - doomed
    assert len(result.quarantined) == len(doomed)
    assert result.quarantined.schema == QUARANTINE_SCHEMA


def test_l1_11_every_row_failing_is_still_ok_with_an_empty_rel() -> None:
    # "Empty" is a declared, distinguishable outcome (BRIEF P3) — not a Quarantine.
    result = ops.select(rel([(1, 1), (2, 1)]), boom)
    assert isinstance(result, outcome_mod.Ok)
    assert len(result.rel) == 0
    assert len(result.quarantined) == 2
    assert result.unwrap() == rel([])  # and it unwraps, because nothing failed at node level


def test_l1_11_an_empty_input_is_not_a_quarantine_either() -> None:
    result = ops.select(rel([]), boom)
    assert isinstance(result, outcome_mod.Ok)
    assert len(result.rel) == 0 and len(result.quarantined) == 0


@pytest.mark.parametrize(
    "call",
    [
        lambda source: ops.select(source, boom),
        lambda source: ops.map_rows(source, boom, ("k",)),
        lambda source: ops.aggregate(source, ("k",), SUM_INT, boom, "s"),
    ],
    ids=["select", "map_rows", "aggregate"],
)
def test_l1_11_every_operator_taking_a_user_function_quarantines_per_row(call) -> None:
    result = call(rel([(1, 1), (2, 1)]))
    assert isinstance(result, outcome_mod.Ok)
    assert len(result.quarantined) == 2


def test_l1_11_a_quarantine_row_carries_reason_and_provenance() -> None:
    result = ops.select(rel([(7, 1)]), boom)
    (row, annotation), = list(result.quarantined)
    assert set(row) == set(QUARANTINE_SCHEMA)
    assert row["operator"] == "select"
    assert row["row"] == {"k": 7}          # the offending row IS its own provenance
    assert isinstance(row["reason"], str) and row["reason"]
    assert "no good" in row["detail"]      # the exception is reported, not swallowed
    assert annotation == Z.one


def test_l1_11_a_wrongly_shaped_mapped_row_quarantines_rather_than_corrupting_the_schema() -> None:
    result = ops.map_rows(rel([(1, 1), (2, 1)]), lambda r: {"k": r["k"]} if r["k"] == 1 else {"z": 9}, ("k",))
    assert isinstance(result, outcome_mod.Ok)
    assert result.rel.schema == ("k",)
    assert len(result.rel) == 1 and len(result.quarantined) == 1


@pytest.mark.parametrize("escaping", [KeyboardInterrupt, SystemExit, GeneratorExit])
def test_l1_11_base_exception_is_not_caught(escaping) -> None:
    # Wrapping these would make a transform impossible to interrupt. Only `Exception` is
    # a data error; `BaseException` is a control-flow signal (docs/specs/m1.md §5).
    def raise_base(row):
        raise escaping()

    with pytest.raises(escaping):
        ops.select(rel([(1, 1)]), raise_base)


def test_l1_11_a_quarantine_input_propagates_and_names_its_upstream() -> None:
    failed = ops.select(rel([(1, 1)]), lambda r: (_ for _ in ()).throw(RuntimeError("x")))
    node_failure = outcome_mod.Quarantine("upstream-failed", "the node before this one", ())
    for call in (
        lambda: ops.select(node_failure, lambda r: True),
        lambda: ops.project(node_failure, ("k",)),
        lambda: ops.distinct(node_failure),
        lambda: ops.union(node_failure, rel([])),
        lambda: ops.union(rel([]), node_failure),
        lambda: ops.join(node_failure, rel([]), ("k",)),
    ):
        result = call()
        assert isinstance(result, outcome_mod.Quarantine)
        assert "upstream-failed" in (result.reason + result.detail)
    assert isinstance(failed, outcome_mod.Ok)  # a row-wise failure is NOT node-level


def test_l1_11_quarantined_rows_union_through_the_pure_operators() -> None:
    # A quarantine raised in `decode` must not vanish when the row set is later projected.
    first = ops.select(rel([(1, 1), (2, 1)]), lambda r: boom(r) if r["k"] == 1 else True)
    carried = ops.project(first, ("k",))
    assert isinstance(carried, outcome_mod.Ok)
    assert len(carried.quarantined) == 1


def test_l1_11_unwrap_raises_on_a_node_quarantine_and_returns_the_rel_otherwise() -> None:
    assert ops.select(rel([(1, 1)]), lambda r: True).unwrap() == rel([(1, 1)])
    with pytest.raises(outcome_mod.QuarantineError):
        outcome_mod.Quarantine("nope", "detail", ()).unwrap()
