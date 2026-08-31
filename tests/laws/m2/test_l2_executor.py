"""M2 law L2.8 — deletion commutes with the executor (docs/specs/m2.md §8).

FROZEN at m2-laws-freeze.

L2.3 is a statement about the algebra. This is the statement about the SYSTEM: the same
theorem holds when the relations travel through the store and the transform through a
registered descriptor, which is the only form in which a user ever meets it. It is where
"provenance" stops being a property of `Why` and becomes a property of a pipeline.
"""

from __future__ import annotations

import pytest

from _subject import ops, sources  # noqa: E402

from tannen.executor import AlwaysRebuild, Node, TraceStore  # noqa: E402
from tannen.kernel.rel import Rel  # noqa: E402
from tannen.store import Store  # noqa: E402
from tannen.transform import transform  # noqa: E402

#: D0094 §3 — the executor, the store and the trace are machinery; a model of them would
#: be the implementation, which is what the A/B separation exists to prevent (D0094's own
#: scope note). The algebra this law carries through them is model-checked by L2.3.
VALIDATION_REASON = (
    "the executor, store and trace are machinery: a model of them would BE the "
    "implementation. The provenance claim carried through them is L2.3's, which is "
    "model-checked against _model.py and six mutants."
)

SOURCE = "sha256:" + "5e" * 32
LEFT = ({"k": 1, "x": 10}, {"k": 2, "x": 20}, {"k": 3, "x": 30})


@transform(kind="law", params={"law": "L2.8"})
def keep_positive_keys(rel):
    """The node under test: a filter, so the output rows are the input rows and their
    provenance travels unchanged."""
    return ops.select(rel, lambda row: row["k"] > 1)


@pytest.fixture()
def bench(tmp_path):
    return Store(tmp_path / "store"), TraceStore(tmp_path / "traces")


def _build(store, traces, rows):
    rel = sources.ingest(store, SOURCE, ("k", "x"), rows)
    node = Node(keep_positive_keys, [store.put_value(rel.to_value())])
    built = AlwaysRebuild().build(node, store, traces)
    return node, built, Rel.from_value(store.get_value(built.output_ref))


def test_l2_8_a_derivation_carries_its_sources_witnesses(bench) -> None:
    store, traces = bench
    _, _, out = _build(store, traces, LEFT)
    source = sources.ingest(store, SOURCE, ("k", "x"), LEFT)
    for row, (_, why) in out:
        assert why == source.get(row)[1], "a filter moves rows, never their witnesses"


def test_l2_8_deleting_a_source_row_removes_exactly_the_rows_that_cited_it(bench) -> None:
    """L5 through the store and the executor, end to end."""
    store, traces = bench
    _, _, before = _build(store, traces, LEFT)
    deleted = sources.source_row_ref(SOURCE, LEFT[1])
    _, _, after = _build(store, traces, [row for row in LEFT if row != LEFT[1]])
    for row, (_, why) in before:
        cited = any(deleted in support for support in why)
        assert (after.get(row) == before.get(row)) != cited, (
            "a row that cited the deleted source row must have changed, and one that did "
            "not must not have"
        )


def test_l2_8_the_deleted_source_is_a_different_derivation(bench) -> None:
    """A trace hit must never serve the pre-deletion answer: the input ref moves, so the
    derivation id moves, and `TraceStore` keeps one output per derivation (L1.14)."""
    store, traces = bench
    first, _, _ = _build(store, traces, LEFT)
    second, _, _ = _build(store, traces, LEFT[:2])
    assert first.derivation_id != second.derivation_id
    assert traces.lookup(first.derivation_id) != traces.lookup(second.derivation_id)


def test_l2_8_a_stored_and_reloaded_rel_keeps_its_provenance(bench) -> None:
    """`rel/1` round-trips the support sets, so provenance survives the store rather than
    living only in memory (L1.4's round-trip, now with witnesses that mean something)."""
    store, _ = bench
    rel = sources.ingest(store, SOURCE, ("k", "x"), LEFT)
    ref = store.put_value(rel.to_value())
    assert Rel.from_value(store.get_value(ref)) == rel
