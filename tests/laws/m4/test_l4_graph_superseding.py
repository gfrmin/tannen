"""M4 law L4.19 — SUCCESSOR of L3.11–L3.12, graph convergence and the residue theorem,
and the carrier of M3's KILL CRITERION (docs/specs/m4.md §8, §12; docs/specs/m3.md §11).

FROZEN at m4-laws-freeze. Superseded forward under D0106 ruling 2; the M3 file
`tests/laws/m3/test_l3_graph.py` is retained unedited and keeps running. The claim is
L3.11's and L3.12's unchanged: on every catalogue shape × perturbation stream the
incremental integral is the reference one-shot byte for byte, `Why` and superseded
anti_join addresses included, and on the positive fragment `surviving(·, dead)` recovers the
reference from the cumulative run. One frozen check, so one law with two clauses (RT-M3-05's
answer). m3 §11 made a failure of L3.12 the milestone's kill criterion; that criterion now
reads on this law, whose oracle is bound from its bytes and so cannot be quietly swapped.
"""

from __future__ import annotations

import importlib.util as _ilu
from pathlib import Path as _Path

import pytest

pytest.importorskip("tannen.oracles", reason=(
    "M4 boundary not implemented yet (law suite frozen ahead of Session B); M4's laws go "
    "live together — docs/specs/m4.md §11"))

_spec = _ilu.spec_from_file_location("tannen_frozen_m4._frozen_bind",
                                     _Path(__file__).with_name("_frozen_bind.py"))
bind = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(bind)

from hypothesis import given, strategies as st  # noqa: E402

M, TANNEN = bind.m3()

VALIDATED_BY = "tests/laws/m3/_delta_model.py::check_graph_convergence"


@pytest.mark.parametrize("shape", M.SHAPES, ids=[s.name for s in M.SHAPES])
@given(data=st.data())
def test_l4_19_graph_convergence_and_the_residue_theorem(shape, data) -> None:
    schemas, ticks, net = data.draw(M.stream_tables(names="".join(shape.tables)))
    M.check_graph_convergence(TANNEN, shape, schemas, ticks, net)
