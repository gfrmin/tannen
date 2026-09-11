"""M4 law L4.20 — SUCCESSOR of L3.13–L3.14, the multi-`Why` door and the encode gate
(docs/specs/m4.md §8; docs/specs/m3.md §2.2, §2.3).

FROZEN at m4-laws-freeze. Superseded forward under D0106 ruling 2; the M3 file
`tests/laws/m3/test_l3_door.py` is retained unedited and keeps running. The claim is
L3.13's and L3.14's unchanged — `why_slots` finds every `Why`, the witnessed-row door fires
at every position, `anti_join` refuses a multi-`Why` semiring, and no spelling puts a
non-grammar atom into a canonical form [cites: provenance-ref-grammar]. One frozen check,
so one law with two clauses (RT-M3-05's answer); the oracle is bound from its bytes.
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

M, TANNEN = bind.m3()

VALIDATED_BY = "tests/laws/m3/_delta_model.py::check_doors"


def test_l4_20_the_multi_why_door_and_the_encode_gate() -> None:
    M.check_doors(TANNEN)
