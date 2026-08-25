"""M1 law L1.6 — the float door (docs/specs/m1.md §7; BRIEF §5.8, P7).

FROZEN at m1-laws-freeze. `docs/specs/m0.md` §2 promised `Lossy(f, grid)` would arrive
with the Rel layer; this is the law it arrives under. M0 shipped only the refusal, and the
refusal does not move: what changes is that there is now one declared, priced, greppable
way through it [cites: exactness-and-the-door].
"""

from __future__ import annotations

from decimal import Decimal
from fractions import Fraction

import pytest
from hypothesis import given, strategies as st

lossy_mod = pytest.importorskip(
    "tannen.kernel.lossy",
    reason="M1 Lossy not implemented yet (law suite frozen ahead of Session B)",
)
rel_mod = pytest.importorskip("tannen.kernel.rel")
semiring = pytest.importorskip("tannen.kernel.semiring")

from tannen.kernel.encoding import CanonicalEncodingError, encode_canonical  # noqa: E402

Lossy = lossy_mod.Lossy
WHY = "law fixture"


def test_l1_6_quantises_onto_the_declared_grid() -> None:
    # The quantisation is over EXACT rationals: a float IS its binary value, and passing
    # through `repr` first would be a second, hidden lossy step (docs/specs/m1.md §7).
    # 1.005, 1.015 and 2.675 are all a hair BELOW the decimal they are written as.
    cents = Lossy(Decimal("0.01"))
    assert cents(1.005) == Decimal("1.00")
    assert cents(1.015) == Decimal("1.01")
    assert cents(2.675) == Decimal("2.67")   # the classic binary-float surprise, priced
    assert cents(-1.005) == Decimal("-1.00")
    assert cents(0.0) == Decimal("0.00")

    whole = Lossy(Decimal("1"))              # exact ties, so exact half-even behaviour
    assert whole(0.5) == Decimal("0")
    assert whole(1.5) == Decimal("2")
    assert whole(2.5) == Decimal("2")
    assert whole(-1.5) == Decimal("-2")

    coarse = Lossy(Decimal("0.25"))          # a grid that is not a power of ten
    assert coarse(1.1) == Decimal("1.00")
    assert coarse(1.2) == Decimal("1.25")
    assert coarse(1.125) == Decimal("1.00")  # 4.5 grid units exactly: ties to the even one
    assert coarse(-1.125) == Decimal("-1.00")


@given(st.floats(allow_nan=False, allow_infinity=False, min_value=-1e6, max_value=1e6))
def test_l1_6_output_is_an_exact_decimal_on_the_grid(value: float) -> None:
    grid = Decimal("0.01")
    result = Lossy(grid)(value)
    assert isinstance(result, Decimal)
    # On the grid exactly, and the NEAREST such point — both checked over exact rationals,
    # so the law never asks the implementation to agree with a rounded intermediate.
    assert Fraction(result) % Fraction(grid) == 0
    assert abs(Fraction(result) - Fraction(value)) <= Fraction(grid) / 2
    encode_canonical(result)  # ... and canonically encodable, which was the whole point


@given(st.floats(allow_nan=False, allow_infinity=False, min_value=-1e6, max_value=1e6))
def test_l1_6_is_a_deterministic_pure_function(value: float) -> None:
    assert Lossy(Decimal("0.001"))(value) == Lossy(Decimal("0.001"))(value)


@pytest.mark.parametrize(
    "grid",
    [Decimal("0"), Decimal("-0.01"), Decimal("NaN"), Decimal("Infinity"), 0.01, "0.01", 1],
    ids=["zero", "negative", "nan", "inf", "float-grid", "str-grid", "int-grid"],
)
def test_l1_6_the_grid_must_be_a_positive_finite_decimal(grid) -> None:
    with pytest.raises(lossy_mod.LossyError):
        Lossy(grid)


@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), float("-inf"), "1.5", Decimal("1.5"), 1, None],
    ids=["nan", "inf", "-inf", "str", "decimal", "int", "none"],
)
def test_l1_6_only_a_finite_float_goes_through_the_door(value) -> None:
    with pytest.raises(lossy_mod.LossyError):
        Lossy(Decimal("0.01"))(value)


def test_l1_6_a_lossy_is_not_itself_a_value() -> None:
    # What enters a Rel is the door's OUTPUT. The door itself has no canonical encoding,
    # so it cannot be smuggled into a row and hashed as data.
    with pytest.raises(CanonicalEncodingError):
        encode_canonical(Lossy(Decimal("0.01")))


def test_l1_6_the_grid_is_priced_into_a_descriptor() -> None:
    # "priced and visible" (BRIEF §5.8): the grid has a canonical image so a transform's
    # params_hash can carry it.
    assert Lossy(Decimal("0.01")).to_value() == {"grid": Decimal("0.01")}
    assert encode_canonical(Lossy(Decimal("0.01")).to_value()) == b'{"grid":{"$decimal":"0.01"}}'
    assert Lossy(Decimal("0.01")).to_value() != Lossy(Decimal("0.1")).to_value()


def test_l1_6_no_float_reaches_a_rel_any_other_way() -> None:
    # The door is the only door. This is M0's encoder, unchanged (docs/specs/m0.md §2).
    with pytest.raises(CanonicalEncodingError):
        rel_mod.Rel(("p",), [({"p": 1.5}, 1)], annotations=semiring.Z, annotations_reason=WHY)
    priced = rel_mod.Rel(
        ("p",),
        [({"p": Lossy(Decimal("0.01"))(1.5)}, 1)],
        annotations=semiring.Z,
        annotations_reason=WHY,
    )
    assert next(iter(priced))[0] == {"p": Decimal("1.50")}
