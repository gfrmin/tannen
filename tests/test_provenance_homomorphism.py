"""`Why` explains an answer; it must never supply one (BRIEF P4).

There are two candidate ways to say "forget the provenance and check the answer did not
move", and they are NOT the same map. Getting them confused is what the `anti_join` defect
this file was written for actually was.

1. The PROJECTION `pi1: (n, w) -> n`. A genuine semiring homomorphism, so Green,
   Karvounarakis & Tannen's result applies: positive relational algebra commutes with it
   for free — `forget_why(op(r1, r2)) == op(forget_why(r1), forget_why(r2))` for every
   operator built from map/project, filter, union and join. That holds for EVERY
   annotation, so the RA+ tests below draw from the whole product, empty `Why` included.

2. The BAG IMAGE `multiplicity`. This is what `to_bag` (§3.3), `aggregate` and `anti_join`
   mean by "really there", and it is what L1.9 uses to state that `Why` is inert. It is
   multiplicative but NOT additive (`mult((1,0_Why) + (0,w))` is 1, while the summands
   have multiplicity 0 each), so it is not a homomorphism at all, and no homomorphism law
   can be stated over it. `test_the_bag_image_is_not_a_homomorphism` pins that.

The two agree everywhere except on annotations with an empty `Why`, where L1.2 (as amended
by D0093) is explicit: both `(0, w)` and `(n, 0_Why)` are non-zero annotations with no bag
image. `distinct`, `aggregate` and `anti_join` sit outside RA+ and follow (2), so they are
tested against `pi1` over the REACHABLE annotations only — and "reachable" is checked here,
not asserted in a comment: `test_the_reachable_annotations_are_closed` and
`test_the_operators_never_manufacture_an_empty_why` are what earn that restriction.
`test_an_empty_why_has_no_bag_image_so_it_cannot_block` pins the disagreement itself, so it
is specified behaviour rather than a gap between two generators.

Not a law under tests/laws/m1 — that directory is SEALED at m1-laws-freeze (D0056) and
nothing may be added beside it. This is ordinary post-freeze test coverage for a defect
found by review, the same shape as RT-M1-01/D0102.
"""

from __future__ import annotations

from hypothesis import given, strategies as st

from tannen.kernel import ops
from tannen.kernel.algebra import Monoid
from tannen.kernel.rel import Rel
from tannen.kernel.semiring import Why, Z, ZxWhy

#: Syntactically valid refs (§2); their content never matters here, only their shape.
REFS = tuple(f"sha256:{n:064x}" for n in range(1, 4))

_support_set = st.frozensets(st.sampled_from(REFS), min_size=1, max_size=2)
_count = st.integers(min_value=0, max_value=3)


def _annotations(*, min_support: int):
    """`min_support=1` draws the REACHABLE annotations — those a row can actually carry,
    every one of them witnessed. `min_support=0` also draws `(n, 0_Why)`: constructible
    through the public `Rel(...)`, never produced by an operator, and the exact place the
    projection and the bag image part company."""
    support = st.sets(_support_set, min_size=min_support, max_size=2)
    return st.tuples(_count, support).map(lambda t: (t[0], Why.of(*t[1])))


REACHABLE = _annotations(min_support=1)
ANY_ANNOTATION = _annotations(min_support=0)


def _rel(schema: tuple[str, ...], annotation=REACHABLE, key_range=(-2, 2), val_range=(-3, 3)):
    row = st.fixed_dictionaries(
        {schema[0]: st.integers(*key_range), schema[1]: st.integers(*val_range)}
    )
    pairs = st.lists(st.tuples(row, annotation), max_size=4)
    return pairs.map(lambda ps: Rel(schema, ps, annotations=ZxWhy))


def forget_why(rel: Rel) -> Rel:
    """`pi1`, lifted to a `Rel`: project `ZxWhy` down to `Z`, dropping `Why`. Test-only;
    stating the homomorphism law is the only reason it exists."""
    assert rel.annotations.name == "Z*Why", f"forget_why: {rel.annotations.name} has no Why"
    return Rel(
        rel.schema,
        ((row, annotation[0]) for row, annotation in rel),
        annotations=Z,
        annotations_reason="test: forgot Why to state the homomorphism law",
    )


SCHEMA_A = ("k", "x")
SCHEMA_B = ("k", "y")
SUM = Monoid("sum", lambda a, b: a + b, 0, witnesses=range(-6, 7))


# ------------------------------------------- RA+: the law holds for EVERY annotation


@given(a=_rel(SCHEMA_A, ANY_ANNOTATION))
def test_forget_why_commutes_with_select(a: Rel) -> None:
    predicate = lambda row: row["x"] > 0
    assert forget_why(ops.select(a, predicate).unwrap()) == ops.select(forget_why(a), predicate).unwrap()


@given(a=_rel(SCHEMA_A, ANY_ANNOTATION))
def test_forget_why_commutes_with_project(a: Rel) -> None:
    assert forget_why(ops.project(a, ("k",)).unwrap()) == ops.project(forget_why(a), ("k",)).unwrap()


@given(a=_rel(SCHEMA_A, ANY_ANNOTATION), b=_rel(SCHEMA_A, ANY_ANNOTATION))
def test_forget_why_commutes_with_union(a: Rel, b: Rel) -> None:
    assert forget_why(ops.union(a, b).unwrap()) == ops.union(forget_why(a), forget_why(b)).unwrap()


@given(a=_rel(SCHEMA_A, ANY_ANNOTATION), b=_rel(SCHEMA_B, ANY_ANNOTATION))
def test_forget_why_commutes_with_join(a: Rel, b: Rel) -> None:
    left = forget_why(ops.join(a, b, ("k",)).unwrap())
    right = ops.join(forget_why(a), forget_why(b), ("k",)).unwrap()
    assert left == right


# ------------------------ outside RA+: the law holds over the REACHABLE annotations


@given(a=_rel(SCHEMA_A))
def test_forget_why_commutes_with_distinct(a: Rel) -> None:
    """`distinct` goes through `collapse`, which is componentwise, so its `Z` side never
    reads `Why` — it agrees with the projection on the whole product, not just here."""
    assert forget_why(ops.distinct(a).unwrap()) == ops.distinct(forget_why(a)).unwrap()


@given(a=_rel(SCHEMA_A))
def test_forget_why_commutes_with_aggregate(a: Rel) -> None:
    """`aggregate` weights each value by `multiplicity`, so it follows the bag image, not
    the projection. Over reachable annotations the two coincide and this holds."""
    left = forget_why(ops.aggregate(a, ("k",), SUM, lambda row: row["x"], "s").unwrap())
    right = ops.aggregate(forget_why(a), ("k",), SUM, lambda row: row["x"], "s").unwrap()
    assert left == right


@given(a=_rel(SCHEMA_A), b=_rel(SCHEMA_B))
def test_forget_why_commutes_with_anti_join(a: Rel, b: Rel) -> None:
    """The defect this file was written for. Before the fix in `ops.py`, presence was
    `annotation != zero`, so a right row of `(0, {{ref}})` — no bag image, but non-zero —
    blocked a matching left row under `ZxWhy` and not under `Z`."""
    left = forget_why(ops.anti_join(a, b, ("k",)).unwrap())
    right = ops.anti_join(forget_why(a), forget_why(b), ("k",)).unwrap()
    assert left == right


# ------------------------------- what earns the restriction on the three tests above


@given(a=REACHABLE, b=REACHABLE)
def test_the_reachable_annotations_are_closed(a, b) -> None:
    """`add` and `mul` both preserve a non-empty `Why`, so an operator fed witnessed rows
    cannot produce an unwitnessed one. This is the invariant the three tests above rely
    on; it is a theorem about the semiring, so it is checked rather than commented."""
    assert ZxWhy.add(a, b)[1] != Why.zero
    assert ZxWhy.mul(a, b)[1] != Why.zero


@given(a=_rel(SCHEMA_A), b=_rel(SCHEMA_B))
def test_the_operators_never_manufacture_an_empty_why(a: Rel, b: Rel) -> None:
    """The same invariant end to end, through the operators themselves rather than
    through the algebra: witnessed in, witnessed out."""
    results = [
        ops.select(a, lambda row: row["x"] > 0),
        ops.project(a, ("k",)),
        ops.union(a, a),
        ops.join(a, b, ("k",)),
        ops.distinct(a),
        ops.aggregate(a, ("k",), SUM, lambda row: row["x"], "s"),
        ops.anti_join(a, b, ("k",)),
    ]
    for outcome in results:
        for _, annotation in outcome.unwrap():
            assert annotation[1] != Why.zero


# ------------------------------------------------- the disagreement, pinned in place


def test_the_bag_image_is_not_a_homomorphism() -> None:
    """Why there is no homomorphism law to state over the bag image: it is multiplicative
    (L1.2 asserts that) but not additive, so it is not a semiring homomorphism, and `pi1`
    is the only "forget Why" map that is one."""
    a, b = (1, Why.zero), (0, Why.of({REFS[0]}))
    assert ZxWhy.multiplicity(a) == 0 and ZxWhy.multiplicity(b) == 0
    assert ZxWhy.multiplicity(ZxWhy.add(a, b)) == 1  # ... and 1 != 0 + 0


def test_an_empty_why_has_no_bag_image_so_it_cannot_block() -> None:
    """The one place `anti_join` deliberately disagrees with `pi1`, stated rather than
    left to a generator's silence. `(3, 0_Why)` is non-zero, so `Rel` keeps it (L1.4), but
    L1.2/D0093 give it no bag image — `to_bag` sees an empty relation, so there is nothing
    to block with, and the left row survives. Under `Z` the same row is three copies and
    blocks. `anti_join` follows `to_bag` and `aggregate` here; making it follow `pi1`
    instead would leave it the only operator disagreeing with the bag image."""
    unwitnessed = Rel(
        ("k", "y"), [({"k": 1, "y": 9}, (3, Why.zero))], annotations=ZxWhy,
        annotations_reason="test: the annotation with no bag image",
    )
    assert len(unwitnessed) == 1 and unwitnessed.to_bag() == []
    left = Rel(
        ("k", "x"), [({"k": 1, "x": 1}, (1, Why.of({REFS[0]})))], annotations=ZxWhy,
        annotations_reason="test: an ordinary witnessed row",
    )
    assert len(ops.anti_join(left, unwitnessed, ("k",)).unwrap()) == 1
    assert len(ops.anti_join(forget_why(left), forget_why(unwitnessed), ("k",)).unwrap()) == 0


def test_a_survivors_witness_can_give_an_unwitnessed_row_a_bag_image() -> None:
    """The far edge of the same unreachable state, pinned so it is not a surprise later:
    `anti_join` adds a witness to survivors, so a left row of `(2, 0_Why)` — no bag image
    going in — comes out as `(2, {addr})`, which has one. Only reachable by constructing
    the input directly; `test_the_reachable_annotations_are_closed` is why no operator
    can hand this to another."""
    left = Rel(
        ("k", "x"), [({"k": 1, "x": 1}, (2, Why.zero))], annotations=ZxWhy,
        annotations_reason="test: unwitnessed, so no bag image",
    )
    right = Rel(
        ("k", "y"), [({"k": 9, "y": 9}, (1, Why.of({REFS[0]})))], annotations=ZxWhy,
        annotations_reason="test: a non-matching right row",
    )
    assert left.to_bag() == []
    assert ops.anti_join(left, right, ("k",)).unwrap().to_bag() == [(1, 1), (1, 1)]  # 2 copies
