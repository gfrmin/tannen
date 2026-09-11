"""M4 law L4.2 — capture before read (docs/specs/m4.md §3; BRIEF P1, §4).

FROZEN at m4-laws-freeze.

"All nondeterminism enters through oracles whose outputs are captured immutably before
anything reads them." The caller of an invocation receives a capture's ref, and the only
value it can read is what that capture — already in the store — says. If the reservation or
the capture cannot be written, the invocation is refused and no value escapes; a returned
ref resolves in a fresh session over the same store; and a capture altered behind the
store's back is refused on read, never served from a copy held in memory.
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

M = bind.m4("_boundary_model")
TANNEN = bind.m4("_boundary_subject").make(M)

VALIDATED_BY = "tests/laws/m4/_boundary_model.py::check_capture_before_read"


@pytest.mark.parametrize("kind", M.KINDS)
def test_l4_2_a_clean_invocation_is_read_back_from_its_capture(kind) -> None:
    M.check_capture_before_read(TANNEN, kind, M.spec_for(kind, 0, 1), "none")


@pytest.mark.parametrize("kind", M.KINDS)
@pytest.mark.parametrize("fault", ["reservation", "capture"])
def test_l4_2_a_write_that_did_not_happen_withholds_the_value(kind, fault) -> None:
    """A failed reservation write means nothing was called; a failed capture write after
    the call means the value is withheld — either way the caller gets a refusal by name."""
    M.check_capture_before_read(TANNEN, kind, M.spec_for(kind, 0, 1), fault)
