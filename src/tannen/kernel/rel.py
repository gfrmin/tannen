"""`Rel[K, S]` — the annotated relation and its `rel/1` canonical form (docs/specs/m1.md §3).

A finite K-relation: rows (mappings from column name to an M0-encodable value) to
annotations in a commutative semiring S, with finite support.

- Row identity IS the row's canonical encoding: equal bytes are one row and their
  annotations `add`. The stored row is the DECODED canonical form (NFC text, minimal
  Decimal), so what comes back out of a Rel is what its identity was computed over.
- Zero annotations are absent, not stored — dropped after merging, and "zero" means the
  semiring's `zero` and nothing else: under ℤ × Why, `(0, {{r}})` is retained (§3).
- Iteration is in canonical-byte order. Every operator and every canonical form depends on
  that order and on nothing hash-seeded (L1.15).
- `annotations=None` means the default `ZxWhy`; any other choice requires
  `annotations_reason` (§3.2, D0002). The reason is NOT part of identity.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from typing import Any

from tannen.kernel.encoding import content_address, decode_canonical, encode_canonical
from tannen.kernel.outcome import OperatorError
from tannen.kernel.semiring import SEMIRINGS, ZxWhy, is_bag_semiring

__all__ = ["DEFAULT_ANNOTATIONS", "REL_TAG", "Rel", "RelError"]

REL_TAG = "rel/1"
DEFAULT_ANNOTATIONS = ZxWhy
_SEMIRING_SHAPE = ("name", "zero", "one", "add", "mul", "encode")


class RelError(ValueError):
    """A schema, row shape, annotation choice or canonical-form violation, refused by name."""


def _validate_schema(schema: Any) -> tuple[str, ...]:
    try:
        columns = tuple(schema)
    except TypeError as exc:
        raise RelError(f"schema must be an iterable of column names, not {schema!r}") from exc
    if not columns:
        raise RelError("a Rel has at least one column (§3)")
    for column in columns:
        if not isinstance(column, str):
            raise RelError(f"a column name is a str, not {type(column).__name__}: {column!r}")
    if len(set(columns)) != len(columns):
        raise RelError(f"duplicate column name in {columns!r}")
    return tuple(sorted(columns))


def _validate_annotations(annotations: Any, reason: Any) -> tuple[Any, str | None]:
    semiring = DEFAULT_ANNOTATIONS if annotations is None else annotations
    missing = [attr for attr in _SEMIRING_SHAPE if not hasattr(semiring, attr)]
    if missing:
        raise RelError(f"annotations must be a Semiring; {semiring!r} lacks {missing}")
    if reason is not None and not isinstance(reason, str):
        raise RelError("annotations_reason must be a str")
    if semiring.name != DEFAULT_ANNOTATIONS.name and reason is None:
        raise RelError(
            f"choosing {semiring.name!r} over the default {DEFAULT_ANNOTATIONS.name!r} requires "
            "annotations_reason — the opt-down happens with a recorded reason (BRIEF §5.5, D0002)"
        )
    return semiring, reason


def _merge(columns: tuple[str, ...], semiring: Any, rows: Iterable[Any]) -> dict[bytes, tuple[dict, Any]]:
    """Validate and merge `(row, annotation)` pairs by canonical row bytes."""
    expected = frozenset(columns)
    merged: dict[bytes, tuple[dict, Any]] = {}
    for pair in rows:
        try:
            row, annotation = pair
        except (TypeError, ValueError) as exc:
            raise RelError(f"rows are (row, annotation) pairs, not {pair!r}") from exc
        if not isinstance(row, Mapping):
            raise RelError(f"a row is a mapping, not {type(row).__name__}")
        if frozenset(row) != expected:
            raise RelError(f"ragged row: columns {sorted(map(repr, row))} against schema {columns!r}")
        key = encode_canonical(dict(row))  # CanonicalEncodingError propagates: the M0 door, unchanged
        semiring.encode(annotation)  # the annotation must have an image, or it is not one
        if key in merged:
            merged[key] = (merged[key][0], semiring.add(merged[key][1], annotation))
        else:
            merged[key] = (decode_canonical(key), annotation)
    return merged


class Rel:
    __slots__ = ("_schema", "_annotations", "_reason", "_entries", "_index", "_address")

    def __init__(
        self,
        schema: Iterable[str],
        rows: Iterable[Any] = (),
        *,
        annotations: Any = None,
        annotations_reason: str | None = None,
    ) -> None:
        columns = _validate_schema(schema)
        semiring, reason = _validate_annotations(annotations, annotations_reason)
        self._init(columns, semiring, reason, _merge(columns, semiring, rows))

    # -- package-internal construction (operators and the executor build from merged rows)

    @classmethod
    def _build(
        cls, schema: tuple[str, ...], semiring: Any, reason: str | None, merged: dict[bytes, tuple[dict, Any]]
    ) -> Rel:
        rel = object.__new__(cls)
        rel._init(schema, semiring, reason, merged)
        return rel

    def _init(self, columns: tuple[str, ...], semiring: Any, reason: str | None, merged: dict) -> None:
        self._schema = columns
        self._annotations = semiring
        self._reason = reason
        self._entries = tuple(
            (key, row, annotation)
            for key, (row, annotation) in sorted(merged.items())
            if annotation != semiring.zero
        )
        self._index = {key: i for i, (key, _, _) in enumerate(self._entries)}
        self._address: str | None = None

    @classmethod
    def _from_pairs(cls, schema: Iterable[str], semiring: Any, reason: str | None, rows: Iterable[Any]) -> Rel:
        """Package-internal: validate and merge `(row, annotation)` pairs WITHOUT re-applying the
        annotations_reason rule — the choice was recorded when the source Rel was constructed,
        and a Rel decoded by `from_value` legitimately carries no reason. Operators build their
        quarantined-row Rels through this."""
        columns = _validate_schema(schema)
        return cls._build(columns, semiring, reason, _merge(columns, semiring, rows))

    def _items(self) -> Iterator[tuple[bytes, dict, Any]]:
        """`(canonical bytes, row, annotation)` in canonical order. Rows are the stored dicts —
        callers copy before handing one to user code."""
        return iter(self._entries)

    # -- the public surface

    @property
    def schema(self) -> tuple[str, ...]:
        return self._schema

    @property
    def annotations(self) -> Any:
        return self._annotations

    @property
    def annotations_reason(self) -> str | None:
        return self._reason

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> Iterator[tuple[dict, Any]]:
        for _, row, annotation in self._entries:
            yield dict(row), annotation

    def get(self, row: Mapping[str, Any]) -> Any:
        """The annotation of `row`; the semiring's `zero` when absent (never an error)."""
        index = self._index.get(encode_canonical(dict(row)))
        return self._annotations.zero if index is None else self._entries[index][2]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Rel):
            return NotImplemented
        return (
            self._schema == other._schema
            and self._annotations.name == other._annotations.name
            and [(k, a) for k, _, a in self._entries] == [(k, a) for k, _, a in other._entries]
        )

    def __hash__(self) -> int:
        return hash(self.content_address())

    def __repr__(self) -> str:
        return f"Rel({self._schema!r}, {len(self)} row(s), annotations={self._annotations.name!r})"

    # -- the canonical form (§3.1)

    def to_value(self) -> dict[str, Any]:
        S = self._annotations
        return {
            "tannen": REL_TAG,
            "schema": list(self._schema),
            "semiring": S.name,
            "rows": [[dict(row), S.encode(annotation)] for _, row, annotation in self._entries],
        }

    def content_address(self) -> str:
        if self._address is None:
            self._address = content_address(self.to_value())
        return self._address

    @classmethod
    def from_value(cls, value: Any) -> Rel:
        if not isinstance(value, Mapping) or value.get("tannen") != REL_TAG:
            raise RelError(f"not a {REL_TAG} value: {value!r}")
        name = value.get("semiring")
        if name not in SEMIRINGS:
            raise RelError(f"semiring {name!r} is not one this build ships; refusing to guess (§2)")
        S = SEMIRINGS[name]
        columns = _validate_schema(value.get("schema", ()))
        rows = value.get("rows")
        if not isinstance(rows, list):
            raise RelError("rows must be a list")
        pairs = []
        for entry in rows:
            if not isinstance(entry, (list, tuple)) or len(entry) != 2:
                raise RelError(f"a row entry is [row, annotation], not {entry!r}")
            pairs.append((entry[0], S.decode(entry[1])))
        return cls._build(columns, S, None, _merge(columns, S, pairs))

    # -- the bag image (§3.3)

    def to_bag(self) -> list[tuple[Any, ...]]:
        S = self._annotations
        if not is_bag_semiring(S):
            raise OperatorError(
                f"to_bag: {S.name} declares no bag structure (multiplicity/collapse), so it has "
                "no bag image (docs/specs/m1.md §2.1)"
            )
        bag: list[tuple[Any, ...]] = []
        for _, row, annotation in self._entries:
            copies = S.multiplicity(annotation)  # SemiringError on a negative: the cone law
            bag.extend([tuple(row[column] for column in self._schema)] * copies)
        return bag
