"""M4 law L4.14 — SUCCESSOR of L3.1–L3.4, the delta calculus (docs/specs/m4.md §8;
docs/specs/m3.md §2–§3).

FROZEN at m4-laws-freeze. Superseded forward under D0106 ruling 2; the M3 file
`tests/laws/m3/test_l3_delta.py` is retained unedited and keeps running.

The claim is L3.1–L3.4's, verbatim in substance: delta-capability is declared per
component; `diff(R, R) = ∅`, `apply(R, ∅) = R`, `apply(R, diff(S, R))` reaches `S`; a
retraction is witnessed by what it retracts; an over-retraction is refused by name. Two
things change, and only two. (1) The frozen oracle is bound FROM ITS BYTES by file location
(`_frozen_bind.m3()`), never by a bare import a decoy can claim first — RT-M3-04's real fix.
(2) RT-M3-05's answer: L3.1–L3.4 are four rows sharing one frozen check, and a row that
shares its only node is a clause of the law that node attests. So they are ONE law here,
with four clauses, and one evidence record says so honestly.
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

VALIDATED_BY = "tests/laws/m3/_delta_model.py::check_delta_algebra"


@given(w=M.two_worlds(names="ab"))
def test_l4_14_the_delta_calculus(w) -> None:
    schemas, small, big, lost = w
    M.check_delta_algebra(TANNEN, schemas, small, big, lost)
