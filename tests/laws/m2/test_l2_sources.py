"""M2 laws L2.1–L2.2 — source identity, and the annotation that must be witnessed
(docs/specs/m2.md §2, §3).

FROZEN at m2-laws-freeze. L2.2 carries forward the claim of the M1 node retired by D0128
(`test_l1_5_mixing_semirings_is_refused_by_name`), which constructs `(2, Why.zero)` as
incidental filler — a value D0110 makes unconstructible. The claim was never wrong; only
its filler was, so it is restated here with a witnessed one.
"""

from __future__ import annotations

import pytest
from hypothesis import given, strategies as st

import _model as M  # noqa: E402
from _subject import TANNEN, Rel, RelError, Why, ops, sources  # noqa: E402

from tannen.kernel.encoding import CanonicalEncodingError, content_address  # noqa: E402
from tannen.kernel.refs import RefError, is_ref  # noqa: E402
from tannen.kernel.semiring import Z  # noqa: E402
from tannen.store import Store  # noqa: E402

#: D0094 §3. L2.1 is about the store and cannot be model-checked: a model of it would BE
#: the implementation, which is what the A/B separation exists to prevent. L2.2's algebra
#: half is model-checked; the declaration names the stronger of the two.
VALIDATED_BY = "tests/laws/m2/_model.py::check_witnessed_construction"
VALIDATION_REASON = (
    "L2.1 is store IO — a model of `ingest` writing one srcrow/1 value per row would be "
    "the implementation. Its assertions are about bytes at rest, which the model cannot "
    "have. L2.2 is model-checked (see VALIDATED_BY)."
)

SOURCE = "sha256:" + "5e" * 32
OTHER = "sha256:" + "6f" * 32
ROWS = ({"k": 1, "x": 10}, {"k": 1, "x": 11}, {"k": 2, "x": 10})


@pytest.fixture()
def store(tmp_path):
    return Store(tmp_path / "store")


def test_l2_1_a_source_row_ref_is_the_address_of_what_it_names(store) -> None:
    for row in ROWS:
        ref = sources.source_row_ref(SOURCE, row)
        assert is_ref(ref), "a source row ref is a ref in the pinned grammar"
        assert ref == content_address(sources.source_row_value(SOURCE, row))


def test_l2_1_distinct_rows_and_distinct_sources_get_distinct_refs() -> None:
    """What makes the deletion test discriminate (D0126): one ref per source row, not one
    per source, and not one per row content shared across sources."""
    refs = {sources.source_row_ref(SOURCE, row) for row in ROWS}
    assert len(refs) == len(ROWS)
    assert sources.source_row_ref(SOURCE, ROWS[0]) != sources.source_row_ref(OTHER, ROWS[0])


def test_l2_1_every_atom_an_ingest_mints_resolves_to_the_row_it_names(store) -> None:
    """A citation to a document that does not exist is not provenance. `ingest` writes the
    value before it hands out the ref."""
    rel = sources.ingest(store, SOURCE, ("k", "x"), ROWS)
    for _, (_, why) in rel:
        for support in why:
            for atom in support:
                value = store.get_value(atom)
                assert value["tannen"] == sources.SOURCE_ROW_TAG
                assert value["source"] == SOURCE
                assert value["row"] in ROWS


def test_l2_1_an_ingested_row_is_annotated_with_its_own_ref_and_nothing_else(store) -> None:
    rel = sources.ingest(store, SOURCE, ("k", "x"), ROWS)
    assert rel.annotations.name == "Z*Why", "sources are ZxWhy: deltas AND support, unasked"
    for row, (count, why) in rel:
        assert count == 1
        assert why == Why.of({sources.source_row_ref(SOURCE, row)})


def test_l2_1_identical_rows_in_one_source_are_one_row_with_one_witness(store) -> None:
    """A source is content-addressed, so two identical rows are the same row: the count
    adds and the witness does not. Stated because the alternative — an index in the ref —
    would make ingest order-dependent, which is the one thing content addressing buys."""
    rel = sources.ingest(store, SOURCE, ("k", "x"), (ROWS[0], ROWS[0], ROWS[1]))
    assert len(rel) == 2
    assert rel.get(ROWS[0]) == (2, Why.of({sources.source_row_ref(SOURCE, ROWS[0])}))


def test_l2_1_ingest_is_idempotent(store) -> None:
    """The store is write-once and append-only; re-ingesting the same source writes
    nothing new and yields the same Rel, byte for byte (L0.5)."""
    first = sources.ingest(store, SOURCE, ("k", "x"), ROWS)
    refs = set(store.iter_refs())
    second = sources.ingest(store, SOURCE, ("k", "x"), ROWS)
    assert first.content_address() == second.content_address()
    assert set(store.iter_refs()) == refs


def test_l2_1_a_row_outside_the_encodable_domain_is_refused_by_name(store) -> None:
    """The M0 door, unchanged: ingest mints no ref for a row it cannot canonicalise."""
    with pytest.raises(CanonicalEncodingError):
        sources.ingest(store, SOURCE, ("k", "x"), [{"k": 1, "x": 1.5}])
    assert list(store.iter_refs()) == [], "nothing is written for a row that was refused"


def test_l2_1_a_source_that_is_not_a_ref_is_refused_by_name(store) -> None:
    """The pinned grammar has one home (`tannen.kernel.refs`) and ingest does not open a
    second: a source that is not a ref cannot become the `source` field of a srcrow/1."""
    with pytest.raises(RefError):
        sources.ingest(store, "not-a-ref", ("k", "x"), ROWS)
    assert list(store.iter_refs()) == []


def test_l2_2_an_annotation_claiming_copies_it_cannot_derive_is_refused() -> None:
    """D0110, owner-authorised. `(n, ∅)` asserts "n copies of this row, and there is no
    derivation of it", which is a contradiction in a provenance semiring, not a value."""
    M.check_witnessed_construction(TANNEN)


def test_l2_2_from_value_refuses_it_too() -> None:
    """The door is at construction or it is not a door: a stored `rel/1` carrying `[n, []]`
    decodes through the same check."""
    poisoned = {
        "tannen": "rel/1", "schema": ["a"], "semiring": "Z*Why",
        "rows": [[{"a": 1}, [2, []]]],
    }
    with pytest.raises(RelError):
        Rel.from_value(poisoned)


def test_l2_2_a_semiring_with_no_why_component_is_untouched() -> None:
    """The rule is located structurally by `why_slot` (D0109), so `Z` — which makes no
    provenance claim — keeps accepting every annotation it always did."""
    rel = Rel(("a",), [({"a": 1}, 2)], annotations=Z, annotations_reason="law: Z makes no claim")
    assert len(rel) == 1


def test_l2_2_mixing_semirings_is_still_refused_by_name() -> None:
    """Carried forward from the M1 node D0128 retires. The claim is unchanged; only the
    filler annotation is now a witnessed one."""
    witness = Why.of({"sha256:" + "11" * 32})
    z_rel = Rel(("a",), [({"a": 1}, 2)], annotations=Z, annotations_reason="law: the Z side")
    default_rel = Rel(("a",), [({"a": 1}, (2, witness))])
    with pytest.raises(ops.OperatorError):
        ops.union(z_rel, default_rel).unwrap()
