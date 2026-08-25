"""M1 laws L1.7–L1.9 — the operator algebra (docs/specs/m1.md §4, §4.2, §4.4).

FROZEN at m1-laws-freeze.

L1.7 is the type rules: every ill-typed call refused BY NAME, never silently repaired.
L1.8 is the identities each operator ships (BRIEF §4).
L1.9 is the two properties that make the L6 mapping meaningful before DuckDB is involved:
the non-negative cone is closed, and the Why component is inert on the data.
"""

from __future__ import annotations

import operator

import pytest
from hypothesis import given, strategies as st

ops = pytest.importorskip(
    "tannen.kernel.ops",
    reason="M1 operators not implemented yet (law suite frozen ahead of Session B)",
)
rel_mod = pytest.importorskip("tannen.kernel.rel")
semiring = pytest.importorskip("tannen.kernel.semiring")
algebra = pytest.importorskip("tannen.kernel.algebra")

import _fragment as F  # noqa: E402  (frozen beside this file; see docs/specs/m1.md §11)

Rel = rel_mod.Rel
Z, Why, ZxWhy = semiring.Z, semiring.Why, semiring.ZxWhy
WHY = "law fixture: this suite is about this semiring"
R1 = "sha256:" + "11" * 32
SUM_INT = algebra.Monoid("sum-int", operator.add, 0, (-3, -1, 0, 1, 2, 5))


class _NoBagStructure:
    """ℤ's algebra with the `BagSemiring` methods deliberately ABSENT.

    A perfectly good commutative semiring that simply does not declare `multiplicity` or
    `collapse`. The law is about the absence being detected at the call (docs/specs/m1.md
    §2.1), not about exotic algebra — so the algebra here is the one already known good.
    """

    name = "NoBag"
    zero = 0
    one = 1
    add = staticmethod(operator.add)
    mul = staticmethod(operator.mul)
    encode = staticmethod(lambda a: a)


NO_BAG = _NoBagStructure()


def _ann(S, n: int):
    return (n, Why.of({R1})) if S.name == "Z*Why" else n


def rel(schema, pairs, S=Z):
    rows = [(row, _ann(S, n)) for row, n in pairs]
    if S.name == rel_mod.DEFAULT_ANNOTATIONS.name:
        return Rel(schema, rows)
    return Rel(schema, rows, annotations=S, annotations_reason=WHY)


def table(name: str, pairs, S=Z):
    return rel(F.TABLES[name], pairs, S)


SEMIRINGS = [Z, ZxWhy]
SEMIRING_IDS = ["Z", "Z*Why"]
over_semirings = pytest.mark.parametrize("S", SEMIRINGS, ids=SEMIRING_IDS)


# ------------------------------------------------------------------- L1.7 type rules


@pytest.mark.parametrize(
    ("call", "why"),
    [
        (lambda: ops.project(table("a", []), ("nope",)), "column not in schema"),
        (lambda: ops.project(table("a", []), ()), "empty projection"),
        (lambda: ops.project(table("a", []), ("k", "k")), "duplicate column"),
        (lambda: ops.union(table("a", []), table("b", [])), "different schemas"),
        (lambda: ops.join(table("a", []), table("c", []), ("k",)), "non-key column clash: x"),
        (lambda: ops.join(table("a", []), table("b", []), ()), "empty join key"),
        (lambda: ops.join(table("a", []), table("b", []), ("nope",)), "join key in neither"),
        (lambda: ops.join(table("a", []), table("b", []), ("x",)), "join key not in both"),
        (lambda: ops.anti_join(table("a", []), table("b", []), ()), "empty anti-join key"),
        (lambda: ops.anti_join(table("a", []), table("b", []), ("x",)), "anti key not in both"),
        (lambda: ops.aggregate(table("a", []), (), SUM_INT, lambda r: 1, "s"), "empty by"),
        (lambda: ops.aggregate(table("a", []), ("k",), SUM_INT, lambda r: 1, "k"), "into collides with by"),
        (lambda: ops.aggregate(table("a", []), ("nope",), SUM_INT, lambda r: 1, "s"), "by not in schema"),
        (lambda: ops.aggregate(table("a", []), ("k",), object(), lambda r: 1, "s"), "not a Monoid"),
        (lambda: ops.map_rows(table("a", []), lambda r: r, ()), "empty declared schema"),
    ],
    ids=[
        "project-missing", "project-empty", "project-duplicate", "union-schemas",
        "join-clash", "join-empty-on", "join-unknown-on", "join-one-sided-on",
        "anti-empty-on", "anti-one-sided-on", "aggregate-empty-by", "aggregate-into-in-by",
        "aggregate-unknown-by", "aggregate-not-a-monoid", "map-empty-schema",
    ],
)
def test_l1_7_ill_typed_calls_are_refused_by_name(call, why) -> None:
    with pytest.raises(ops.OperatorError):
        call()


def test_l1_7_mixing_semirings_is_refused() -> None:
    z_side = table("a", [({"k": 1, "x": 1}, 1)], Z)
    default_side = table("a", [({"k": 1, "x": 1}, 1)], ZxWhy)
    for call in (
        lambda: ops.union(z_side, default_side),
        lambda: ops.join(z_side, table("b", [], ZxWhy), ("k",)),
        lambda: ops.anti_join(z_side, table("b", [], ZxWhy), ("k",)),
    ):
        with pytest.raises(ops.OperatorError):
            call()


def test_l1_7_bag_operators_refuse_a_semiring_without_bag_structure() -> None:
    # distinct, aggregate and the bag image need structure a commutative semiring does not
    # have. Refused at the call, by name — never silently coerced (docs/specs/m1.md §2.1).
    assert not semiring.is_bag_semiring(NO_BAG)
    bare = Rel(("k", "x"), [({"k": 1, "x": 2}, 1)], annotations=NO_BAG, annotations_reason=WHY)
    with pytest.raises(ops.OperatorError):
        ops.distinct(bare)
    with pytest.raises(ops.OperatorError):
        ops.aggregate(bare, ("k",), SUM_INT, lambda r: r["x"], "s")
    with pytest.raises(ops.OperatorError):
        bare.to_bag()
    # ... and the operators that need only a Semiring still work over it.
    assert ops.union(bare, bare).unwrap().get({"k": 1, "x": 2}) == 2


@over_semirings
def test_l1_7_well_typed_calls_return_the_declared_schema(S) -> None:
    a = table("a", [({"k": 1, "x": 2}, 1)], S)
    b = table("b", [({"k": 1, "y": 3}, 1)], S)
    assert ops.select(a, lambda r: True).unwrap().schema == ("k", "x")
    assert ops.project(a, ("k",)).unwrap().schema == ("k",)
    assert ops.union(a, a).unwrap().schema == ("k", "x")
    assert ops.join(a, b, ("k",)).unwrap().schema == ("k", "x", "y")
    assert ops.distinct(a).unwrap().schema == ("k", "x")
    assert ops.anti_join(a, b, ("k",)).unwrap().schema == ("k", "x")
    assert ops.aggregate(a, ("k",), SUM_INT, lambda r: r["x"], "s").unwrap().schema == ("k", "s")
    assert ops.map_rows(a, lambda r: {"z": r["k"]}, ("z",)).unwrap().schema == ("z",)


def test_l1_7_join_emits_one_copy_of_each_key_column() -> None:
    # USING-style, matching the SQL image of docs/specs/m1.md §10.
    a = table("a", [({"k": 1, "x": 2}, 1)])
    b = table("b", [({"k": 1, "y": 3}, 1)])
    joined = ops.join(a, b, ("k",)).unwrap()
    assert joined.schema == ("k", "x", "y")
    assert joined.get({"k": 1, "x": 2, "y": 3}) == 1


# ------------------------------------------------------------------- L1.8 identities


@over_semirings
@given(F.table_rows("a"), F.table_rows("c"))
def test_l1_8_union_is_commutative_and_associative_with_empty_as_identity(S, left, right) -> None:
    a, c = table("a", left, S), table("c", right, S)
    empty = table("a", [], S)
    assert ops.union(a, c).unwrap() == ops.union(c, a).unwrap()
    assert ops.union(a, empty).unwrap() == a
    assert ops.union(empty, a).unwrap() == a
    assert (
        ops.union(ops.union(a, c), empty).unwrap() == ops.union(a, ops.union(c, empty)).unwrap()
    )


@over_semirings
@given(F.table_rows("a"), F.table_rows("b"))
def test_l1_8_join_is_commutative_up_to_schema(S, left, right) -> None:
    a, b = table("a", left, S), table("b", right, S)
    assert ops.join(a, b, ("k",)).unwrap() == ops.join(b, a, ("k",)).unwrap()


@over_semirings
@given(F.table_rows("a"), F.table_rows("b"), F.table_rows("d"))
def test_l1_8_join_is_associative(S, left, middle, right) -> None:
    a, b, d = table("a", left, S), table("b", middle, S), table("d", right, S)
    lhs = ops.join(ops.join(a, b, ("k",)), d, ("k",)).unwrap()
    rhs = ops.join(a, ops.join(b, d, ("k",)), ("k",)).unwrap()
    assert lhs == rhs


@over_semirings
@given(F.table_rows("a"), F.table_rows("c"), F.table_rows("b"))
def test_l1_8_join_distributes_over_union(S, left, other, right) -> None:
    a, c, b = table("a", left, S), table("c", other, S), table("b", right, S)
    lhs = ops.join(ops.union(a, c), b, ("k",)).unwrap()
    rhs = ops.union(ops.join(a, b, ("k",)), ops.join(c, b, ("k",))).unwrap()
    assert lhs == rhs


@over_semirings
@given(F.table_rows("a"))
def test_l1_8_filter_fusion(S, rows) -> None:
    a = table("a", rows, S)
    p, q = (lambda r: r["x"] > 0), (lambda r: r["k"] != 0)
    fused = ops.select(a, lambda r: p(r) and q(r)).unwrap()
    assert ops.select(ops.select(a, p), q).unwrap() == fused
    assert ops.select(ops.select(a, q), p).unwrap() == fused


@over_semirings
@given(F.table_rows("d"))
def test_l1_8_project_composition(S, rows) -> None:
    # π_C ∘ π_D ≡ π_C for C ⊆ D, and projection SUMS (bag semantics).
    d = table("d", rows, S)
    assert ops.project(ops.project(d, ("f", "k")), ("k",)).unwrap() == ops.project(d, ("k",)).unwrap()
    assert ops.project(d, d.schema).unwrap() == d


@over_semirings
@given(F.table_rows("a"))
def test_l1_8_distinct_is_idempotent(S, rows) -> None:
    a = table("a", rows, S)
    once = ops.distinct(a).unwrap()
    assert ops.distinct(once).unwrap() == once
    for _, annotation in once:
        assert S.multiplicity(annotation) in (0, 1)


@over_semirings
@given(F.table_rows("a"))
def test_l1_8_anti_join_against_empty_is_the_identity(S, rows) -> None:
    a, empty_b = table("a", rows, S), table("b", [], S)
    assert ops.anti_join(a, empty_b, ("k",)).unwrap() == a
    # ... and against a matching-everything relation it is empty.
    every_key = table("b", [({"k": row["k"], "y": 0}, 1) for row, _ in a], S)
    assert len(ops.anti_join(a, every_key, ("k",)).unwrap()) == 0


@over_semirings
@given(F.table_rows("a"))
def test_l1_8_aggregate_equals_the_direct_fold(S, rows) -> None:
    a = table("a", rows, S)
    result = ops.aggregate(a, ("k",), SUM_INT, lambda r: r["x"], "s").unwrap()
    expected: dict[int, int] = {}
    for row, annotation in a:  # canonical-encoding order, per docs/specs/m1.md §4.1
        expected[row["k"]] = expected.get(row["k"], SUM_INT.identity) + row["x"] * S.multiplicity(
            annotation
        )
    assert {row["k"]: row["s"] for row, _ in result} == expected
    for _, annotation in result:
        assert S.multiplicity(annotation) == 1  # one output row per group


# --------------------------------------------- L1.9 the cone, and Why's inertness


@pytest.mark.parametrize("shape", F.SHAPES, ids=[s.name for s in F.SHAPES])
@given(st.data())
def test_l1_9_the_fragment_preserves_the_non_negative_cone(shape, data) -> None:
    # Subtraction is not in M1's surface, so no operator here can make a negative
    # annotation — and to_bag, which refuses one, is how we find out (docs/specs/m1.md §4.4).
    rels = {name: table(name, data.draw(F.table_rows(name))) for name in F.TABLES}
    result = F.evaluate(shape.plan, rels, ops, {"sum": SUM_INT, "count": SUM_INT})
    for _, annotation in result:
        assert Z.multiplicity(annotation) >= 0
    result.to_bag()  # raises SemiringError on a negative; reaching here is the assertion


@pytest.mark.parametrize("shape", F.SHAPES, ids=[s.name for s in F.SHAPES])
@given(st.data())
def test_l1_9_the_why_component_is_inert_on_the_data(shape, data) -> None:
    # Provenance that changed the answer would not be provenance. Same graph, same rows,
    # two semirings; the bag images must agree.
    drawn = {name: data.draw(F.table_rows(name)) for name in F.TABLES}
    monoids = {"sum": SUM_INT, "count": SUM_INT}
    plain = F.evaluate(shape.plan, {n: table(n, r, Z) for n, r in drawn.items()}, ops, monoids)
    with_why = F.evaluate(shape.plan, {n: table(n, r, ZxWhy) for n, r in drawn.items()}, ops, monoids)
    assert plain.to_bag() == with_why.to_bag()
    assert plain.schema == with_why.schema
