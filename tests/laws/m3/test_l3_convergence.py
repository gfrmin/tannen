"""M3 laws L3.9–L3.10 — source convergence (docs/specs/m3.md §5, BRIEF L3).

FROZEN at m3-laws-freeze.

The heart of BRIEF L3: any partition of a source's arrivals, in any batch order,
interleaved across sources, converges to the one-shot ingest of the net rows —
byte-identically. Retractions net too: arrive/retract/re-arrive streams reach `ingest`
of the surviving rows, and the ledger's `dead` set is exactly the refs the stream
killed. Every perturbation stream is a NAMED case (D0118): `one-shot`, `empty-batch`,
`partition-k`, `interleave`, `arrive-retract`, `partial-retract`, `retract-rearrive`,
`retract-to-empty`, `same-tick-co-arrival`, `right-moves` — drawn on purpose, reported
through `event()`, no thresholds.
"""

from __future__ import annotations

from hypothesis import given

import _delta_model as M  # noqa: E402
from _delta_subject import TANNEN  # noqa: E402

VALIDATED_BY = "tests/laws/m3/_delta_model.py::check_convergence"


@given(s=M.stream_tables(names="a"))
def test_l3_9_and_10_source_convergence(s) -> None:
    """On every single-source shape, the streamed integral equals the one-shot ingest of
    the net rows byte-identically, and `dead` is the stream's kill-list."""
    schemas, ticks, net = s
    M.check_convergence(TANNEN, schemas, ticks, net)
