"""M3 law L3.16 — the differential law (docs/specs/m3.md §9).

FROZEN at m3-laws-freeze.

The `_fragment.py`/DuckDB pattern (L1.16) and the M2 provenance differential (L2.9),
now over TIME: the shipped package and the frozen model, each driving the same
perturbation stream through the same catalogue shape, must agree annotation for
annotation on the final integral — support sets included. Its oracle IS `_model.py`, so
this file declares `VALIDATION_REASON` rather than naming a model family (that would be
circular — the L2.9 precedent). Relation addresses are the one subject-relative atom, so
they are normalised to a placeholder before comparison (the m2 `_relabel` rule, applied
streamwise).
"""

from __future__ import annotations

import pytest
from hypothesis import given, strategies as st

import _delta_model as M  # noqa: E402
from _delta_subject import TANNEN  # noqa: E402

VALIDATION_REASON = (
    "L3.16 IS the differential: its oracle is _model.py, so naming a model family would "
    "be circular (the L2.9 precedent). The model is exercised against its mutants by "
    "tests/test_law_validation.py; this asserts the shipped package matches it over "
    "every catalogue shape and perturbation stream."
)


@pytest.mark.parametrize("shape", M.SHAPES, ids=[s.name for s in M.SHAPES])
@given(data=st.data())
def test_l3_16_the_package_agrees_with_the_model_over_the_stream(shape, data) -> None:
    schemas, ticks, net = data.draw(M.stream_tables(names="".join(shape.tables)))
    M.check_differential(TANNEN, shape, schemas, ticks, net)
