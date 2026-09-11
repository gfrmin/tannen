"""The export door: only a `serve` node leaves (docs/specs/m4.md §7; BRIEF P8, §5.9; L4.10).

m1 §6 promised that "the `serve` default for exports arrives with the export surface at M4";
this is it. An export admits a `Built` whose layer is `Layer.SERVE` — project and select only,
so its provenance is trivially that of what it projects — and emits exactly that node's
output bytes, the same bytes every time. Anything wider (a `decode` map, a `derive` join or
distinct) is refused by name, and so are the two `Built`s with nothing honest to say about
what ran: a trace hit, whose layer is unknown because nothing ran, and a node that
quarantined as a whole, which has no output. ClickHouse emission is out of M4; a later
emitter is a consumer of this function and inherits its door rather than re-deciding it
(D0222).
"""

from __future__ import annotations

from tannen.executor import Built
from tannen.kernel.layers import Layer, LayerError
from tannen.store import Store

__all__ = ["export"]


def export(store: Store, built: Built) -> bytes:
    """The output bytes of a serve-layer node, verified on read."""
    if not isinstance(built, Built):
        raise TypeError(f"export takes the Built an executor returned, not {type(built).__name__}")
    if built.layer is not Layer.SERVE:
        ran = (built.layer.name if built.layer is not None
               else "unknown — a trace hit ran nothing; rebuild it with AlwaysRebuild to export it")
        raise LayerError(
            f"an export admits only a serve-layer node (project and select); {built.derivation_id} "
            f"is {ran} after running {sorted(built.operators)} (docs/specs/m4.md §7)"
        )
    if built.output_ref is None:
        raise LayerError(f"{built.derivation_id} quarantined as a whole; there is nothing to export")
    return store.get_bytes(built.output_ref)
