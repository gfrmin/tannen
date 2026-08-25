"""M1 law L1.3 — declared algebra is law-checked at registration
(docs/specs/m1.md §4.3; BRIEF §5.6 "an aggregate with untested algebra cannot be
constructed").

FROZEN at m1-laws-freeze. The point of this law is negative: it is not that a good monoid
works, it is that a BAD ONE CANNOT BE BUILT. Checking at construction rather than at use
is what makes the shortest spelling the lawful one (BRIEF P9).
"""

from __future__ import annotations

import operator

import pytest

algebra = pytest.importorskip(
    "tannen.kernel.algebra",
    reason="M1 algebra not implemented yet (law suite frozen ahead of Session B)",
)

INT_WITNESSES = (-3, -1, 0, 1, 2, 5)
STR_WITNESSES = ("", "a", "bb")


def test_l1_3_lawful_monoids_construct() -> None:
    total = algebra.Monoid("sum-int", operator.add, 0, INT_WITNESSES)
    assert total.name == "sum-int"
    assert total.identity == 0
    assert total.fold([1, 2, 3]) == 6
    assert total.fold([]) == 0  # the identity is what an empty fold means

    # Associative but NOT commutative is a perfectly good Monoid: aggregate fixes the
    # fold order instead of demanding commutativity (docs/specs/m1.md §4.1).
    concat = algebra.Monoid("concat", operator.add, "", STR_WITNESSES)
    assert concat.fold(["a", "bb"]) == "abb"

    group = algebra.AbelianGroup("sum-int-group", operator.add, 0, operator.neg, INT_WITNESSES)
    assert group.inverse(3) == -3
    assert group.op(3, group.inverse(3)) == group.identity


@pytest.mark.parametrize(
    ("name", "op", "identity"),
    [
        ("not-associative", lambda a, b: a - b, 0),
        ("not-associative-mean", lambda a, b: (a + b) // 2, 0),
        ("wrong-identity", operator.add, 1),
        ("op-ignores-right", lambda a, b: a, 0),
    ],
    ids=["subtraction", "midpoint", "wrong-identity", "left-projection"],
)
def test_l1_3_unlawful_monoids_cannot_be_constructed(name, op, identity) -> None:
    with pytest.raises(algebra.AlgebraError):
        algebra.Monoid(name, op, identity, INT_WITNESSES)


@pytest.mark.parametrize(
    ("name", "op", "identity", "inverse"),
    [
        ("not-commutative", operator.add, "", lambda s: s),          # str concat: not commutative
        ("bad-inverse", operator.add, 0, lambda n: n),               # n + n != 0
    ],
    ids=["not-commutative", "bad-inverse"],
)
def test_l1_3_unlawful_groups_cannot_be_constructed(name, op, identity, inverse) -> None:
    witnesses = STR_WITNESSES if isinstance(identity, str) else INT_WITNESSES
    with pytest.raises(algebra.AlgebraError):
        algebra.AbelianGroup(name, op, identity, inverse, witnesses)


def test_l1_3_witnesses_are_required_evidence_not_a_formality() -> None:
    # The caller supplies the evidence; the kernel does not guess a generator, and an
    # empty witness set would make the check vacuous (docs/specs/m1.md §4.3).
    with pytest.raises(algebra.AlgebraError):
        algebra.Monoid("no-witnesses", operator.add, 0, ())


def test_l1_3_a_raising_op_is_an_algebra_error_not_a_leak() -> None:
    def explode(a, b):
        raise ZeroDivisionError("boom")

    with pytest.raises(algebra.AlgebraError):
        algebra.Monoid("raises", explode, 0, INT_WITNESSES)
