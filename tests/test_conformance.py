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


@pytest.mark.parametrize("record", RECORDS, ids=_ids(RECORDS))
def test_record_is_schema_valid(record: dict) -> None:
    jsonschema.Draft202012Validator(SCHEMA).validate(record)


@pytest.mark.parametrize("record", RECORDS, ids=_ids(RECORDS))
def test_vendored_snapshots_match_recorded_hashes(record: dict) -> None:
    for source in record["sources"]:
        snapshot = REPO_ROOT / source["snapshot"]["path"]
        assert snapshot.exists(), f"missing snapshot {source['snapshot']['path']}"
        digest = hashlib.sha256(snapshot.read_bytes()).hexdigest()
        assert digest == source["snapshot"]["sha256"], (
            f"snapshot drifted: {source['snapshot']['path']}"
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
