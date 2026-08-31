"""Sources — where a `Why` atom comes from, and how anyone follows it back
(docs/specs/m2.md §2, §7).

M1 shipped `Why`, made `ℤ × Why` the default, and gave every operator a semiring rule that
IS its provenance rule. It shipped no way to **mint** a ref from data: `Rel(...)` accepted
whatever `Why` a caller hand-wrote, so BRIEF §6's L5 — delete a source row, and every
changed output row must have carried its ref — was not merely unimplemented, it was
*unstatable*. There were no source rows and no refs for them. This module is the missing
half.

A **source** is a ref: the identity of bytes hashed outside the system
[cites: pkm-event-identity]. A **source row** is one row decoded out of it, and its ref is
the content address of the `srcrow/1` value naming both:

    {"tannen": "srcrow/1", "source": "sha256:…", "row": {…}}

The effectful shell, deliberately outside `tannen.kernel`: `ingest` writes to the store and
`lineage` reads from it. That is exactly why it lives here — the kernel imports no IO
(contract `kernel-no-io`), and a source layer that crept into it would be caught there.

This is **not** the capture layer. BRIEF P8's `capture` is oracles only and arrives at M4;
`ingest` is deterministic and reads rows a caller already holds. A relation it returns
enters at `decode` or `derive` like any other.

Nothing here opens a second home for the ref grammar or for row shape: a bad source is
refused by `tannen.kernel.refs`, an unencodable row by `tannen.kernel.encoding`, and a
ragged one by `tannen.kernel.rel` (BRIEF §2 — restatement is duplication, duplication is
drift).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from tannen.kernel.encoding import CanonicalEncodingError, content_address
from tannen.kernel.refs import is_ref, ref_hex
from tannen.kernel.rel import Rel, RelError
from tannen.kernel.semiring import Why
from tannen.store import MissingRef, Store

__all__ = [
    "CITATION_KINDS",
    "SOURCE_ROW_TAG",
    "Citation",
    "ingest",
    "lineage",
    "source_row_ref",
    "source_row_value",
]

#: The tag of the value a source-row ref addresses. Versioned like every other tannen
#: value tag: a change of shape is a new tag, never a reinterpretation of this one.
SOURCE_ROW_TAG = "srcrow/1"

#: What `lineage` may answer. There is no fourth kind for a malformed atom because
#: `Why.of` refuses a non-ref by name, so one cannot reach a `Rel` (§7).
CITATION_KINDS = ("source-row", "value", "unresolved")


# ----------------------------------------------------------------- minting a source row


def source_row_value(source: str, row: Mapping[str, Any]) -> dict[str, Any]:
    """The `srcrow/1` value naming `source` and one `row` decoded out of it.

    The value is what the ref addresses and what `ingest` writes, so every atom this
    system mints dereferences to a value explaining itself (D0126). A ref computed but
    never stored is a citation to a document that does not exist.
    """
    ref_hex(source)  # RefError by name: the grammar has one home and this opens no second
    if not isinstance(row, Mapping):
        raise RelError(f"a source row is a mapping, not {type(row).__name__}")
    return {"tannen": SOURCE_ROW_TAG, "source": source, "row": dict(row)}


def source_row_ref(source: str, row: Mapping[str, Any]) -> str:
    """The content address of `source_row_value(source, row)` — one atom, one source row.

    One ref per *row* and not per *source*, because a per-source ref makes L5 stop
    discriminating: deleting any row would move every output row's provenance equally
    (D0126). And no index in the ref, because that would make ingest order-dependent,
    which is the one thing content addressing buys.
    """
    return content_address(source_row_value(source, row))


def ingest(store: Store, source: str, schema: Iterable[str], rows: Iterable[Mapping[str, Any]]) -> Rel:
    """Every row of `source` as a `Rel` over the default `ZxWhy`, each annotated with its
    own source-row ref — and every one of those refs written to `store` first (D0126).

    Deltas *and* support, unasked (BRIEF §5.5): the returned relation carries
    `(occurrences, Why.of({its own ref}))` per row.

    **Identical rows in one source are one row.** A source is content-addressed, so two
    rows with the same canonical bytes have the same ref: their counts add and their
    witness does not.

    **Idempotent.** The store is write-once, so re-ingesting the same source writes nothing
    and returns a `Rel` with the same address (L0.5).

    **Nothing is written for a row that was refused.** Every value is minted and the
    relation built *before* the first write, so a source outside the pinned grammar
    (`RefError`), a row outside the encodable domain (`CanonicalEncodingError`, the M0 door
    unchanged) or a ragged one (`RelError`) leaves the store exactly as it found it.

    The cost is one store write per distinct row. It is append-only and it is not
    optimised: there is no performance work before M5 (BRIEF §10), and a lineage nobody
    can follow would be the wrong thing made fast.
    """
    ref_hex(source)  # up front, so an empty `rows` cannot let a bad source through unlooked-at
    minted = [(row, source_row_value(source, row)) for row in rows]
    pairs = [(row, (1, Why.of({content_address(value)}))) for row, value in minted]
    rel = Rel(schema, pairs)
    for _, value in minted:
        store.put_value(value)
    return rel


# ------------------------------------------------------------------------- the lineage read


@dataclass(frozen=True)
class Citation:
    """One atom of a support set, resolved against the store."""

    ref: str
    kind: str  # one of CITATION_KINDS
    source: str | None = None
    row: dict[str, Any] | None = None


def lineage(store: Store, why: Any) -> tuple[tuple[Citation, ...], ...]:
    """Support sets in, resolved citations out, structure preserved exactly.

    A `serve`-layer read: it changes neither the relation nor the store.

    **It is total**, and that is required rather than defensive. §6's absence witness cites
    a relation's content address and nothing guarantees that relation was ever stored, so
    an atom that does not resolve to a value is *classified* `"unresolved"` — never raised
    on. A lineage read that can fail is one nobody puts in a serve path, and an
    unfollowable citation would make §2's per-row store write pointless.

    One thing does propagate, and it is not a resolution failure: `IntegrityError` — bytes
    at rest that no longer hash to the ref they are filed under. That is the store
    reporting its own contract broken, and laundering it into `"unresolved"` would hide
    tampering inside the one read a reader most trusts.

    Ordering is `Why`'s own canonical order, so the same witness reads back the same way
    every time (L1.15), and the shape of `why` is checked by the semiring that owns it.
    """
    return tuple(
        tuple(_cite(store, atom) for atom in support)
        for support in Why.encode(why)  # canonical order, and a shape check by name
    )


def _cite(store: Store, ref: str) -> Citation:
    try:
        value = store.get_value(ref)
    except (MissingRef, CanonicalEncodingError):
        # Absent, or present as bytes that are not a value at all (a source's raw bytes,
        # say). Either way there is no value here to describe.
        return Citation(ref=ref, kind="unresolved")
    origin, row = (value.get("source"), value.get("row")) if isinstance(value, Mapping) else (None, None)
    if (
        isinstance(value, Mapping)
        and value.get("tannen") == SOURCE_ROW_TAG
        and is_ref(origin)
        and isinstance(row, Mapping)
    ):
        return Citation(ref=ref, kind="source-row", source=origin, row=dict(row))
    return Citation(ref=ref, kind="value")
