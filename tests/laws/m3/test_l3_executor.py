"""M3 law L3.15 — the incremental executor through store and trace
(docs/specs/m3.md §7; BRIEF L1).

FROZEN at m3-laws-freeze.

The convergence laws (L3.9–L3.12) are about the CALCULUS, driven by `_model.run_ticks`.
This is the statement about the SYSTEM: the shipped `tannen.incremental` executor,
threading state and the ledger through the real `Store` and `TraceStore`, is what a user
meets, and it must be the same content-addressed, one-derivation-one-output, replayable
machinery M1 froze — now with a step per tick. A model of the executor would BE the
implementation (D0094 §3, the L2.8 precedent), so this law is `VALIDATION_REASON`, not
model-checked; the algebra it carries through the store is L3.9–L3.12's.

It pins the §7 surface Session B implements:

  DeltaNode(operator, **params)          declared operator application; .descriptor is
                                         the content address of its declared form
  Ledger()  /  Ledger.EMPTY              the dead-set carrier (§6), content-addressed
  advance(store, traces, node, state_ref, delta_refs, ledger_ref)
        -> result with .state_ref, .delta_ref, .ledger_ref, .step_id, .rebuilt
     (state_ref is None on the first tick; step_id is the derivation id of this step,
      the key TraceStore records; rebuilt is False on a trace hit — L1.14's shape)
  ingest_delta(store, source, schema, arrivals, retractions) -> Rel   (tannen.sources)
"""

from __future__ import annotations

import pytest

incremental = pytest.importorskip(
    "tannen.incremental",
    reason="M3 delta executor not implemented yet (law suite frozen ahead of Session B)",
)
sources = pytest.importorskip("tannen.sources")

from tannen.executor import TraceStore  # noqa: E402
from tannen.kernel.rel import Rel  # noqa: E402
from tannen.store import Store  # noqa: E402

VALIDATION_REASON = (
    "the incremental executor, store and trace are machinery: a model of them would BE "
    "the implementation, which the A/B separation exists to prevent (D0094 §3, the L2.8 "
    "precedent). The convergence carried through them is L3.9-L3.12's, model-checked "
    "against _model.py and its mutants."
)

DeltaNode = incremental.DeltaNode
Ledger = incremental.Ledger
advance = incremental.advance
ingest_delta = sources.ingest_delta

SOURCE = "sha256:" + "3e" * 32
SCHEMA = ("k", "x")
ARRIVALS = ({"k": 1, "x": 10}, {"k": 2, "x": 20}, {"k": 3, "x": 30})


@pytest.fixture()
def bench(tmp_path):
    return Store(tmp_path / "store"), TraceStore(tmp_path / "traces")


def _feed(store, entries):
    """A source delta as a stored ref, the shape `advance` consumes."""
    rel = ingest_delta(store, SOURCE, SCHEMA, entries, ())
    return store.put_value(rel.to_value())


def test_l3_15_a_delta_node_descriptor_is_the_address_of_its_declared_form(bench) -> None:
    """Two spellings of the same declared node are the same descriptor; a different
    operand order or parameter is a different one (§7)."""
    a = DeltaNode("select", predicate_id="x-positive")
    b = DeltaNode("select", predicate_id="x-positive")
    c = DeltaNode("project", columns=("k",))
    assert a.descriptor == b.descriptor
    assert a.descriptor != c.descriptor


def test_l3_15_one_derivation_one_output_and_a_replay_hits_the_trace(bench) -> None:
    """A step is a pure function of (descriptor, state, ledger, deltas), so replaying the
    same tick hits the trace and computes nothing new (§7; L1.14 for the reference
    executor, one step on)."""
    store, traces = bench
    node = DeltaNode("select", predicate_id="x-positive")
    d0 = _feed(store, tuple((row, row["x"], SOURCE) for row in ARRIVALS))
    first = advance(store, traces, node, None, [d0], Ledger.EMPTY)
    again = advance(store, traces, node, None, [d0], Ledger.EMPTY)
    assert first.state_ref == again.state_ref
    assert not again.rebuilt, "a replayed step must be served from the trace, not recomputed"


def test_l3_15_an_empty_tick_moves_no_state(bench) -> None:
    """`apply(R, ∅)` is `R` byte-identically (L3.2), so an empty delta advances the state
    ref to itself — idempotency (BRIEF L2) at the executor."""
    store, traces = bench
    node = DeltaNode("select", predicate_id="x-positive")
    d0 = _feed(store, tuple((row, row["x"], SOURCE) for row in ARRIVALS))
    seeded = advance(store, traces, node, None, [d0], Ledger.EMPTY)
    empty = store.put_value(Rel(SCHEMA, []).to_value())
    stepped = advance(store, traces, node, seeded.state_ref, [empty], seeded.ledger_ref)
    assert stepped.state_ref == seeded.state_ref


def test_l3_15_a_tampered_trace_raises(bench) -> None:
    """A recorded output that no longer resolves is not a cache miss (L1.14's rule, one
    step on): the executor raises rather than quietly rebuilding."""
    store, traces = bench
    node = DeltaNode("select", predicate_id="x-positive")
    d0 = _feed(store, tuple((row, row["x"], SOURCE) for row in ARRIVALS))
    done = advance(store, traces, node, None, [d0], Ledger.EMPTY)
    from tannen.executor import TraceIntegrityError
    traces.record(done.step_id, "sha256:" + "00" * 32)  # a mapping to nothing
    with pytest.raises(TraceIntegrityError):
        advance(store, traces, node, None, [d0], Ledger.EMPTY)
