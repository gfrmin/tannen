"""M4 law L4.18 — SUCCESSOR of L3.9–L3.10, source convergence (docs/specs/m4.md §8;
docs/specs/m3.md §5, §6).

FROZEN at m4-laws-freeze. Superseded forward under D0106 ruling 2; the M3 file
`tests/laws/m3/test_l3_convergence.py` is retained unedited and keeps running. The claim is
L3.9's and L3.10's unchanged — any partition, order and interleaving of a single source's
arrivals and retractions reaches the one-shot ingest of the net rows byte-identically, and
the ledger's dead set is the stream's kill-list. One frozen check, so one law with two
clauses (RT-M3-05's answer, docs/specs/m4.md §8); the oracle is bound from its bytes.
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

from hypothesis import given  # noqa: E402

M, TANNEN = bind.m3()

VALIDATED_BY = "tests/laws/m3/_delta_model.py::check_convergence"


@given(s=M.stream_tables(names="a"))
def test_l4_18_source_convergence(s) -> None:
    schemas, ticks, net = s
    M.check_convergence(TANNEN, schemas, ticks, net)
