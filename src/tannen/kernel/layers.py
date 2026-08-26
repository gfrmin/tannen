"""The layer lattice (docs/specs/m1.md §6; BRIEF P8, §5.9).

Four layers form a CHAIN under operator-set inclusion, so "the most restrictive layer
admitting these operators" is well defined. The operator set comes from the run — every
Outcome carries `operators` — never from a parser: a static scan fails OPEN (an aliased or
getattr-reached operator yields a narrower layer than the truth), a runtime check fails
closed (D0083).

`check_layer` accepts a declaration at or wider than what ran and raises on one that is
narrower: a node may promise less power than it has, never more restraint than it practises.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from enum import IntEnum
from types import MappingProxyType

from tannen.kernel.ops import OPERATORS

__all__ = ["LAYER_OPERATORS", "Layer", "LayerError", "check_layer", "layer_of"]


class LayerError(ValueError):
    """An unknown operator, or a declared layer narrower than the operators that ran."""


class Layer(IntEnum):
    CAPTURE = 0  # nothing — oracles only (M4)
    SERVE = 1
    DECODE = 2
    DERIVE = 3


_ALL = frozenset(OPERATORS)

LAYER_OPERATORS: Mapping[Layer, frozenset[str]] = MappingProxyType(
    {
        Layer.CAPTURE: frozenset(),
        Layer.SERVE: frozenset({"project", "select"}),
        Layer.DECODE: frozenset({"project", "select", "map_rows"}),
        Layer.DERIVE: _ALL,
    }
)


def layer_of(operators: Iterable[str]) -> Layer:
    """The least layer admitting every operator named."""
    used = frozenset(operators)
    unknown = used - _ALL
    if unknown:
        raise LayerError(f"not an operator: {sorted(unknown)} (the eight are {OPERATORS})")
    for layer in Layer:  # ascending
        if used <= LAYER_OPERATORS[layer]:
            return layer
    raise AssertionError("unreachable: DERIVE admits every operator")


def check_layer(declared: Layer, operators: Iterable[str]) -> Layer:
    """Accept a declaration at or wider than what ran; refuse a narrower one by name."""
    if not isinstance(declared, Layer):
        raise LayerError(f"declared layer must be a Layer member, not {declared!r}")
    needed = layer_of(operators)
    if declared < needed:
        raise LayerError(
            f"declared {declared.name} but ran {sorted(frozenset(operators))}, which needs "
            f"{needed.name}: a node may not claim more restraint than it practises (§6)"
        )
    return declared
