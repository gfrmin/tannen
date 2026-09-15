"""M5 law L5.4 — the vertical is SELECTED, never chosen (docs/specs/m5.md §2; BRIEF §8, §9).

FROZEN at m5-laws-freeze. BRIEF §8: "the agent selects the Renavon source minimising (parser LOC
× distinct operators required) among sources with a visible export, and records the choice +
measurement as a decision record. No question is asked." The measurement is Tier-C door
renavon-first-contact's to take (docs/specs/m5.md §0.2), so this law is stated over it rather
than over any source this session could have read.

THE RULE, with the ambiguities BRIEF leaves pinned here (D0128's "silence resolved by a pinning
property test"):
  - a measurement that measures one source twice, or names an operator outside tannen's
    catalogue in ANY candidate, is refused whole;
  - eligible = `visible_export`; none eligible is refused;
  - minimise (parser_loc × distinct operators, distinct operators, source id as UTF-8 bytes).
    A tie on the product breaks toward FEWER operators; a further tie on operators is also a
    tie on LOC (the product fixes it), so the source id is the last and total key.
The catalogue is `tannen.kernel.ops.OPERATORS` itself — derived from the package, never listed.

At the gate: the measurement the owner authorised, `.dogfood/measurement.json`, selects the
vertical the corpus is of — computed by this law, not only asked of the implementation.
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
from hypothesis import given  # noqa: E402

M = bind.m5("_dogfood_model")
TANNEN = bind.m5("_dogfood_subject").make(M)

from tannen.kernel import ops  # noqa: E402

VALIDATED_BY = "tests/laws/m5/_dogfood_model.py::check_selection"


def test_l5_4_the_catalogue_is_the_packages_own() -> None:
    assert TANNEN.catalogue is ops.OPERATORS and ops.OPERATORS, \
        "the selection rule's catalogue is not tannen.kernel.ops.OPERATORS"


@pytest.mark.parametrize("case", sorted(M.SELECTION_CASES))
def test_l5_4_named_measurements_select_by_the_rule(case) -> None:
    M.check_selection(TANNEN, M.SELECTION_CASES[case])


@M._profile(100)
@given(measurement=M.measurements(ops.OPERATORS))
def test_l5_4_drawn_measurements_select_by_the_rule(measurement) -> None:
    M.check_selection(TANNEN, measurement)


def test_l5_4_the_gate_measurement_selects_the_corpus_vertical() -> None:
    measurement = json.loads((DOGFOOD / "measurement.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(M.schema("measurement")).validate(measurement)
    vertical = json.loads((DOGFOOD / "corpus.json").read_text(encoding="utf-8"))["vertical"]
    assert M.expected_selection(measurement, ops.OPERATORS) == vertical, (
        "the corpus is not of the vertical the gate measurement selects (BRIEF §8)")
    assert TANNEN.select(measurement) == vertical
