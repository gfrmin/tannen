"""M4 law L4.25 — a step served from a trace is the step a fresh trace would compute
(RT-M3-03; docs/specs/m4.md §8; docs/specs/m3-corrections.md §1).

FROZEN at m4-laws-freeze.

RT-M3-03 (high): `derivation_id` is order-insensitive by frozen M1 design (L1.13), so a
binary node's two operand orders share one `step_id`; with identical schemas nothing refuses
the swap, and a recorded trace serves one order's answer to the other with `rebuilt=False`.
It is wrong for `anti_join`, which does not commute, AND for `join`, which does — because
its state keeps the two children's integrals by position (m3-corrections.md §1; this
freeze's record corrects D0211's "exactly {anti_join}"). `union` is sound: linear, no
per-input state.

The law is behavioural and names no remedy's mechanism: for every binary operator the
package declares, a step answered from a trace recorded under the other operand order must
equal the same call against an empty trace store — state, delta and ledger. The remedy
docs/specs/m4.md §8 pins is D0211's first: the executor folds operand ROLES into the step's
derivation inputs for a node whose roles are not interchangeable, so the two orders are two
derivations because they are two different input values. `derivation_id`'s formula is not
widened — owner-signed D0171 ruling (2) stands.
"""

from __future__ import annotations

import pytest

pytest.importorskip("tannen.oracles", reason=(
    "M4 boundary not implemented yet (law suite frozen ahead of Session B); M4's laws go "
    "live together — docs/specs/m4.md §11"))
incremental = pytest.importorskip("tannen.incremental")
sources = pytest.importorskip("tannen.sources")

from tannen.executor import TraceStore  # noqa: E402
from tannen.store import Store  # noqa: E402

VALIDATION_REASON = (
    "trace service is executor machinery; a model of it would BE the implementation "
    "(D0094 §3). The comparison's other side is the package itself against an empty trace "
    "store, which isolates the trace as the only thing that can make the answers differ."
)

DeltaNode = incremental.DeltaNode
Ledger = incremental.Ledger
advance = incremental.advance

SOURCE_A = "sha256:" + "a6" * 32
SOURCE_B = "sha256:" + "b6" * 32
SCHEMA = ("k",)
COLUMN_PARAMS = ("on", "by", "columns")

BINARY = tuple(sorted(incremental.binary_operators()))


def _node(operator: str) -> DeltaNode:
    params = {}
    for name in incremental.required_params(operator):
        if name not in COLUMN_PARAMS:
            pytest.fail(f"{operator} declares {name!r}; this law knows only column "
                        "parameters — extend it by forward supersession, never by edit")
        params[name] = SCHEMA
    return DeltaNode(operator, **params)


def _refs(store):
    a = sources.ingest(store, SOURCE_A, SCHEMA, [{"k": 1}, {"k": 2}])
    b = sources.ingest(store, SOURCE_B, SCHEMA, [{"k": 1}])
    return store.put_value(a.to_value()), store.put_value(b.to_value())


def _triple(done):
    return (done.state_ref, done.delta_ref, done.ledger_ref)


@pytest.mark.parametrize("operator", BINARY)
@pytest.mark.parametrize("recorded_first", ["ab", "ba"])
def test_l4_25_a_trace_served_step_is_what_a_fresh_trace_computes(operator, recorded_first,
                                                                   tmp_path) -> None:
    store = Store(tmp_path / "store")
    a, b = _refs(store)
    first, second = ([a, b], [b, a]) if recorded_first == "ab" else ([b, a], [a, b])
    node = _node(operator)
    recorded = TraceStore(tmp_path / "recorded")
    advance(store, recorded, node, None, first, Ledger.EMPTY, record=True)
    served = advance(store, recorded, node, None, second, Ledger.EMPTY)
    truth = advance(store, TraceStore(tmp_path / "empty"), node, None, second, Ledger.EMPTY)
    assert _triple(served) == _triple(truth), (
        f"{operator}: the trace served the other operand order's recorded answer — the two "
        "orders shared a step id while computing different things (RT-M3-03)")


def test_l4_25_the_binary_operators_come_from_the_package() -> None:
    """Derived, never listed (D0171 ruling (3), D0211): whatever the package declares binary
    is quantified over, and the three M3 knows of must be among them."""
    assert {"join", "union", "anti_join"} <= set(BINARY)
    for operator in BINARY:
        assert operator in incremental.DELTA_OPERATORS
        assert _node(operator).arity == 2
