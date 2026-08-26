"""Declared algebra, law-checked at construction (docs/specs/m1.md §4.3; BRIEF §5.6).

"An aggregate with untested algebra cannot be constructed." The caller supplies finite
`witnesses`; construction checks every law over every triple drawn from them and raises
`AlgebraError` by name. No Hypothesis at run time — registration is not a test.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

__all__ = ["AbelianGroup", "AlgebraError", "Monoid"]


class AlgebraError(ValueError):
    """The declared algebra fails one of its laws on the supplied witnesses."""


class Monoid:
    """`(op, identity)` associative with `identity` a two-sided identity, over `witnesses`."""

    __slots__ = ("name", "op", "identity", "witnesses")

    def __init__(self, name: str, op: Callable[[Any, Any], Any], identity: Any, witnesses: Iterable[Any]) -> None:
        if not isinstance(name, str) or not name:
            raise AlgebraError("a monoid needs a non-empty name")
        if not callable(op):
            raise AlgebraError(f"{name}: op {op!r} is not callable")
        try:
            witnesses = tuple(witnesses)
        except TypeError as exc:
            raise AlgebraError(f"{name}: witnesses must be a finite iterable") from exc
        if not witnesses:
            raise AlgebraError(
                f"{name}: witnesses must be non-empty — the caller supplies the evidence, "
                "the kernel does not guess a generator (BRIEF §5.6)"
            )
        self.name, self.op, self.identity, self.witnesses = name, op, identity, witnesses
        self._check_laws()

    def _apply(self, a: Any, b: Any) -> Any:
        try:
            return self.op(a, b)
        except Exception as exc:  # a law check that crashes is a failed law, named as such
            raise AlgebraError(f"{self.name}: op raised {type(exc).__name__}: {exc}") from exc

    def _check_laws(self) -> None:
        for a in self.witnesses:
            if self._apply(self.identity, a) != a or self._apply(a, self.identity) != a:
                raise AlgebraError(f"{self.name}: {self.identity!r} is not an identity for {a!r}")
        for a in self.witnesses:
            for b in self.witnesses:
                for c in self.witnesses:
                    if self._apply(self._apply(a, b), c) != self._apply(a, self._apply(b, c)):
                        raise AlgebraError(f"{self.name}: op is not associative on {(a, b, c)!r}")

    def fold(self, values: Iterable[Any]) -> Any:
        """Left fold from `identity`, in the order given (§4.1 fixes that order upstream)."""
        acc = self.identity
        for value in values:
            acc = self.op(acc, value)
        return acc

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.name!r})"


class AbelianGroup(Monoid):
    """A commutative monoid with inverses, checked over the witnesses."""

    __slots__ = ("inverse",)

    def __init__(
        self,
        name: str,
        op: Callable[[Any, Any], Any],
        identity: Any,
        inverse: Callable[[Any], Any],
        witnesses: Iterable[Any],
    ) -> None:
        if not callable(inverse):
            raise AlgebraError(f"{name}: inverse {inverse!r} is not callable")
        self.inverse = inverse
        super().__init__(name, op, identity, witnesses)

    def _invert(self, a: Any) -> Any:
        try:
            return self.inverse(a)
        except Exception as exc:
            raise AlgebraError(f"{self.name}: inverse raised {type(exc).__name__}: {exc}") from exc

    def _check_laws(self) -> None:
        super()._check_laws()
        for a in self.witnesses:
            for b in self.witnesses:
                if self._apply(a, b) != self._apply(b, a):
                    raise AlgebraError(f"{self.name}: op is not commutative on {(a, b)!r}")
        for a in self.witnesses:
            inv = self._invert(a)
            if self._apply(a, inv) != self.identity or self._apply(inv, a) != self.identity:
                raise AlgebraError(f"{self.name}: {inv!r} is not an inverse of {a!r}")
