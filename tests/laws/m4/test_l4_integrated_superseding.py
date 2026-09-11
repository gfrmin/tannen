"""M4 law L4.17 — SUCCESSOR of L3.7–L3.8, integrated operators consume integrals, never
deltas (docs/specs/m4.md §8; docs/specs/m3.md §3.4, §4).

FROZEN at m4-laws-freeze. Superseded forward under D0106 ruling 2; the M3 file
`tests/laws/m3/test_l3_integrated.py` is retained unedited and keeps running. The claim is
L3.7's and L3.8's unchanged. They shared one frozen check, so by RT-M3-05's answer they are
one law here with two clauses (docs/specs/m4.md §8); the oracle is bound from its bytes.
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

VALIDATED_BY = "tests/laws/m3/_delta_model.py::check_integrated_ops"


@given(w=M.two_worlds(names="ab"))
def test_l4_17_integrated_operators_consume_integrals_never_deltas(w) -> None:
    schemas, small, big, lost = w
    M.check_integrated_ops(TANNEN, schemas, small, big, lost)
