"""M4 law L4.24 — every catalogue shape, binary nodes included, driven through the SHIPPED
executor, reaches the reference byte for byte (RT-M3-02; docs/specs/m4.md §8;
docs/specs/m3.md §4, §7).

FROZEN at m4-laws-freeze.

RT-M3-02 (high): the contagion rule's operator set lives in the package, and its three
members fail unequally when one goes missing — `distinct` and `aggregate` raise, `anti_join`
returns a WRONG ANSWER in silence. The frozen M3 laws could not see it: L3.11/L3.12 decide
replay inside the subject adapter, and every `DeltaNode` in L3.15 is unary. D0198 added an
unfrozen guard; this is the frozen law.

The driver below is a frozen caller of `tannen.incremental.advance`, the shape a user
writes (there is no graph object, m3 §7). Two rules make it a test of the PACKAGE rather
than of itself:

  * it never declares `replay=True` on an `anti_join` node — whether that node replays is
    the package's to decide (`_ALWAYS_REPLAYS`), so removing `anti_join` from that set
    reaches this law;
  * it chooses integrals or deltas for a node's inputs by reading `node.replay`, never by
    computing the rule itself. The only contagion it computes is the caller's half, m3 §7's
    own: a node strictly ABOVE an `anti_join` is declared `replay=True`.

The reference is the one-shot evaluation over `tannen.sources.ingest` of the net rows —
the same srcrow refs the executor mints — compared by `read` and by content address.
"""

from __future__ import annotations

import importlib.util as _ilu
import tempfile
from pathlib import Path as _Path

import pytest

pytest.importorskip("tannen.oracles", reason=(
    "M4 boundary not implemented yet (law suite frozen ahead of Session B); M4's laws go "
    "live together — docs/specs/m4.md §11"))

_spec = _ilu.spec_from_file_location("tannen_frozen_m4._frozen_bind",
                                     _Path(__file__).with_name("_frozen_bind.py"))
bind = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(bind)

from hypothesis import given, strategies as st  # noqa: E402

M, TANNEN = bind.m3()

incremental = pytest.importorskip("tannen.incremental")
sources = pytest.importorskip("tannen.sources")

from tannen.executor import TraceStore  # noqa: E402
from tannen.kernel.rel import Rel  # noqa: E402
from tannen.store import Store  # noqa: E402

VALIDATION_REASON = (
    "the oracle is the M3 reference evaluation (tests/laws/m3/_delta_model.py `evaluate` "
    "under the frozen tannen subject), so naming a family would be circular; the driver's "
    "teeth were watched at the freeze by removing anti_join from the package's replay set "
    "and by dropping join's held state (docs/specs/m4.md §8)."
)

DeltaNode = incremental.DeltaNode
Ledger = incremental.Ledger
advance = incremental.advance

SOURCES = {"a": "sha256:" + "a4" * 32, "b": "sha256:" + "b4" * 32, "c": "sha256:" + "c4" * 32}
HEADS = {"select", "project", "map_rows", "union", "join", "distinct", "anti_join", "aggregate"}


def _children(plan) -> list:
    return [part for part in plan[1:] if isinstance(part, tuple) and part
            and (part[0] == "src" or part[0] in HEADS)]


def _anti_below(plan) -> bool:
    """An `anti_join` strictly below `plan` (the caller's half of the contagion rule)."""
    return any(child[0] == "anti_join" or _anti_below(child) for child in _children(plan)
               if child[0] != "src")


def _declare(plan) -> DeltaNode:
    head = plan[0]
    extra = {"replay": True} if head != "anti_join" and _anti_below(plan) else {}
    if head == "select":
        return DeltaNode("select", predicate_id=plan[2], **extra)
    if head == "project":
        return DeltaNode("project", columns=tuple(plan[2]), **extra)
    if head == "map_rows":
        return DeltaNode("map_rows", map_id=plan[2], **extra)
    if head == "union":
        return DeltaNode("union", **extra)
    if head == "join":
        return DeltaNode("join", on=tuple(plan[3]), **extra)
    if head == "distinct":
        return DeltaNode("distinct", **extra)
    if head == "anti_join":
        return DeltaNode("anti_join", on=tuple(plan[3]))
    if head == "aggregate":
        return DeltaNode("aggregate", by=tuple(plan[2]), column=plan[3], into=plan[4],
                         monoid_id="sum", **extra)
    raise AssertionError(f"unknown plan head {head!r}")


def _sources_of(plan, acc=None) -> set:
    acc = set() if acc is None else acc
    if plan[0] == "src":
        acc.add(plan)
    for child in _children(plan):
        _sources_of(child, acc)
    return acc


def drive(root, plan, schemas, ticks) -> Rel:
    """Advance every node of `plan` through every tick; return the final top integral."""
    store, traces = Store(root / "store"), TraceStore(root / "traces")
    ledger = Ledger.EMPTY
    nodes, state, delta, integral = {}, {}, {}, {}

    def step(p, inputs) -> None:
        nonlocal ledger
        done = advance(store, traces, nodes[p], state.get(p), inputs, ledger)
        assert done.quarantine is None, f"{p}: {done.quarantine}"
        state[p] = done.state_ref
        ledger = Ledger.from_value(store.get_value(done.ledger_ref))
        delta[p] = done.delta_ref
        integral[p] = store.get_value(done.state_ref)["output"]

    for tick in ticks:
        advanced: set = set()
        for src in sorted(_sources_of(plan)):
            entries = tick.get(src[1], ())
            rel = sources.ingest_delta(
                store, SOURCES[src[1]], schemas[src[1]],
                [(row, dn) for row, dn, _ in entries if dn > 0],
                [(row, -dn) for row, dn, _ in entries if dn < 0])
            nodes.setdefault(src, DeltaNode("source"))
            step(src, [store.put_value(rel.to_value())])
            advanced.add(src)

        def visit(p) -> None:
            if p in advanced:
                return
            for child in _children(p):
                visit(child)
            node = nodes.setdefault(p, _declare(p))
            step(p, [integral[c] if node.replay else delta[c] for c in _children(p)])
            advanced.add(p)

        visit(plan)
    return Rel.from_value(store.get_value(integral[plan]))


def reference(root, plan, schemas, net) -> Rel:
    store = Store(root / "reference")
    rels = {name: sources.ingest(store, SOURCES[name], schemas[name],
                                 [row for row, count, _ in net.get(name, ())
                                  for _ in range(count)])
            for name in schemas}
    return M.evaluate(TANNEN, plan, rels)


@pytest.mark.parametrize("shape", M.SHAPES, ids=[s.name for s in M.SHAPES])
@given(data=st.data())
def test_l4_24_every_shape_through_the_shipped_executor_reaches_the_reference(shape, data):
    schemas, ticks, net = data.draw(M.stream_tables(names="".join(shape.tables)))
    with tempfile.TemporaryDirectory() as scratch:
        root = _Path(scratch)
        got = drive(root, shape.plan, schemas, ticks)
        want = reference(root, shape.plan, schemas, net)
        assert TANNEN.read(got) == TANNEN.read(want) and \
            TANNEN.address(got) == TANNEN.address(want), (
            f"{shape.name}: the shipped executor's integral is not the reference\n"
            f"  got:  {TANNEN.read(got)!r}\n  want: {TANNEN.read(want)!r}")


def test_l4_24_every_binary_operator_is_driven_by_some_shape() -> None:
    """The catalogue must reach every binary operator the package declares, derived from
    the package — a new binary operator with no shape fails here first."""
    used = {head for shape in M.SHAPES for head in _heads(shape.plan)}
    binary = set(incremental.binary_operators())
    assert {"join", "union", "anti_join"} <= binary
    assert binary <= used, f"binary operators no shape drives: {sorted(binary - used)}"


def _heads(plan) -> set:
    return {plan[0]} | {h for child in _children(plan) for h in _heads(child)}
