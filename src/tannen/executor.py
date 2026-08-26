"""The reference (non-incremental) executor and its two rebuilders (docs/specs/m1.md §8;
BRIEF §4, §7). A shell module: it reads and writes the store and the trace directory.

- `Node(transform, inputs)`: a registered transform applied to store refs of Rel values;
  `derivation_id` follows (§8, L1.13).
- `TraceStore(root)`: `derivation_id -> output_ref`, append-only. Re-recording the same
  mapping is a no-op; a DIFFERENT output for the same derivation raises
  `TraceIntegrityError` — one derivation, one output.
- `AlwaysRebuild` recomputes and records. `VerifyingTrace` consults the trace first; on a
  hit it verifies the recorded output resolves and passes the store's verify-on-read, and
  raises `TraceIntegrityError` if not — a missing or altered recorded output is not a cache
  miss, because the store is append-only and write-once, so its absence means something
  happened outside the store's contract and quietly rebuilding would erase the evidence.
- A node that yields a `Quarantine` writes NO trace entry: a quarantine is a report about a
  run, not a cached result.
- `Built.layer` is `layer_of(outcome.operators)` — what the node actually did — and a
  transform declaring a narrower layer raises `LayerError` here, the one place that knows.

`VerifyingTrace` is BRIEF §7's "degenerate governor whose prior is a dirty bit"; the
Grade-S wire schema is deferred to M4 (D0088). `Node` and `Built` expose the M1-available
subset of the Request fields: descriptors, inputs, and the staleness the trace computes.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tannen.kernel.derivation import derivation_id
from tannen.kernel.layers import Layer, check_layer, layer_of
from tannen.kernel.outcome import QUARANTINE_SCHEMA, Ok, Outcome, Quarantine
from tannen.kernel.refs import RefError, is_ref, ref_hex
from tannen.kernel.rel import Rel
from tannen.store import IntegrityError, MissingRef, Store
from tannen.transform import descriptor_of

__all__ = ["AlwaysRebuild", "Built", "Node", "TraceIntegrityError", "TraceStore", "VerifyingTrace"]


class TraceIntegrityError(Exception):
    """A trace that contradicts itself or the store: never a cache miss."""


class Node:
    """One derivation: a registered transform over store refs of Rel values."""

    __slots__ = ("transform", "inputs", "derivation_id")

    def __init__(self, transform: Any, inputs: Any) -> None:
        descriptor = descriptor_of(transform)  # TransformError for an unregistered function
        refs = tuple(inputs)
        for ref in refs:
            if not is_ref(ref):
                raise RefError(f"node inputs are store refs, not {ref!r}")
        self.transform = transform
        self.inputs = refs
        self.derivation_id = derivation_id(descriptor, refs)

    def __repr__(self) -> str:
        return f"Node({self.transform.label}, {len(self.inputs)} input(s), {self.derivation_id})"


@dataclass(frozen=True)
class Built:
    derivation_id: str
    output_ref: str | None  # None when the node quarantined as a whole
    rebuilt: bool  # False on a verified trace hit
    layer: Layer | None  # what ran; None on a trace hit, where nothing ran
    operators: frozenset[str]


class TraceStore:
    """`derivation_id -> output_ref`, one file per derivation, written atomically."""

    def __init__(self, root: Any) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        return self._root

    def _path(self, derivation: str) -> Path:
        return self._root / ref_hex(derivation)  # RefError on a malformed id

    def lookup(self, derivation: str) -> str | None:
        path = self._path(derivation)
        if not path.exists():
            return None
        recorded = path.read_text(encoding="utf-8").strip()
        if not is_ref(recorded):  # a trace file holding a non-ref was rewritten by hand
            raise TraceIntegrityError(f"{derivation}: trace holds {recorded!r}, not a store ref")
        return recorded

    def record(self, derivation: str, output_ref: str) -> None:
        if not is_ref(output_ref):
            raise RefError(f"an output is a store ref, not {output_ref!r}")
        existing = self.lookup(derivation)
        if existing == output_ref:
            return  # idempotent
        if existing is not None:
            raise TraceIntegrityError(
                f"{derivation}: already recorded output {existing}; refusing {output_ref} — "
                "one derivation, one output (docs/specs/m1.md §8)"
            )
        fd, tmp = tempfile.mkstemp(dir=self._root, prefix=".trace-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(output_ref + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, self._path(derivation))
        except BaseException:
            try:
                os.unlink(tmp)
            except FileNotFoundError:
                pass
            raise


def _run(node: Node, store: Store) -> Outcome:
    """Load the inputs, call the transform, normalise what it returns to an Outcome."""
    inputs = [Rel.from_value(store.get_value(ref)) for ref in node.inputs]
    try:
        result = node.transform(*inputs)
    except Exception as exc:  # a whole-node failure; BaseException crosses untouched (§5)
        return Quarantine(
            reason=type(exc).__name__,
            detail=str(exc) or type(exc).__name__,
            provenance=node.inputs,
            operators=frozenset(),
        )
    if isinstance(result, (Ok, Quarantine)):
        return result
    if isinstance(result, Rel):
        empty = Rel._build(QUARANTINE_SCHEMA, result.annotations, result.annotations_reason, {})
        return Ok(rel=result, quarantined=empty, operators=frozenset())
    return Quarantine(
        reason="bad-return",
        detail=f"{node.transform.label} returned {type(result).__name__}, not a Rel or an Outcome",
        provenance=node.inputs,
        operators=frozenset(),
    )


def _materialise(node: Node, store: Store, traces: TraceStore) -> Built:
    outcome = _run(node, store)
    layer = layer_of(outcome.operators)
    declared = node.transform.layer
    if declared is not None:
        check_layer(declared, outcome.operators)  # LayerError: narrower than what ran (§6)
    if isinstance(outcome, Quarantine):
        return Built(node.derivation_id, None, True, layer, outcome.operators)
    output_ref = store.put_value(outcome.rel.to_value())
    traces.record(node.derivation_id, output_ref)
    return Built(node.derivation_id, output_ref, True, layer, outcome.operators)


class AlwaysRebuild:
    """Recompute every time; record the trace anyway."""

    def build(self, node: Node, store: Store, traces: TraceStore) -> Built:
        return _materialise(node, store, traces)


class VerifyingTrace:
    """Serve a recorded output if it verifies; rebuild on a miss; RAISE on a bad record."""

    def build(self, node: Node, store: Store, traces: TraceStore) -> Built:
        recorded = traces.lookup(node.derivation_id)
        if recorded is None:
            return _materialise(node, store, traces)
        try:
            store.get_bytes(recorded)  # verify-on-read: absent or altered content raises
        except (MissingRef, IntegrityError, RefError) as exc:
            raise TraceIntegrityError(
                f"{node.derivation_id}: the trace names {recorded}, which does not resolve in "
                f"the store ({type(exc).__name__}: {exc}) — not a cache miss (docs/specs/m1.md §8)"
            ) from exc
        return Built(node.derivation_id, recorded, False, None, frozenset())
