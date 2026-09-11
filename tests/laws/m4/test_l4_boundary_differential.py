"""M4 law L4.13 — the differential law at the boundary (docs/specs/m4.md §10).

FROZEN at m4-laws-freeze.

The L1.16 / L2.9 / L3.16 pattern, now over invocations: the shipped package and the frozen
model, each driven through the same scenario — sessions in each mode, a budget, oracles of
every kind, a stream of asks across two sessions, injected write faults, a world that
overruns its declared worst case — must agree on every step's outcome, every value read
back, and how many times each transport was called. Capture refs are subject-relative and
never compared; the values read are ref-free by construction. Its oracle IS
`_boundary_model.py`, so this file declares `VALIDATION_REASON` rather than naming a family.
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

M = bind.m4("_boundary_model")
TANNEN = bind.m4("_boundary_subject").make(M)

VALIDATION_REASON = (
    "L4.13 IS the differential: its oracle is _boundary_model.py, so naming a model family "
    "would be circular (the L2.9/L3.16 precedent). The model is exercised against its "
    "mutants by tests/test_law_validation.py; this asserts the shipped package matches it "
    "over every named spend case in every first-session mode and over drawn scenarios."
)


@pytest.mark.parametrize("first", ["spend", "replay", None])
@pytest.mark.parametrize("case", sorted(M.SPEND_CASES))
def test_l4_13_the_package_agrees_with_the_model_on_every_named_case(case, first) -> None:
    budget, oracles, steps, faults = M.SPEND_CASES[case]
    M.check_differential(TANNEN, (budget, oracles, steps, faults, (first, "spend")))


@given(s=M.differential_scenarios())
def test_l4_13_the_package_agrees_with_the_model_on_drawn_scenarios(s) -> None:
    M.check_differential(TANNEN, s)
