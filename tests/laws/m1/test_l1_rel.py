"""M1 laws L1.4–L1.5 — `Rel` identity and its annotation defaults
(docs/specs/m1.md §3, §3.1, §3.2).

FROZEN at m1-laws-freeze. `golden-rels.json` is the frozen oracle for the `rel/1`
canonical form: Session A computed those thirteen addresses against the M0 encoder, and
M1's kill criterion is a mismatch here — fix the encoding before anything else lands
(docs/specs/m1.md §10).
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest
from hypothesis import given, strategies as st

rel_mod = pytest.importorskip(
    "tannen.kernel.rel",
    reason="M1 Rel not implemented yet (law suite frozen ahead of Session B)",
)
ops = pytest.importorskip(
    "tannen.kernel.ops",
    reason="M1 operators not implemented yet (law suite frozen ahead of Session B)",
)
semiring = pytest.importorskip("tannen.kernel.semiring")

from tannen.kernel.encoding import CanonicalEncodingError, encode_canonical  # noqa: E402
from tannen.store import Store  # noqa: E402

Rel = rel_mod.Rel
Z, B, Why, ZxWhy = semiring.Z, semiring.B, semiring.Why, semiring.ZxWhy

GOLDEN = json.loads((Path(__file__).parent / "golden-rels.json").read_text(encoding="utf-8"))

R1 = "sha256:" + "11" * 32
R2 = "sha256:" + "22" * 32

#: Every non-default semiring choice needs one (§3.2); in a law file the reason is that
#: the law is about that semiring.
WHY = "law fixture: this vector exists to pin this semiring's encoding"


def _one_row_z():
    return Rel(("a",), [({"a": 1}, 3)], annotations=Z, annotations_reason=WHY)


def _zxwhy_one_row():
    return Rel(("a",), [({"a": 1}, (2, Why.of({R1})))])


#: name -> the recipe the golden address is the address OF. Kept here rather than in the
#: JSON so that the construction is frozen alongside the expectation.
BUILDERS = {
    "empty-z": lambda: Rel(("a", "b"), (), annotations=Z, annotations_reason=WHY),
    "one-row-z": _one_row_z,
    # A row supplied with the semiring zero is ABSENT, not stored — same address as above.
    "zero-dropped": lambda: Rel(
        ("a",), [({"a": 1}, 3), ({"a": 2}, 0)], annotations=Z, annotations_reason=WHY
    ),
    # Row identity is the row's CANONICAL ENCODING, so these are one row and 1 + 2 = 3.
    "decimal-merge": lambda: Rel(
        ("p",),
        [({"p": Decimal("1.50")}, 1), ({"p": Decimal("1.5")}, 2)],
        annotations=Z,
        annotations_reason=WHY,
    ),
    # ... and so are the NFD and NFC spellings of the same string.
    "nfc-merge": lambda: Rel(
        ("a",),
        # NFD then NFC — written as escapes so the law is visibly about normalisation
        [({"a": "he\u0301llo"}, 1), ({"a": "h\u00e9llo"}, 1)],
        annotations=Z,
        annotations_reason=WHY,
    ),
    "bool-rel": lambda: Rel(
        ("a",), [({"a": 1}, True), ({"a": 2}, True)], annotations=B, annotations_reason=WHY
    ),
    "why-antichain": lambda: Rel(
        ("a",),
        [({"a": 1}, Why.of({R1}, {R1, R2}))],
        annotations=Why,
        annotations_reason=WHY,
    ),
    "zxwhy-one-row": _zxwhy_one_row,
    # Support but no surviving copies: not the product zero, so the row is RETAINED.
    "zxwhy-zero-count": lambda: Rel(("a",), [({"a": 1}, (0, Why.of({R1})))]),
    "union-z": lambda: ops.union(
        _one_row_z(),
        Rel(("a",), [({"a": 1}, 2), ({"a": 2}, 1)], annotations=Z, annotations_reason=WHY),
    ).unwrap(),
    "join-z": lambda: ops.join(
        Rel(("k", "x"), [({"k": 1, "x": 10}, 2)], annotations=Z, annotations_reason=WHY),
        Rel(("k", "y"), [({"k": 1, "y": 20}, 3)], annotations=Z, annotations_reason=WHY),
        ("k",),
    ).unwrap(),
    "project-sum": lambda: ops.project(
        Rel(
            ("a", "b"),
            [({"a": 1, "b": 1}, 2), ({"a": 1, "b": 2}, 5)],
            annotations=Z,
            annotations_reason=WHY,
        ),
        ("a",),
    ).unwrap(),
    "distinct-zxwhy": lambda: ops.distinct(_zxwhy_one_row()).unwrap(),
}


# ------------------------------------------------------------------- L1.4 Rel identity


def test_l1_4_the_golden_corpus_is_complete() -> None:
    # A vector with no builder, or a builder with no vector, silently narrows this law.
    assert {vector["name"] for vector in GOLDEN} == set(BUILDERS)


@pytest.mark.parametrize("vector", GOLDEN, ids=[v["name"] for v in GOLDEN])
def test_l1_4_golden_conformance(vector: dict) -> None:
    rel = BUILDERS[vector["name"]]()
    assert encode_canonical(rel.to_value()) == vector["canonical"].encode("utf-8"), vector["note"]
    assert rel.content_address() == vector["address"], vector["note"]


def test_l1_4_zero_annotations_are_absent_not_stored() -> None:
    assert BUILDERS["zero-dropped"]().content_address() == BUILDERS["one-row-z"]().content_address()
    assert len(BUILDERS["zero-dropped"]()) == 1
    empty = Rel(("a",), [({"a": 1}, 0)], annotations=Z, annotations_reason=WHY)
    assert len(empty) == 0
    assert empty.get({"a": 1}) == Z.zero  # an absent row reads as zero, not as an error


def test_l1_4_a_zero_component_is_not_the_product_zero() -> None:
    # The one place a naive "drop empty rows" rule would silently lose data (§3).
    retained = BUILDERS["zxwhy-zero-count"]()
    assert len(retained) == 1
    assert retained.content_address() != Rel(("a",), ()).content_address()
    assert retained.to_bag() == []  # ... and yet it has no bag image


def test_l1_4_from_value_inverts_to_value() -> None:
    for build in BUILDERS.values():
        rel = build()
        assert Rel.from_value(rel.to_value()) == rel


def test_l1_4_an_unknown_semiring_is_refused_by_name() -> None:
    value = dict(BUILDERS["one-row-z"]().to_value())
    value["semiring"] = "NotASemiringWeShip"
    with pytest.raises(rel_mod.RelError):
        Rel.from_value(value)


@pytest.mark.parametrize(
    ("schema", "rows"),
    [
        (("a",), [({"a": 1.5}, 1)]),                 # bare float: the M0 door, unchanged
        (("a",), [({"a": float("nan")}, 1)]),
        (("a",), [({"a": b"bytes"}, 1)]),
        (("a",), [({"a": (1, 2)}, 1)]),
    ],
    ids=["float", "nan", "bytes", "tuple"],
)
def test_l1_4_rows_are_m0_values_and_nothing_wider(schema, rows) -> None:
    with pytest.raises(CanonicalEncodingError):
        Rel(schema, rows, annotations=Z, annotations_reason=WHY)


@pytest.mark.parametrize(
    ("schema", "rows"),
    [
        (("a", "b"), [({"a": 1}, 1)]),               # ragged: missing a column
        (("a",), [({"a": 1, "b": 2}, 1)]),           # ragged: extra column
        ((), [({}, 1)]),                             # a Rel with no columns is not a Rel
        (("a", "a"), [({"a": 1}, 1)]),               # duplicate column
        ((1,), [({1: 1}, 1)]),                       # a column name is a str
    ],
    ids=["missing-column", "extra-column", "no-columns", "duplicate-column", "int-column"],
)
def test_l1_4_schemas_are_enforced_by_name(schema, rows) -> None:
    with pytest.raises(rel_mod.RelError):
        Rel(schema, rows, annotations=Z, annotations_reason=WHY)


def test_l1_4_schema_is_sorted_however_it_was_given() -> None:
    given_backwards = Rel(("x", "k"), [({"k": 1, "x": 2}, 1)], annotations=Z, annotations_reason=WHY)
    given_forwards = Rel(("k", "x"), [({"k": 1, "x": 2}, 1)], annotations=Z, annotations_reason=WHY)
    assert given_backwards.schema == ("k", "x")
    assert given_backwards.content_address() == given_forwards.content_address()


@given(st.lists(st.tuples(st.integers(-3, 3), st.integers(1, 4)), max_size=6))
def test_l1_4_round_trips_through_the_m0_store(tmp_path_factory, pairs) -> None:
    store = Store(tmp_path_factory.mktemp("store"))
    rel = Rel(("a",), [({"a": a}, n) for a, n in pairs], annotations=Z, annotations_reason=WHY)
    ref = store.put_value(rel.to_value())
    assert ref == rel.content_address()  # one address space (docs/specs/m0.md §3)
    assert Rel.from_value(store.get_value(ref)) == rel


# ------------------------------------------------------- L1.5 annotation defaults (D0002)


def test_l1_5_the_default_is_z_cross_why() -> None:
    # BRIEF §5.5: every pipeline gets deltas AND support-set provenance without asking.
    assert Rel(("a",)).annotations.name == "Z*Why"
    assert rel_mod.DEFAULT_ANNOTATIONS.name == "Z*Why"
    assert Rel(("a",)).annotations_reason is None


@pytest.mark.parametrize("S", ["Z", "B", "Why"])
def test_l1_5_opting_down_without_a_reason_is_refused(S) -> None:
    chosen = semiring.SEMIRINGS[S]
    with pytest.raises(rel_mod.RelError):
        Rel(("a",), (), annotations=chosen)
    assert Rel(("a",), (), annotations=chosen, annotations_reason=WHY).annotations.name == S


def test_l1_5_z_only_is_the_spelling_the_brief_uses() -> None:
    opted = Rel(("a",), [({"a": 1}, 2)], annotations=semiring.Z_ONLY, annotations_reason=WHY)
    assert opted.annotations.name == "Z"
    assert opted.annotations_reason == WHY


def test_l1_5_the_reason_is_not_part_of_identity() -> None:
    one = Rel(("a",), [({"a": 1}, 2)], annotations=Z, annotations_reason="because A")
    two = Rel(("a",), [({"a": 1}, 2)], annotations=Z, annotations_reason="because B")
    assert one.content_address() == two.content_address()
    assert one == two
    assert "because A" not in encode_canonical(one.to_value()).decode("utf-8")


def test_l1_5_operators_propagate_the_reason_rather_than_re_demanding_it() -> None:
    left = Rel(("a",), [({"a": 1}, 2)], annotations=Z, annotations_reason=WHY)
    right = Rel(("a",), [({"a": 2}, 1)], annotations=Z, annotations_reason=WHY)
    assert ops.union(left, right).unwrap().annotations_reason == WHY
    assert ops.distinct(left).unwrap().annotations_reason == WHY
    assert ops.project(left, ("a",)).unwrap().annotations_reason == WHY


def test_l1_5_mixing_semirings_is_refused_by_name() -> None:
    z_rel = Rel(("a",), [({"a": 1}, 2)], annotations=Z, annotations_reason=WHY)
    default_rel = Rel(("a",), [({"a": 1}, (2, Why.zero))])
    with pytest.raises(ops.OperatorError):
        ops.union(z_rel, default_rel).unwrap()
