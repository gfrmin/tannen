"""Conformance suite, parameterised over concepts/*.yaml at collection time (BRIEF §2).

The records are the test manifest: a grade-S record naming a missing vector corpus
fails COLLECTION (not merely a test), so the registry cannot rot without turning CI
red. S-pending rows surface as explicit skips carrying their pending_reason.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import jsonschema
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

RECORD_PATHS = sorted((REPO_ROOT / "concepts").glob("*.yaml"))
RECORDS = [yaml.safe_load(p.read_text(encoding="utf-8")) for p in RECORD_PATHS]

# Collection-time failure for a grade-S record without its corpus (BRIEF §2).
for _record in RECORDS:
    if _record.get("grade") == "S":
        _vectors = REPO_ROOT / (_record.get("conformance") or {}).get("vectors", "")
        if not _vectors.is_dir() or not any(_vectors.iterdir()):
            raise RuntimeError(
                f"concept {_record.get('id')} is grade S but its vector corpus "
                f"{_record.get('conformance', {}).get('vectors')} is missing or empty"
            )

SCHEMA = json.loads(
    (REPO_ROOT / "governance" / "schemas" / "concept-record.schema.json").read_text(encoding="utf-8")
)


def _ids(records: list[dict]) -> list[str]:
    return [r["id"] for r in records]


def _expected_citation_pins() -> int | None:
    """governance/policy.yaml#concept_registry.expected_citation_pins, or None when the
    policy declares no expectation.

    Declared means the repository is in the configuration D0115 mechanism (a) makes
    legal — a cited snapshot may be ABSENT and is then verified by pin alone (the
    published clone carries the citation, the authorised clone carries the bytes) — and
    the count in test_citation_pins_are_accounted_for is what keeps that from being a
    vacuous pass (D0116 species I). Undeclared means every cited snapshot must be
    present, which is what this file always asserted. Mirrors scripts/check_concepts.py
    (patch 01); found by rehearsing the publication sitting, where this suite failed the
    gate on the rewritten history one record at a time (D0183).
    """
    policy = REPO_ROOT / "governance" / "policy.yaml"
    if not policy.exists():
        return None
    registry = (yaml.safe_load(policy.read_text(encoding="utf-8")) or {}).get("concept_registry") or {}
    value = registry.get("expected_citation_pins")
    return value if isinstance(value, int) else None


EXPECTED_PINS = _expected_citation_pins()


@pytest.mark.parametrize("record", RECORDS, ids=_ids(RECORDS))
def test_record_is_schema_valid(record: dict) -> None:
    jsonschema.Draft202012Validator(SCHEMA).validate(record)


@pytest.mark.parametrize("record", RECORDS, ids=_ids(RECORDS))
def test_vendored_snapshots_match_recorded_hashes(record: dict) -> None:
    for source in record["sources"]:
        snapshot = REPO_ROOT / source["snapshot"]["path"]
        if not snapshot.exists():
            # Pin-only citation: legal only when the policy declares how many pins the
            # registry must account for, and counted there rather than verified here.
            assert EXPECTED_PINS is not None, f"missing snapshot {source['snapshot']['path']}"
            continue
        digest = hashlib.sha256(snapshot.read_bytes()).hexdigest()
        assert digest == source["snapshot"]["sha256"], (
            f"snapshot drifted: {source['snapshot']['path']}"
        )


def test_citation_pins_are_accounted_for() -> None:
    """by_bytes + by_pin equals the owner-signed expectation when one is declared, so a
    truncated registry cannot agree with itself; when none is declared, no cited snapshot
    is absent and the registry is non-empty. Non-vacuous in either configuration."""
    by_bytes = by_pin = 0
    for record in RECORDS:
        for source in record["sources"]:
            if (REPO_ROOT / source["snapshot"]["path"]).exists():
                by_bytes += 1
            else:
                by_pin += 1
    assert by_bytes + by_pin > 0, "no citation pins at all — the registry is empty"
    if EXPECTED_PINS is None:
        assert by_pin == 0, (
            f"{by_pin} cited snapshot(s) absent, and governance/policy.yaml declares no "
            "concept_registry.expected_citation_pins to count them against"
        )
    else:
        assert by_bytes + by_pin == EXPECTED_PINS, (
            f"citation pins accounted for = {by_bytes + by_pin} ({by_bytes} by bytes, "
            f"{by_pin} by pin), but governance/policy.yaml expects {EXPECTED_PINS}"
        )


@pytest.mark.parametrize(
    "record",
    [r for r in RECORDS if r["grade"] in ("S", "S-pending")],
    ids=_ids([r for r in RECORDS if r["grade"] in ("S", "S-pending")]),
)
def test_grade_s_vectors(record: dict) -> None:
    if record["grade"] == "S-pending":
        pytest.skip(f"S-pending: {record['conformance']['pending_reason']}")
    # Grade S proper: parse-all-positives / reject-all-negatives / round-trip.
    # No grade-S concept has published vectors yet; when one does, the corpus
    # iteration lands here and the collection guard above already enforces presence.
    corpus = REPO_ROOT / record["conformance"]["vectors"]
    assert any(corpus.iterdir())


def test_every_brief_row_has_a_record() -> None:
    # BRIEF §2's table has eight rows; Session 0 files one record per row.
    assert len(RECORDS) == 8, f"expected 8 concept records, found {len(RECORDS)}"
    postures = {r["id"]: r["posture"] for r in RECORDS}
    assert postures["semiring-relations"] == "own"
    assert postures["credence-functor-seam"] == "acknowledge"
    assert sum(1 for p in postures.values() if p == "adopt") == 6
