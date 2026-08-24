"""M0 law L0.10 — the evidence-record schema and its frozen vectors
(docs/specs/m0.md §6; BRIEF P6, §7: evidence records are Grade-S data shipping
alongside the laws that emit them).

FROZEN at m0-laws-freeze. Unlike the other law modules this one runs today: it
needs no kernel, only the frozen schema and vectors — parse-all-positives /
reject-all-negatives, the Grade-S conformance shape.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA = json.loads(
    (REPO_ROOT / "governance" / "schemas" / "evidence-record.schema.json").read_text(encoding="utf-8")
)
VECTORS_ROOT = REPO_ROOT / "tests" / "laws" / "evidence-vectors"
POSITIVE = sorted((VECTORS_ROOT / "positive").glob("*.json"))
NEGATIVE = sorted((VECTORS_ROOT / "negative").glob("*.json"))

if not POSITIVE or not NEGATIVE:
    raise RuntimeError("evidence-record vector corpus is missing a side (Grade-S corpus must have both)")


def test_l0_10_schema_is_a_valid_2020_12_schema() -> None:
    jsonschema.Draft202012Validator.check_schema(SCHEMA)


@pytest.mark.parametrize("path", POSITIVE, ids=[p.stem for p in POSITIVE])
def test_l0_10_parses_all_positives(path: Path) -> None:
    record = json.loads(path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(SCHEMA).validate(record)


@pytest.mark.parametrize("path", NEGATIVE, ids=[p.stem for p in NEGATIVE])
def test_l0_10_rejects_all_negatives(path: Path) -> None:
    record = json.loads(path.read_text(encoding="utf-8"))
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(SCHEMA).validate(record)
