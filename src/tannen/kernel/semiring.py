"""Semirings: the annotation algebra `Rel` is parameterised by (docs/specs/m1.md §2, §2.1).

One mechanism, two uses (BRIEF P4): `Z` gives Z-sets and deltas, `B` gives sets, `Why`
gives support-set provenance, and `product` composes them. `ZxWhy` is the default.

Equality between semirings is BY NAME, never by object identity — a product built twice
compares equal, and `name` is what the `rel/1` canonical form records. In-memory product
elements are 2-tuples; their canonical image is a 2-list, because the M0 encoder refuses
tuples and the golden corpus was computed with lists.

`BagSemiring` (§2.1) is the extra structure `distinct`, `aggregate` and the bag image need:
`multiplicity` (copies in the bag) and `collapse` ("one row, same support"). A semiring
that does not declare them is refused BY NAME at the call, never coerced.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol

from tannen.kernel.encoding import encode_canonical
from tannen.kernel.refs import is_ref

__all__ = [
    "B",
    "BagSemiring",
    "SEMIRINGS",
    "Semiring",
    "SemiringError",
    "Why",
    "Z",
    "Z_ONLY",
    "ZxWhy",
    "is_bag_semiring",
    "product",
    "why_slot",
]


class SemiringError(ValueError):
    """An annotation outside a semiring's domain, or a bag operation it cannot define."""


class Semiring(Protocol):
    name: str
    zero: Any
    one: Any

    def add(self, a: Any, b: Any) -> Any: ...
    def mul(self, a: Any, b: Any) -> Any: ...
    def encode(self, a: Any) -> Any: ...
    def decode(self, value: Any) -> Any: ...


class BagSemiring(Semiring, Protocol):
    def multiplicity(self, a: Any) -> int: ...
    def collapse(self, a: Any) -> Any: ...


class _Base:
    name: str
    zero: Any
    one: Any

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _Base) and other.name == self.name

    def __hash__(self) -> int:
        return hash(self.name)

    def __repr__(self) -> str:
        return f"<Semiring {self.name}>"


# ------------------------------------------------------------------------------ Z, B


class _Z(_Base):
    name = "Z"
    zero = 0
    one = 1

    def _check(self, n: Any) -> int:
        if type(n) is not int:  # bool is an int subclass and is not an integer annotation
            raise SemiringError(f"Z: {n!r} is not an int annotation")
        return n

    def add(self, a: Any, b: Any) -> int:
        return self._check(a) + self._check(b)

    def mul(self, a: Any, b: Any) -> int:
        return self._check(a) * self._check(b)

    def encode(self, a: Any) -> int:
        return self._check(a)

    def decode(self, value: Any) -> int:
        return self._check(value)

    def multiplicity(self, a: Any) -> int:
        if self._check(a) < 0:
            raise SemiringError(
                f"Z: {a} has no bag image — a negative multiplicity is the delta executor's "
                "business at M3, not a count (docs/specs/m1.md §2.1)"
            )
        return a

    def collapse(self, a: Any) -> int:
        if self._check(a) < 0:
            raise SemiringError(f"Z: {a} has no set image (docs/specs/m1.md §2.1)")
        return 1 if a > 0 else 0


class _B(_Base):
    name = "B"
    zero = False
    one = True

    def _check(self, b: Any) -> bool:
        if type(b) is not bool:
            raise SemiringError(f"B: {b!r} is not a bool annotation")
        return b

    def add(self, a: Any, b: Any) -> bool:
        return self._check(a) or self._check(b)

    def mul(self, a: Any, b: Any) -> bool:
        return self._check(a) and self._check(b)

    def encode(self, a: Any) -> bool:
        return self._check(a)

    def decode(self, value: Any) -> bool:
        return self._check(value)

    def multiplicity(self, a: Any) -> int:
        return 1 if self._check(a) else 0

    def collapse(self, a: Any) -> bool:
        return self._check(a)


# ------------------------------------------------------------------------------- Why


def _antichain(sets: Iterable[frozenset[str]]) -> frozenset[frozenset[str]]:
    """Drop every support set that is a STRICT superset of another (§2: antichain-normalised)."""
    candidates = set(sets)
    return frozenset(s for s in candidates if not any(other < s for other in candidates))


class _Why(_Base):
    name = "Why"
    zero: frozenset[frozenset[str]] = frozenset()
    one: frozenset[frozenset[str]] = frozenset({frozenset()})

    @staticmethod
    def of(*support_sets: Iterable[str]) -> frozenset[frozenset[str]]:
        """The constructor. Each argument is one support set of refs; the result is
        antichain-normalised. `Why.of()` is `zero`; `Why.of(())` is `one`."""
        sets = []
        for support in support_sets:
            atoms = frozenset(support)
            for atom in atoms:
                if not is_ref(atom):
                    raise SemiringError(f"Why: {atom!r} is not a ref in the pinned grammar")
            sets.append(atoms)
        return _antichain(sets)

    def _check(self, w: Any) -> frozenset[frozenset[str]]:
        if not isinstance(w, frozenset) or not all(isinstance(s, frozenset) for s in w):
            raise SemiringError(f"Why: {w!r} is not a set of support sets (use Why.of)")
        return w

    def add(self, a: Any, b: Any) -> frozenset[frozenset[str]]:
        return _antichain(self._check(a) | self._check(b))

    def mul(self, a: Any, b: Any) -> frozenset[frozenset[str]]:
        return _antichain(x | y for x in self._check(a) for y in self._check(b))

    def encode(self, w: Any) -> list[list[str]]:
        # Each support sorted by code point; the outer list by the canonical bytes of the
        # inner (§2). Nothing here depends on set iteration order (L1.15).
        return sorted((sorted(s) for s in self._check(w)), key=encode_canonical)

    def decode(self, value: Any) -> frozenset[frozenset[str]]:
        if not isinstance(value, list) or not all(isinstance(s, list) for s in value):
            raise SemiringError(f"Why: {value!r} is not an encoded Why element")
        return self.of(*value)

    def multiplicity(self, w: Any) -> int:
        return 1 if self._check(w) else 0

    def collapse(self, w: Any) -> frozenset[frozenset[str]]:
        return self._check(w)  # add is idempotent: Why is its own collapse


# --------------------------------------------------------------------------- product


class _Product(_Base):
    """Componentwise. Elements are 2-tuples; the encoded image is a 2-list."""

    def __init__(self, left: Any, right: Any) -> None:
        self.left, self.right = left, right
        self.name = f"{left.name}*{right.name}"
        self.zero = (left.zero, right.zero)
        self.one = (left.one, right.one)

    def _check(self, a: Any) -> tuple[Any, Any]:
        if not (isinstance(a, tuple) and len(a) == 2):
            raise SemiringError(f"{self.name}: {a!r} is not a pair")
        return a

    def add(self, a: Any, b: Any) -> tuple[Any, Any]:
        a, b = self._check(a), self._check(b)
        return (self.left.add(a[0], b[0]), self.right.add(a[1], b[1]))

    def mul(self, a: Any, b: Any) -> tuple[Any, Any]:
        a, b = self._check(a), self._check(b)
        return (self.left.mul(a[0], b[0]), self.right.mul(a[1], b[1]))

    def encode(self, a: Any) -> list[Any]:
        a = self._check(a)
        return [self.left.encode(a[0]), self.right.encode(a[1])]

    def decode(self, value: Any) -> tuple[Any, Any]:
        if not (isinstance(value, list) and len(value) == 2):
            raise SemiringError(f"{self.name}: {value!r} is not an encoded pair")
        return (self.left.decode(value[0]), self.right.decode(value[1]))


class _BagProduct(_Product):
    def multiplicity(self, a: Any) -> int:
        a = self._check(a)
        return self.left.multiplicity(a[0]) * self.right.multiplicity(a[1])

    def collapse(self, a: Any) -> tuple[Any, Any]:
        a = self._check(a)
        return (self.left.collapse(a[0]), self.right.collapse(a[1]))


def is_bag_semiring(semiring: Any) -> bool:
    """Whether `semiring` declares the §2.1 structure. Structural, by the two names."""
    return callable(getattr(semiring, "multiplicity", None)) and callable(
        getattr(semiring, "collapse", None)
    )


def why_slot(semiring: Any) -> str | None:
    """Where a `Why` component lives in `semiring`, structurally, by name (§2): `"self"`,
    `"left"`, `"right"`, or `None` if there isn't one. `ZxWhy` (`product(Z, Why)`) resolves
    to `"right"`; a bare `Why` resolves to `"self"`; `Z` or `B` alone resolve to `None`.

    A fact about the semiring, not about any operator — which is why it lives here and not
    beside its first caller. Two things want it: enriching an annotation with a witness
    (`ops.anti_join`), and asking whether an annotation claims copies of a row it has no
    derivation for (D0109, if the owner takes it)."""
    if semiring.name == "Why":
        return "self"
    left = getattr(semiring, "left", None)
    if left is not None and left.name == "Why":
        return "left"
    right = getattr(semiring, "right", None)
    if right is not None and right.name == "Why":
        return "right"
    return None


def product(left: Any, right: Any) -> _Product:
    """The product semiring. A BagSemiring iff both components are."""
    cls = _BagProduct if is_bag_semiring(left) and is_bag_semiring(right) else _Product
    return cls(left, right)


# --------------------------------------------------------------------------- shipped

Z = _Z()
B = _B()
Why = _Why()
ZxWhy = product(Z, Why)
#: BRIEF §5.5 spells the opt-down `Z_ONLY`; it is `Z`, not a copy of it.
Z_ONLY = Z

#: name -> instance. `Rel.from_value` consults it; an unknown name is refused, never guessed.
SEMIRINGS: dict[str, Any] = {S.name: S for S in (Z, B, Why, ZxWhy)}
