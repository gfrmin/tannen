"""Evidence records — `docs/specs/m0.md` §6; BRIEF P6, §7 (Grade S, owned).

Every law run emits one content-addressed record validating against the frozen schema
`governance/schemas/evidence-record.schema.json`. The record's id is the content
address of its canonical encoding, which is why the record carries no id field.

The schema is *consumed*, never restated: a hand-rolled validator here would be a
second normative home for the same shape, and duplication is drift (BRIEF §2).
"""

from __future__ import annotations

import datetime as dt
import os
import platform
from collections.abc import Iterable, Iterator
from importlib import metadata
from pathlib import Path
from typing import Any

import jsonschema

from tannen.store import Store

__all__ = [
    "EvidenceError",
    "EvidenceStore",
    "FORMAT_VERSION",
    "build_record",
    "environment",
    "evidence_root",
    "load_schema",
    "validate_record",
]

FORMAT_VERSION = 0
SCHEMA_REL = Path("governance") / "schemas" / "evidence-record.schema.json"
EVIDENCE_REL = Path("evidence")
EVIDENCE_ROOT_ENV = "TANNEN_EVIDENCE_ROOT"

#: Packages whose versions make a verdict reproducible (the schema requires at least
#: pytest and hypothesis).
RECORDED_PACKAGES = ("pytest", "hypothesis", "jsonschema")


class EvidenceError(Exception):
    """An evidence record is not what the frozen schema says an evidence record is."""


def load_schema(root: Path) -> dict:
    import json

    return json.loads((root / SCHEMA_REL).read_text(encoding="utf-8"))


def evidence_root(root: Path) -> Path:
    """Where the evidence store lives; `TANNEN_EVIDENCE_ROOT` overrides."""
    override = os.environ.get(EVIDENCE_ROOT_ENV)
    return Path(override) if override else root / EVIDENCE_REL


def environment() -> dict[str, Any]:
    packages: dict[str, str] = {}
    for name in RECORDED_PACKAGES:
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            continue
    return {"python": platform.python_version(), "packages": packages}


def build_record(
    *,
    law_id: str,
    milestone: str,
    verdict: str,
    descriptors: Iterable[str],
    seed: str | None,
    run_at: str | None = None,
    examined: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """One record for one law run. `run_at` is the runner's wall clock, never the
    kernel's: the kernel has no clock (BRIEF P7).

    `examined` is WHAT THE RUN ACTUALLY EXAMINED (D0117). It is OMITTED when the caller
    has nothing to say rather than written as a zero: a record whose measure is absent
    and a record whose measure is nothing are different facts, and the first is what
    every record written before this field existed attests.
    """
    record: dict[str, Any] = {
        "format_version": FORMAT_VERSION,
        "law_id": law_id,
        "milestone": milestone,
        "verdict": verdict,
        "run_at": run_at or dt.datetime.now(dt.timezone.utc).isoformat(timespec="microseconds"),
        "seed": seed,
        "descriptors": sorted(descriptors),
        "environment": environment(),
    }
    if examined is not None:
        record["examined"] = examined
    return record


def validate_record(record: Any, schema: dict) -> None:
    errors = sorted(
        jsonschema.Draft202012Validator(schema).iter_errors(record),
        key=lambda e: list(e.absolute_path),
    )
    if errors:
        detail = "; ".join(
            f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}" for e in errors
        )
        raise EvidenceError(f"evidence record violates the frozen schema — {detail}")


class EvidenceStore:
    """The evidence stream as a content-addressed store.

    Write-once and append-only like every tannen store: a verdict, once recorded,
    is part of the record.
    """

    def __init__(self, root: Path, store_root: Path | None = None) -> None:
        self._repo_root = root
        self._schema = load_schema(root)
        self._store = Store(store_root if store_root is not None else evidence_root(root))

    @property
    def store(self) -> Store:
        return self._store

    @property
    def schema(self) -> dict:
        return self._schema

    def put(self, record: dict[str, Any]) -> str:
        """Validate against the frozen schema, then store. Invalid never reaches disk."""
        validate_record(record, self._schema)
        return self._store.put_value(record)

    def records(self) -> Iterator[tuple[str, dict[str, Any]]]:
        """Every valid evidence record in the store, with its ref."""
        for ref, record, problem in self.scan():
            if problem is None:
                yield ref, record

    def scan(self) -> Iterator[tuple[str, Any, str | None]]:
        """Every stored value, tagged with why it is not an evidence record, if it is not."""
        for ref in self._store.iter_refs():
            try:
                value = self._store.get_value(ref)
            except Exception as exc:  # integrity or encoding failure: surface it
                yield ref, None, f"unreadable: {exc}"
                continue
            if not isinstance(value, dict) or "law_id" not in value:
                yield ref, value, "not an evidence record"
                continue
            try:
                validate_record(value, self._schema)
            except EvidenceError as exc:
                yield ref, value, str(exc)
                continue
            yield ref, value, None
