"""M2 laws L2.3–L2.4 — provenance soundness by deletion, and minimal witnesses
(docs/specs/m2.md §5; BRIEF §6 law L5).

FROZEN at m2-laws-freeze. Defects here are never edited: record the defect, freeze a
superseding file under the CURRENT milestone's directory, mark the old one superseded in
MANIFEST.sha256's notes (CLAUDE.md; D0106 ruling 2).

BRIEF §6 asks for soundness — "delete a source row; every changed output row must have
carried its ref". Antichain-normalised `Why` is PosBool, so the true statement is an
IFF and it is what is frozen here (D0127): the witnesses of an output row over `R \\ D`
are exactly the witnesses over `R` that D does not touch. Soundness is a corollary.
"""

from __future__ import annotations

import pytest
from hypothesis import given, strategies as st

import _model as M  # noqa: E402  (the model half, frozen beside this file)
from _subject import TANNEN  # noqa: E402  (skips the module until tannen.sources exists)

#: D0094 §3 — every frozen law file declares how it was validated before the freeze.
VALIDATED_BY = "tests/laws/m2/_model.py::check_deletion_characterisation"


def _one_atom(tables, pick: int):
    atoms = M.source_atoms(tables)
    return frozenset(atoms[pick % len(atoms):][:1]) if atoms else frozenset()


@pytest.mark.parametrize("shape", M.POSITIVE, ids=[s.name for s in M.POSITIVE])
@given(st.data())
def test_l2_3_deleting_sources_leaves_exactly_the_untouched_witnesses(shape, data) -> None:
    """L5 at full strength on the positive fragment: `select`, `project`, `map_rows`,
    `union`, `join`, `distinct`. A row survives iff some support set is disjoint from the
    deleted refs, and it survives carrying exactly those support sets."""
    tables = data.draw(M.source_tables(names=shape.tables, overlap="partial"))
    deleted = _one_atom(tables, data.draw(st.integers(0, 5)))
    M.check_deletion_characterisation(TANNEN, shape, tables, deleted)


@pytest.mark.parametrize("shape", M.ANTI, ids=[s.name for s in M.ANTI])
@given(st.data())
def test_l2_3_the_theorem_holds_across_an_anti_join_for_left_deletions(shape, data) -> None:
    """Deleting on the LEFT of an anti-join leaves the right relation's address unmoved,
    so the same characterisation applies unchanged. Deleting on the RIGHT moves that
    address and is L2.6's subject — the two halves are separated here rather than
    averaged into one weaker claim."""
    tables = data.draw(M.source_tables(names=shape.tables, overlap="partial"))
    left = M.source_atoms({shape.tables[0]: tables[shape.tables[0]]})
    M.check_deletion_characterisation(TANNEN, shape, tables, frozenset(left[:1]))


@pytest.mark.parametrize("shape", M.AGGREGATE, ids=[s.name for s in M.AGGREGATE])
@pytest.mark.parametrize("overlap", ["grouped", "full"])
@given(st.data())
def test_l2_3_an_aggregate_carries_the_theorem_on_its_group_key(shape, overlap, data) -> None:
    """`aggregate` is outside the fragment above, and the reason is stated rather than
    worked around: the folded value reads the deleted rows' VALUES, so deleting a
    contributing row replaces the output row with a different one and no claim about
    THAT row surviving could be true. The group key is where the theorem lives."""
    tables = data.draw(M.source_tables(names=shape.tables, overlap=overlap))
    deleted = _one_atom(tables, data.draw(st.integers(0, 5)))
    M.check_aggregate_key_characterisation(TANNEN, shape, tables, deleted)


@pytest.mark.parametrize("shape", M.POSITIVE, ids=[s.name for s in M.POSITIVE])
@given(st.data())
def test_l2_4_every_support_set_is_a_minimal_witness(shape, data) -> None:
    """Antichain, sufficiency, minimality (§5.2). Minimality is NOT "deleting a proper
    subset leaves the row standing" — a join witness `{a, b}` dies when either half goes
    and is minimal all the same. It is that keeping only the support set yields the row,
    and keeping only a proper subset of it does not."""
    tables = data.draw(M.source_tables(names=shape.tables, overlap="full"))
    M.check_minimal_witnesses(TANNEN, shape, tables)
