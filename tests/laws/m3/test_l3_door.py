"""M3 laws L3.13–L3.14 — the two doors D0142 routed here (docs/specs/m3.md §2.2, §2.3).

FROZEN at m3-laws-freeze.

L3.13 closes RT-M2-04: `why_slots` finds EVERY `Why` location by recursive descent, so
the witnessed-row refusal fires under every multi-`Why` product — `product(Why, Why)`,
`product(ZxWhy, B)`, `product(Z, ZxWhy)`, `product(ZxWhy, ZxWhy)` — making frozen m2 §3's
"any semiring carrying a Why" true at its stated strength; and `anti_join` refuses a
multi-`Why` semiring by name, because its absence witness has two inequivalent readings
there. The shipped M2 locator, returning only the first slot, is the mutant
`why-slot-first-match`. L3.14 closes RT-M2-07: the encode gate refuses a non-grammar
atom, so no spelling puts one into a `Rel`, a canonical form, or a content address.
"""

from __future__ import annotations

import _delta_model as M  # noqa: E402
from _delta_subject import TANNEN  # noqa: E402

VALIDATED_BY = "tests/laws/m3/_delta_model.py::check_doors"


def test_l3_13_and_14_the_multi_why_door_and_the_encode_gate() -> None:
    """No generator: the door checks quantify over `_model.SEMIRING_SPECS`, a fixed set
    chosen to exercise every product shape the single-slot locator misses."""
    M.check_doors(TANNEN)
