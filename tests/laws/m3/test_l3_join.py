"""M3 law L3.6 — the bilinear join delta rule (docs/specs/m3.md §4).

FROZEN at m3-laws-freeze.

`join` is bilinear, and the delta rule is PINNED as the two-term form
`join(ΔA, B_old) ⊎ join(A_new, ΔB)` (D0159): on the group components it equals
`A_new ⋈ B_new − A_old ⋈ B_old` outright, and its equivalence to the three-term
expansion `ΔA⋈B_old ⊎ A_old⋈ΔB ⊎ ΔA⋈ΔB` is asserted as a clause. The both-old-sides
spelling drops the same-tick co-arrival term ΔA⋈ΔB and is the mutant
`join-both-sides-old`; this law kills it.
"""

from __future__ import annotations

from hypothesis import given

import _delta_model as M  # noqa: E402
from _delta_subject import TANNEN  # noqa: E402

VALIDATED_BY = "tests/laws/m3/_delta_model.py::check_bilinear_join"


@given(w=M.two_worlds(names="ab"))
def test_l3_6_the_bilinear_join_delta_rule(w) -> None:
    """The two-term form applied to `join(old, old)` reaches `join(new, new)`; the
    three-term expansion reaches the same integral (the two deltas may differ only in
    rows whose counts cancelled, which `apply` drops); both hold in both directions."""
    schemas, small, big, lost = w
    M.check_bilinear_join(TANNEN, schemas, small, big, lost)
