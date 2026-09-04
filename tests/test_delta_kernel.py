"""Delta-calculus behaviour chosen during implementation, beyond what the frozen M3 laws
pin (docs/specs/m3.md §2–§4).

`tests/laws/m3/` is the contract and it is sealed; these are the decisions the contract
left open — which semirings are delta-capable, what each door's refusal SAYS, and the
shapes the law's generators never draw. They live outside `tests/laws/` deliberately:
they are not laws, they emit no evidence, and they may be edited (the M0 precedent,
`tests/test_kernel_surface.py`).
"""

from __future__ import annotations

import pytest

from tannen.kernel import delta, ops, semiring
from tannen.kernel.algebra import AbelianGroup, Monoid
from tannen.kernel.outcome import OperatorError
from tannen.kernel.rel import Rel, RelError
from tannen.kernel.semiring import B, SemiringError, Why, Z, ZxWhy, product

REF_A = "sha256:" + "a1" * 32
REF_B = "sha256:" + "b2" * 32
REASON = "M3 kernel test: probing a non-default annotation choice"

SUM_GROUP = AbelianGroup("sum", lambda a, b: a + b, 0, lambda a: -a, witnesses=tuple(range(-6, 7)))
SUM_MONOID = Monoid("sum", lambda a, b: a + b, 0, witnesses=tuple(range(-6, 7)))


def rel(pairs, schema=("k", "x")):
    return Rel(schema, pairs)


def zx(count, *supports):
    return (count, Why.of(*supports))


# ------------------------------------------------------------- delta-capability (§2.1)


@pytest.mark.parametrize(
    "annotations, capable",
    [
        (Z, True),
        (Why, True),
        (B, False),
        (ZxWhy, True),
        (product(Why, Why), True),
        (product(ZxWhy, B), False),
        (product(Z, product(Z, Why)), True),
    ],
)
def test_delta_capability_is_declared_per_component_and_recursive(annotations, capable) -> None:
    """Every leaf must declare `negate`, at any depth. `B` never does: symmetric
    difference is not subtraction, and coercing it would be exactly the silent repair the
    doors exist to refuse."""
    assert delta.is_delta_semiring(annotations) is capable


def test_negate_refuses_a_semiring_that_cannot_subtract_by_name() -> None:
    r = Rel(("k",), [({"k": 1}, True)], annotations=B, annotations_reason=REASON)
    with pytest.raises(SemiringError, match="not delta-capable"):
        delta.negate(r)


@pytest.mark.parametrize(
    "annotations, groups, whys",
    [
        (Z, ((),), ()),
        (Why, (), ((),)),
        (ZxWhy, (("left",),), (("right",),)),
        (product(ZxWhy, ZxWhy), (("left", "left"), ("right", "left")),
         (("left", "right"), ("right", "right"))),
    ],
)
def test_the_two_locators_partition_a_product(annotations, groups, whys) -> None:
    """`group_slots` finds what can subtract and `why_slots` what carries provenance —
    the same recursive descent, and between them no component of a shipped product goes
    unlooked-at. That is the RT-M2-04 shape applied to the other half."""
    assert delta.group_slots(annotations) == groups
    assert semiring.why_slots(annotations) == whys


# ----------------------------------------------------------------- diff and apply (§3)


def test_diff_of_a_relation_with_itself_is_the_empty_delta() -> None:
    r = rel([({"k": 1, "x": 2}, zx(3, {REF_A}))])
    assert len(delta.diff(r, r)) == 0


def test_diff_emits_a_moved_why_with_zero_group_components() -> None:
    """§3.2's fourth bullet, which no generator in the frozen suite draws directly: the
    counts agree and the `Why` moved, so the delta is `(0, new Why)` — the shape by which
    a replacement operator's re-cited address propagates to a parent."""
    old = rel([({"k": 1, "x": 2}, zx(1, {REF_A}))])
    new = rel([({"k": 1, "x": 2}, zx(1, {REF_A}, {REF_B}))])
    d = delta.diff(new, old)
    ((row, annotation),) = list(d)
    assert row == {"k": 1, "x": 2}
    assert annotation == zx(0, {REF_A}, {REF_B})


def test_apply_drops_a_row_whose_count_cancelled_including_a_witnessed_zero() -> None:
    """§3.3 step 2. Construction still RETAINS `(0, {{r}})` (frozen L1.4, D0093) — `apply`
    is a new operation choosing what to emit, and the reference over the net rows has no
    such row."""
    base = rel([({"k": 1, "x": 2}, zx(1, {REF_A}))])
    d = rel([({"k": 1, "x": 2}, zx(-1, {REF_A}))])
    assert len(delta.apply(base, d, frozenset())) == 0
    assert len(rel([({"k": 1, "x": 2}, zx(0, {REF_A}))])) == 1, "construction is untouched"


def test_apply_refuses_an_over_retraction_naming_the_row_and_the_shortfall() -> None:
    """§3.3 step 1: m1 §4.4's promised loud break, landing at the operation whose
    arguments made the question askable rather than at a distant `to_bag`."""
    base = rel([({"k": 1, "x": 2}, zx(1, {REF_A}))])
    d = rel([({"k": 1, "x": 2}, zx(-3, {REF_A}))])
    with pytest.raises(SemiringError) as raised:
        delta.apply(base, d, frozenset())
    message = str(raised.value)
    assert "over-retraction" in message
    assert "'k': 1" in message and "-2" in message


def test_apply_runs_the_valuation_over_rows_the_delta_never_touched() -> None:
    """§3.3 step 3 is a pass over the ENTIRE result, not over the delta's footprint —
    uniform, deterministic, and unoptimised on purpose (BRIEF §10). A row nothing in this
    tick mentioned still loses a support set whose ref died in it."""
    base = rel([
        ({"k": 1, "x": 2}, zx(1, {REF_A})),
        ({"k": 9, "x": 9}, zx(1, {REF_A}, {REF_B})),
    ])
    empty = rel([])
    out = delta.apply(base, empty, frozenset({REF_B}))
    assert out.get({"k": 9, "x": 9}) == zx(1, {REF_A})


def test_apply_lets_the_witnessed_row_alarm_fire_rather_than_repairing_it() -> None:
    """A row whose count survives but whose every witness died is unreachable when the
    calculus is right, and is the calculus's own alarm when it is not — so nothing in
    `apply` catches it (§3.3)."""
    base = rel([({"k": 1, "x": 2}, zx(1, {REF_A}))])
    with pytest.raises(RelError, match="unwitnessed"):
        delta.apply(base, rel([]), frozenset({REF_A}))


def test_apply_of_the_empty_delta_is_byte_identical() -> None:
    """BRIEF L2 at the calculus level (L3.2), asserted through the content address rather
    than through `==`: normalisation is idempotent."""
    base = rel([({"k": 1, "x": 2}, zx(2, {REF_A}))])
    assert delta.apply(base, rel([]), frozenset()).content_address() == base.content_address()


def test_diff_and_apply_refuse_a_mismatched_pair_by_name() -> None:
    left = rel([({"k": 1, "x": 2}, zx(1, {REF_A}))])
    other_schema = Rel(("k",), [({"k": 1}, zx(1, {REF_A}))])
    other_semiring = Rel(("k", "x"), [({"k": 1, "x": 2}, 1)], annotations=Z, annotations_reason=REASON)
    with pytest.raises(OperatorError, match="schemas differ"):
        delta.diff(left, other_schema)
    with pytest.raises(OperatorError, match="semirings differ"):
        delta.apply(left, other_semiring)


def test_surviving_kills_a_support_set_that_mentions_one_dead_ref() -> None:
    """A support set is a conjunction, so one dead ref kills the whole set and the row
    keeps its other derivations (M2 §4, verbatim)."""
    why = Why.of({REF_A, REF_B}, {REF_A})
    assert delta.surviving(why, frozenset({REF_B})) == Why.of({REF_A})
    assert delta.surviving(why, frozenset()) is why


# ------------------------------------------------------------------ the derived rules (§4)


def test_linear_delta_refuses_a_non_monotone_operator_by_name() -> None:
    """`distinct`, `aggregate` and `anti_join` have no linear rule to reach for: their
    rule is replacement over integrals, and a raw delta never takes operand position at
    one of them (§3.4, the D0109 answer)."""
    d = rel([({"k": 1, "x": 2}, zx(1, {REF_A}))])
    assert len(delta.linear_delta("select", d, lambda row: row["x"] > 0)) == 1
    with pytest.raises(OperatorError, match="not a linear operator"):
        delta.linear_delta("anti_join", d, d, ("k",))


def test_group_aggregate_delta_refuses_a_monoid_that_declares_no_inverse() -> None:
    """The subtractive form leans on a DECLARED inverse whose laws were checked at
    construction; a plain `Monoid` has none, and guessing one is not on offer (L3.8)."""
    r = rel([({"k": 1, "x": 2}, zx(1, {REF_A}))])
    with pytest.raises(OperatorError, match="AbelianGroup"):
        delta.group_aggregate_delta(
            r, r, ("k",), SUM_MONOID, lambda row: row["x"], "s", Rel(("k", "s"), [])
        )


def test_the_subtractive_and_replacement_aggregates_agree_byte_for_byte() -> None:
    """D0160's agreement, on a hand-built shrink the property test's generators need luck
    to draw: two rows in one group, one of them partially retracted."""
    old = rel([
        ({"k": 1, "x": 2}, zx(3, {REF_A})),
        ({"k": 1, "x": 5}, zx(1, {REF_B})),
    ])
    new = rel([
        ({"k": 1, "x": 2}, zx(1, {REF_A})),
        ({"k": 1, "x": 5}, zx(1, {REF_B})),
    ])
    replacement = ops.aggregate(new, ("k",), SUM_MONOID, lambda row: row["x"], "s").unwrap()
    subtractive = delta.group_aggregate_delta(
        old, new, ("k",), SUM_GROUP, lambda row: row["x"], "s",
        ops.aggregate(old, ("k",), SUM_MONOID, lambda row: row["x"], "s").unwrap(),
    )
    assert subtractive.content_address() == replacement.content_address()
    assert subtractive.get({"k": 1, "s": 7}) == zx(1, {REF_A}, {REF_B})


def test_join_delta_takes_every_relation_the_law_quantifies_over() -> None:
    """The two-term form reads `d_a`, `b_old`, `a_new` and `d_b`; `a_old` and `b_new` are
    taken all the same, so the both-old-sides spelling is EXPRESSIBLE and dies as the
    mutant `join-both-sides-old` rather than being unwritable (D0159)."""
    a_old = Rel(("k", "x"), [])
    b_old = Rel(("k", "y"), [])
    d_a = Rel(("k", "x"), [({"k": 1, "x": 2}, zx(1, {REF_A}))])
    d_b = Rel(("k", "y"), [({"k": 1, "y": 3}, zx(1, {REF_B}))])
    a_new = delta.apply(a_old, d_a, frozenset())
    b_new = delta.apply(b_old, d_b, frozenset())
    two_term = delta.join_delta(a_old, a_new, d_a, b_old, b_new, d_b, ("k",))
    # the co-arrival term is the whole answer here: both sides are new in this tick
    assert two_term.get({"k": 1, "x": 2, "y": 3}) == zx(1, {REF_A, REF_B})


# -------------------------------------------------------------- the encode gate (§2.3)


def test_the_encode_gate_closes_the_arithmetic_route_into_a_canonical_form() -> None:
    """`Why.of` has always refused a non-grammar atom, but an element built by operator
    arithmetic over a hand-crafted frozenset skipped it and reached a `rel/1` value and a
    content address. The gate is in `encode`, which every construction and every address
    goes through, so there is no spelling left (RT-M2-07, L3.14)."""
    smuggled = frozenset({frozenset({"not-a-ref"})})
    with pytest.raises(SemiringError, match="not a ref in the pinned grammar"):
        Why.encode(smuggled)
    with pytest.raises(SemiringError, match="not a ref in the pinned grammar"):
        Rel(("k",), [({"k": 1}, (1, smuggled))])
