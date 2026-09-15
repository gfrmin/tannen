"""M5 law L5.7 — the comparator: byte identity, never normalised (docs/specs/m5.md §4, §5;
BRIEF §8).

FROZEN at m5-laws-freeze. "Byte-identical vs production" means bytes: no trailing newline
forgiven, no whitespace stripped, no re-encoding before the comparison. `tannen.dogfood.compare`
returns one `unanalysed` `divergence/1` per corpus item whose tannen output differs from
production's, in corpus order, naming both refs and the first differing byte (the shorter length
when one is a prefix of the other); none for an identical item; and it refuses, by name, outputs
that do not answer exactly the corpus's items. Analysis is a separate act (§5): the comparator
never classifies.
"""

from __future__ import annotations

import importlib.util as _ilu
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

from hypothesis import given  # noqa: E402

M = bind.m5("_dogfood_model")
TANNEN = bind.m5("_dogfood_subject").make(M)

VALIDATED_BY = "tests/laws/m5/_dogfood_model.py::check_comparator"


@pytest.mark.parametrize("case", sorted(M.COMPARATOR_CASES))
def test_l5_7_named_cases_compare_byte_for_byte(case) -> None:
    M.check_comparator(TANNEN, M.COMPARATOR_CASES[case])


@M._profile(100)
@given(cases=M.byte_cases())
def test_l5_7_drawn_cases_compare_byte_for_byte(cases) -> None:
    M.check_comparator(TANNEN, cases)
