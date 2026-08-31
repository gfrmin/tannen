"""The MODEL half of M2's provenance laws — the frozen oracle (docs/specs/m2.md §9).

FROZEN at m2-laws-freeze, and frozen deliberately, for the reason D0094 gives: under the
frozen-oracle protocol every law is an `importorskip` at exactly the moment it becomes
unrewritable, so `pytest tests/laws/m2` prints the same "N skipped" whether the laws are
correct, contradictory or nonsense. A model beside them turns Session A's gate from "the
laws do not run" into "the laws pass against a model and fail against a stated mutant".

It imports NOTHING from tannen (the `_fragment.py` precedent, D0089): a law module passes
its subject in, so this file can never be the reason a pre-implementation run *errors*
instead of *skipping*.

Three things live here.

1.  A naive, self-contained transcription of the spec: PosBool `Why`, the annotation
    product ℤ × Why, and the operators of docs/specs/m2.md §4 over plain dicts. It may be
    quadratic and partial, because nothing ships it.
2.  The `Subject` interface every check is written against, and `MODEL`, the model's own
    implementation of it. `tests/laws/m2/_subject.py` builds the tannen one.
3.  `MUTANTS` — deliberately broken subjects, one per model-checked law family. A law that
    passes against its mutant is not testing what it claims (D0094 §2, D0092's discipline).
    `MUTANTS["antijoin-disjunctive"]` is not a hypothetical: it is tannen's M1 behaviour as
    shipped, and L2.6 failing against it is D0132's defect stated as a law.

Generators follow D0118's rule: the empty relation is drawn as a NAMED case rather than
as a side effect of the size distribution, each shape declares the case it exists to
exercise, and every draw reports its own shape through hypothesis `event()`. No thresholds
anywhere — D0118 measured why a floor is the wrong instrument.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from hypothesis import event, strategies as st

__all__ = [
    "ATOMS",
    "MODEL",
    "MUTANTS",
    "REQUIRED",
    "FAMILIES",
    "SHAPES",
    "Shape",
    "run_family",
    "Subject",
    "ann_add",
    "ann_mul",
    "antichain",
    "atoms_of",
    "check_absence_witness",
    "check_aggregate_key_characterisation",
    "check_deletion_characterisation",
    "check_differential",
    "check_inertness",
    "check_minimal_witnesses",
    "check_witnessed_construction",
    "delete",
    "evaluate",
    "source_tables",
    "tables_of",
    "surviving",
    "why_add",
    "why_mul",
]

# --------------------------------------------------------------------------- the algebra

#: A `Why` element is a finite antichain of finite support sets of refs (m2 §2, m1 §2).
#: Antichain-normalised sets-of-sets ARE PosBool — which is why §5's survival theorem is
#: exact rather than approximate.


def antichain(sets: Any) -> frozenset:
    candidates = {frozenset(s) for s in sets}
    return frozenset(s for s in candidates if not any(other < s for other in candidates))


def why_add(a: Any, b: Any) -> frozenset:
    return antichain(set(a) | set(b))


def why_mul(a: Any, b: Any) -> frozenset:
    return antichain(x | y for x in a for y in b)


WHY_ZERO: frozenset = frozenset()
WHY_ONE: frozenset = frozenset({frozenset()})
ZERO = (0, WHY_ZERO)
ONE = (1, WHY_ONE)


def ann_add(p: Any, q: Any) -> tuple:
    return (p[0] + q[0], why_add(p[1], q[1]))


def ann_mul(p: Any, q: Any) -> tuple:
    return (p[0] * q[0], why_mul(p[1], q[1]))


def collapse(p: Any) -> tuple:
    return (1 if p[0] > 0 else 0, p[1])


def multiplicity(p: Any) -> int:
    return p[0] * (1 if p[1] else 0)


def atoms_of(why: Any) -> frozenset:
    """Every ref mentioned anywhere in a `Why` element."""
    return frozenset(atom for support in why for atom in support)


def surviving(why: Any, deleted: Any) -> frozenset:
    """The witnesses of `why` untouched by deleting `deleted` — §5's prediction, and the
    whole content of L2.3: a support set survives iff it is disjoint from the deleted
    atoms, and the row survives iff any support set does."""
    deleted = frozenset(deleted)
    return antichain(s for s in why if not (s & deleted))


# ------------------------------------------------------------------------ the model Rel


class ModelRefusal(Exception):
    """The model's analogue of `RelError` — a value the spec says is not a value."""


def _key(row: dict) -> tuple:
    return tuple(sorted(row.items()))


class MRel:
    """A finite K-relation as a dict. Naive on purpose."""

    def __init__(self, schema: Any, pairs: Any, *, witnessed: bool = True, add: Any = None) -> None:
        add = ann_add if add is None else add
        self.schema = tuple(sorted(schema))
        merged: dict = {}
        for row, annotation in pairs:
            if tuple(sorted(row)) != self.schema:
                raise ModelRefusal(f"ragged row {row!r} against schema {self.schema!r}")
            k = _key(row)
            merged[k] = (row, add(merged[k][1], annotation) if k in merged else annotation)
        self.rows = {}
        for k, (row, annotation) in merged.items():
            if annotation == ZERO:
                continue  # zero annotations are absent, not stored (m1 §3)
            if witnessed and not annotation[1]:
                # D0110: an annotation claiming copies of a row it has no derivation for
                # is a contradiction in a provenance semiring, not a value.
                raise ModelRefusal(f"unwitnessed annotation {annotation!r} for row {row!r}")
            self.rows[k] = (dict(row), annotation)

    def __iter__(self):
        for _, (row, annotation) in sorted(self.rows.items()):
            yield dict(row), annotation

    def __len__(self) -> int:
        return len(self.rows)

    def read(self) -> dict:
        return {k: annotation for k, (_, annotation) in self.rows.items()}

    def bag(self) -> list:
        out = []
        for _, (row, annotation) in sorted(self.rows.items()):
            out.extend([tuple(row[c] for c in self.schema)] * multiplicity(annotation))
        return sorted(out, key=repr)

    def address(self) -> str:
        payload = json.dumps(
            [self.schema, [[sorted(r.items()), [a[0], sorted(sorted(s) for s in a[1])]]
                           for _, (r, a) in sorted(self.rows.items())]],
            sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(payload).hexdigest()


# --------------------------------------------------------------------------- the subject


class Subject:
    """What a law needs of an implementation. `MODEL` is the transcription; `_subject.py`
    wraps tannen in the same shape. Every check below is written against this and nothing
    else, so the same assertion text runs against both."""

    name = "model"
    refusal = ModelRefusal

    # -- the algebra, as hooks: a mutant may break the semiring itself, not only an operator
    def w_add(self, a: Any, b: Any) -> frozenset:
        return why_add(a, b)

    def w_mul(self, a: Any, b: Any) -> frozenset:
        return why_mul(a, b)

    def a_add(self, p: Any, q: Any) -> tuple:
        return (p[0] + q[0], self.w_add(p[1], q[1]))

    def a_mul(self, p: Any, q: Any) -> tuple:
        return (p[0] * q[0], self.w_mul(p[1], q[1]))

    def rel(self, schema: Any, pairs: Any) -> Any:
        return MRel(schema, pairs, add=self.a_add)

    def read(self, r: Any) -> dict:
        return r.read()

    def bag(self, r: Any) -> list:
        return r.bag()

    def address(self, r: Any) -> str:
        return r.address()

    # -- operators (docs/specs/m2.md §4; the M1 semiring rules, unchanged)

    def select(self, r: Any, predicate: Any) -> Any:
        return MRel(r.schema, [(row, a) for row, a in r if predicate(row)], add=self.a_add)

    def project(self, r: Any, columns: Any) -> Any:
        cols = tuple(sorted(columns))
        return MRel(cols, [({c: row[c] for c in cols}, a) for row, a in r], add=self.a_add)

    def map_rows(self, r: Any, f: Any, schema: Any) -> Any:
        return MRel(schema, [(f(row), a) for row, a in r], add=self.a_add)

    def union(self, a: Any, b: Any) -> Any:
        return MRel(a.schema, list(a) + list(b), add=self.a_add)

    def join(self, a: Any, b: Any, on: Any) -> Any:
        keys = tuple(sorted(on))
        schema = tuple(sorted(set(a.schema) | set(b.schema)))
        out = []
        for ra, aa in a:
            for rb, ab in b:
                if all(ra[k] == rb[k] for k in keys):
                    out.append(({**ra, **rb}, self.a_mul(aa, ab)))
        return MRel(schema, out, add=self.a_add)

    def distinct(self, r: Any) -> Any:
        return MRel(r.schema, [(row, collapse(a)) for row, a in r], add=self.a_add)

    def anti_join(self, a: Any, b: Any, on: Any) -> Any:
        keys = tuple(sorted(on))
        present = {tuple(row[k] for k in keys) for row, ann in b if multiplicity(ann) > 0}
        witness = frozenset({frozenset({b.address()})}) if len(b) else None
        out = []
        for row, ann in a:
            if tuple(row[k] for k in keys) in present:
                continue
            # CONJUNCTION (D0132). The claim is "this row's own derivation held AND the
            # right relation lacked this key at this version". `add` would read as OR and
            # would leave the absence witness standing alone as an independent derivation.
            out.append((row, self.combine_witness(ann, witness) if witness else ann))
        return MRel(a.schema, out, add=self.a_add)

    def combine_witness(self, annotation: Any, witness: Any) -> tuple:
        return (annotation[0], self.w_mul(annotation[1], witness))

    def aggregate_sum(self, r: Any, by: Any, column: str, into: str) -> Any:
        keys = tuple(sorted(by))
        groups: dict = {}
        for row, ann in r:
            groups.setdefault(tuple(row[k] for k in keys), []).append((row, ann))
        out = []
        for members in groups.values():
            total = members[0][1]
            for _, ann in members[1:]:
                total = self.a_add(total, ann)
            folded = sum(row[column] * multiplicity(ann) for row, ann in members)
            head = members[0][0]
            out.append(({**{k: head[k] for k in keys}, into: folded}, collapse(total)))
        return MRel(tuple(sorted(keys + (into,))), out, add=self.a_add)


#: Exactly what a check calls on a subject. `_subject.py` asserts the tannen adapter
#: defines EVERY name here in its own `__dict__` — it deliberately does not subclass
#: `Subject`, because inheriting would let a forgotten method fall back to model code and
#: report the model passing while wearing tannen's name.
REQUIRED = (
    "name", "refusal", "rel", "read", "bag", "address",
    "select", "project", "map_rows", "union", "join", "distinct", "anti_join", "aggregate_sum",
)

MODEL = Subject()


# ---------------------------------------------------------------------------- the shapes

#: The atom alphabet. Source rows carry ONE atom each — that is what makes "delete a
#: source row" a concrete act rather than a symbolic one, and what makes a witness
#: minimal-checkable (§5).
ATOMS = tuple(f"sha256:{n:064x}" for n in range(1, 13))

TABLES = {"a": ("k", "x"), "b": ("k", "y"), "c": ("k", "z")}


class Shape:
    """One named plan, plus the case it exists to exercise (D0118: a shape declares its
    own interesting case rather than inheriting one from the size distribution)."""

    __slots__ = ("name", "plan", "tables", "note")

    def __init__(self, name: str, plan: Any, tables: Any, note: str) -> None:
        self.name, self.plan, self.tables, self.note = name, plan, tuple(tables), note

    def __repr__(self) -> str:
        return f"Shape({self.name!r})"


A, B, C = ("src", "a"), ("src", "b"), ("src", "c")

#: Composition depth is bought by making shapes composite rather than by generating trees
#: — a generator bug in a frozen file can only be superseded, never fixed (D0089).
POSITIVE = (
    Shape("select", ("select", A, "x-positive"), "a", "a filter whose literal comes from the column it filters"),
    Shape("project", ("project", A, ("k",)), "a", "projection SUMS, so two rows share one output witness"),
    Shape("map-rows", ("map_rows", A, "k-only"), "a", "a total map; distinct rows may collide"),
    Shape("union", ("union", ("project", A, ("k",)), ("project", B, ("k",))), "ab", "add: two independent witnesses"),
    Shape("join", ("join", A, B, ("k",)), "ab", "mul: one witness carrying both sides"),
    Shape("distinct", ("distinct", ("project", A, ("k",))), "a", "collapse keeps the support"),
    Shape("join-then-project", ("project", ("join", A, B, ("k",)), ("k",)), "ab", "mul then add"),
    Shape("join-three", ("join", ("join", A, B, ("k",)), C, ("k",)), "abc", "three-way support sets"),
    Shape("union-of-joins",
          ("union", ("project", ("join", A, B, ("k",)), ("k",)), ("project", ("join", A, C, ("k",)), ("k",))),
          "abc", "the same row reachable two ways: a genuine antichain of two witnesses"),
    Shape("distinct-of-union", ("distinct", ("union", ("project", A, ("k",)), ("project", B, ("k",)))), "ab",
          "collapse after add"),
    Shape("select-then-join", ("join", ("select", A, "x-positive"), B, ("k",)), "ab", "filter under a join"),
    #: The one shape that makes antichain normalisation OBSERVABLE: a row derivable from
    #: `a` alone AND from `a ⋈ b`, so `{a}` and `{a, b}` meet in one element and the
    #: superset must be dropped. Without it nothing in the catalogue can tell a normalised
    #: `Why` from an unnormalised one, and the `no-antichain` mutant survives (D0094 §2).
    Shape("union-with-join",
          ("union", ("project", A, ("k",)), ("project", ("join", A, B, ("k",)), ("k",))),
          "ab", "a redundant superset witness: the antichain must drop {a, b} beside {a}"),
)

AGGREGATE = (
    Shape("aggregate-sum", ("aggregate", A, ("k",), "x", "s"), "a",
          "the group KEY is monotone; the folded VALUE is not (§5)"),
    Shape("aggregate-of-join", ("aggregate", ("join", A, B, ("k",)), ("k",), "x", "s"), "ab",
          "aggregate over a join"),
)

ANTI = (
    Shape("anti-join", ("anti_join", A, B, ("k",)), "ab", "PARTIAL key overlap: some survive, some do not"),
    Shape("anti-join-then-project", ("project", ("anti_join", A, B, ("k",)), ("x",)), "ab",
          "the absence witness travelling through a projection"),
    Shape("join-then-anti", ("anti_join", ("join", A, B, ("k",)), C, ("k",)), "abc",
          "an absence witness on top of a two-source witness"),
)

SHAPES = POSITIVE + AGGREGATE + ANTI

PREDICATES = {"x-positive": lambda row: row.get("x", 0) > 0}
MAPS = {"k-only": lambda row: {"k": row["k"]}}
MAP_SCHEMAS = {"k-only": ("k",)}


def evaluate(subject: Subject, plan: Any, rels: dict) -> Any:
    head = plan[0]
    if head == "src":
        return rels[plan[1]]
    if head == "select":
        return subject.select(evaluate(subject, plan[1], rels), PREDICATES[plan[2]])
    if head == "project":
        return subject.project(evaluate(subject, plan[1], rels), plan[2])
    if head == "map_rows":
        return subject.map_rows(evaluate(subject, plan[1], rels), MAPS[plan[2]], MAP_SCHEMAS[plan[2]])
    if head == "distinct":
        return subject.distinct(evaluate(subject, plan[1], rels))
    if head == "union":
        return subject.union(evaluate(subject, plan[1], rels), evaluate(subject, plan[2], rels))
    if head == "join":
        return subject.join(evaluate(subject, plan[1], rels), evaluate(subject, plan[2], rels), plan[3])
    if head == "anti_join":
        return subject.anti_join(evaluate(subject, plan[1], rels), evaluate(subject, plan[2], rels), plan[3])
    if head == "aggregate":
        return subject.aggregate_sum(evaluate(subject, plan[1], rels), plan[2], plan[3], plan[4])
    raise AssertionError(f"unknown plan head {head!r}")


def tables_of(plan: Any) -> frozenset:
    """The source table names a plan actually reads. `shape.tables` lists what the SHAPE
    draws; a sub-plan reads a subset of it, and L2.6 needs the subset — in `join-then-anti`
    the right operand is `c` alone while `a` and `b` sit on the left."""
    if not isinstance(plan, tuple):
        return frozenset()
    if plan[0] == "src":
        return frozenset({plan[1]})
    return frozenset().union(*(tables_of(part) for part in plan[1:])) if len(plan) > 1 else frozenset()


def right_operand(plan: Any) -> Any:
    """The `anti_join` right operand of a plan, or None. L2.6 needs it by name: the atom
    the witness cites is that relation's address, and no other."""
    if not isinstance(plan, tuple):
        return None
    if plan[0] == "anti_join":
        return plan[2]
    for part in plan[1:]:
        found = right_operand(part)
        if found is not None:
            return found
    return None


# ------------------------------------------------------------------------- the generators

#: D0118: the empty relation is drawn as a NAMED case, not as the default outcome of an
#: unbounded size draw, and each table reports the shape it was drawn as.
_KEYS = (0, 1, 2)
_VALUES = (-2, 0, 1, 3)


def _rows(schema: tuple, keys: Any, atoms: Any) -> Any:
    value = st.sampled_from(_VALUES)
    row = st.fixed_dictionaries({schema[0]: st.sampled_from(tuple(keys)), schema[1]: value})
    body = st.lists(st.tuples(row, st.integers(1, 3)), min_size=1, max_size=4)  # named-empty below
    return st.one_of(st.just([]), body).map(
        lambda pairs: [
            (row, (m, frozenset({frozenset({atom})})))
            for (row, m), atom in zip(pairs, atoms)
        ]
    )


@st.composite
def source_tables(draw: Any, names: str = "abc", overlap: str = "partial") -> dict:
    """One `MRel`-shaped payload per named table, each source row carrying its own atom.

    `overlap` declares the case (D0118): `"partial"` gives an anti-join something to both
    keep and drop, `"full"` gives a join something to match on, `"none"` exercises the
    empty result as a case that was CHOSEN rather than one that happened, and `"grouped"`
    forces MULTI-MEMBER GROUPS, which is the case an aggregate exists to exercise.

    `"grouped"` was added because it had to be, and the measurement is worth recording:
    the `aggregate-forgets-the-group` mutant — an aggregate citing only its group's first
    member — survives 20 draws under `"full"` and dies only around 200, because it is
    caught solely when the DELETED row is the first member of a group with at least two.
    Under `"grouped"` it dies well inside 25. That is D0118's rule paying for itself: the
    fix was to draw the interesting case on purpose, not to raise the example budget until
    the accident happened often enough.
    """
    keys = {
        "partial": (_KEYS, (1, 2, 3)),
        "full": (_KEYS, _KEYS),
        "none": ((0, 1), (7, 8)),
        "grouped": ((0,), (0,)),
    }[overlap]
    out: dict = {}
    pool = iter(ATOMS)
    for index, name in enumerate(names):
        schema = TABLES[name]
        rows = draw(_rows(schema, keys[0] if index == 0 else keys[1], pool))
        out[name] = (schema, rows)
        event(f"table {name}: {'empty' if not rows else 'non-empty'}")
    event(f"overlap: {overlap}")
    return out


def build(subject: Subject, tables: dict) -> dict:
    return {name: subject.rel(schema, rows) for name, (schema, rows) in tables.items()}


def delete(tables: dict, deleted: Any) -> dict:
    """`R \\ D` — drop every source row whose atom is deleted. This is the ONLY thing
    "delete a source row" means in these laws (§5); the store is append-only and nothing
    here removes bytes from it."""
    deleted = frozenset(deleted)
    return {
        name: (schema, [(row, a) for row, a in rows if not (atoms_of(a[1]) & deleted)])
        for name, (schema, rows) in tables.items()
    }


def source_atoms(tables: dict) -> tuple:
    seen: list = []
    for _, rows in tables.values():
        for _, annotation in rows:
            seen.extend(sorted(atoms_of(annotation[1])))
    return tuple(sorted(set(seen)))


# ------------------------------------------------------------------------------ the checks
#
# Each takes a Subject and raises AssertionError. The frozen law modules call these with
# tannen's subject; tests/test_law_validation.py calls them with MODEL (must pass) and with
# each MUTANTS entry (must fail). One assertion text, two stands.


def check_witnessed_construction(subject: Subject) -> None:
    """L2.2 — nonzero implies witnessed (D0110)."""
    atom = frozenset({frozenset({ATOMS[0]})})
    ok = subject.rel(("k", "x"), [({"k": 1, "x": 1}, (2, atom))])
    assert len(subject.read(ok)) == 1, "a witnessed row is an ordinary row"

    try:
        subject.rel(("k", "x"), [({"k": 1, "x": 1}, (2, WHY_ZERO))])
    except subject.refusal:
        pass
    else:
        raise AssertionError("an unwitnessed nonzero annotation was accepted (D0110)")

    # ...and the zero annotation is still merely ABSENT, not a refusal.
    dropped = subject.rel(("k", "x"), [({"k": 1, "x": 1}, ZERO)])
    assert subject.read(dropped) == {}, "the semiring zero is dropped, not refused"

    # (0, {{r}}) is NOT the product zero: witnessed, no bag image, retained (m1 §3, D0093).
    retained = subject.rel(("k", "x"), [({"k": 1, "x": 1}, (0, atom))])
    assert len(subject.read(retained)) == 1, "(0, {{r}}) is witnessed and retained"
    assert subject.bag(retained) == [], "...and has no bag image"


def check_deletion_characterisation(subject: Subject, shape: Shape, tables: dict, deleted: Any) -> None:
    """L2.3 — the survival theorem, both directions, on the positive fragment.

    Antichain-normalised `Why` is PosBool, so the witnesses of an output row over `R \\ D`
    are EXACTLY the witnesses over `R` that D does not touch. That is stronger than the
    soundness BRIEF §6 asks for and it subsumes it.
    """
    before = subject.read(evaluate(subject, shape.plan, build(subject, tables)))
    after = subject.read(evaluate(subject, shape.plan, build(subject, delete(tables, deleted))))
    for key, annotation in before.items():
        predicted = surviving(annotation[1], deleted)
        if predicted:
            assert key in after, f"{shape.name}: {key} had a surviving witness {predicted} and vanished"
            assert after[key][1] == predicted, (
                f"{shape.name}: {key} survived with {after[key][1]}, expected exactly {predicted}"
            )
        else:
            assert key not in after, f"{shape.name}: {key} had no surviving witness and is still here"
    for key in after:
        assert key in before, f"{shape.name}: {key} APPEARED when rows were deleted (monotonicity)"


def check_aggregate_key_characterisation(subject: Subject, shape: Shape, tables: dict, deleted: Any) -> None:
    """L2.3, the aggregate clause — and the reason `aggregate` is not in the fragment above.

    An aggregate's output row is `by + {into: folded}`, and `folded` reads the deleted
    rows' VALUES, not merely their presence. Deleting a contributing row therefore replaces
    the output row with a different one, and no statement about that row surviving can be
    true. What IS true, and is all that is claimed, is the characterisation on the GROUP
    KEY: project the output onto `by` and the survival theorem holds there exactly.
    """
    assert shape.plan[0] == "aggregate", f"{shape.name} is not an aggregate"
    keyed = ("project", shape.plan, shape.plan[2])
    before = subject.read(evaluate(subject, keyed, build(subject, tables)))
    after = subject.read(evaluate(subject, keyed, build(subject, delete(tables, deleted))))
    for key, annotation in before.items():
        predicted = surviving(annotation[1], deleted)
        if predicted:
            assert key in after and after[key][1] == predicted, (
                f"{shape.name}: group {key} predicted {predicted}, got {after.get(key)}"
            )
        else:
            assert key not in after, f"{shape.name}: group {key} outlived all its witnesses"
    for key in after:
        assert key in before, f"{shape.name}: group {key} APPEARED when rows were deleted"


def check_minimal_witnesses(subject: Subject, shape: Shape, tables: dict) -> None:
    """L2.4 — every support set is a genuine MINIMAL witness.

    Minimality is NOT "deleting a proper subset of S leaves the row standing" — a join
    witness `{a, b}` dies when either half goes, and it is minimal all the same. It is:

      * ANTICHAIN — no support set strictly contains another, so nothing redundant is
        carried;
      * SUFFICIENCY — keeping ONLY S's source rows still yields the row, so S really is a
        derivation and not a bystander;
      * MINIMALITY — keeping only a PROPER SUBSET of S does not yield the row, so nothing
        in S is surplus.

    Sufficiency is what an `add` where the spec says `mul` breaks, and minimality is what
    dropping antichain normalisation breaks; between them no atom in a support set is
    decorative.
    """
    rels = build(subject, tables)
    before = subject.read(evaluate(subject, shape.plan, rels))
    everything = frozenset(source_atoms(tables))
    for key, (_, why) in before.items():
        supports = sorted(why, key=lambda s: (len(s), sorted(s)))
        for support in supports:
            for other in supports:
                assert not (other < support), (
                    f"{shape.name}: {sorted(support)} strictly contains {sorted(other)}, so it is "
                    "not an antichain member and carries a redundant citation"
                )
            kept = subject.read(evaluate(subject, shape.plan, build(subject, delete(tables, everything - support))))
            assert key in kept, (
                f"{shape.name}: keeping only {sorted(support)} did not yield {key}, so that "
                "support set is not a derivation of it"
            )
            for atom in sorted(support):
                proper = support - {atom}
                short = subject.read(evaluate(subject, shape.plan, build(subject, delete(tables, everything - proper))))
                assert key not in short, (
                    f"{shape.name}: keeping only {sorted(proper)} — a PROPER subset of "
                    f"{sorted(support)} — still yielded {key}, so the witness is not minimal"
                )


def check_inertness(subject: Subject, shape: Shape, tables: dict) -> None:
    """L2.5 — `Why` explains an answer and never supplies one: the bag image is what it
    would be with no provenance at all. Stated over the bag rather than over π₁ because
    the bag image is what `to_bag`, `aggregate` and `anti_join` all mean by "really
    there" (D0107)."""
    witnessed = build(subject, tables)
    stripped = build(subject, {
        name: (schema, [(row, (a[0], WHY_ONE)) for row, a in rows])
        for name, (schema, rows) in tables.items()
    })
    assert subject.bag(evaluate(subject, shape.plan, witnessed)) == \
        subject.bag(evaluate(subject, shape.plan, stripped)), \
        f"{shape.name}: the answer moved when the provenance did"


def check_absence_witness(subject: Subject, shape: Shape, tables: dict) -> None:
    """L2.6 — the absence witness is a CONJUNCTION (D0132), and deleting on the right
    invalidates it rather than appearing in it."""
    rels = build(subject, tables)
    right_plan = right_operand(shape.plan)
    assert right_plan is not None, f"{shape.name} has no anti_join"
    right = evaluate(subject, right_plan, rels)
    out = subject.read(evaluate(subject, shape.plan, rels))
    if len(subject.read(right)) == 0:
        # Against a genuinely empty relation there was nothing to check, so nothing to
        # cite: anti_join is exactly the identity (L1.8) and adds no atom.
        address = subject.address(right)
        for key, (_, why) in out.items():
            assert all(address not in support for support in why), \
                f"{shape.name}: an empty right operand was cited anyway at {key}"
        return

    address = subject.address(right)
    for key, (_, why) in out.items():
        assert why, f"{shape.name}: {key} survived unwitnessed"
        assert all(address in support for support in why), (
            f"{shape.name}: {key} carries a support set without the absence witness — the "
            "claim is conjunctive, so `add` leaves the citation standing as an independent "
            "derivation of a row it cannot derive (D0132)"
        )

    # Deleting ANY right source row moves the right relation's address, so no witness of
    # the old output survives: every output row must be recomputed, never inherited.
    reads = tables_of(right_plan)
    right_atoms = source_atoms({n: t for n, t in tables.items() if n in reads})
    if right_atoms and out:
        after_tables = delete(tables, {right_atoms[0]})
        after_rels = build(subject, after_tables)
        after_right = evaluate(subject, right_plan, after_rels)
        after = subject.read(evaluate(subject, shape.plan, after_rels))
        new_address = subject.address(after_right)
        assert new_address != address, f"{shape.name}: deleting a right row left the address unmoved"
        for key, (_, why) in after.items():
            assert all(address not in support for support in why), (
                f"{shape.name}: {key} still cites the SUPERSEDED right-relation address"
            )


def _relabel(read: dict, address: Any) -> dict:
    """Substitute a placeholder for a subject's own anti_join witness atom.

    The witness cites the right relation's CONTENT ADDRESS, and the model's addressing is
    its own (it has no canonical encoder and must not borrow tannen's, or the differential
    would compare tannen against itself). Everything else about the atom — that there is
    exactly one, in exactly these support sets — is comparable, so only the atom's spelling
    is normalised away.
    """
    if address is None:
        return read
    return {
        key: (count, antichain(frozenset("<right>" if a == address else a for a in support)
                               for support in why))
        for key, (count, why) in read.items()
    }


def check_differential(subject: Subject, shape: Shape, tables: dict) -> None:
    """L2.9 — the shipped package agrees with the frozen model, annotation for annotation.

    The `_fragment.py`/DuckDB pattern (L1.16) applied to provenance: a model Session B
    cannot edit is an oracle, and unlike DuckDB this one has support sets to compare.
    """
    mine, theirs = build(subject, tables), build(MODEL, tables)
    right_plan = right_operand(shape.plan)
    got = _relabel(
        subject.read(evaluate(subject, shape.plan, mine)),
        subject.address(evaluate(subject, right_plan, mine)) if right_plan else None,
    )
    want = _relabel(
        MODEL.read(evaluate(MODEL, shape.plan, theirs)),
        MODEL.address(evaluate(MODEL, right_plan, theirs)) if right_plan else None,
    )
    assert got == want, f"{shape.name}: {subject.name} and the model disagree"


# ------------------------------------------------------------------------------ the mutants
#
# One per model-checked family. D0094 §2: a law that passes against a deliberately broken
# model is not testing what it claims, and the mutant half is the only half that catches a
# law which cannot fail.


class _NoAntichain(Subject):
    """Support sets are never minimised, so a row cites witnesses it does not need."""
    name = "no-antichain"

    def w_add(self, a, b):
        return frozenset(set(a) | set(b))

    def w_mul(self, a, b):
        return frozenset(x | y for x in a for y in b)


class _MulLeftOnly(Subject):
    """`join` keeps only the left support, so a two-source row cites one source."""
    name = "mul-left-only"

    def join(self, a, b, on):
        keys = tuple(sorted(on))
        schema = tuple(sorted(set(a.schema) | set(b.schema)))
        out = []
        for ra, aa in a:
            for rb, ab in b:
                if all(ra[k] == rb[k] for k in keys):
                    out.append(({**ra, **rb}, (aa[0] * ab[0], aa[1])))
        return MRel(schema, out)


class _DisjunctiveAntiJoin(Subject):
    """tannen's M1 behaviour as shipped: the absence witness combined with `add`.

    Not a hypothetical mutant. This is the defect D0132 records, and L2.6 failing here is
    the evidence that the law discriminates.
    """
    name = "antijoin-disjunctive"

    def combine_witness(self, annotation, witness):
        return (annotation[0], why_add(annotation[1], witness))


class _UnwitnessedSources(Subject):
    """Construction admits `(n, ∅)` — the door D0110 closes."""
    name = "unwitnessed-source"

    def rel(self, schema, pairs):
        return MRel(schema, pairs, witnessed=False, add=self.a_add)


class _AggregateForgetsTheGroup(Subject):
    """An aggregate whose output cites only the group's FIRST member, so a group survives
    the deletion of rows it was built from without its support saying so."""
    name = "aggregate-forgets-the-group"

    def aggregate_sum(self, r, by, column, into):
        keys = tuple(sorted(by))
        groups: dict = {}
        for row, ann in r:
            groups.setdefault(tuple(row[k] for k in keys), []).append((row, ann))
        out = []
        for members in groups.values():
            folded = sum(row[column] * multiplicity(ann) for row, ann in members)
            head = members[0][0]
            out.append(({**{k: head[k] for k in keys}, into: folded}, collapse(members[0][1])))
        return MRel(tuple(sorted(keys + (into,))), out, add=self.a_add)


class _SupportCounts(Subject):
    """The bag image reads the support, so provenance supplies an answer instead of
    explaining one — the thing BRIEF P4 exists to prevent."""
    name = "support-counts"

    def bag(self, r):
        out = []
        for row, annotation in r:
            copies = multiplicity(annotation) * max(1, len(annotation[1]))
            out.extend([tuple(row[c] for c in r.schema)] * copies)
        return sorted(out, key=repr)


class _NoWitnessAtAll(Subject):
    """anti_join cites nothing: the survivor's support is its input's, unchanged."""
    name = "antijoin-no-witness"

    def combine_witness(self, annotation, witness):
        return annotation


MUTANTS = {
    m.name: m for m in (
        _NoAntichain(), _MulLeftOnly(), _DisjunctiveAntiJoin(), _UnwitnessedSources(),
        _AggregateForgetsTheGroup(), _SupportCounts(), _NoWitnessAtAll(),
    )
}

#: Which check each mutant must be caught by. The pairing is part of the freeze: a mutant
#: nobody aims a check at proves nothing (D0094 §2).
CAUGHT_BY = {
    "no-antichain": "check_minimal_witnesses",
    "mul-left-only": "check_deletion_characterisation",
    "antijoin-disjunctive": "check_absence_witness",
    "unwitnessed-source": "check_witnessed_construction",
    "aggregate-forgets-the-group": "check_aggregate_key_characterisation",
    "support-counts": "check_inertness",
    "antijoin-no-witness": "check_absence_witness",
}


# ------------------------------------------------------------------------------ the harness
#
# The mutant matrix's driver, frozen with the model it drives. The law modules parametrize
# the SAME shape groups one shape at a time, so a law failure names the shape; this runs a
# whole family in one call, which is what a mutant needs. Nothing mechanically checks that
# the two coverages agree — stated rather than implied, because it is the one seam in this
# arrangement that a guard cannot watch.


def _profile(max_examples: int) -> Any:
    from hypothesis import HealthCheck, settings

    return settings(
        max_examples=max_examples, deadline=None, derandomize=True,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )


def _one_atom(tables: dict, pick: int) -> frozenset:
    atoms = source_atoms(tables)
    return frozenset(atoms[pick % len(atoms):][:1]) if atoms else frozenset()


def run_family(subject: Subject, family: str, max_examples: int = 25) -> None:
    """Run one model-checked family against `subject`; raise on the first counterexample.

    The shape is bound by a FACTORY closure and never by a default argument: hypothesis
    refuses a property with defaults, and a driver that dies of its own signature would
    report every mutant killed without ever running a law — which is exactly the vacuous
    green this whole apparatus exists to prevent (D0116).
    """
    from hypothesis import given

    profile = _profile(max_examples)

    def drive(strategies: dict, prop: Any) -> None:
        profile(given(**strategies)(prop))()

    def with_deletion(shape: Shape, overlap: str, chooser: Any) -> None:
        def prop(tables: dict, pick: int) -> None:
            check_deletion_characterisation(subject, shape, tables, chooser(shape, tables, pick))
        drive(dict(tables=source_tables(names=shape.tables, overlap=overlap), pick=st.integers(0, 5)), prop)

    def unary(check: Any, shape: Shape, overlap: str) -> None:
        def prop(tables: dict) -> None:
            check(subject, shape, tables)
        drive(dict(tables=source_tables(names=shape.tables, overlap=overlap)), prop)

    if family == "check_witnessed_construction":
        check_witnessed_construction(subject)
    elif family == "check_deletion_characterisation":
        for shape in POSITIVE:
            with_deletion(shape, "partial", lambda s, t, p: _one_atom(t, p))
        for shape in ANTI:  # left-side deletions only; the right operand's address is L2.6's
            with_deletion(shape, "partial",
                          lambda s, t, p: frozenset(source_atoms({s.tables[0]: t[s.tables[0]]})[:1]))
    elif family == "check_aggregate_key_characterisation":
        for shape in AGGREGATE:
            for overlap in ("grouped", "full"):
                def bound(tables: dict, pick: int, s: Shape = shape) -> None:
                    check_aggregate_key_characterisation(subject, s, tables, _one_atom(tables, pick))
                drive(dict(tables=source_tables(names=shape.tables, overlap=overlap),
                           pick=st.integers(0, 5)),
                      (lambda f: (lambda tables, pick: f(tables, pick)))(bound))
    elif family == "check_minimal_witnesses":
        for shape in POSITIVE:
            unary(check_minimal_witnesses, shape, "full")
    elif family == "check_inertness":
        for shape in SHAPES:
            unary(check_inertness, shape, "partial")
    elif family == "check_absence_witness":
        for shape in ANTI:
            for overlap in ("partial", "none", "full"):
                unary(check_absence_witness, shape, overlap)
    elif family == "check_differential":
        for shape in SHAPES:
            unary(check_differential, shape, "partial")
    else:
        raise AssertionError(f"unknown family {family!r}")


#: Every family the harness can run. `CAUGHT_BY` maps each mutant to the one that kills it.
FAMILIES = (
    "check_witnessed_construction",
    "check_deletion_characterisation",
    "check_aggregate_key_characterisation",
    "check_minimal_witnesses",
    "check_inertness",
    "check_absence_witness",
)
