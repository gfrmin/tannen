"""M4 law L4.21 — SUCCESSOR of L3.15, the incremental executor through store and trace,
CORRECTED (docs/specs/m4.md §8; docs/specs/m3-corrections.md §1–§2; BRIEF L1).

FROZEN at m4-laws-freeze. Superseded forward under D0106 ruling 2; the M3 file
`tests/laws/m3/test_l3_executor.py` is retained unedited and keeps running — its assertions
still hold; what was false was what they were said to show.

L3.15's node was named `…_a_replay_hits_the_trace` and its docstring said a step "is a pure
function of (descriptor, state, ledger, deltas), so replaying the same tick hits the trace".
Both were false as frozen (D0204, owner ruling D0171 (1)): `advance` consults the trace and
by default writes none, so a default replay RECOMPUTES and writes nothing new — `rebuilt` is
a store measurement, not a trace hit — and the step was also a function of a registry named
in none of those inputs (RT-M3-01, D0197). This law states what is true:

  * a DeltaNode's descriptor is the content address of its declared form;
  * a default replay builds nothing new, and leaves the trace unwritten;
  * a step the caller RECORDED is served from the trace;
  * an empty tick moves no state;
  * a tampered trace raises — not a cache miss;
  * replay is byte-deterministic across fresh stores.

NOT carried forward, and stated: the L3.15 row's "a quarantining step moves nothing". No
L3.15 node ever tested it, and a successor may not state more than its nodes attest (D0161's
holding). Code-address identity is RT-M3-01's law, L4.23.
"""

from __future__ import annotations

import pytest

pytest.importorskip("tannen.oracles", reason=(
    "M4 boundary not implemented yet (law suite frozen ahead of Session B); M4's laws go "
    "live together — docs/specs/m4.md §11"))
incremental = pytest.importorskip("tannen.incremental")
sources = pytest.importorskip("tannen.sources")

from tannen.executor import TraceIntegrityError, TraceStore  # noqa: E402
from tannen.kernel.rel import Rel  # noqa: E402
from tannen.store import Store  # noqa: E402

VALIDATION_REASON = (
    "the incremental executor, store and trace are machinery: a model of them would BE the "
    "implementation, which the A/B separation exists to prevent (D0094 §3, the L2.8 and "
    "L3.15 precedent). The convergence carried through them is L4.18-L4.19's and L4.24's."
)

DeltaNode = incremental.DeltaNode
Ledger = incremental.Ledger
advance = incremental.advance

SOURCE = "sha256:" + "3e" * 32
SCHEMA = ("k", "x")
ARRIVALS = ({"k": 1, "x": 10}, {"k": 2, "x": 20}, {"k": 3, "x": 30})


def _bench(root):
    return Store(root / "store"), TraceStore(root / "traces")


def _feed(store, entries):
    rel = sources.ingest_delta(store, SOURCE, SCHEMA, entries, ())
    return store.put_value(rel.to_value())


def _arrivals():
    return tuple((row, row["x"], SOURCE) for row in ARRIVALS)


def test_l4_21_a_delta_node_descriptor_is_the_address_of_its_declared_form() -> None:
    a = DeltaNode("select", predicate_id="x-positive")
    b = DeltaNode("select", predicate_id="x-positive")
    c = DeltaNode("project", columns=("k",))
    assert a.descriptor == b.descriptor
    assert a.descriptor != c.descriptor


def test_l4_21_a_default_replay_builds_nothing_new_and_writes_no_trace(tmp_path) -> None:
    store, traces = _bench(tmp_path)
    node = DeltaNode("select", predicate_id="x-positive")
    d0 = _feed(store, _arrivals())
    first = advance(store, traces, node, None, [d0], Ledger.EMPTY)
    again = advance(store, traces, node, None, [d0], Ledger.EMPTY)
    assert (first.state_ref, first.delta_ref, first.ledger_ref) == \
        (again.state_ref, again.delta_ref, again.ledger_ref)
    assert first.step_id == again.step_id
    assert not again.rebuilt, "a replay wrote something the store did not already hold"
    assert traces.lookup(first.step_id) is None, "advance recorded a trace nobody asked for"


def test_l4_21_a_recorded_step_is_served_from_the_trace(tmp_path) -> None:
    store, traces = _bench(tmp_path)
    node = DeltaNode("select", predicate_id="x-positive")
    d0 = _feed(store, _arrivals())
    done = advance(store, traces, node, None, [d0], Ledger.EMPTY, record=True)
    assert traces.lookup(done.step_id) is not None, "record=True wrote no trace"
    served = advance(store, traces, node, None, [d0], Ledger.EMPTY)
    assert not served.rebuilt
    assert (served.state_ref, served.delta_ref, served.ledger_ref) == \
        (done.state_ref, done.delta_ref, done.ledger_ref)


def test_l4_21_an_empty_tick_moves_no_state(tmp_path) -> None:
    store, traces = _bench(tmp_path)
    node = DeltaNode("select", predicate_id="x-positive")
    seeded = advance(store, traces, node, None, [_feed(store, _arrivals())], Ledger.EMPTY)
    empty = store.put_value(Rel(SCHEMA, []).to_value())
    stepped = advance(store, traces, node, seeded.state_ref, [empty], seeded.ledger_ref)
    assert stepped.state_ref == seeded.state_ref


def test_l4_21_a_tampered_trace_raises(tmp_path) -> None:
    store, traces = _bench(tmp_path)
    node = DeltaNode("select", predicate_id="x-positive")
    d0 = _feed(store, _arrivals())
    done = advance(store, traces, node, None, [d0], Ledger.EMPTY)
    traces.record(done.step_id, "sha256:" + "00" * 32)
    with pytest.raises(TraceIntegrityError):
        advance(store, traces, node, None, [d0], Ledger.EMPTY)


def test_l4_21_replay_is_byte_deterministic_across_fresh_stores(tmp_path) -> None:
    ticks = (_arrivals(), (({"k": 4, "x": 40}, 1, SOURCE),))

    def run(root):
        store, traces = _bench(root)
        node = DeltaNode("select", predicate_id="x-positive")
        state, ledger, out = None, Ledger.EMPTY, []
        for entries in ticks:
            done = advance(store, traces, node, state, [_feed(store, entries)], ledger)
            state, ledger = done.state_ref, done.ledger_ref
            out.append((done.step_id, done.state_ref, done.delta_ref, done.ledger_ref))
        return out

    assert run(tmp_path / "one") == run(tmp_path / "two")
