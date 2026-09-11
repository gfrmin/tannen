"""M4 law L4.5 — SpendGuard, default-deny, as a fold over the store
(docs/specs/m4.md §4; BRIEF §4, §5.10; Tier-C door 1).

FROZEN at m4-laws-freeze.

A novel invocation is admitted iff the budget names a scope, a unit and a ceiling for the
oracle's kind and for the total, the oracle's unit is the budget's, and for BOTH ceilings
`ceiling > 0 and spent + worst_case <= ceiling` — so a zero ceiling refuses even a free
call, which is what `budget.yaml` has promised since the opening. The worst case is exact
and known before the call. A reservation is written BEFORE the call and a capture settles
it after, so `spent` is a fold over the store — the settled price of every capture in scope,
and the worst case of every reservation nothing settled — never a counter a second session
could start again from zero. Money is an integer in a named unit; nothing is a float.

Every scenario's outcome is predicted step by step from that rule and the package must
agree, transport call counts included.
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

VALIDATED_BY = "tests/laws/m4/_boundary_model.py::check_spend"


@pytest.mark.parametrize("case", sorted(M.SPEND_CASES))
def test_l4_5_spendguard_agrees_with_the_rule_on_every_named_case(case) -> None:
    M.check_spend(TANNEN, M.SPEND_CASES[case])


@given(s=M.spend_scenarios())
def test_l4_5_spendguard_agrees_with_the_rule_on_drawn_streams(s) -> None:
    M.check_spend(TANNEN, s)
