"""M1 laws L1.1–L1.2 — the semirings (docs/specs/m1.md §2, §11).

FROZEN at m1-laws-freeze. Pre-implementation this module is a visible skip
(importorskip); M1 completion requires it green with zero skips. Wrong laws are never
edited: record the defect, freeze a superseding file (CLAUDE.md).
"""

from __future__ import annotations

import pytest
from hypothesis import given, strategies as st

semiring = pytest.importorskip(
    "tannen.kernel.semiring",
    reason="M1 semirings not implemented yet (law suite frozen ahead of Session B)",
)

from tannen.kernel.encoding import encode_canonical  # noqa: E402  (M0; exists already)

REFS = [f"sha256:{c * 64}" for c in "0123456789ab"[:6]]


def _why_elements():
    """Antichain-normalised Why elements over a small ref alphabet."""
    return st.frozensets(st.frozensets(st.sampled_from(REFS), max_size=3), max_size=3).map(
        lambda sets: semiring.Why.of(*sets)
    )


def _z_elements():
    return st.integers(min_value=-6, max_value=6)


def elements_of(name: str):
    return {
        "Z": _z_elements(),
        "B": st.booleans(),
        "Why": _why_elements(),
        "Z*Why": st.tuples(_z_elements(), _why_elements()),
    }[name]


def _non_negative(S, a):
    """Map an element onto the non-negative cone the bag operations are defined on (§2.1)."""
    if S.name == "Z":
        return abs(a)
    if S.name == "Z*Why":
        return (abs(a[0]), a[1])
    return a


def _shipped():
    return [semiring.Z, semiring.B, semiring.Why, semiring.ZxWhy]


def _ids():
    return [S.name for S in _shipped()]


parametrised = pytest.mark.parametrize("S", _shipped(), ids=_ids())


# --------------------------------------------------------------- L1.1 semiring axioms


def test_l1_1_the_shipped_semirings_are_the_pinned_ones() -> None:
    assert [S.name for S in _shipped()] == ["Z", "B", "Why", "Z*Why"]
    for S in _shipped():
        assert semiring.SEMIRINGS[S.name] is S
    assert semiring.ZxWhy.name == "Z*Why"
    assert semiring.Z_ONLY is semiring.Z  # spelled exactly as BRIEF §5.5 spells it


@parametrised
@given(st.data())
def test_l1_1_identities_and_annihilation(S, data) -> None:
    a = data.draw(elements_of(S.name))
    assert S.add(a, S.zero) == a == S.add(S.zero, a)
    assert S.mul(a, S.one) == a == S.mul(S.one, a)
    assert S.mul(a, S.zero) == S.zero == S.mul(S.zero, a)


@parametrised
@given(st.data())
def test_l1_1_commutativity(S, data) -> None:
    a, b = data.draw(elements_of(S.name)), data.draw(elements_of(S.name))
    assert S.add(a, b) == S.add(b, a)
    assert S.mul(a, b) == S.mul(b, a)


@parametrised
@given(st.data())
def test_l1_1_associativity_and_distribution(S, data) -> None:
    draw = lambda: data.draw(elements_of(S.name))  # noqa: E731
    a, b, c = draw(), draw(), draw()
    assert S.add(S.add(a, b), c) == S.add(a, S.add(b, c))
    assert S.mul(S.mul(a, b), c) == S.mul(a, S.mul(b, c))
    assert S.mul(a, S.add(b, c)) == S.add(S.mul(a, b), S.mul(a, c))


@parametrised
@given(st.data())
def test_l1_1_annotations_are_canonically_encodable(S, data) -> None:
    # No identity without an encoding: a Rel's address is the address of its annotated
    # content (docs/specs/m1.md §2, §3.1).
    a = data.draw(elements_of(S.name))
    assert encode_canonical(S.encode(a)) == encode_canonical(S.encode(a))


def test_l1_1_why_is_antichain_normalised_and_refuses_non_refs() -> None:
    r0, r1 = REFS[0], REFS[1]
    assert semiring.Why.of({r0}, {r0, r1}) == semiring.Why.of({r0})
    assert semiring.Why.zero == frozenset()
    assert semiring.Why.one == frozenset({frozenset()})
    assert semiring.Why.add(semiring.Why.of({r0}), semiring.Why.of({r0, r1})) == semiring.Why.of({r0})
    assert semiring.Why.mul(semiring.Why.of({r0}), semiring.Why.of({r1})) == semiring.Why.of({r0, r1})
    with pytest.raises(Exception):
        semiring.Why.of({"not-a-ref"})


def test_l1_1_products_compose_generically() -> None:
    zz = semiring.product(semiring.Z, semiring.Z)
    assert zz.name == "Z*Z"
    assert (zz.zero, zz.one) == ((0, 0), (1, 1))
    assert zz.add((1, 2), (3, 4)) == (4, 6)
    assert zz.mul((2, 3), (4, 5)) == (8, 15)
    # Equality is by name, never by object identity: a product built twice is one semiring.
    assert semiring.product(semiring.Z, semiring.Why).name == semiring.ZxWhy.name


# ------------------------------------------------------- L1.2 the BagSemiring extension


@parametrised
def test_l1_2_every_shipped_semiring_is_a_bag_semiring(S) -> None:
    assert semiring.is_bag_semiring(S)


@parametrised
@given(st.data())
def test_l1_2_collapse_axioms(S, data) -> None:
    a = _non_negative(S, data.draw(elements_of(S.name)))
    b = _non_negative(S, data.draw(elements_of(S.name)))
    assert S.collapse(S.zero) == S.zero
    assert S.collapse(S.collapse(a)) == S.collapse(a)
    # The WEAK form: collapse is not additive (collapse(1 + 1) = 1, not 2).
    assert S.collapse(S.add(a, b)) == S.collapse(S.add(S.collapse(a), S.collapse(b)))


@parametrised
@given(st.data())
def test_l1_2_multiplicity_axioms(S, data) -> None:
    a = _non_negative(S, data.draw(elements_of(S.name)))
    assert S.multiplicity(S.zero) == 0
    assert S.multiplicity(a) >= 0
    assert (S.multiplicity(a) > 0) == (a != S.zero)


def test_l1_2_negative_multiplicity_is_refused_by_name() -> None:
    # A negative annotation has no bag or set image; defining one is M3's job (§2.1).
    for bad in (-1, -7):
        with pytest.raises(semiring.SemiringError):
            semiring.Z.multiplicity(bad)
        with pytest.raises(semiring.SemiringError):
            semiring.Z.collapse(bad)
    assert (semiring.Z.multiplicity(3), semiring.Z.collapse(3), semiring.Z.collapse(0)) == (3, 1, 0)


def test_l1_2_product_multiplicity_and_collapse_are_componentwise() -> None:
    # Everything about ℤ × Why follows from this rather than being special-cased.
    w = semiring.Why.of({REFS[0]})
    assert semiring.ZxWhy.collapse((3, w)) == (1, w)
    assert semiring.ZxWhy.multiplicity((3, w)) == 3
    # Support but no surviving copies: NOT the product zero, and yet absent from the bag
    # image (docs/specs/m1.md §2.1, §3).
    assert (0, w) != semiring.ZxWhy.zero
    assert semiring.ZxWhy.multiplicity((0, w)) == 0
