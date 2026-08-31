"""M2 law L2.6 — the absence witness is a conjunction (docs/specs/m2.md §6; D0132).

FROZEN at m2-laws-freeze.

`anti_join` is outside RA+, so no derivation fixes what its survivors should cite; the
choice is a convention and this law is where the convention is pinned. tannen as shipped
at M1 combines the witness with `add`, which reads as OR and leaves the citation standing
as an INDEPENDENT derivation of a row it cannot derive — so an output row is predicted to
survive the deletion of the very source row it came from. The claim being made is
conjunctive: "this row's own derivation held AND the right relation lacked this key at
this version." `_model.MUTANTS["antijoin-disjunctive"]` is the M1 behaviour, kept as the
mutant this law must kill.
"""

from __future__ import annotations

import pytest
from hypothesis import given, strategies as st

import _model as M  # noqa: E402
from _subject import TANNEN  # noqa: E402

VALIDATED_BY = "tests/laws/m2/_model.py::check_absence_witness"


@pytest.mark.parametrize("shape", M.ANTI, ids=[s.name for s in M.ANTI])
@pytest.mark.parametrize("overlap", ["partial", "none", "full"])
@given(st.data())
def test_l2_6_the_absence_witness_is_conjunctive_and_deletion_invalidates_it(
    shape, overlap, data
) -> None:
    """Three claims (§6): every survivor's every support set carries the right relation's
    address; an empty right operand is cited by nothing, because there was nothing to
    check; and deleting any row the right operand reads moves that address, so no witness
    of the old output survives into the new one — an anti-join's rows are recomputed,
    never inherited.

    `overlap` is drawn as a NAMED case rather than left to chance (D0118): `partial` gives
    the operator something to both keep and drop, `none` makes every left row survive, and
    `full` empties the result — the case that would otherwise be the accidental default.
    """
    tables = data.draw(M.source_tables(names=shape.tables, overlap=overlap))
    M.check_absence_witness(TANNEN, shape, tables)
