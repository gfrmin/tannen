"""M5 law L5.1 — `tannen run` is clamped to the checked-in budget (docs/specs/m5.md §6;
BRIEF §5.10, §9.2 door 1; D0240 item (2), D0241, D0242).

FROZEN at m5-laws-freeze. Successor of ONE node:
`tests/laws/m4/test_l4_modes.py::test_l4_4_tannen_run_spend_is_the_one_spelling_that_can_call`,
which spends through the CLI against a budget file of its own. Owner ruling D0240: a library
enforces the authorisation it is handed and must not read the constitution, so the CLI — not
SpendGuard — is where the checked-in budget.yaml binds. The retirement is `pending` in
governance/laws.yaml at this freeze (the node still passes until the clamp lands, D0128), and
Session B promotes it to `superseded` in the change that lands the clamp.

THE RULE. Without `--spend`, neither budget flag is consulted: replay-only refuses a novel
invocation exactly as L4.4 froze. With `--spend`:
  - no flag, or `--budget` naming the checked-in budget.yaml at `find_root()`: admitted against
    that file;
  - `--budget` naming ANY OTHER file: refused as `SpendDenied`, naming `--budget-override`,
    before the transport and with nothing written;
  - `--budget-override PATH`: admitted against PATH — the one spelling that spends against a
    budget the repository did not check in, and the claim the retired node carried;
  - both flags: a usage error.
Admission is L4.5's: a zero ceiling refuses even a zero-priced call. A capture made under
`--spend` replays without it and reaches no transport.

The refusal is `SpendDenied`, not a new class, deliberately: L4.4's second node (`--spend` with
a zero budget of its own) must keep reading `SpendDenied`, and only its third node is retired.
"""

from __future__ import annotations

import importlib.util as _ilu
from pathlib import Path as _Path

import pytest

REPO_ROOT = _Path(__file__).resolve().parents[3]
if not (REPO_ROOT / ".dogfood" / "corpus.json").is_file():
    pytest.skip("M5 dogfood corpus absent — every M5 law goes live together when an authorised "
                "corpus is present at .dogfood/corpus.json (docs/specs/m5.md §8)",
                allow_module_level=True)

pytest.importorskip("tannen.dogfood", reason=(
    "M5 dogfood not implemented yet (law suite frozen ahead of Session B); M5's laws go "
    "live together — docs/specs/m5.md §8"))

_spec = _ilu.spec_from_file_location("tannen_frozen_m5._dogfood_bind",
                                     _Path(__file__).with_name("_dogfood_bind.py"))
bind = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(bind)

M = bind.m5("_dogfood_model")
TANNEN = bind.m5("_dogfood_subject").make(M)

VALIDATED_BY = "tests/laws/m5/_dogfood_model.py::check_clamp"


@pytest.mark.parametrize("scenario", M.CLAMP_SCENARIOS,
                         ids=[f"spend={s}-{f}-in{c}-other{o}" for s, f, c, o in M.CLAMP_SCENARIOS])
def test_l5_1_tannen_run_is_clamped_to_the_checked_in_budget(scenario) -> None:
    M.check_clamp(TANNEN, scenario)


def test_l5_1_budget_override_is_the_one_spelling_that_spends_against_another_file() -> None:
    """The retired node's claim, carried forward: with the checked-in budget at zero and another
    file authorising the call, `--budget` cannot spend against it and `--budget-override` can —
    and what it captured replays without `--spend`."""
    M.check_clamp(TANNEN, (True, "budget-other", 0, M.BIG))
    M.check_clamp(TANNEN, (True, "override-other", 0, M.BIG))
