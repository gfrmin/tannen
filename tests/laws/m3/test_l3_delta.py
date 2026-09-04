"""M3 laws L3.1–L3.4 — the delta calculus (docs/specs/m3.md §2–§3).

FROZEN at m3-laws-freeze.

A delta is a `Rel` over the same semiring (§3.1): `Rel` already constructs negative ℤ
counts, and the witnessed-row invariant already gives `(-1, {{r}})` a home and refuses
`(-1, ∅)`. These laws pin the calculus that operates on such relations — delta-capability
declared per component (`negate` law-checked, `Why` a fixed point, `B` refused);
`diff`/`apply` and their identities, with `apply`'s normalisation order (add → cone check
→ group-zero drop → valuation) pinned; the witnessed retraction; and the cone guard that
turns m1 §4.4's promised loud break into an `apply`-site refusal.
"""

from __future__ import annotations

from hypothesis import given

import _delta_model as M  # noqa: E402
from _delta_subject import TANNEN  # noqa: E402

VALIDATED_BY = "tests/laws/m3/_delta_model.py::check_delta_algebra"


@given(w=M.two_worlds(names="ab"))
def test_l3_1_through_4_the_delta_calculus(w) -> None:
    """`diff(R, R) = ∅`; `apply(R, ∅) = R` byte-identically; `apply(R, diff(S, R))`
    reaches `S` and the reverse reaches `R` under the deletion valuation; a pure
    retraction is witnessed by what it retracts; `negate` retracts outright; an
    over-retraction is refused by name (L3.4); an unwitnessed retraction is not a value
    (L3.3, D0110's rule under negation)."""
    schemas, small, big, lost = w
    M.check_delta_algebra(TANNEN, schemas, small, big, lost)
