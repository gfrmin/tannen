"""M2 law L2.7 — lineage is a total `serve`-layer read (docs/specs/m2.md §7).

FROZEN at m2-laws-freeze.

The point of minting resolvable refs (D0126) is that somebody can follow them, and the
point of this law is that following them is TOTAL: an atom that does not resolve is
classified, never raised on. A lineage read that can fail is one nobody puts in a serve
path, and an unfollowable citation would make the whole srcrow/1 write pointless.
"""

from __future__ import annotations

import pytest

from _subject import Rel, Why, sources  # noqa: E402

from tannen.store import Store  # noqa: E402

#: D0094 §3 — L2.7 is about a read surface over the store, which a model cannot have.
VALIDATION_REASON = (
    "lineage resolves refs against a real store; a model of it would be the "
    "implementation, and its assertions are about bytes at rest. The algebra it reads — "
    "the support sets themselves — is model-checked by L2.3-L2.6."
)

SOURCE = "sha256:" + "5e" * 32
ROWS = ({"k": 1, "x": 10}, {"k": 2, "x": 20})
ABSENT = "sha256:" + "de" * 32


@pytest.fixture()
def store(tmp_path):
    return Store(tmp_path / "store")


def test_l2_7_a_source_row_atom_resolves_to_the_source_and_the_row(store) -> None:
    rel = sources.ingest(store, SOURCE, ("k", "x"), ROWS)
    for row, (_, why) in rel:
        supports = sources.lineage(store, why)
        assert len(supports) == 1 and len(supports[0]) == 1
        citation = supports[0][0]
        assert citation.kind == "source-row"
        assert citation.source == SOURCE
        assert citation.row == row


def test_l2_7_an_atom_that_is_not_in_the_store_is_classified_not_raised_on(store) -> None:
    """Totality, and the case that makes it matter: `anti_join` cites the right relation's
    address, and nothing guarantees that relation was ever stored."""
    supports = sources.lineage(store, Why.of({ABSENT}))
    assert supports[0][0].kind == "unresolved"
    assert supports[0][0].ref == ABSENT
    assert supports[0][0].row is None


def test_l2_7_a_stored_value_that_is_not_a_source_row_is_classified_as_a_value(store) -> None:
    rel = Rel(("a",), [({"a": 1}, (1, Why.of({sources.source_row_ref(SOURCE, ROWS[0])})))])
    ref = store.put_value(rel.to_value())
    citation = sources.lineage(store, Why.of({ref}))[0][0]
    assert citation.kind == "value"
    assert citation.ref == ref


def test_l2_7_the_support_set_structure_is_preserved_exactly(store) -> None:
    """Lineage resolves atoms; it does not reshape the antichain. Two witnesses in, two
    witnesses out, with the same atoms in each."""
    a, b, c = (sources.source_row_ref(SOURCE, row) for row in (ROWS[0], ROWS[1], ROWS[0]))
    why = Why.of({a}, {b, ABSENT})
    supports = sources.lineage(store, why)
    assert len(supports) == len(why)
    assert {frozenset(cite.ref for cite in support) for support in supports} == why


def test_l2_7_reading_lineage_changes_neither_the_relation_nor_the_store(store) -> None:
    rel = sources.ingest(store, SOURCE, ("k", "x"), ROWS)
    address, refs = rel.content_address(), set(store.iter_refs())
    for _, (_, why) in rel:
        sources.lineage(store, why)
    assert rel.content_address() == address
    assert set(store.iter_refs()) == refs


def test_l2_7_an_atom_outside_the_pinned_grammar_is_unconstructible() -> None:
    """Why lineage needs no fourth classification: `Why.of` refuses a non-ref by name, so
    a malformed atom cannot reach a Rel and therefore cannot reach a lineage read."""
    with pytest.raises(Exception) as caught:
        Why.of({"not-a-ref"})
    assert caught.type.__name__ == "SemiringError"
