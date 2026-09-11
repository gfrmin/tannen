"""Executor and source-delta behaviour chosen during implementation, beyond what frozen
L3.15 pins (docs/specs/m3.md §6, §7).

L3.15 states that the shipped executor is content-addressed, one-derivation-one-output
and replayable, over one unary node. The convergence the executor carries is L3.9–L3.12's
and is model-checked there. What is left — the entry shape `ingest_delta` accepts, what
each refusal SAYS, the ledger's ordering rule, the contagion rule as the caller must
spell it, and the two properties `advance` inherits from M1 rather than inventing — is
decided here, outside `tests/laws/` where it can be edited.

`tests/laws/` is sealed (D0089), so this file is where an implementation-detail test for
M3's shell belongs; the M0 precedent is `tests/test_kernel_surface.py`.
"""

from __future__ import annotations

import pytest

from tannen.executor import TraceStore
from tannen.incremental import (
    MONOIDS,
    Advanced,
    DeltaNode,
    Ledger,
    advance,
    register_predicate,
)
from tannen.kernel import ops
from tannen.kernel.outcome import OperatorError
from tannen.kernel.refs import RefError
from tannen.kernel.rel import Rel, RelError
from tannen.sources import ingest, ingest_delta, lineage, source_row_ref
from tannen.store import Store

SOURCE_A = "sha256:" + "a1" * 32
SOURCE_B = "sha256:" + "b2" * 32
SCHEMA_A = ("k", "x")
SCHEMA_B = ("k", "y")

A1 = {"k": 1, "x": 5}
A2 = {"k": 2, "x": 7}
A3 = {"k": 3, "x": 8}
B1 = {"k": 1, "y": 9}
B2 = {"k": 2, "y": 11}


class Runner:
    """The caller side of §7: it owns the topological order and threads the ledger.

    There is no graph object in `tannen.incremental` on purpose (§7), so a driver like
    this is what a user writes. Keeping it in the test rather than in the package is the
    point: it has no law of its own, and API surface with no law is what M3 declined.
    """

    def __init__(self, tmp_path) -> None:
        self.store = Store(tmp_path / "store")
        self.traces = TraceStore(tmp_path / "traces")
        self.ledger = Ledger.EMPTY
        self.state: dict[str, str | None] = {}
        self.delta: dict[str, str] = {}
        self.integral: dict[str, str] = {}

    def feed(self, source: str, schema, arrivals=(), retractions=()) -> str:
        rel = ingest_delta(self.store, source, schema, arrivals, retractions)
        return self.store.put_value(rel.to_value())

    def step(self, name: str, node: DeltaNode, inputs, **kwargs) -> Advanced:
        done = advance(
            self.store, self.traces, node, self.state.get(name), inputs, self.ledger, **kwargs
        )
        self.state[name] = done.state_ref
        self.ledger = Ledger.from_value(self.store.get_value(done.ledger_ref))
        self.delta[name] = done.delta_ref
        self.integral[name] = self.store.get_value(done.state_ref)["output"]
        return done

    def rel(self, name: str) -> Rel:
        return Rel.from_value(self.store.get_value(self.integral[name]))


def address(rel: Rel) -> str:
    return rel.content_address()


# --------------------------------------------------------------------- ingest_delta (§3.1)


def test_a_retraction_is_witnessed_by_the_ref_of_the_row_it_removes(tmp_path) -> None:
    """§3.1: the retraction's atom is the srcrow ref of the very row being retracted, so
    a reader can follow the citation back to what went away [cites: pkm-event-identity].
    That is also what lets the ledger name what died (§6)."""
    store = Store(tmp_path / "store")
    delta = ingest_delta(store, SOURCE_A, SCHEMA_A, (), [(A2, 1)])
    ((row, (count, why)),) = list(delta)
    assert row == A2 and count == -1
    ((citation,),) = lineage(store, why)
    assert citation.kind == "source-row"
    assert citation.source == SOURCE_A and citation.row == A2
    assert citation.ref == source_row_ref(SOURCE_A, A2)


def test_an_arrival_and_a_retraction_of_one_row_mint_the_same_ref(tmp_path) -> None:
    """A srcrow ref depends on `(source, row)` and on nothing else — not batch, not order,
    not count. That is why resurrection works at all (§6): the ref that comes back is the
    ref that died, because the bytes are the same bytes."""
    store = Store(tmp_path / "store")
    arrived = ingest_delta(store, SOURCE_A, SCHEMA_A, [(A1, 2)], ())
    retracted = ingest_delta(store, SOURCE_A, SCHEMA_A, (), [(A1, 2)])
    assert arrived.get(A1)[1] == retracted.get(A1)[1]
    assert arrived.get(A1)[0] == 2 and retracted.get(A1)[0] == -2


def test_the_three_element_entry_is_accepted_and_its_atom_is_superseded(tmp_path) -> None:
    """The M3 stream vocabulary the frozen laws write in is `(row, occurrences, atom)`.
    tannen mints its own ref from `(source, row)` — content addressing's whole point —
    so the given atom is checked against the pinned grammar and then superseded (D0166).
    Naming a different ref there changes nothing and is not an error."""
    store = Store(tmp_path / "store")
    triple = ingest_delta(store, SOURCE_A, SCHEMA_A, [(A1, 1, SOURCE_B)], ())
    pair = ingest_delta(store, SOURCE_A, SCHEMA_A, [(A1, 1)], ())
    assert address(triple) == address(pair)
    assert triple.get(A1)[1] == ops.Why.of({source_row_ref(SOURCE_A, A1)})


@pytest.mark.parametrize(
    "arrivals, retractions, match",
    [
        ([(A1, 0)], (), "positive int"),
        ([(A1, -1)], (), "positive int"),
        ((), [(A1, -1)], "positive int"),
        ([(A1, True)], (), "positive int"),
        ([(A1,)], (), "row, occurrences"),
        ([(A1, 1, "not-a-ref")], (), "not a ref in the pinned grammar"),
    ],
)
def test_ingest_delta_refuses_a_malformed_entry_by_name(tmp_path, arrivals, retractions, match) -> None:
    """The sign is the argument's job, never the number's: the shortest spelling of an
    arrival must not be able to retract (BRIEF §5)."""
    store = Store(tmp_path / "store")
    with pytest.raises(RelError, match=match):
        ingest_delta(store, SOURCE_A, SCHEMA_A, arrivals, retractions)


def test_nothing_is_written_for_a_batch_that_was_refused(tmp_path) -> None:
    """`ingest`'s rule, unchanged: every value is minted and the relation built before the
    first write, so a refused batch leaves the store exactly as it found it."""
    store = Store(tmp_path / "store")
    with pytest.raises(RelError):
        ingest_delta(store, SOURCE_A, SCHEMA_A, [(A1, 1), ({"k": 1}, 1)], ())
    assert list(store.iter_refs()) == []


# ------------------------------------------------------------------ the ledger (§6)


def test_a_retraction_kills_a_ref_and_a_re_arrival_resurrects_it(tmp_path) -> None:
    """§6's ordering rule, which the model's `retract-rearrive` stream found: an arrival
    discards its ref BEFORE the source's `apply`. Applying first would let the valuation
    kill the very witness the arrival carries, and the witnessed-row alarm would fire on
    a perfectly lawful stream — so this is the ordering that keeps a re-arrival a value."""
    r = Runner(tmp_path)
    source = DeltaNode("source")
    ref = source_row_ref(SOURCE_A, A1)

    r.step("a", source, [r.feed(SOURCE_A, SCHEMA_A, [(A1, 1)])])
    assert r.ledger.dead == frozenset()

    r.step("a", source, [r.feed(SOURCE_A, SCHEMA_A, (), [(A1, 1)])])
    assert r.ledger.dead == frozenset({ref}), "a retraction that empties a row kills its ref"
    assert len(r.rel("a")) == 0

    r.step("a", source, [r.feed(SOURCE_A, SCHEMA_A, [(A1, 1)])])
    assert r.ledger.dead == frozenset(), "an arrival resurrects its ref"
    assert address(r.rel("a")) == address(ingest(r.store, SOURCE_A, SCHEMA_A, [A1]))


def test_a_partial_retraction_moves_a_count_without_killing_a_ref(tmp_path) -> None:
    """`dead` is "net count is now zero", not "something was retracted": a row still
    standing has not died, and its witness must survive to explain the copies that remain."""
    r = Runner(tmp_path)
    source = DeltaNode("source")
    r.step("a", source, [r.feed(SOURCE_A, SCHEMA_A, [(A1, 3)])])
    r.step("a", source, [r.feed(SOURCE_A, SCHEMA_A, (), [(A1, 1)])])
    assert r.ledger.dead == frozenset()
    assert r.rel("a").get(A1)[0] == 2


# ------------------------------------------------------- the executor over a graph (§7)


def test_a_two_source_join_stream_reaches_the_reference(tmp_path) -> None:
    """A delta-maintained node over two streams that move independently: the bilinear rule
    through the real store, ledger threaded by the caller, converging byte-identically to
    the one-shot join of the net sources (BRIEF L4 at the executor)."""
    r = Runner(tmp_path)
    src_a, src_b = DeltaNode("source"), DeltaNode("source")
    node = DeltaNode("join", on=("k",))

    def tick(a_arrivals=(), a_retractions=(), b_arrivals=(), b_retractions=()):
        r.step("a", src_a, [r.feed(SOURCE_A, SCHEMA_A, a_arrivals, a_retractions)])
        r.step("b", src_b, [r.feed(SOURCE_B, SCHEMA_B, b_arrivals, b_retractions)])
        r.step("j", node, [r.delta["a"], r.delta["b"]])

    tick(a_arrivals=[(A1, 1), (A2, 1)], b_arrivals=[(B1, 1)])
    tick(a_arrivals=[(A3, 1)], b_arrivals=[(B2, 1)])
    tick(a_retractions=[(A2, 1)])

    want = ops.join(
        ingest(r.store, SOURCE_A, SCHEMA_A, [A1, A3]),
        ingest(r.store, SOURCE_B, SCHEMA_B, [B1, B2]),
        ("k",),
    ).unwrap()
    assert address(r.rel("j")) == address(want)
    assert r.ledger.dead == frozenset({source_row_ref(SOURCE_A, A2)})


def test_the_contagion_rule_sheds_a_superseded_anti_join_address(tmp_path) -> None:
    """§4's contagion rule, spelled the way a caller must spell it: `anti_join` replays
    over its children's integrals (it always does), and the `project` ABOVE it is declared
    `replay=True` because an `anti_join` lies below.

    Without that, the tick-0 citation — the right relation's address while it was
    non-empty — would still stand in the project's integral after the right side emptied,
    dominated by nothing and filtered by nothing, because a semilattice cannot subtract.
    The reference has no such citation, and byte identity is the law.
    """
    r = Runner(tmp_path)
    src_a, src_b = DeltaNode("source"), DeltaNode("source")
    anti = DeltaNode("anti_join", on=("k",))
    above = DeltaNode("project", columns=("x",), replay=True)

    def tick(a_arrivals=(), b_arrivals=(), b_retractions=()):
        r.step("a", src_a, [r.feed(SOURCE_A, SCHEMA_A, a_arrivals)])
        r.step("b", src_b, [r.feed(SOURCE_B, SCHEMA_B, b_arrivals, b_retractions)])
        r.step("aj", anti, [r.integral["a"], r.integral["b"]])
        r.step("pj", above, [r.integral["aj"]])

    # b holds k=1, so A1 is anti-joined away and A2 survives, citing b's address.
    tick(a_arrivals=[(A1, 1), (A2, 1)], b_arrivals=[(B1, 1)])
    supports = list(r.rel("pj").get({"x": 7})[1])
    assert len(supports) == 1 and len(supports[0]) == 2, \
        "tick 0's survivor cites its own srcrow AND the non-empty right relation"

    tick(b_retractions=[(B1, 1)])

    want = ops.project(
        ops.anti_join(
            ingest(r.store, SOURCE_A, SCHEMA_A, [A1, A2]),
            Rel(SCHEMA_B, []),
            ("k",),
        ).unwrap(),
        ("x",),
    ).unwrap()
    assert address(r.rel("pj")) == address(want)


def test_the_two_aggregate_rules_agree_at_the_executor(tmp_path) -> None:
    """L3.8 where a user meets it: two nodes differing only in whether they declare a
    monoid or a group must hold the same integral at every tick. The group node maintains
    each touched fold through its declared `inverse` and keeps its input integral in
    state; the monoid node recomputes. Which rule runs is DECLARED, never inferred."""
    r = Runner(tmp_path)
    source = DeltaNode("source")
    by_monoid = DeltaNode("aggregate", by=("k",), column="x", into="s", monoid_id="sum")
    by_group = DeltaNode("aggregate", by=("k",), column="x", into="s", group_id="sum")

    def tick(arrivals=(), retractions=()):
        r.step("a", source, [r.feed(SOURCE_A, SCHEMA_A, arrivals, retractions)])
        r.step("m", by_monoid, [r.integral["a"]])
        r.step("g", by_group, [r.integral["a"]])
        assert address(r.rel("m")) == address(r.rel("g"))

    tick(arrivals=[(A1, 2), ({"k": 1, "x": 4}, 1)])
    tick(arrivals=[(A2, 1)])
    tick(retractions=[(A1, 1)])
    assert r.rel("g").get({"k": 1, "s": 9}) is not None
    assert address(r.rel("g")) == address(
        ops.aggregate(
            ingest(r.store, SOURCE_A, SCHEMA_A, [A1, {"k": 1, "x": 4}, A2]),
            ("k",), MONOIDS["sum"], lambda row: row["x"], "s",
        ).unwrap()
    )


# --------------------------------------------------------- what advance inherits from M1


def test_a_replayed_step_is_served_from_the_trace_when_the_caller_records(tmp_path) -> None:
    """§7's "replaying a stream hits traces", available as the caller's act. `advance`
    does not record by default: frozen L3.15's tamper case pins that a plain `advance`
    leaves `step_id` free for the caller to write, which is the same division M1 already
    makes between `AlwaysRebuild` and `VerifyingTrace` (D0167)."""
    r = Runner(tmp_path)
    node = DeltaNode("select", predicate_id="x-positive")
    fed = r.feed(SOURCE_A, SCHEMA_A, [(A1, 1)])

    first = advance(r.store, r.traces, node, None, [fed], Ledger.EMPTY)
    assert first.rebuilt and r.traces.lookup(first.step_id) is None

    recorded = advance(r.store, r.traces, node, None, [fed], Ledger.EMPTY, record=True)
    assert r.traces.lookup(recorded.step_id) is not None
    served = advance(r.store, r.traces, node, None, [fed], Ledger.EMPTY)
    assert not served.rebuilt
    assert served.state_ref == first.state_ref and served.delta_ref == first.delta_ref


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "reversed by D0232: a binary node's operand roles now enter its step's derivation "
        "inputs (RT-M3-03, frozen L4.25). Strict, so reverting the remedy turns this red."
    ),
)
def test_a_binary_step_id_inherits_derivation_ids_order_insensitivity(tmp_path) -> None:
    """RETIRED by D0232 as a strict xfail rather than deleted: D0167 and D0211 bind this node,
    and the conftest.py idiom (D0128) keeps a retirement a live assertion. Its body is the pin
    exactly as it stood.

    A PIN, not a claim that this is ideal (D0167). `derivation_id` is order-insensitive
    in its inputs by frozen M1 design (m1 §8, L1.13) and M1's own `Node(transform, inputs)`
    already has this property — `f(a, b)` and `f(b, a)` share a derivation id there too.
    §7 pins the same formula for a step, so a binary node's operand order is not part of
    its step id. `advance` therefore does not record by default, and a caller that does
    must not permute operands. If the formula is ever changed, this test is what says a
    decision is being reversed rather than a bug being fixed.
    """
    r = Runner(tmp_path)
    node = DeltaNode("anti_join", on=("k",))
    a = r.store.put_value(ingest(r.store, SOURCE_A, SCHEMA_A, [A1, A2]).to_value())
    b = r.store.put_value(ingest(r.store, SOURCE_B, SCHEMA_B, [B1]).to_value())

    left = advance(r.store, r.traces, node, None, [a, b], Ledger.EMPTY)
    right = advance(r.store, r.traces, node, None, [b, a], Ledger.EMPTY)
    assert left.step_id == right.step_id
    assert left.state_ref != right.state_ref, "the two orders compute different things"


def test_binary_operators_and_required_params_are_derived() -> None:
    """The two names frozen L4.24/L4.25 quantify over (D0226). Both are READ OFF the
    package's own arity and parameter tables, never listed (D0171 ruling (3), D0211) — so
    this asserts the tables agree with each other and with the operator catalogue, and that
    the three binary operators M3 knows of are among what is derived, without writing the
    derived set down. Reached through the module inside the body so this file still
    collects on a package that predates them."""
    import tannen.incremental as inc

    binary = inc.binary_operators()
    assert {"join", "union", "anti_join"} <= set(binary)
    assert list(binary) == sorted(binary), "a derived set is returned in one order"
    for operator in binary:
        node = DeltaNode(operator, **{p: ("k",) for p in inc.required_params(operator)})
        assert node.arity == 2
    assert set(inc._REQUIRED) == set(inc._ARITY) == set(inc.DELTA_OPERATORS)
    with pytest.raises(OperatorError, match="not a delta operator"):
        inc.required_params("nonsense")


def test_every_binary_nodes_operand_roles_are_part_of_its_step_id(tmp_path) -> None:
    """RT-M3-03's remedy (D0232; frozen as L4.25): a binary step names which input held which
    role, so the two operand orders are two derivations. Quantified over the DERIVED binary
    set with no operator exempted by name — which operators could safely share a step id
    across a swap is an operator set, and D0211 forbids writing one down. `anti_join` keeps
    the retired pin's positive control: its two orders really do compute different states,
    so a shared id would have been a wrong answer, not a harmless cache hit."""
    import tannen.incremental as inc

    r = Runner(tmp_path)
    a = r.store.put_value(ingest(r.store, SOURCE_A, ("k",), [{"k": 1}, {"k": 2}]).to_value())
    b = r.store.put_value(ingest(r.store, SOURCE_B, ("k",), [{"k": 1}]).to_value())
    for operator in inc.binary_operators():
        node = DeltaNode(operator, **{p: ("k",) for p in inc.required_params(operator)})
        left = advance(r.store, r.traces, node, None, [a, b], Ledger.EMPTY)
        right = advance(r.store, r.traces, node, None, [b, a], Ledger.EMPTY)
        assert left.step_id != right.step_id, f"{operator}: two operand orders share one step id"
        if operator == "anti_join":
            assert left.state_ref != right.state_ref, "the two orders compute different things"


# ------------------------------------------------------------------ declaration doors


@pytest.mark.parametrize(
    "kwargs, match",
    [
        (dict(operator="select", predicate_id="nope"), "is not registered"),
        (dict(operator="aggregate", by=("k",), column="x", into="s"), "exactly one of"),
        (dict(operator="aggregate", by=("k",), column="x", into="s",
              monoid_id="sum", group_id="sum"), "exactly one of"),
        (dict(operator="select"), "missing parameter"),
        (dict(operator="select", predicate_id="x-positive", on=("k",)), "unknown parameter"),
        (dict(operator="project", columns=()), "non-empty tuple"),
        (dict(operator="nonsense"), "not a delta operator"),
        (dict(operator="source", replay=True), "no children to replay over"),
    ],
)
def test_a_node_is_refused_at_declaration_not_at_the_tick(kwargs, match) -> None:
    """A plan's mistakes should not wait for data to arrive to be found: parameters are
    validated and the code they name is resolved when the node is declared."""
    operator = kwargs.pop("operator")
    with pytest.raises(OperatorError, match=match):
        DeltaNode(operator, **kwargs)


def test_a_column_parameters_order_is_not_part_of_the_declared_node() -> None:
    """Two spellings of the same node are the same descriptor (§7), so a column set is
    sorted into the declared form rather than carried as the caller happened to type it."""
    assert DeltaNode("project", columns=("k", "x")).descriptor == \
        DeltaNode("project", columns=("x", "k")).descriptor
    assert DeltaNode("project", columns=("k",)).descriptor != \
        DeltaNode("project", columns=("k", "x")).descriptor
    assert DeltaNode("project", columns=("k",)).descriptor != \
        DeltaNode("project", columns=("k",), replay=True).descriptor, \
        "replay is part of the declared form: a replaying node is a different node"
    assert DeltaNode("anti_join", on=("k",)).descriptor == \
        DeltaNode("anti_join", on=("k",), replay=True).descriptor, \
        "anti_join replays whatever the caller says, so saying so changes nothing"


def test_advance_refuses_a_wrong_arity_or_a_non_ref_by_name(tmp_path) -> None:
    r = Runner(tmp_path)
    node = DeltaNode("join", on=("k",))
    fed = r.feed(SOURCE_A, SCHEMA_A, [(A1, 1)])
    with pytest.raises(OperatorError, match="takes 2 input ref"):
        advance(r.store, r.traces, node, None, [fed], Ledger.EMPTY)
    with pytest.raises(RefError, match="a delta ref is a store ref"):
        advance(r.store, r.traces, node, None, [fed, "nope"], Ledger.EMPTY)
    with pytest.raises(OperatorError, match="not a DeltaNode"):
        advance(r.store, r.traces, "select", None, [fed], Ledger.EMPTY)


# --------------------------------------------------------------------- quarantine (P3)


def _explodes_on_seven(row):
    """User code that fails on one row and answers for the others."""
    if row["x"] == 7:
        raise ValueError("x is 7")
    return True


register_predicate("m3-test-explodes", _explodes_on_seven)


def test_a_row_that_fails_in_user_code_is_reported_and_is_not_state(tmp_path) -> None:
    """Quarantine rows are reports about a tick, never state (§7): the failing row is
    named by `quarantined_ref` and is simply absent from the integral. A NODE-level
    quarantine cannot arise here — `advance`'s inputs are relations loaded from the store,
    never an upstream `Quarantine` — so `Advanced.quarantine` is the P3 rule stated where
    it belongs rather than a path this suite can reach."""
    r = Runner(tmp_path)
    source = DeltaNode("source")
    node = DeltaNode("select", predicate_id="m3-test-explodes")
    r.step("a", source, [r.feed(SOURCE_A, SCHEMA_A, [(A1, 1), (A2, 1)])])
    done = r.step("s", node, [r.delta["a"]])

    assert done.quarantine is None
    assert done.quarantined_ref is not None
    ((row, _),) = list(Rel.from_value(r.store.get_value(done.quarantined_ref)))
    assert row["operator"] == "select" and row["row"] == A2
    assert r.rel("s").get(A2) == r.rel("s").annotations.zero
    assert r.rel("s").get(A1)[0] == 1


# ------------------------------------- RT-M3-02: the replacement set, derived not remembered

#: One two-tick stream per delta operator. Every member of `DELTA_OPERATORS` must appear —
#: a sweep that silently omits an operator would report a smaller divergent set and agree
#: with a smaller `_ALWAYS_REPLAYS`, which is the exact failure this file is closing.
#: `union` needs both sides on one schema; everything else pairs SCHEMA_A with SCHEMA_B.
_STREAMS: dict[str, dict] = {
    "source": {"params": {}},
    "select": {"params": {"predicate_id": "x-positive"}},
    "project": {"params": {"columns": ("x",)}},
    "map_rows": {"params": {"map_id": "k-only"}},
    "union": {"params": {}, "b_schema": SCHEMA_A, "b_rows": (A2, A3)},
    "join": {"params": {"on": ("k",)}},
    "distinct": {"params": {}},
    "anti_join": {"params": {"on": ("k",)}},
    "aggregate": {"params": {"by": ("k",), "column": "x", "into": "s", "monoid_id": "sum"}},
}


def _final_integral(tmp_path, operator: str, *, replay: bool) -> str:
    """Run `operator`'s two-tick stream and return the address of its integral.

    Tick 1 arrives rows on both sides; tick 2 RETRACTS one from each. The retraction is the
    whole experiment: a delta-maintained semilattice cannot subtract, so an operator whose
    rule must be replacement diverges here, and one whose rule is genuinely incremental
    does not.

    The caller feeds INTEGRALS to a replaying node and DELTAS to a maintained one — §7's
    caller-side policy, and the thing `_ALWAYS_REPLAYS` decides. `replay` is passed
    EXPLICITLY here rather than inherited from that set, so the two runs differ in the
    declared flag alone; the caller in the sweep below empties the set first so nothing else
    can be deciding. `source` is its own subject: it consumes an `ingest_delta` result
    rather than an integral, and `replay=True` is refused for it outright (§6, §7).
    """
    spec = _STREAMS[operator]
    b_schema = spec.get("b_schema", SCHEMA_B)
    b_first, b_second = spec.get("b_rows", (B1, B2))
    r = Runner(tmp_path)
    src_a, src_b = DeltaNode("source"), DeltaNode("source")
    node = None if operator == "source" else DeltaNode(operator, replay=replay, **spec["params"])

    def tick(a_arrivals=(), a_retractions=(), b_arrivals=(), b_retractions=()) -> None:
        r.step("a", src_a, [r.feed(SOURCE_A, SCHEMA_A, a_arrivals, a_retractions)])
        r.step("b", src_b, [r.feed(SOURCE_B, b_schema, b_arrivals, b_retractions)])
        if node is not None:
            carrier = r.integral if node.replay else r.delta
            inputs = [carrier["a"]] if node.arity == 1 else [carrier["a"], carrier["b"]]
            r.step("n", node, inputs)

    tick(a_arrivals=[(A1, 1), (A2, 1)], b_arrivals=[(b_first, 1), (b_second, 1)])
    tick(a_retractions=[(A1, 1)], b_retractions=[(b_first, 1)])
    return address(r.rel("a" if node is None else "n"))


def test_the_sweep_covers_every_delta_operator() -> None:
    """The derivation below is only as good as its input set, and an input set that is
    itself a hand-written dict is the very thing under investigation. Pin it against the
    package's own tuple so adding an operator without a stream fails here first."""
    import tannen.incremental as inc

    assert set(_STREAMS) == set(inc.DELTA_OPERATORS)


def test_the_always_replays_set_is_derived_from_behaviour_not_from_memory(tmp_path) -> None:
    """RT-M3-02, and D0171 ruling (3)'s "derive AND assert" in one test.

    `_ALWAYS_REPLAYS` is a hand-written frozenset naming the operators whose delta rule is
    replacement whatever the caller declares (§4). Nothing derived it and nothing checked
    it, and its three members fail UNEQUALLY: emptying the set makes `distinct` and
    `aggregate` raise loudly, while `anti_join` simply returns a wrong answer — the
    stale-retention unsoundness of D0163, served silently, with no exception and no
    divergence any frozen law observes. Measured at the M3 boundary: with `anti_join`
    removed, `pytest tests/laws/m3` is still 38/38 green.

    So the set is measured rather than trusted: run each operator's stream with the rule in
    force and again with it emptied, and collect the operators that diverge or raise. That
    set must be exactly `_ALWAYS_REPLAYS`. A member wrongly present fails because nothing
    diverges for it; a member wrongly absent fails because something does.
    """
    import tannen.incremental as inc

    declared = set(inc._ALWAYS_REPLAYS)
    saved = inc._ALWAYS_REPLAYS
    measured: set[str] = set()
    try:
        # Emptied for the WHOLE sweep, so `replay` is exactly what each node declares and
        # the declared set is not quietly deciding the experiment meant to check it. An
        # earlier spelling compared the declared set against an emptied one, which cannot
        # fail for a member wrongly ABSENT: both runs would then be the maintained one.
        inc._ALWAYS_REPLAYS = frozenset()
        for operator in sorted(inc.DELTA_OPERATORS):
            if operator == "source":
                continue  # `replay=True` is refused for it, so there is no pair to compare
            replayed = _final_integral(tmp_path / f"on-{operator}", operator, replay=True)
            try:
                maintained = _final_integral(tmp_path / f"off-{operator}", operator, replay=False)
            except Exception:
                measured.add(operator)
                continue
            if maintained != replayed:
                measured.add(operator)
    finally:
        inc._ALWAYS_REPLAYS = saved

    assert "source" not in declared, "source has no replay form, so it cannot be in the set"
    assert measured == declared, (
        f"the replacement rule is declared for {sorted(declared)} but behaviour says "
        f"{sorted(measured)}. An operator in the second set and not the first is maintained "
        f"incrementally and must not be; one in the first and not the second is replaying "
        f"for no reason this stream can see."
    )


# -------------------------------------------- RT-M3-01: a descriptor names code, not a string


def _risk_ok_honest(row):
    return row.get("x", 0) < 100


def _risk_ok_hostile(row):
    return True


def test_a_reused_predicate_name_no_longer_mints_the_same_descriptor() -> None:
    """RT-M3-01, the regression. Two processes over one trace store, differing only in what
    they register under a name, used to produce one descriptor and one `step_id` — so the
    second was served the first's answer with `rebuilt=False` and `TraceIntegrityError`
    could not fire, because nothing had been tampered with. A regression against M1, which
    hashes a transform's source text (D0084) and refuses a lambda for want of one.

    The registry is reset between the two registrations because that is exactly what a new
    process does — "across runs the registry is rebuilt from empty" is the finding's own
    sentence, and it is why the in-process re-registration guard never applied.
    """
    import tannen.incremental as inc

    saved_registry, saved_code = dict(inc.PREDICATES), dict(inc._CODE)
    try:
        register_predicate("rt-m3-01", _risk_ok_honest)
        honest = DeltaNode("select", predicate_id="rt-m3-01").descriptor
        del inc.PREDICATES["rt-m3-01"], inc._CODE[("predicate", "rt-m3-01")]
        register_predicate("rt-m3-01", _risk_ok_hostile)
        hostile = DeltaNode("select", predicate_id="rt-m3-01").descriptor
    finally:
        inc.PREDICATES.clear(), inc.PREDICATES.update(saved_registry)
        inc._CODE.clear(), inc._CODE.update(saved_code)

    assert honest != hostile, (
        "two different predicates under one name mint one descriptor, so a trace keyed by "
        "it serves the answer to a computation that was never run (RT-M3-01)"
    )


def _rt_m3_01_map(row):
    return {"k": row["k"]}


def test_a_map_out_schema_is_part_of_the_declared_node() -> None:
    """RT-M3-01's residue (D0231; frozen as L4.23). One map body registered under one name
    with two different out-schemas used to mint one descriptor, because the schema was
    resolved from the registry at tick time and appeared in no declared form
    (docs/specs/m3-corrections.md §1). Reset between the registrations for the reason the
    predicate case above gives: that is what a new process does."""
    import tannen.incremental as inc

    saved_maps, saved_code = dict(inc.MAPS), dict(inc._CODE)
    try:
        inc.register_map("rt-m3-01-map", _rt_m3_01_map, ("k",))
        declared_k = DeltaNode("map_rows", map_id="rt-m3-01-map").descriptor
        del inc.MAPS["rt-m3-01-map"], inc._CODE[("map", "rt-m3-01-map")]
        inc.register_map("rt-m3-01-map", _rt_m3_01_map, ("key",))
        declared_key = DeltaNode("map_rows", map_id="rt-m3-01-map").descriptor
    finally:
        inc.MAPS.clear(), inc.MAPS.update(saved_maps)
        inc._CODE.clear(), inc._CODE.update(saved_code)

    assert declared_k != declared_key, (
        "one map body under one name with two out-schemas minted one descriptor — the "
        "schema a node's rows take is part of what the node computes (RT-M3-01)"
    )


def test_a_lambda_cannot_be_registered_for_the_reason_m1_refuses_one() -> None:
    """M1's `transform` refuses a lambda because it has no addressable source; M3 read the
    same fact as a licence and shipped four. The catalogue is named functions now."""
    with pytest.raises(OperatorError, match="a lambda cannot be registered"):
        register_predicate("rt-m3-01-lambda", lambda row: True)


def test_a_registry_entry_inserted_behind_the_registrar_is_refused_by_name() -> None:
    """`PREDICATES` is a plain mutable dict in `__all__`, so the registrar can be bypassed
    with one assignment — the finding says so. A bypassed entry has no code address, and a
    descriptor that cannot name its code must not be minted at all."""
    import tannen.incremental as inc

    inc.PREDICATES["rt-m3-01-smuggled"] = _risk_ok_hostile
    try:
        with pytest.raises(OperatorError, match="has no code address"):
            DeltaNode("select", predicate_id="rt-m3-01-smuggled")
    finally:
        del inc.PREDICATES["rt-m3-01-smuggled"]
