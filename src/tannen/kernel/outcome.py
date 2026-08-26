"""What an operator returns (docs/specs/m1.md §5; BRIEF P3, §5.4).

    Outcome = Ok(rel, quarantined, operators) | Quarantine(reason, detail, provenance, operators)

Row-wise failures quarantine the row into `Ok.quarantined`; whole-node failures are a
`Quarantine`, which propagates through every operator untouched. `operators` is the set of
operator names that contributed — ordinary data on the value, so the kernel stays pure and
the layer check (§6) reads what actually ran. "Empty" is an `Ok` with an empty `rel`.

`OperatorError` is defined here rather than in `ops` because `Rel.to_bag` raises it and
`ops` imports `Rel`; `ops` re-exports it, so `ops.OperatorError` is this class.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # annotation only — no runtime import, so rel -> outcome is acyclic
    from tannen.kernel.rel import Rel

__all__ = ["Ok", "OperatorError", "Outcome", "QUARANTINE_SCHEMA", "Quarantine", "QuarantineError"]

#: The schema every quarantined-row Rel carries (§5). Sorted, like every schema.
QUARANTINE_SCHEMA: tuple[str, ...] = ("detail", "operator", "reason", "row")


class OperatorError(ValueError):
    """An ill-typed operator call, refused by name (§4) — raised at the call, never deferred."""


class QuarantineError(Exception):
    """`unwrap()` on a node-level `Quarantine`."""


@dataclass(frozen=True)
class Ok:
    rel: Rel
    quarantined: Rel
    operators: frozenset[str] = frozenset()

    def unwrap(self) -> Rel:
        return self.rel


@dataclass(frozen=True)
class Quarantine:
    reason: str
    detail: str
    provenance: tuple[str, ...]
    operators: frozenset[str] = frozenset()

    def unwrap(self) -> Rel:
        raise QuarantineError(f"{self.reason}: {self.detail}")


Outcome = Ok | Quarantine
