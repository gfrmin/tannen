"""M5 law L5.5 — `corpus/1` is Grade S (docs/specs/m5.md §3; BRIEF §2.1, P2).

FROZEN at m5-laws-freeze. The corpus names the frozen inputs of the M5 vertical and production's
outputs for them, by content address only [cites: pkm-event-identity]: no Renavon bytes are
carried in the record, and the store that resolves its refs lives outside the repository
(`.dogfood/store/`, gitignored — docs/specs/m5.md §8). It also names the vertical's pipeline and
the owner-signed record that opened door renavon-first-contact (L5.8). Its refs are in the
pinned grammar [cites: provenance-ref-grammar]. Conformance is parse-all-positives,
reject-all-negatives; and the corpus actually present conforms.
"""

from __future__ import annotations

import importlib.util as _ilu
import json
from pathlib import Path as _Path

import pytest

REPO_ROOT = _Path(__file__).resolve().parents[3]
CORPUS = REPO_ROOT / ".dogfood" / "corpus.json"
if not CORPUS.is_file():
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

POSITIVE = M.vector_paths("corpus", "positive")
NEGATIVE = M.vector_paths("corpus", "negative")
if not POSITIVE or not NEGATIVE:
    raise RuntimeError("the corpus/1 corpus is missing a side (a Grade-S corpus has both)")


def test_l5_5_the_schema_is_a_valid_2020_12_schema() -> None:
    jsonschema.Draft202012Validator.check_schema(M.schema("corpus"))


@pytest.mark.parametrize("path", POSITIVE, ids=[p.stem for p in POSITIVE])
def test_l5_5_parses_all_positives(path) -> None:
    jsonschema.Draft202012Validator(M.schema("corpus")).validate(
        json.loads(path.read_text(encoding="utf-8")))


@pytest.mark.parametrize("path", NEGATIVE, ids=[p.stem for p in NEGATIVE])
def test_l5_5_rejects_all_negatives(path) -> None:
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(M.schema("corpus")).validate(
            json.loads(path.read_text(encoding="utf-8")))


def test_l5_5_the_corpus_present_conforms_and_names_each_item_once() -> None:
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(M.schema("corpus")).validate(corpus)
    ids = [item["id"] for item in corpus["items"]]
    assert len(set(ids)) == len(ids), "the corpus names an item twice"
