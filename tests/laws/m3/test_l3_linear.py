"""M3 law L3.5 — linear operators are their own delta rule (docs/specs/m3.md §4).

FROZEN at m3-laws-freeze.

DBSP's rule for linear operators: `select`, `project`, `map_rows`, `union` commute with
differentiation, so applying `op(Δ)` to `op(old)` reaches `op(new)` — no separate delta
rule to write, and the M1 operators (whose semiring rules use `add`/`mul` only, never the
bag image) already compute their own delta form. Tested in both directions, because the
shrink direction is where the M1 cone assumption L1.9 froze first meets a negative.
"""

from __future__ import annotations

from hypothesis import given

import _delta_model as M  # noqa: E402
from _delta_subject import TANNEN  # noqa: E402

VALIDATED_BY = "tests/laws/m3/_delta_model.py::check_linear_rules"


@given(w=M.two_worlds(names="ab"))
def test_l3_5_linear_operators_are_their_own_delta_rule(w) -> None:
    schemas, small, big, lost = w
    M.check_linear_rules(TANNEN, schemas, small, big, lost)
