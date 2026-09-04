"""M3 laws L3.11–L3.12 — graph convergence and the residue theorem
(docs/specs/m3.md §5, §7; BRIEF L4).

FROZEN at m3-laws-freeze.

BRIEF L4 on random composite graphs: on every catalogue shape driven by every
perturbation stream, the delta executor's final integral equals the reference
executor's one-shot output over the net sources — byte-identically, `Why` included, and
superseded `anti_join` addresses gone (the contagion rule's reach, §4). L3.11 is the
coherence underneath it: on the positive fragment, the un-valuated run carries the
CUMULATIVE run's witnesses, and `surviving(w, dead)` recovers the reference exactly —
frozen L2.3 applied to the atoms the stream deleted. The mutants `no-ledger` (serves the
cumulative Why as the answer) and `antijoin-delta-maintained` (this spec's own refuted
first draft) both die here.
"""

from __future__ import annotations

import pytest
from hypothesis import given, strategies as st

import _delta_model as M  # noqa: E402
from _delta_subject import TANNEN  # noqa: E402

VALIDATED_BY = "tests/laws/m3/_delta_model.py::check_graph_convergence"


@pytest.mark.parametrize("shape", M.SHAPES, ids=[s.name for s in M.SHAPES])
@given(data=st.data())
def test_l3_11_and_12_graph_convergence_and_the_residue_theorem(shape, data) -> None:
    schemas, ticks, net = data.draw(M.stream_tables(names="".join(shape.tables)))
    M.check_graph_convergence(TANNEN, shape, schemas, ticks, net)
