"""M4 law L4.15 — SUCCESSOR of L3.5, linear operators are their own delta rule
(docs/specs/m4.md §8; docs/specs/m3.md §4).

FROZEN at m4-laws-freeze. Superseded forward under D0106 ruling 2; the M3 file
`tests/laws/m3/test_l3_linear.py` is retained unedited and keeps running. The claim is
L3.5's unchanged; only the binding of the frozen oracle changes — from its bytes, by file
location (`_frozen_bind.m3()`), RT-M3-04's real fix.
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

VALIDATED_BY = "tests/laws/m3/_delta_model.py::check_linear_rules"


@given(w=M.two_worlds(names="ab"))
def test_l4_15_linear_operators_are_their_own_delta_rule(w) -> None:
    schemas, small, big, lost = w
    M.check_linear_rules(TANNEN, schemas, small, big, lost)
