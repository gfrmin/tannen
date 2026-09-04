"""M3 laws L3.7–L3.8 — the integrated operators (docs/specs/m3.md §3.4, §4).

FROZEN at m3-laws-freeze.

`distinct`, `aggregate` and `anti_join` are non-monotone: their delta rule is
replacement (recompute over the new input integral). The D0109 answer's two halves both
live here — replacement over a grow-then-shrink stream reaches the reference per
operator; and a raw delta reaching any of them, or `to_bag`, still RAISES by name, so
negatives are lawful in delta position only. `aggregate` over a declared `AbelianGroup`
adds the subtractive form (L3.8), where P5's "abelian group for subtractability" engages
and the declared `inverse` becomes load-bearing — the mutant `group-inverse-wrong` dies
only because the group laws are tested directly, and `antijoin-eats-delta` (the
D0109/D0114 mutant) dies because feeding a delta to `anti_join` answers where the honest
executor refuses.
"""

from __future__ import annotations

from hypothesis import given

import _delta_model as M  # noqa: E402
from _delta_subject import TANNEN  # noqa: E402

VALIDATED_BY = "tests/laws/m3/_delta_model.py::check_integrated_ops"


@given(w=M.two_worlds(names="ab"))
def test_l3_7_and_8_integrated_operators_consume_integrals_never_deltas(w) -> None:
    schemas, small, big, lost = w
    M.check_integrated_ops(TANNEN, schemas, small, big, lost)
