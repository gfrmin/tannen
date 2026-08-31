"""M2 law L2.9 — the shipped package agrees with the frozen model (docs/specs/m2.md §9.1).

FROZEN at m2-laws-freeze.

L1.16's shape, one layer up: `_fragment.py` made DuckDB the oracle for the ANSWER, and
`_model.py` is the oracle for the PROVENANCE — which DuckDB has none of. A model Session B
cannot edit is an oracle; the seal is what makes that true (D0089).
"""

from __future__ import annotations

import pytest
from hypothesis import given, strategies as st

import _model as M  # noqa: E402
from _subject import TANNEN  # noqa: E402

#: D0094 §3. A differential law against the model cannot be validated BY the model — that
#: is the one circularity the ratchet cannot break, and naming it is better than pretending
#: otherwise. What validates the model is L2.3–L2.6, which are model-checked against it and
#: against six mutants; this law inherits exactly that much confidence and no more.
VALIDATION_REASON = (
    "the model IS this law's oracle, so `validated_by: _model.py` would be circular. The "
    "model's own validation is L2.3-L2.6 plus the mutant matrix in "
    "tests/test_law_validation.py, which is what this law rests on."
)


@pytest.mark.parametrize("shape", M.SHAPES, ids=[s.name for s in M.SHAPES])
@pytest.mark.parametrize("overlap", ["partial", "full"])
@given(st.data())
def test_l2_9_tannen_and_the_model_agree_annotation_for_annotation(shape, overlap, data) -> None:
    """Only the anti-join witness ATOM is normalised away — the model addresses its own
    relations and must not borrow tannen's encoder, or this would compare tannen with
    itself. That there is exactly one such atom, in exactly these support sets, is
    compared like everything else."""
    tables = data.draw(M.source_tables(names=shape.tables, overlap=overlap))
    M.check_differential(TANNEN, shape, tables)
