"""M1 laws L1.13–L1.14 — derivation identity and the two rebuilders
(docs/specs/m1.md §8; BRIEF §4, §7).

FROZEN at m1-laws-freeze.

L1.13 is `DerivationId = H(transform_descriptor, sorted(input_ids))`, BRIEF §4 verbatim.
L1.14 is the rebuilders: `AlwaysRebuild` and `VerifyingTrace` must agree, and a trace that
has been tampered with must be DETECTED rather than trusted. The strict reading is pinned
deliberately — a recorded output that has gone missing is an integrity failure, not a cache
miss, because the store is append-only and write-once, so its absence means something
happened outside the store's contract and quietly rebuilding would erase the only evidence.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given, strategies as st

executor_mod = pytest.importorskip(
    "tannen.executor",
    reason="M1 executor not implemented yet (law suite frozen ahead of Session B)",
)
derivation = pytest.importorskip("tannen.kernel.derivation")
transform_mod = pytest.importorskip("tannen.transform")
ops = pytest.importorskip("tannen.kernel.ops")
rel_mod = pytest.importorskip("tannen.kernel.rel")
semiring = pytest.importorskip("tannen.kernel.semiring")
layers = pytest.importorskip("tannen.kernel.layers")

from tannen.kernel.encoding import content_address  # noqa: E402
from tannen.kernel.refs import is_ref  # noqa: E402
from tannen.store import Store  # noqa: E402

Rel = rel_mod.Rel
Z = semiring.Z
WHY = "law fixture"
DESCRIPTORS = [f"sha256:{c * 64}" for c in "abcdef"]


@transform_mod.transform(kind="derive", params={})
def keep_positive(source):
    return ops.select(source, lambda row: row["k"] > 0)


@transform_mod.transform(kind="derive", params={})
def join_on_k(left, right):
    return ops.join(left, right, ("k",))


@transform_mod.transform(kind="derive", params={}, layer=layers.Layer.SERVE)
def joins_but_claims_serve(left, right):
    return ops.join(left, right, ("k",))


@transform_mod.transform(kind="derive", params={})
def always_raises(source):
    raise RuntimeError("this node fails as a whole")


def rel(pairs):
    return Rel(("k",), [({"k": k}, n) for k, n in pairs], annotations=Z, annotations_reason=WHY)


@pytest.fixture()
def store(tmp_path: Path):
    return Store(tmp_path / "store")


@pytest.fixture()
def traces(tmp_path: Path):
    return executor_mod.TraceStore(tmp_path / "traces")


# --------------------------------------------------------- L1.13 derivation identity


def test_l1_13_is_the_address_of_the_pinned_two_field_value() -> None:
    ref = derivation.derivation_id(DESCRIPTORS[0], [DESCRIPTORS[2], DESCRIPTORS[1]])
    assert ref == content_address(
        {"inputs": sorted([DESCRIPTORS[2], DESCRIPTORS[1]]), "transform": DESCRIPTORS[0]}
    )
    assert is_ref(ref)


@given(st.permutations(DESCRIPTORS[1:4]))
def test_l1_13_is_order_insensitive_in_its_inputs(order) -> None:
    # `sorted(input_ids)`: which order the caller happened to hold them in is not part of
    # what was derived.
    assert derivation.derivation_id(DESCRIPTORS[0], order) == derivation.derivation_id(
        DESCRIPTORS[0], DESCRIPTORS[1:4]
    )


def test_l1_13_changes_when_the_descriptor_or_any_input_changes() -> None:
    base = derivation.derivation_id(DESCRIPTORS[0], [DESCRIPTORS[1], DESCRIPTORS[2]])
    assert base != derivation.derivation_id(DESCRIPTORS[3], [DESCRIPTORS[1], DESCRIPTORS[2]])
    assert base != derivation.derivation_id(DESCRIPTORS[0], [DESCRIPTORS[1], DESCRIPTORS[3]])
    assert base != derivation.derivation_id(DESCRIPTORS[0], [DESCRIPTORS[1]])
    assert base != derivation.derivation_id(
        DESCRIPTORS[0], [DESCRIPTORS[1], DESCRIPTORS[2], DESCRIPTORS[2]]
    )


@pytest.mark.parametrize(
    ("descriptor", "inputs"),
    [("not-a-ref", DESCRIPTORS[1:2]), (DESCRIPTORS[0], ["not-a-ref"])],
    ids=["bad-descriptor", "bad-input"],
)
def test_l1_13_refuses_anything_outside_the_pinned_ref_grammar(descriptor, inputs) -> None:
    with pytest.raises(Exception):
        derivation.derivation_id(descriptor, inputs)


def test_l1_13_a_node_carries_the_same_id(store) -> None:
    ref = store.put_value(rel([(1, 1)]).to_value())
    node = executor_mod.Node(keep_positive, (ref,))
    assert node.derivation_id == derivation.derivation_id(keep_positive.descriptor_id, (ref,))


# ----------------------------------------------------------------- L1.14 rebuilders


def test_l1_14_both_rebuilders_produce_the_same_output(store, traces) -> None:
    ref = store.put_value(rel([(-1, 1), (1, 2), (3, 1)]).to_value())
    node = executor_mod.Node(keep_positive, (ref,))

    rebuilt = executor_mod.AlwaysRebuild().build(node, store, traces)
    served = executor_mod.VerifyingTrace().build(node, store, traces)

    assert rebuilt.output_ref == served.output_ref
    assert rebuilt.derivation_id == served.derivation_id == node.derivation_id
    assert rebuilt.rebuilt is True and served.rebuilt is False
    assert Rel.from_value(store.get_value(rebuilt.output_ref)) == rel([(1, 2), (3, 1)])


def test_l1_14_always_rebuild_ignores_a_trace_but_still_records_one(store, traces) -> None:
    ref = store.put_value(rel([(1, 1)]).to_value())
    node = executor_mod.Node(keep_positive, (ref,))
    first = executor_mod.AlwaysRebuild().build(node, store, traces)
    assert traces.lookup(node.derivation_id) == first.output_ref
    second = executor_mod.AlwaysRebuild().build(node, store, traces)
    assert second.rebuilt is True and second.output_ref == first.output_ref


def test_l1_14_a_verifying_trace_hit_is_not_a_rebuild(store, traces) -> None:
    ref = store.put_value(rel([(1, 1)]).to_value())
    node = executor_mod.Node(keep_positive, (ref,))
    assert executor_mod.VerifyingTrace().build(node, store, traces).rebuilt is True
    assert executor_mod.VerifyingTrace().build(node, store, traces).rebuilt is False


def test_l1_14_a_trace_pointing_at_absent_content_is_an_integrity_failure(store, traces) -> None:
    # NOT a cache miss. The store is append-only and write-once, so a recorded output that
    # will not resolve means something happened outside the store's contract.
    ref = store.put_value(rel([(1, 1)]).to_value())
    node = executor_mod.Node(keep_positive, (ref,))
    traces.record(node.derivation_id, "sha256:" + "0" * 64)
    with pytest.raises(executor_mod.TraceIntegrityError):
        executor_mod.VerifyingTrace().build(node, store, traces)


def test_l1_14_a_tampered_stored_output_is_detected(store, tmp_path: Path, traces) -> None:
    ref = store.put_value(rel([(1, 1)]).to_value())
    node = executor_mod.Node(keep_positive, (ref,))
    built = executor_mod.AlwaysRebuild().build(node, store, traces)

    victim = next(
        path
        for path in (tmp_path / "store").rglob("*")
        if path.is_file() and path.read_bytes() == store.get_bytes(built.output_ref)
    )
    victim.write_bytes(b'{"tampered":true}')

    with pytest.raises(Exception) as caught:
        executor_mod.VerifyingTrace().build(node, store, traces)
    assert not isinstance(caught.value, AssertionError)


def test_l1_14_one_derivation_has_one_output(store, traces) -> None:
    ref = store.put_value(rel([(1, 1)]).to_value())
    node = executor_mod.Node(keep_positive, (ref,))
    built = executor_mod.AlwaysRebuild().build(node, store, traces)
    traces.record(node.derivation_id, built.output_ref)  # idempotent: same mapping, no-op
    with pytest.raises(executor_mod.TraceIntegrityError):
        traces.record(node.derivation_id, "sha256:" + "1" * 64)


def test_l1_14_a_quarantined_node_writes_no_trace(store, traces) -> None:
    # A quarantine is a report about a run, not a cached result.
    ref = store.put_value(rel([(1, 1)]).to_value())
    node = executor_mod.Node(always_raises, (ref,))
    built = executor_mod.AlwaysRebuild().build(node, store, traces)
    assert built.output_ref is None
    assert traces.lookup(node.derivation_id) is None


def test_l1_14_the_built_layer_is_what_actually_ran(store, traces) -> None:
    left = store.put_value(rel([(1, 1)]).to_value())
    right = store.put_value(
        Rel(("k", "y"), [({"k": 1, "y": 2}, 1)], annotations=Z, annotations_reason=WHY).to_value()
    )
    node = executor_mod.Node(join_on_k, (left, right))
    built = executor_mod.AlwaysRebuild().build(node, store, traces)
    assert built.layer is layers.Layer.DERIVE

    only_selects = executor_mod.Node(keep_positive, (left,))
    assert executor_mod.AlwaysRebuild().build(only_selects, store, traces).layer is layers.Layer.SERVE


def test_l1_14_a_transform_claiming_a_narrower_layer_than_it_runs_is_refused(store, traces) -> None:
    # The check happens HERE, at the one place that knows what ran (docs/specs/m1.md §6).
    left = store.put_value(rel([(1, 1)]).to_value())
    right = store.put_value(
        Rel(("k", "y"), [({"k": 1, "y": 2}, 1)], annotations=Z, annotations_reason=WHY).to_value()
    )
    node = executor_mod.Node(joins_but_claims_serve, (left, right))
    with pytest.raises(layers.LayerError):
        executor_mod.AlwaysRebuild().build(node, store, traces)


def test_l1_14_an_unregistered_transform_cannot_be_built(store, traces) -> None:
    with pytest.raises(transform_mod.TransformError):
        executor_mod.Node(lambda source: source, ())
