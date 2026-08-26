"""The float door (docs/specs/m1.md §7; BRIEF §5.8, P7).

    Lossy(grid: Decimal)(value: float) -> Decimal

Maps a finite float to the nearest integer multiple of `grid`, ties to the EVEN multiple,
over exact rationals — never through a rounded intermediate. A float IS its binary value:
`1.005` is `1.00499…`, so on a `0.01` grid it goes to `1.00`. The result is built from the
grid's own digit tuple, so no decimal context precision is ever consulted.

A `Lossy` is not itself a value: `encode_canonical(Lossy(...))` raises. `to_value()` is the
grid, so a transform's `params_hash` prices it.
"""

from __future__ import annotations

import math
from decimal import Decimal
from fractions import Fraction
from typing import Any

__all__ = ["Lossy", "LossyError"]


class LossyError(ValueError):
    """A grid or a value the door refuses, by name."""


class Lossy:
    __slots__ = ("_grid", "_grid_digits", "_grid_exponent")

    def __init__(self, grid: Any) -> None:
        if type(grid) is not Decimal:
            raise LossyError(
                f"grid must be a Decimal, not {type(grid).__name__} — silent coercion is the "
                "thing a door exists to prevent (§7)"
            )
        if not grid.is_finite() or grid <= 0:
            raise LossyError(f"grid must be finite and > 0, got {grid}")
        sign, digits, exponent = grid.as_tuple()
        self._grid = grid
        self._grid_digits = int("".join(map(str, digits)))
        self._grid_exponent = exponent

    @property
    def grid(self) -> Decimal:
        return self._grid

    def __call__(self, value: Any) -> Decimal:
        if type(value) is not float:
            raise LossyError(f"the door takes a float, not {type(value).__name__}: {value!r}")
        if not math.isfinite(value):
            raise LossyError(f"{value!r} is not a finite float")
        steps = round(Fraction(value) / Fraction(self._grid))  # exact; Fraction rounds half to even
        scaled = steps * self._grid_digits  # result = scaled × 10**exponent, exactly
        sign = 1 if scaled < 0 else 0
        digits = tuple(int(d) for d in str(abs(scaled)))
        return Decimal((sign, digits, self._grid_exponent))

    def to_value(self) -> dict[str, Decimal]:
        return {"grid": self._grid}

    def __repr__(self) -> str:
        return f"Lossy({self._grid!r})"
