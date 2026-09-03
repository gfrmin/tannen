"""`Why` explains an answer; it must never supply one (BRIEF P4).

There are two candidate ways to say "forget the provenance and check the answer did not
move", and they are NOT the same map. Getting them confused is what the `anti_join` defect
this file was written for actually was.

1. The PROJECTION `pi1: (n, w) -> n`. A genuine semiring homomorphism, so Green,
   Karvounarakis & Tannen's result applies: positive relational algebra commutes with it
   for free — `forget_why(op(r1, r2)) == op(forget_why(r1), forget_why(r2))` for every
   operator built from map/project, filter, union and join.

2. The BAG IMAGE `multiplicity`. This is what `to_bag` (§3.3), `aggregate` and `anti_join`
   mean by "really there", and it is what L1.9 uses to state that `Why` is inert.

The two part company on exactly one shape: `(n, 0_Why)` with `n != 0`, where `pi1` says
`n` copies and the bag image says none. **D0110 makes that shape unconstructible** — a
retained row is a witnessed row (docs/specs/m2.md §3), enforced in `Rel._init` — so over
every annotation a `Rel` can hold the two maps now AGREE, and the disagreement D0107
weighed dissolves instead of having to be decided. That is why this file draws ONE
generator where it used to draw two: the `REACHABLE` / `ANY_ANNOTATION` split existed only
to keep the unwitnessed annotations away from the tests that could not survive them, and
there are no unwitnessed annotations left to keep away.

What survives the collapse, and is pinned below rather than asserted in a comment:

* the bag image is still not a semiring homomorphism (`test_the_bag_image_is_not_a_...`)
  — but every witness to that is now an annotation `Rel` refuses to retain, which is the
  precise sense in which the disagreement is gone from relations and not from the algebra;
* the door itself, because a generator that can no longer draw a value is not evidence
  that the value was refused;
* `(0, w)` — witnessed, retained, no bag image — which D0093 kept and D0110 does not
  touch, and which is the one annotation `anti_join` must still not let block a left row.

THE ALARM, AND WHY ITS NAME IS NOW WRONG ON PURPOSE.
`test_the_alarm_is_closed_an_unwitnessed_row_cannot_be_constructed` fed `anti_join` a
`(2, 0_Why)` left row and watched the absence witness hand it a bag image it did not have
going in. D0110 said it was "the test that should be read the day an ingest path lands";
docs/specs/m2.md §3 says this is that day. It has been READ, and what it reported is that
its own premise is gone: the input it needs is refused at construction. So the node now
asserts the REFUSAL — the opposite claim under the old name.

The name is stale and is kept deliberately. D0110 is Tier C and OWNER-SIGNED, and the
signature is over the record's whole bytes (D0063 ruling 2), so retargeting its binding to
a renamed node costs an owner re-signature — an owner-only act, queued to the M2 boundary
sitting (D0138). Deleting or renaming the node here would leave a signed record binding
something that does not collect, which `scripts/check_decisions.py` fails, and no amount
of tidiness is worth a red guard on an owner's signature. The docstring carries what the
name no longer can.

Not a law under tests/laws/m1 — that directory is SEALED at m1-laws-freeze (D0056) and
nothing may be added beside it. This is ordinary post-freeze test coverage for a defect
found by review, the same shape as RT-M1-01/D0102.
"""

from __future__ import annotations

import pytest
from hypothesis import given, strategies as st

from tannen.kernel import ops
from tannen.kernel.algebra import Monoid
from tannen.kernel.rel import Rel, RelError
from tannen.kernel.semiring import Why, Z, ZxWhy

#: Syntactically valid refs (§2); their content never matters here, only their shape.
REFS = tuple(f"sha256:{n:064x}" for n in range(1, 4))

_support_set = st.frozensets(st.sampled_from(REFS), min_size=1, max_size=2)
_count = st.integers(min_value=0, max_value=3)

#: THE annotation generator — one, not two. Every annotation a `Rel` can retain is
#: witnessed, so `min_support=0` would draw values the constructor refuses rather than
#: values the operators must cope with (D0110).
ANNOTATIONS = st.tuples(_count, st.sets(_support_set, min_size=1, max_size=2)).map(
    lambda t: (t[0], Why.of(*t[1]))
)


def _rel(schema: tuple[str, ...], key_range=(-2, 2), val_range=(-3, 3)):
    row = st.fixed_dictionaries(
        {schema[0]: st.integers(*key_range), schema[1]: st.integers(*val_range)}
    )
    pairs = st.lists(st.tuples(row, ANNOTATIONS), max_size=4)
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


# ------------------------------------------------------- RA+: the law holds for free


@given(a=_rel(SCHEMA_A))
def test_forget_why_commutes_with_select(a: Rel) -> None:
    predicate = lambda row: row["x"] > 0
    assert forget_why(ops.select(a, predicate).unwrap()) == ops.select(forget_why(a), predicate).unwrap()


@given(a=_rel(SCHEMA_A))
def test_forget_why_commutes_with_project(a: Rel) -> None:
    assert forget_why(ops.project(a, ("k",)).unwrap()) == ops.project(forget_why(a), ("k",)).unwrap()


@given(a=_rel(SCHEMA_A), b=_rel(SCHEMA_A))
def test_forget_why_commutes_with_union(a: Rel, b: Rel) -> None:
    assert forget_why(ops.union(a, b).unwrap()) == ops.union(forget_why(a), forget_why(b)).unwrap()


@given(a=_rel(SCHEMA_A), b=_rel(SCHEMA_B))
def test_forget_why_commutes_with_join(a: Rel, b: Rel) -> None:
    left = forget_why(ops.join(a, b, ("k",)).unwrap())
    right = ops.join(forget_why(a), forget_why(b), ("k",)).unwrap()
    assert left == right


# --------------------- outside RA+: the same law, and no restricted generator any more


@given(a=_rel(SCHEMA_A))
def test_forget_why_commutes_with_distinct(a: Rel) -> None:
    """`distinct` goes through `collapse`, which is componentwise, so its `Z` side never
    reads `Why` — it agrees with the projection on the whole product, not just here."""
    assert forget_why(ops.distinct(a).unwrap()) == ops.distinct(forget_why(a)).unwrap()


@given(a=_rel(SCHEMA_A))
def test_forget_why_commutes_with_aggregate(a: Rel) -> None:
    """`aggregate` weights each value by `multiplicity`, so it follows the bag image, not
    the projection. Over the annotations a `Rel` can hold the two coincide (D0110), which
    is why this no longer needs a generator of its own."""
    left = forget_why(ops.aggregate(a, ("k",), SUM, lambda row: row["x"], "s").unwrap())
    right = ops.aggregate(forget_why(a), ("k",), SUM, lambda row: row["x"], "s").unwrap()
    assert left == right


@given(a=_rel(SCHEMA_A), b=_rel(SCHEMA_B))
def test_forget_why_commutes_with_anti_join(a: Rel, b: Rel) -> None:
    """The defect this file was written for. Before the fix in `ops.py`, presence was
    `annotation != zero`, so a right row of `(0, {{ref}})` — no bag image, but non-zero —
    blocked a matching left row under `ZxWhy` and not under `Z`. The absence witness M2
    multiplies into the survivors (D0132) touches only the `Why` component, so it cannot
    move this side of the identity."""
    left = forget_why(ops.anti_join(a, b, ("k",)).unwrap())
    right = ops.anti_join(forget_why(a), forget_why(b), ("k",)).unwrap()
    assert left == right


# ---------------------------------------------- what the single generator now rests on


@given(a=ANNOTATIONS, b=ANNOTATIONS)
def test_the_witnessed_annotations_are_closed(a, b) -> None:
    """`add` and `mul` both preserve a non-empty `Why`, so an operator fed witnessed rows
    cannot produce an unwitnessed one. It is a theorem about the semiring, so it is
    checked rather than commented — and since D0110 it is also what keeps every operator
    clear of a constructor that would now refuse the result."""
    assert ZxWhy.add(a, b)[1] != Why.zero
    assert ZxWhy.mul(a, b)[1] != Why.zero


@given(a=_rel(SCHEMA_A), b=_rel(SCHEMA_B))
def test_the_operators_never_manufacture_an_empty_why(a: Rel, b: Rel) -> None:
    """The same invariant end to end, through the operators themselves rather than through
    the algebra: witnessed in, witnessed out. Since D0110 an operator that broke it would
    RAISE inside `_finish` rather than return a bad `Rel`, so this now also checks that no
    operator trips the new door on well-formed input."""
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


# -------------------------------------------- the disagreement, and where it now lives


def test_the_bag_image_is_not_a_homomorphism() -> None:
    """Why there is no homomorphism law to state over the bag image: it is multiplicative
    (L1.2 asserts that) but not additive, so it is not a semiring homomorphism, and `pi1`
    is the only "forget Why" map that is one.

    Every witness to the failure carries an empty `Why`, which is exactly why the failure
    no longer reaches a relation: these are algebra elements, and `Rel` refuses to retain
    them (the next test). The bag image stays a bad homomorphism; it just has nothing left
    to be bad ON."""
    a, b = (1, Why.zero), (0, Why.of({REFS[0]}))
    assert ZxWhy.multiplicity(a) == 0 and ZxWhy.multiplicity(b) == 0
    assert ZxWhy.multiplicity(ZxWhy.add(a, b)) == 1  # ... and 1 != 0 + 0


def test_the_alarm_is_closed_an_unwitnessed_row_cannot_be_constructed() -> None:
    """THE ALARM, READ — and now the opposite claim, under a name kept stale on purpose
    (see the module docstring: D0110 is owner-signed and binds this node id).

    What it used to assert, verbatim from M1: a left row of `(2, 0_Why)` has no bag image
    going in, `anti_join` adds its absence witness to the survivor, and the row comes out
    with two copies — provenance manufacturing an answer, which is the one thing BRIEF P4
    forbids. It was green only because nothing reachable could construct that input.

    What it asserts now: the input is refused. Both halves of the old scenario are built
    below and the LEFT one never gets made, which is the whole of D0110 in one line.

    It is also what earns this file's single annotation generator. A generator that
    quietly cannot reach a case looks exactly like a case that cannot exist, and this repo
    has already paid for that confusion once (D0114). L2.2 asserts the same refusal inside
    the frozen corpus; the duplicate is deliberate and it is local to the generator that
    depends on it.
    """
    right = Rel(("k", "y"), [({"k": 9, "y": 9}, (1, Why.of({REFS[0]})))], annotations=ZxWhy)
    assert len(right) == 1, "the right operand of the old scenario is still ordinary"
    with pytest.raises(RelError):
        Rel(("k", "x"), [({"k": 1, "x": 1}, (2, Why.zero))], annotations=ZxWhy)


def test_a_zero_count_with_support_is_retained_and_still_cannot_block() -> None:
    """The half of the L1.2/D0093 pair that D0110 does NOT touch: `(0, w)` is witnessed, is
    not the product zero, and is retained — with no bag image, so `anti_join` must not let
    it block a matching left row. `pi1` agrees here (it projects to `0`, which `Z` drops),
    which is the whole reason the two maps now coincide on everything a `Rel` can hold."""
    blocked = Rel(("k", "y"), [({"k": 1, "y": 9}, (0, Why.of({REFS[0]})))], annotations=ZxWhy)
    assert len(blocked) == 1 and blocked.to_bag() == []
    left = Rel(("k", "x"), [({"k": 1, "x": 1}, (1, Why.of({REFS[1]})))], annotations=ZxWhy)
    assert len(ops.anti_join(left, blocked, ("k",)).unwrap()) == 1
    assert len(ops.anti_join(forget_why(left), forget_why(blocked), ("k",)).unwrap()) == 1
