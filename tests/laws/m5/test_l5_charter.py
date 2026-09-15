"""M5 law L5.9 — the charter: every corpus item is byte-identical to production, or its
divergence is analysed (docs/specs/m5.md §4, §5, §12; BRIEF §8). M5's KILL CRITERION.

FROZEN at m5-laws-freeze. BRIEF §8: "M5 dogfood: one Renavon vertical, byte-identical vs
production on frozen inputs, divergences analysed (production bugs found = wins)".

Over the authorised corpus at `.dogfood/corpus.json` and the store at `.dogfood/store/`:
`tannen.dogfood.run(store, corpus)` answers every item with an output ref, and THIS LAW — not
the implementation's comparator — reads both outputs' bytes and compares them. Every item whose
bytes differ carries an analysed `divergence/1` at `.dogfood/divergences/<item>.json` naming the
same refs and the same first differing byte; no item whose bytes agree carries one (a stale
analysis is a claim about a divergence that no longer exists); and nothing recorded is still
`unanalysed`. A corpus with no items is refused: a charter over nothing passes everything.
"""

from __future__ import annotations

import importlib.util as _ilu
import json
from pathlib import Path as _Path

import pytest

REPO_ROOT = _Path(__file__).resolve().parents[3]
DOGFOOD = REPO_ROOT / ".dogfood"
if not (DOGFOOD / "corpus.json").is_file():
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
bind.m5("_dogfood_subject")  # the sentinel: tannen.dogfood present, or a visible skip

from tannen import dogfood  # noqa: E402
from tannen.store import Store  # noqa: E402

VALIDATION_REASON = (
    "the charter is over the one real corpus, which no model holds; its comparison is done by "
    "the law from the store's bytes, and the comparator it would otherwise trust is L5.7's, "
    "model-checked."
)


def _run() -> tuple[dict, Store, dict]:
    corpus = json.loads((DOGFOOD / "corpus.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(M.schema("corpus")).validate(corpus)
    store = Store(DOGFOOD / "store")
    return corpus, store, dict(dogfood.run(store, corpus))


def _recorded() -> dict:
    validator = jsonschema.Draft202012Validator(M.schema("divergence"))
    out = {}
    for path in sorted((DOGFOOD / "divergences").glob("*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        validator.validate(value)
        assert path.stem == value["item"], f"{path.name} records item {value['item']!r}"
        out[value["item"]] = value
    return out


def test_l5_9_every_item_is_identical_or_its_divergence_is_analysed() -> None:
    corpus, store, outputs = _run()
    items = corpus["items"]
    assert items, "the corpus has no items — a charter over nothing passes everything"
    assert set(outputs) == {item["id"] for item in items}, (
        "the run did not answer exactly the corpus's items")
    recorded = _recorded()
    problems = []
    for item in items:
        tannen = store.get_bytes(outputs[item["id"]])
        production = store.get_bytes(item["production_output"])
        offset = M.first_difference(tannen, production)
        found = recorded.get(item["id"])
        if offset is None:
            if found is not None:
                problems.append(f"{item['id']}: identical, but a divergence is recorded (stale)")
            continue
        if found is None:
            problems.append(f"{item['id']}: differs at byte {offset}, and no divergence is recorded")
            continue
        if (found["input"], found["tannen_output"], found["production_output"], found["offset"]) \
                != (item["input"], outputs[item["id"]], item["production_output"], offset):
            problems.append(f"{item['id']}: the recorded divergence describes different bytes")
        if found["classification"] == "unanalysed":
            problems.append(f"{item['id']}: the divergence is recorded but not analysed")
    orphans = sorted(set(recorded) - {item["id"] for item in items})
    problems += [f"{name}: a divergence is recorded for an item the corpus does not have"
                 for name in orphans]
    assert not problems, "M5's charter (BRIEF §8) is not met:\n  " + "\n  ".join(problems)
