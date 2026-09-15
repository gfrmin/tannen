"""M5 law L5.6 — `divergence/1` is Grade S (docs/specs/m5.md §5; BRIEF §2.1, §8).

FROZEN at m5-laws-freeze. BRIEF §8: byte-identical against production, "divergences analysed
(production bugs found = wins)". A divergence is data [owns]: the item, the input, both outputs
by ref, the first differing byte, and a classification from a closed set — `unanalysed` as the
comparator writes it (no analysis, no evidence), or `tannen-defect`, `production-defect`,
`input-drift`, `specification-gap` once analysed, each with a non-empty analysis, and a
production defect with at least one evidence ref. Conformance is parse-all-positives,
reject-all-negatives.
"""

from __future__ import annotations

import importlib.util as _ilu
import json
from pathlib import Path as _Path

import pytest

REPO_ROOT = _Path(__file__).resolve().parents[3]
if not (REPO_ROOT / ".dogfood" / "corpus.json").is_file():
    pytest.skip("M5 dogfood corpus absent — every M5 law goes live together when an authorised "
                "corpus is present at .dogfood/corpus.json (docs/specs/m5.md §8)",
                allow_module_level=True)

pytest.importorskip("tannen.dogfood", reason=(
    "M5 dogfood not implemented yet (law suite frozen ahead of Session B); M5's laws go "
    "live together — docs/specs/m5.md §8"))

_spec = _ilu.spec_from_file_location("tannen_frozen_m5._dogfood_bind",
                                     _Path(__file__).with_name("_dogfood_bind.py"))
bind = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(bind)

import jsonschema  # noqa: E402

M = bind.m5("_dogfood_model")

VALIDATION_REASON = (
    "Grade-S conformance is its own check: the frozen schema against its frozen positive and "
    "negative vectors, which is exactly what a model of it would restate."
)

POSITIVE = M.vector_paths("divergence", "positive")
NEGATIVE = M.vector_paths("divergence", "negative")
if not POSITIVE or not NEGATIVE:
    raise RuntimeError("the divergence/1 corpus is missing a side (a Grade-S corpus has both)")


def test_l5_6_the_schema_is_a_valid_2020_12_schema() -> None:
    jsonschema.Draft202012Validator.check_schema(M.schema("divergence"))


@pytest.mark.parametrize("path", POSITIVE, ids=[p.stem for p in POSITIVE])
def test_l5_6_parses_all_positives(path) -> None:
    jsonschema.Draft202012Validator(M.schema("divergence")).validate(
        json.loads(path.read_text(encoding="utf-8")))


@pytest.mark.parametrize("path", NEGATIVE, ids=[p.stem for p in NEGATIVE])
def test_l5_6_rejects_all_negatives(path) -> None:
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(M.schema("divergence")).validate(
            json.loads(path.read_text(encoding="utf-8")))
