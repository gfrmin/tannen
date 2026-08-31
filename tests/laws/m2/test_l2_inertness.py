"""M2 law L2.5 — `Why` explains an answer and never supplies one (docs/specs/m2.md §5.3;
BRIEF P4).

FROZEN at m2-laws-freeze.

M1's L1.9 said this of the operators over hand-written annotations. It has to be said
again once a SOURCE mints them, because that is the first point at which the support sets
are not a test fixture: if ingest could make the answer depend on the provenance, every
pipeline's output would depend on how much lineage anyone happened to record.
"""

from __future__ import annotations

import pytest
from hypothesis import given, strategies as st

import _model as M  # noqa: E402
from _subject import TANNEN  # noqa: E402

VALIDATED_BY = "tests/laws/m2/_model.py::check_inertness"


@pytest.mark.parametrize("shape", M.SHAPES, ids=[s.name for s in M.SHAPES])
@given(st.data())
def test_l2_5_the_answer_does_not_move_when_the_provenance_does(shape, data) -> None:
    """Stated over the BAG IMAGE rather than over the projection `pi1: (n, w) -> n`,
    because the bag image is what `to_bag`, `aggregate` and `anti_join` all mean by
    "really there" (D0107). The two agree on every reachable annotation once D0110 makes
    the unwitnessed ones unconstructible, which is the point of doing this at M2."""
    tables = data.draw(M.source_tables(names=shape.tables, overlap="partial"))
    M.check_inertness(TANNEN, shape, tables)
