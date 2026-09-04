"""The MODEL half of M3's delta-executor laws — the frozen oracle (docs/specs/m3.md §9).

FROZEN at m3-laws-freeze, for D0094's reason, restated at every freeze because it is the
point: under the frozen-oracle protocol every law is an `importorskip` at exactly the
moment it becomes unrewritable, so `pytest tests/laws/m3` prints the same "N skipped"
whether the laws are correct, contradictory or nonsense. A model beside them turns
Session A's gate from "the laws do not run" into "the laws pass against a model and fail
against a stated mutant".

It imports NOTHING from tannen (the `_fragment.py`/m2 `_model.py` precedent, D0089): a
law module passes its subject in, so this file can never be the reason a
pre-implementation run *errors* instead of *skipping*.

The bare-import name is `_delta_model`, NOT `_model` — deliberately, and it is the
lesson RT-M1-01/RT-M2-01 left. Python caches imports by name in `sys.modules`, so two
milestone directories that both ship an oracle called `_model` collide: a bare
`import _model` in an m3 law would receive m2's cached module, and `plugin.py`'s
oracle-shadow guard (D0142) `Exit`s the run rather than resolve it either way. m1 chose
`_fragment`, m2 chose `_model`; m3 chooses `_delta_model`/`_delta_subject` for the same
reason. The real fix the red team named — package-qualified imports in the frozen files
— is a bigger change (it makes `tests/laws` a package) and stays queued; a
milestone-unique bare name is the cheap, sound interim (D0165).

Four things live here.

1.  A naive, self-contained transcription of docs/specs/m3.md §2–§7: the ℤ × Why algebra
    (as at M2, plus the cone refusals the M1 bag image makes and M3 keeps), the delta
    calculus (`negate`, `diff`, `apply` with its pinned normalisation order), the derived
    per-operator rules, and `run_ticks` — the incremental evaluation of a plan over a
    perturbation stream, with the ledger's `dead` bookkeeping and the anti_join
    contagion rule.
2.  The `Subject` interface every check is written against, and `MODEL`.
    `tests/laws/m3/_delta_subject.py` builds the tannen one.
3.  The perturbation streams (§9.3): named shapes, `event()`-reported, no thresholds.
4.  `MUTANTS` — deliberately broken subjects, each aimed at by exactly one family
    (`CAUGHT_BY`). Two are tannen's own tempting wrong behaviours written down before
    they could be written in (`apply-keeps-zero-rows`, `antijoin-eats-delta`), and
    `why-slot-first-match` is the M2 locator as shipped — the `antijoin-disjunctive`
    precedent exactly.

Generators follow D0118's rule (D0130 at M2): the degenerate case is drawn as a NAMED
case, each stream declares the case it exists to exercise, and every draw reports its
shape through hypothesis `event()`. No thresholds anywhere.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from hypothesis import event, strategies as st

__all__ = [
    "ATOMS",
    "CAUGHT_BY",
    "CONVERGENCE_SHAPES",
    "FAMILIES",
    "MODEL",
    "MUTANTS",
    "REQUIRED",
    "SEMIRING_SPECS",
    "SHAPES",
    "Shape",
    "Subject",
    "check_bilinear_join",
    "check_convergence",
    "check_delta_algebra",
    "check_differential",
    "check_doors",
    "check_graph_convergence",
    "check_integrated_ops",
    "check_linear_rules",
    "evaluate",
    "net_of",
    "one_shot",
    "run_family",
    "run_ticks",
    "stream_tables",
    "surviving",
    "two_worlds",
]

# --------------------------------------------------------------------------- the algebra
#
# Transcribed fresh rather than imported from the m2 model: each sealed directory is
# self-contained (D0089), and the ONE deliberate difference is that `multiplicity` and
# `collapse` here carry M1's cone refusals — the m2 model never met a negative, and M3's
# whole subject is what happens around them (docs/specs/m3.md §2.1, §3.4).


class ModelRefusal(Exception):
    """The model's analogue of `RelError` — a value the spec says is not a value."""


class ModelConeRefusal(ModelRefusal):
    """The model's analogue of `SemiringError` on a negative bag image — the refusal
    M1 made, M3 keeps, and §3.4 re-commissions as the executor's tripwire."""


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


def collapse(p: Any) -> tuple:
    if p[0] < 0:
        raise ModelConeRefusal(f"negative count {p[0]} has no set image (m1 §2.1)")
    return (1 if p[0] > 0 else 0, p[1])


def multiplicity(p: Any) -> int:
    if p[0] < 0:
        raise ModelConeRefusal(f"negative count {p[0]} has no bag image (m1 §2.1)")
    return p[0] * (1 if p[1] else 0)


def atoms_of(why: Any) -> frozenset:
    return frozenset(atom for support in why for atom in support)


def surviving(why: Any, deleted: Any) -> frozenset:
    """M2 §4's valuation, verbatim: a support set survives iff disjoint from `deleted`.
    M3 promotes it from spec prose to the third normalisation step of `apply` (§3.3) and
    to the residue theorem (§5, L3.11)."""
    deleted = frozenset(deleted)
    return antichain(s for s in why if not (s & deleted))


# ------------------------------------------------------------------------ the model Rel


def _key(row: dict) -> tuple:
    return tuple(sorted(row.items()))


class MRel:
    """A finite K-relation as a dict. Naive on purpose. Identical in shape to the m2
    model's, and like it enforces D0110's witnessed-row rule — which under M3's calculus
    is also the retraction rule: `(-1, ∅)` is refused for the same reason `(3, ∅)` is."""

    def __init__(self, schema: Any, pairs: Any, *, witnessed: bool = True, add: Any = None) -> None:
        add = add if add is not None else (lambda p, q: (p[0] + q[0], why_add(p[1], q[1])))
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


# ------------------------------------------------------- semiring specs (the door checks)
#
# A spec is a tree: "Z" | "B" | "Why" | ("product", left, right). The door checks (§2.2,
# L3.13) quantify over these — the model computes slot paths structurally, and the tannen
# adapter builds the real semiring from the same tree. A slot path is a tuple of
# "left"/"right" steps; () names a bare `Why`.

SEMIRING_SPECS = {
    "ZxWhy": ("product", "Z", "Why"),
    "WhyxWhy": ("product", "Why", "Why"),
    "ZxWhy-x-B": ("product", ("product", "Z", "Why"), "B"),
    "Z-x-ZxWhy": ("product", "Z", ("product", "Z", "Why")),
    "ZxWhy-x-ZxWhy": ("product", ("product", "Z", "Why"), ("product", "Z", "Why")),
}

_REF_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def spec_slots(spec: Any) -> tuple:
    """Every `Why` location in a spec, as paths — the honest answer `why_slots` must give."""
    if spec == "Why":
        return ((),)
    if isinstance(spec, tuple) and spec[0] == "product":
        return tuple(("left",) + p for p in spec_slots(spec[1])) + \
            tuple(("right",) + p for p in spec_slots(spec[2]))
    return ()


def spec_one(spec: Any) -> Any:
    """The multiplicative unit of a spec'd semiring, as a nested value."""
    if spec == "Z":
        return 1
    if spec == "B":
        return True
    if spec == "Why":
        return WHY_ONE
    return (spec_one(spec[1]), spec_one(spec[2]))


def poke_empty_why(value: Any, path: tuple) -> Any:
    """`value` with the `Why` at `path` replaced by the empty element — the annotation the
    witnessed-row door must refuse, wherever the `Why` sits."""
    if not path:
        return WHY_ZERO
    head, rest = path[0], path[1:]
    left, right = value
    return (poke_empty_why(left, rest), right) if head == "left" else (left, poke_empty_why(right, rest))


# --------------------------------------------------------------------------- the subject


class Subject:
    """What a law needs of an implementation. Every check is written against this and
    nothing else, so the same assertion text runs against the model, each mutant, and
    tannen. Hooks are fine-grained so a mutant can break one mechanism — the semilattice,
    the valuation, one derived rule, the retire bookkeeping — without forging the rest."""

    name = "model"
    refusal = ModelRefusal
    cone_refusal = ModelConeRefusal

    # -- the algebra, as hooks
    def w_add(self, a: Any, b: Any) -> frozenset:
        return why_add(a, b)

    def w_mul(self, a: Any, b: Any) -> frozenset:
        return why_mul(a, b)

    def a_add(self, p: Any, q: Any) -> tuple:
        return (p[0] + q[0], self.w_add(p[1], q[1]))

    def a_mul(self, p: Any, q: Any) -> tuple:
        return (p[0] * q[0], self.w_mul(p[1], q[1]))

    # -- the declared group ℤ rides on (§4's subtractive aggregate; L3.8)
    g_id = 0

    def g_op(self, a: Any, b: Any) -> Any:
        return a + b

    def g_inv(self, a: Any) -> Any:
        return -a

    # -- construction and reads
    def rel(self, schema: Any, pairs: Any) -> Any:
        return MRel(schema, pairs, add=self.a_add)

    def ingest(self, schema: Any, entries: Any) -> Any:
        """One-shot source: `entries` is a sequence of (row, count, atom), one atom per
        distinct row — the model's image of `srcrow/1` (§3.1)."""
        return MRel(schema, [(row, (count, frozenset({frozenset({atom})})))
                             for row, count, atom in entries], add=self.a_add)

    def source_delta(self, schema: Any, entries: Any) -> Any:
        """A source delta: (row, ±count, atom) — retractions witnessed by the ref of the
        row they retract (§3.1)."""
        return MRel(schema, [(row, (count, frozenset({frozenset({atom})})))
                             for row, count, atom in entries], add=self.a_add)

    def read(self, r: Any) -> dict:
        return r.read()

    def bag(self, r: Any) -> list:
        return r.bag()

    def address(self, r: Any) -> str:
        return r.address()

    # -- the eight operators (m1 §4 / the m2 model, unchanged semantics)
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
            out.append((row, self.combine_witness(ann, witness) if witness else ann))
        return MRel(a.schema, out, add=self.a_add)

    def combine_witness(self, annotation: Any, witness: Any) -> tuple:
        return (annotation[0], self.w_mul(annotation[1], witness))  # conjunction (D0132)

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

    # -- the delta calculus (docs/specs/m3.md §3)
    def negate(self, r: Any) -> Any:
        """The delta that retracts `r` outright: counts negated, witnesses kept (§2.1 —
        `Why` is a fixed point of negation)."""
        return MRel(r.schema, [(row, (-a[0], a[1])) for row, a in r], add=self.a_add)

    def diff(self, new: Any, old: Any) -> Any:
        """§3.2: group difference on counts; `new`'s `Why` where the row occurs in `new`,
        `old`'s where it does not — a pure retraction stays witnessed by what it
        retracts. Rows identical in both are omitted."""
        pairs = []
        for k in sorted(set(new.rows) | set(old.rows)):
            row = (new.rows.get(k) or old.rows[k])[0]
            na = new.rows[k][1] if k in new.rows else ZERO
            oa = old.rows[k][1] if k in old.rows else ZERO
            if na == oa:
                continue
            pairs.append((row, (na[0] - oa[0], na[1] if k in new.rows else oa[1])))
        return MRel(new.schema, pairs, add=self.a_add)

    def apply(self, base: Any, delta: Any, dead: Any) -> Any:
        """§3.3, the pinned order: pointwise add; the CONE CHECK (an over-retraction is
        refused by name — m1 §4.4's loud break, landed); the GROUP-ZERO DROP (a row whose
        count cancelled is gone, `(0, {{r}})` included — construction still retains that
        value, `apply` chooses not to emit it); the VALUATION over the entire result. A
        row whose count survives but whose every witness died is then refused by the
        witnessed-row rule at construction — the calculus's own alarm."""
        dead = frozenset(dead)
        merged: dict = {k: (row, ann) for k, (row, ann) in base.rows.items()}
        for k, (row, ann) in delta.rows.items():
            merged[k] = (row, self.a_add(merged[k][1], ann) if k in merged else ann)
        pairs = []
        for _, (row, (n, w)) in sorted(merged.items()):
            if n < 0:
                raise ModelConeRefusal(
                    f"over-retraction: row {row!r} driven to count {n} (§3.3 step 1)")
            if n == 0:
                continue
            pairs.append((row, (n, surviving(w, dead))))
        return MRel(base.schema, pairs, add=self.a_add)

    # -- the derived rules (§4)
    def join_delta(self, a_old: Any, a_new: Any, d_a: Any, b_old: Any, b_new: Any,
                   d_b: Any, on: Any) -> Any:
        """The pinned two-term bilinear form (D0159): join(ΔA, B_old) ⊎ join(A_new, ΔB)."""
        return self.union(self.join(d_a, b_old, on), self.join(a_new, d_b, on))

    def aggregate_subtractive(self, in_old: Any, in_new: Any, by: Any, column: str,
                              into: str, out_old: Any) -> Any:
        """§4's subtractive form: each group's folded value maintained through the
        declared group — arriving contributions folded in with `g_op`, retracted ones
        with `g_inv` — never recomputed from scratch. Output annotations are recomputed
        from `in_new` (support is the group's union, as ever)."""
        keys = tuple(sorted(by))
        old_folded = {tuple(row[k] for k in keys): row[into] for row, _ in out_old}
        deltas: dict = {}
        for row, (dn, _w) in self.diff(in_new, in_old):
            g = tuple(row[k] for k in keys)
            acc = deltas.get(g, self.g_id)
            step = row[column] if dn > 0 else self.g_inv(row[column])
            for _ in range(abs(dn)):
                acc = self.g_op(acc, step)
            deltas[g] = acc
        groups: dict = {}
        for row, ann in in_new:
            groups.setdefault(tuple(row[k] for k in keys), []).append((row, ann))
        out = []
        for g, members in groups.items():
            folded = self.g_op(old_folded.get(g, self.g_id), deltas.get(g, self.g_id))
            total = members[0][1]
            for _, ann in members[1:]:
                total = self.a_add(total, ann)
            head = members[0][0]
            out.append(({**{k: head[k] for k in keys}, into: folded}, collapse(total)))
        return MRel(tuple(sorted(keys + (into,))), out, add=self.a_add)

    # -- the contagion rule (§4, §7): does this node replay over integrals?
    def replays(self, plan: Any) -> bool:
        return _contains_anti(plan)

    # -- the doors (§2.2, §2.3)
    def why_slots(self, spec: Any) -> tuple:
        return spec_slots(spec)

    def unwitnessed_refused(self, spec: Any, position: tuple) -> bool:
        """Would a one-row relation over `spec` be refused when the `Why` at `position`
        is empty (and every other component is the unit)? §2.2 says yes for EVERY
        position."""
        annotation = poke_empty_why(spec_one(spec), position)
        located = self.why_slots(spec)
        return any(_read_path(annotation, p) == WHY_ZERO for p in located)

    def anti_join_multi_why_refused(self, spec: Any) -> bool:
        """Is `anti_join` refused by name over `spec`? §2.2: yes iff more than one `Why`
        slot — the absence witness has two inequivalent readings there."""
        return len(self.why_slots(spec)) > 1

    def encode_rejects_non_ref(self) -> bool:
        """Does encoding a `Why` carrying a non-grammar atom raise by name? §2.3."""
        bad = frozenset({frozenset({"not-a-ref"})})
        try:
            _model_encode_why(bad)
        except ModelRefusal:
            return True
        return False


def _read_path(value: Any, path: tuple) -> Any:
    for step in path:
        value = value[0] if step == "left" else value[1]
    return value


def _model_encode_why(w: Any) -> list:
    for support in w:
        for atom in support:
            if not _REF_RE.match(atom):
                raise ModelRefusal(f"atom outside the ref grammar: {atom!r}")
    return sorted(sorted(s) for s in w)


#: Exactly what a check calls on a subject. `_delta_subject.py` asserts the tannen adapter
#: defines EVERY name here in its own `__dict__` — no subclassing, no silent fallback to
#: model code (the m2 rule, unchanged). The algebra and group hooks (`w_add`, `g_inv`,
#: `combine_witness`, …) are deliberately NOT here: they exist so a mutant can break one
#: mechanism in the MODEL; no check calls them on a subject directly.
REQUIRED = (
    "name", "refusal", "cone_refusal",
    "rel", "ingest", "source_delta", "read", "bag", "address",
    "select", "project", "map_rows", "union", "join", "distinct", "anti_join",
    "aggregate_sum",
    "negate", "diff", "apply", "join_delta", "aggregate_subtractive", "replays",
    "why_slots", "unwitnessed_refused", "anti_join_multi_why_refused",
    "encode_rejects_non_ref",
)

MODEL = Subject()


# ---------------------------------------------------------------------------- the shapes

ATOMS = tuple(f"sha256:{n:064x}" for n in range(1, 25))

TABLES = {"a": ("k", "x"), "b": ("k", "y"), "c": ("k", "z")}


class Shape:
    """One named plan plus the case it exists to exercise (D0118). `positive` marks the
    monotone fragment L3.11's residue clause quantifies over (M2 §5's fragment plus
    `aggregate` excluded, `anti_join` excluded)."""

    __slots__ = ("name", "plan", "tables", "positive", "note")

    def __init__(self, name: str, plan: Any, tables: Any, positive: bool, note: str) -> None:
        self.name, self.plan, self.tables, self.positive, self.note = \
            name, plan, tuple(tables), positive, note

    def __repr__(self) -> str:
        return f"Shape({self.name!r})"


A, B, C = ("src", "a"), ("src", "b"), ("src", "c")

SHAPES = (
    Shape("identity", A, "a", True, "the source itself: ingest_delta is its own delta rule"),
    Shape("select", ("select", A, "x-positive"), "a", True,
          "a linear filter over a stream that retracts"),
    Shape("project", ("project", A, ("k",)), "a", True,
          "projection SUMS: two source rows share an output row, so a partial retraction "
          "moves a count without killing a witness"),
    Shape("map-rows", ("map_rows", A, "k-only"), "a", True, "a total map; rows may collide"),
    Shape("union", ("union", ("project", A, ("k",)), ("project", B, ("k",))), "ab", True,
          "add: two sources arriving and retracting independently"),
    Shape("join", ("join", A, B, ("k",)), "ab", True,
          "mul: the bilinear rule, co-arrival included"),
    Shape("join-then-project", ("project", ("join", A, B, ("k",)), ("k",)), "ab", True,
          "mul then add through the stream"),
    Shape("union-with-join",
          ("union", ("project", A, ("k",)), ("project", ("join", A, B, ("k",)), ("k",))),
          "ab", True,
          "the antichain-observable shape: {a} beside {a, b}, and a retraction of b must "
          "leave {a} standing alone"),
    Shape("distinct-of-union",
          ("distinct", ("union", ("project", A, ("k",)), ("project", B, ("k",)))), "ab", False,
          "an integrated operator downstream of two streams"),
    Shape("aggregate-sum", ("aggregate", A, ("k",), "x", "s"), "a", False,
          "a retraction moves the folded value: the old output row retracts entirely"),
    Shape("aggregate-of-join", ("aggregate", ("join", A, B, ("k",)), ("k",), "x", "s"),
          "ab", False, "replacement above a bilinear rule"),
    Shape("anti-join", ("anti_join", A, B, ("k",)), "ab", False,
          "a right-side retraction resurrects a left row; the cited address moves"),
    Shape("anti-join-then-project", ("project", ("anti_join", A, B, ("k",)), ("x",)), "ab",
          False, "the superseded address must vanish DOWNSTREAM of the operator that "
          "moved it — the contagion rule's reach"),
    Shape("join-then-anti", ("anti_join", ("join", A, B, ("k",)), C, ("k",)), "abc", False,
          "an absence witness over a two-source witness, all three streams moving"),
)

#: The single-source shapes L3.9/L3.10 (source convergence) quantify over.
CONVERGENCE_SHAPES = tuple(s for s in SHAPES if s.tables == ("a",) or s.tables == "a")

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


def plan_schema(plan: Any, schemas: dict) -> tuple:
    head = plan[0]
    if head == "src":
        return tuple(sorted(schemas[plan[1]]))
    if head in ("select", "distinct"):
        return plan_schema(plan[1], schemas)
    if head == "project":
        return tuple(sorted(plan[2]))
    if head == "map_rows":
        return tuple(sorted(MAP_SCHEMAS[plan[2]]))
    if head == "union":
        return plan_schema(plan[1], schemas)
    if head == "join":
        return tuple(sorted(set(plan_schema(plan[1], schemas)) | set(plan_schema(plan[2], schemas))))
    if head == "anti_join":
        return plan_schema(plan[1], schemas)
    if head == "aggregate":
        return tuple(sorted(tuple(plan[2]) + (plan[4],)))
    raise AssertionError(f"unknown plan head {head!r}")


def _sources(plan: Any, acc: set | None = None) -> set:
    acc = set() if acc is None else acc
    if plan[0] == "src":
        acc.add(plan)
    else:
        for part in plan[1:]:
            if isinstance(part, tuple) and part and isinstance(part[0], str) and (
                    part[0] == "src" or part[0] in _HEADS):
                _sources(part, acc)
    return acc


_HEADS = {"select", "project", "map_rows", "union", "join", "distinct", "anti_join", "aggregate"}


# -------------------------------------------------------------- the incremental evaluator
#
# `run_ticks` IS docs/specs/m3.md §7's tick, written against the Subject hooks so the
# same engine drives the model, every mutant, and tannen's calculus (the shipped
# executor's own store-threaded loop is L3.15's, exercised by the executor law file).
# Sources advance first and update `dead`; derived nodes advance in dependency order
# under the updated ledger; shared subplans advance once per tick.
#
# THE ANTI_JOIN CONTAGION RULE (§4, §7 — found by this model during pre-freeze
# validation, on the `interleave` stream): a node is delta-maintained iff no `anti_join`
# lies at or below it; `anti_join` and everything above it replays over its children's
# integrals every tick. The conjunction is the one operation that EXTENDS an existing
# support set, so its ∅→non-empty transition mints a witness that strictly contains the
# witness minted while the right operand was empty — and the dominated set carries no
# dead atom to filter on, so antichain normalisation silently prefers the stale claim.
# A semilattice cannot subtract; replaying is the honest rule, and BRIEF §10 prices it.


def _contains_anti(plan: Any) -> bool:
    if not isinstance(plan, tuple):
        return False
    if plan[0] == "anti_join":
        return True
    return any(_contains_anti(part) for part in plan[1:])


def run_ticks(subject: Subject, plan: Any, schemas: dict, ticks: Any, *,
              valuate: bool = True):
    """Returns (final output integral, dead)."""
    state: dict = {}
    dead: set = set()

    def ledger() -> frozenset:
        return frozenset(dead) if valuate else frozenset()

    def integral(p: Any) -> Any:
        got = state.get(p)
        return got if got is not None else subject.rel(plan_schema(p, schemas), [])

    for tick in ticks:
        snapshot = dict(state)
        memo: dict = {}

        for src in sorted(_sources(plan)):
            entries = tuple(tick.get(src[1], ()))
            delta = subject.source_delta(schemas[src[1]], entries)
            memo[src] = delta
            # An arrival resurrects its ref BEFORE the apply (§6): applying first would
            # let the valuation kill the very witness the arrival carries, and the
            # witnessed-row alarm fires on a lawful stream. Found by the model's own
            # `retract-rearrive` stream during pre-freeze validation.
            for _row, dn, atom in entries:
                if dn > 0:
                    dead.discard(atom)
            new = subject.apply(integral(src), delta, ledger())
            state[src] = new
            present = {_key(row) for row, _ in new}
            for row, dn, atom in entries:
                if dn < 0 and _key(row) not in present:
                    dead.add(atom)

        def old_of(p: Any) -> Any:
            got = snapshot.get(p)
            return got if got is not None else subject.rel(plan_schema(p, schemas), [])

        def new_of(p: Any) -> Any:
            got = state.get(p)
            return got if got is not None else integral(p)

        def advance(p: Any) -> Any:
            """Advance node `p` for this tick; return its Δout (used only by
            delta-maintained parents). Children first, always."""
            if p in memo:
                return memo[p]
            head = p[0]
            if subject.replays(p):
                # the contagion rule: replay over the children's new integrals
                for part in p[1:]:
                    if isinstance(part, tuple) and part and (
                            part[0] == "src" or part[0] in _HEADS):
                        advance(part)
                if head == "select":
                    out_new = subject.select(new_of(p[1]), PREDICATES[p[2]])
                elif head == "project":
                    out_new = subject.project(new_of(p[1]), p[2])
                elif head == "map_rows":
                    out_new = subject.map_rows(new_of(p[1]), MAPS[p[2]], MAP_SCHEMAS[p[2]])
                elif head == "union":
                    out_new = subject.union(new_of(p[1]), new_of(p[2]))
                elif head == "join":
                    out_new = subject.join(new_of(p[1]), new_of(p[2]), p[3])
                elif head == "distinct":
                    out_new = subject.distinct(new_of(p[1]))
                elif head == "aggregate":
                    out_new = subject.aggregate_sum(new_of(p[1]), p[2], p[3], p[4])
                elif head == "anti_join":
                    out_new = subject.anti_join(new_of(p[1]), new_of(p[2]), p[3])
                else:
                    raise AssertionError(f"unknown plan head {head!r}")
                d = subject.diff(out_new, old_of(p))
                memo[p] = d
                state[p] = out_new
                return d
            if head == "select":
                d = subject.select(advance(p[1]), PREDICATES[p[2]])
            elif head == "project":
                d = subject.project(advance(p[1]), p[2])
            elif head == "map_rows":
                d = subject.map_rows(advance(p[1]), MAPS[p[2]], MAP_SCHEMAS[p[2]])
            elif head == "union":
                dl, dr = advance(p[1]), advance(p[2])
                d = subject.union(dl, dr)
            elif head == "join":
                dl = advance(p[1])
                dr = advance(p[2])
                d = subject.join_delta(old_of(p[1]), new_of(p[1]), dl,
                                       old_of(p[2]), new_of(p[2]), dr, p[3])
            elif head in ("distinct", "aggregate"):
                # replacement at the node (§4): recompute over the new input integral.
                # distinct and aggregate never EXTEND a support set, so the nodes above
                # them stay safely delta-maintained — only anti_join is contagious.
                advance(p[1])
                in_new = new_of(p[1])
                out_new = subject.distinct(in_new) if head == "distinct" \
                    else subject.aggregate_sum(in_new, p[2], p[3], p[4])
                d = subject.diff(out_new, old_of(p))
                memo[p] = d
                state[p] = out_new
                return d
            elif head == "anti_join":
                # reachable only when a subject claims anti_join needs no replay — the
                # unsound diff-and-apply maintenance the contagion rule forbids, kept
                # runnable so the mutant asserting it dies in daylight
                advance(p[1])
                advance(p[2])
                d = subject.diff(
                    subject.anti_join(new_of(p[1]), new_of(p[2]), p[3]), old_of(p))
            else:
                raise AssertionError(f"unknown plan head {head!r}")
            memo[p] = d
            if p[0] != "src":
                state[p] = subject.apply(old_of(p), d, ledger())
            return d

        advance(plan)

    return integral(plan), frozenset(dead)


def net_of(ticks: Any) -> dict:
    """The net entries per source after the whole stream: {name: ((row, count, atom), …)},
    rows with positive net count only, sorted for determinism."""
    per_source: dict = {}
    for tick in ticks:
        for name, entries in tick.items():
            for row, dn, atom in entries:
                slot = per_source.setdefault(name, {})
                key = _key(row)
                have = slot.get(key, (row, 0, atom))
                slot[key] = (row, have[1] + dn, atom)
    return {
        name: tuple((row, count, atom) for _, (row, count, atom) in sorted(slot.items())
                    if count > 0)
        for name, slot in per_source.items()
    }


def one_shot(subject: Subject, plan: Any, schemas: dict, net: dict) -> Any:
    """The reference: ingest the net rows, evaluate once."""
    rels = {name: subject.ingest(schemas[name], net.get(name, ())) for name in schemas}
    return evaluate(subject, plan, rels)


def expected_dead(ticks: Any) -> frozenset:
    """The refs the stream killed: atoms that appeared and whose net count is zero."""
    seen: dict = {}
    for tick in ticks:
        for entries in tick.values():
            for _row, dn, atom in entries:
                seen[atom] = seen.get(atom, 0) + dn
    return frozenset(atom for atom, count in seen.items() if count == 0)


# ------------------------------------------------------------------------- the generators

_KEYS = (0, 1, 2, 3)
_VALUES = (-2, 0, 1, 3)

STREAM_KINDS = (
    "one-shot", "empty-batch", "partition-k", "interleave", "arrive-retract",
    "partial-retract", "retract-rearrive", "retract-to-empty", "same-tick-co-arrival",
    "right-moves",
)


def _base_entries(draw: Any, names: str) -> dict:
    """Per source: distinct rows, one atom each (identical rows in one source are one row
    and one ref — m2 §2), counts 1–3. The empty source is a named case."""
    pool = iter(ATOMS)
    out = {}
    for index, name in enumerate(names):
        schema = TABLES[name]
        keys = _KEYS if index == 0 else _KEYS[1:] + (5,)
        rows = draw(st.one_of(st.just([]), st.lists(
            st.tuples(st.sampled_from(keys), st.sampled_from(_VALUES), st.integers(1, 3)),
            min_size=1, max_size=3, unique_by=lambda t: (t[0], t[1]),
        )))
        out[name] = tuple(
            ({schema[0]: k, schema[1]: v}, count, next(pool)) for k, v, count in rows)
        event(f"table {name}: {'empty' if not rows else 'non-empty'}")
    return out


@st.composite
def stream_tables(draw: Any, names: str = "ab", kind: str | None = None) -> tuple:
    """(schemas, ticks, net) for one named perturbation stream (§9.3). Each kind declares
    the case it exists to exercise; `event()` reports it; the net is computed for the
    reference side."""
    kind = kind if kind is not None else draw(st.sampled_from(STREAM_KINDS))
    base = _base_entries(draw, names)
    flat = [(name, entry) for name in names for entry in base[name]]

    def arrivals(sel: Any) -> dict:
        tick: dict = {}
        for name, entry in sel:
            tick.setdefault(name, []).append(entry)
        return tick

    ticks: list = []
    if kind == "one-shot":
        ticks = [arrivals(flat)]
    elif kind == "empty-batch":
        ticks = [arrivals(flat), {}]
    elif kind == "partition-k":
        assignment = [draw(st.integers(0, 2)) for _ in flat]
        for batch in range(3):
            ticks.append(arrivals([f for f, b in zip(flat, assignment) if b == batch]))
    elif kind == "interleave":
        ticks = [arrivals([(n, e) for n, e in flat if n == name]) for name in names]
    elif kind in ("arrive-retract", "partial-retract", "retract-rearrive"):
        ticks = [arrivals(flat)]
        if flat:
            name, (row, count, atom) = flat[draw(st.integers(0, len(flat) - 1))]
            if kind == "partial-retract" and count < 2:
                count += 1  # ensure something is left standing
                ticks = [arrivals([(n, e) if e[2] != atom else (n, (row, count, atom))
                                   for n, e in flat])]
            take = 1 if kind == "partial-retract" else count
            ticks.append({name: [(row, -take, atom)]})
            if kind == "retract-rearrive":
                ticks.append({name: [(row, 1, atom)]})
    elif kind == "retract-to-empty":
        ticks = [arrivals(flat)]
        victims = [n for n in names if base[n]]
        if victims:
            name = victims[draw(st.integers(0, len(victims) - 1))]
            ticks.append({name: [(row, -count, atom) for row, count, atom in base[name]]})
    elif kind == "same-tick-co-arrival":
        first = [(n, e) for n, e in flat if n == names[0]][:1]
        rest = [f for f in flat if f not in first]
        ticks = [arrivals(first), arrivals(rest)]
    elif kind == "right-moves":
        # The superseded-address case, drawn ON PURPOSE (the D0118 move, needed a second
        # time at this freeze: 25 accidental draws never produced it): the second source
        # is non-empty in tick 0 and CHANGES in tick 1 while a first-source row survives
        # an anti-join against it throughout — so the tick-0 address is cited, then
        # superseded, and only the retire+valuation path can shed it.
        if len(names) >= 2:
            first_name, right_name = names[0], names[1]
            survivor = ({TABLES[first_name][0]: 0, TABLES[first_name][1]: 1}, 1, ATOMS[-1])
            base = dict(base)
            if not any(row[TABLES[first_name][0]] == 0 for row, _, _ in base[first_name]):
                base[first_name] = base[first_name] + (survivor,)
            # value 7 sits outside _VALUES, so a fill row can never collide with a drawn
            # row — identical rows in one source are one row and one ref (m2 §2).
            fill = tuple(({TABLES[right_name][0]: k, TABLES[right_name][1]: 7}, 1, atom)
                         for k, atom in ((1, ATOMS[-2]), (2, ATOMS[-3])))
            need = max(0, 2 - len(base[right_name]))
            base[right_name] = base[right_name] + fill[:need]
            flat = [(name, entry) for name in names for entry in base[name]]
            right = [(n, e) for n, e in flat if n == right_name]
            ticks = [arrivals([f for f in flat if f not in right[1:]]),
                     arrivals(right[1:])]
        else:
            ticks = [arrivals(flat), {}]
    else:
        raise AssertionError(f"unknown stream kind {kind!r}")

    event(f"stream: {kind}")
    schemas = {name: TABLES[name] for name in names}
    return schemas, tuple(ticks), net_of(ticks)


@st.composite
def two_worlds(draw: Any, names: str = "ab") -> tuple:
    """(schemas, entries_small, entries_big, lost_atoms): the big world extends the small
    one, so a monotone plan's witnesses over the small world are dominated by its
    witnesses over the big one — which is what makes the diff/apply round trip
    byte-exact in both directions (§3.2, L3.2)."""
    big = _base_entries(draw, names)
    small: dict = {}
    lost: set = set()
    for name, entries in big.items():
        kept = []
        for row, count, atom in entries:
            keep = draw(st.integers(0, count))
            if keep:
                kept.append((row, keep, atom))
            else:
                lost.add(atom)
        small[name] = tuple(kept)
    event("worlds: small ⊆ big")
    schemas = {name: TABLES[name] for name in names}
    return schemas, small, big, frozenset(lost)


# ------------------------------------------------------------------------------ the checks
#
# Each takes a Subject and raises AssertionError. The frozen law modules call these with
# tannen's subject; tests/test_law_validation.py calls them with MODEL (must pass) and
# with each MUTANTS entry (must fail). A refusal a check did not ask for is converted to
# an AssertionError so a mutant dies as a counterexample, never as an error.


def _same(subject: Subject, got: Any, want: Any, context: str) -> None:
    assert subject.read(got) == subject.read(want) and \
        subject.address(got) == subject.address(want), (
        f"{context}: integrals differ\n  got:  {subject.read(got)!r}\n"
        f"  want: {subject.read(want)!r}")


def _guarded(subject: Subject, thunk: Any, context: str) -> Any:
    try:
        return thunk()
    except (subject.refusal, subject.cone_refusal) as e:
        raise AssertionError(f"{context}: refused unexpectedly — {e}") from e


def check_delta_algebra(subject: Subject, schemas: dict, small: dict, big: dict,
                        lost: Any) -> None:
    """L3.1–L3.4's calculus half: identities, the witnessed retraction, the cone guard."""
    plan = ("project", ("union", ("project", A, ("k",)),
                       ("project", ("join", A, B, ("k",)), ("k",))), ("k",)) \
        if set(schemas) >= {"a", "b"} else ("project", A, ("k",))
    rels_small = {n: subject.ingest(schemas[n], small.get(n, ())) for n in schemas}
    rels_big = {n: subject.ingest(schemas[n], big.get(n, ())) for n in schemas}
    r = _guarded(subject, lambda: evaluate(subject, plan, rels_small), "eval small")
    s = _guarded(subject, lambda: evaluate(subject, plan, rels_big), "eval big")

    empty = subject.rel(plan_schema(plan, schemas), [])
    assert len(subject.read(_guarded(subject, lambda: subject.diff(r, r), "diff(R,R)"))) == 0, \
        "diff(R, R) must be the empty delta"
    _same(subject, _guarded(subject, lambda: subject.apply(r, empty, frozenset()),
                            "apply(R, ∅)"), r, "apply(R, ∅, ∅) = R")

    up = _guarded(subject, lambda: subject.diff(s, r), "diff(S,R)")
    _same(subject, _guarded(subject, lambda: subject.apply(r, up, frozenset()),
                            "apply up"), s, "apply(R, diff(S,R), ∅) = S")

    down = _guarded(subject, lambda: subject.diff(r, s), "diff(R,S)")
    _same(subject, _guarded(subject, lambda: subject.apply(s, down, lost), "apply down"),
          r, "apply(S, diff(R,S), lost) = R")

    # the witnessed retraction (L3.3): every pure retraction in `down` carries exactly
    # the witnesses of the row it retracts, taken from the OLD (bigger) relation.
    s_read = {k: a for k, a in subject.read(s).items()}
    r_keys = set(subject.read(r))
    for key, (dn, w) in subject.read(down).items():
        if key not in r_keys:
            assert dn < 0 and w == s_read[key][1], (
                "a pure retraction must be witnessed by what it retracts "
                f"(row {key!r}: got {w!r}, want {s_read[key][1]!r})")

    # negate is the outright retraction (§3.1): applying it with everything dead empties.
    every_atom = frozenset(a for n in big for _, _, a in big[n])
    gone = _guarded(subject, lambda: subject.apply(
        s, subject.negate(s), every_atom), "apply(S, negate(S))")
    assert len(subject.read(gone)) == 0, "apply(S, negate(S), all-atoms) must be empty"

    # the cone guard (L3.4): one retraction too many is refused by name.
    if subject.read(s):
        first_key = sorted(subject.read(s))[0]
        row = dict(first_key)
        n = subject.read(s)[first_key][0]
        over = subject.rel(plan_schema(plan, schemas),
                           [(row, (-(n + 1), frozenset({frozenset({ATOMS[-1]})})))])
        try:
            subject.apply(s, over, frozenset())
        except subject.cone_refusal:
            pass
        else:
            raise AssertionError("an over-retraction was applied instead of refused (§3.3)")

    # an unwitnessed retraction is not a value (L3.3, D0110's rule under negation).
    try:
        subject.rel(("k",), [({"k": 1}, (-1, WHY_ZERO))])
    except subject.refusal:
        pass
    else:
        raise AssertionError("an unwitnessed retraction was accepted at construction")


def check_linear_rules(subject: Subject, schemas: dict, small: dict, big: dict,
                       lost: Any) -> None:
    """L3.5: for every linear operator, the operator is its own delta rule — applying
    op(Δ) to op(old) reaches op(new), byte-identically, in both directions."""
    a_old = subject.ingest(schemas["a"], small.get("a", ()))
    a_new = subject.ingest(schemas["a"], big.get("a", ()))
    b_old = subject.ingest(schemas["b"], small.get("b", ()))
    b_new = subject.ingest(schemas["b"], big.get("b", ()))

    unary = (
        ("select", lambda r: subject.select(r, PREDICATES["x-positive"])),
        ("project", lambda r: subject.project(r, ("k",))),
        ("map_rows", lambda r: subject.map_rows(r, MAPS["k-only"], MAP_SCHEMAS["k-only"])),
    )
    for direction, old, new, dead in (("grow", a_old, a_new, frozenset()),
                                      ("shrink", a_new, a_old, lost)):
        d = _guarded(subject, lambda: subject.diff(new, old), "diff")
        for name, op in unary:
            got = _guarded(subject, lambda: subject.apply(op(old), op(d), dead),
                           f"{name} {direction}")
            _same(subject, got, op(new), f"linear rule for {name} ({direction})")
    # union: both operands move
    for direction, aw, an, bw, bn, dead in (
            ("grow", a_old, a_new, b_old, b_new, frozenset()),
            ("shrink", a_new, a_old, b_new, b_old, lost)):
        pa_old, pa_new = subject.project(aw, ("k",)), subject.project(an, ("k",))
        pb_old, pb_new = subject.project(bw, ("k",)), subject.project(bn, ("k",))
        d = subject.union(subject.diff(pa_new, pa_old), subject.diff(pb_new, pb_old))
        got = _guarded(subject, lambda: subject.apply(
            subject.union(pa_old, pb_old), d, dead), f"union {direction}")
        _same(subject, got, subject.union(pa_new, pb_new),
              f"linear rule for union ({direction})")


def check_bilinear_join(subject: Subject, schemas: dict, small: dict, big: dict,
                        lost: Any) -> None:
    """L3.6: the pinned two-term form reaches join(new, new); the three-term expansion,
    applied, reaches the same integral (the two deltas may differ only in rows whose
    counts cancelled, which `apply` drops)."""
    on = ("k",)
    for direction, sa, sb, dead in (("grow", (small, big), (small, big), frozenset()),
                                    ("shrink", (big, small), (big, small), lost)):
        a_old = subject.ingest(schemas["a"], sa[0].get("a", ()))
        a_new = subject.ingest(schemas["a"], sa[1].get("a", ()))
        b_old = subject.ingest(schemas["b"], sb[0].get("b", ()))
        b_new = subject.ingest(schemas["b"], sb[1].get("b", ()))
        d_a = subject.diff(a_new, a_old)
        d_b = subject.diff(b_new, b_old)
        out_old = subject.join(a_old, b_old, on)
        want = subject.join(a_new, b_new, on)

        two = _guarded(subject, lambda: subject.join_delta(
            a_old, a_new, d_a, b_old, b_new, d_b, on), "two-term")
        _same(subject, _guarded(subject, lambda: subject.apply(out_old, two, dead),
                                "apply two-term"), want,
              f"two-term bilinear join ({direction})")

        three = subject.union(subject.union(
            subject.join(d_a, b_old, on), subject.join(a_old, d_b, on)),
            subject.join(d_a, d_b, on))
        _same(subject, _guarded(subject, lambda: subject.apply(out_old, three, dead),
                                "apply three-term"), want,
              f"three-term expansion ({direction})")


def check_integrated_ops(subject: Subject, schemas: dict, small: dict, big: dict,
                         lost: Any) -> None:
    """L3.7 + L3.8: replacement reaches the reference for the integrated operators; the
    subtractive aggregate agrees with both; and a raw delta at any of them — or at the
    bag image — still raises by name (the D0109 answer's second half)."""
    # Replacement reaches the reference, PER OPERATOR and MID-STREAM: the two worlds
    # become a grow-then-shrink stream (arrive small; arrive the rest; retract the rest),
    # so every integrated operator is exercised over integrals that changed in both
    # directions — never over a one-shot it could not get wrong. (An earlier draft
    # compared a recomputation to itself; a check that cannot fail is not a check, and
    # it was replaced, not patched — D0114, D0116.)
    ticks = _worlds_ticks(small, big)
    net = net_of(ticks)
    for plan in (("distinct", ("project", A, ("k",))),
                 ("aggregate", A, ("k",), "x", "s"),
                 ("anti_join", A, B, ("k",))):
        got, _dead = _guarded(subject, lambda: run_ticks(subject, plan, schemas, ticks),
                              f"stream {plan[0]}")
        want = _guarded(subject, lambda: one_shot(subject, plan, schemas, net),
                        f"one-shot {plan[0]}")
        _same(subject, got, want, f"replacement {plan[0]} over a grow-then-shrink stream")

    # the subtractive aggregate agrees with the replacement fold in both directions
    for direction, sw in (("grow", (small, big)), ("shrink", (big, small))):
        rels_old = {n: subject.ingest(schemas[n], sw[0].get(n, ())) for n in schemas}
        rels_new = {n: subject.ingest(schemas[n], sw[1].get(n, ())) for n in schemas}
        agg_old = subject.aggregate_sum(rels_old["a"], ("k",), "x", "s")
        agg_want = subject.aggregate_sum(rels_new["a"], ("k",), "x", "s")
        sub = _guarded(subject, lambda: subject.aggregate_subtractive(
            rels_old["a"], rels_new["a"], ("k",), "x", "s", agg_old), "subtractive")
        _same(subject, sub, agg_want, f"subtractive aggregate ({direction}) — the "
              "declared group's inverse is load-bearing here (L3.8)")

    # the raises (§3.4): a raw delta with a retraction reaches no integrated operator.
    a_new = subject.ingest(schemas["a"], big.get("a", ()))
    a_old = subject.ingest(schemas["a"], small.get("a", ()))
    d = subject.diff(a_old, a_new)  # shrinking: carries retractions when worlds differ
    if any(ann[0] < 0 for ann in subject.read(d).values()):
        for name, thunk in (
                ("distinct", lambda: subject.distinct(d)),
                ("aggregate", lambda: subject.aggregate_sum(d, ("k",), "x", "s")),
                ("anti_join right", lambda: subject.anti_join(a_new, d, ("k",))),
                ("bag", lambda: subject.bag(d))):
            try:
                thunk()
            except subject.cone_refusal:
                continue
            raise AssertionError(
                f"a raw delta reached {name} and was answered instead of refused — "
                "negatives are lawful in delta position only (§3.4, D0109)")


def _worlds_ticks(small: dict, big: dict) -> tuple:
    """two_worlds as a grow-then-shrink stream: arrive the small world, arrive the
    difference, retract the difference — net is the small world again."""
    tick0: dict = {}
    tick1: dict = {}
    tick2: dict = {}
    for name, entries in big.items():
        kept = {_key(row): count for row, count, _ in small.get(name, ())}
        for row, count, atom in entries:
            have = kept.get(_key(row), 0)
            if have:
                tick0.setdefault(name, []).append((row, have, atom))
            if count - have:
                tick1.setdefault(name, []).append((row, count - have, atom))
                tick2.setdefault(name, []).append((row, -(count - have), atom))
    return (tick0, tick1, tick2)


def check_convergence(subject: Subject, schemas: dict, ticks: Any, net: dict) -> None:
    """L3.9 + L3.10, on single-source shapes: every stream reaches the one-shot ingest of
    the net rows, byte-identically, and the ledger's `dead` is exactly the stream's
    kill-list."""
    for shape in CONVERGENCE_SHAPES:
        got, dead = _guarded(
            subject, lambda: run_ticks(subject, shape.plan, schemas, ticks),
            f"run {shape.name}")
        want = _guarded(subject, lambda: one_shot(subject, shape.plan, schemas, net),
                        f"one-shot {shape.name}")
        _same(subject, got, want, f"{shape.name}: stream vs one-shot")
        assert dead == expected_dead(ticks), (
            f"{shape.name}: ledger dead-set is {sorted(dead)}, "
            f"stream killed {sorted(expected_dead(ticks))}")


def check_graph_convergence(subject: Subject, shape: Shape, schemas: dict, ticks: Any,
                            net: dict) -> None:
    """L3.11 + L3.12: on a composite shape, the executor's final integral equals the
    reference one-shot byte-identically — `Why` included, superseded anti_join addresses
    included, because the contagion rule replays everything above an anti_join; and on
    the positive fragment the un-valuated run carries the cumulative `Why`, from which
    `surviving(·, dead)` recovers the reference exactly — the residue theorem."""
    got, dead = _guarded(
        subject, lambda: run_ticks(subject, shape.plan, schemas, ticks),
        f"run {shape.name}")
    want = _guarded(subject, lambda: one_shot(subject, shape.plan, schemas, net),
                    f"one-shot {shape.name}")
    _same(subject, got, want, f"{shape.name}: incremental vs reference")

    if shape.positive:
        cumulative, run_dead = _guarded(
            subject, lambda: run_ticks(subject, shape.plan, schemas, ticks, valuate=False),
            f"unvaluated run {shape.name}")
        ref = subject.read(want)
        cum = subject.read(cumulative)
        for key, (n, w) in cum.items():
            survived = surviving(w, run_dead)
            if key in ref:
                assert survived == ref[key][1], (
                    f"{shape.name}: residue theorem — surviving({key}) is {survived!r}, "
                    f"reference has {ref[key][1]!r}")
            else:
                assert not survived, (
                    f"{shape.name}: {key} is not in the reference yet its cumulative "
                    f"witnesses survive the valuation: {survived!r}")
        for key in ref:
            assert key in cum, f"{shape.name}: reference row {key} missing from cumulative run"


def check_doors(subject: Subject) -> None:
    """L3.13 + L3.14: `why_slots` finds every `Why`; the witnessed-row door fires at
    every position; `anti_join` refuses a multi-`Why` semiring; the encode gate holds."""
    for label, spec in SEMIRING_SPECS.items():
        want = spec_slots(spec)
        got = subject.why_slots(spec)
        assert tuple(sorted(got)) == tuple(sorted(want)), (
            f"{label}: why_slots found {got!r}, the structure holds {want!r} — a locator "
            "that answers to the first match is RT-M2-04 exactly")
        for position in want:
            assert subject.unwitnessed_refused(spec, position), (
                f"{label}: an empty Why at {position} passed the witnessed-row door — "
                "the frozen claim is ANY semiring carrying a Why (m2 §3)")
        if len(want) > 1:
            assert subject.anti_join_multi_why_refused(spec), (
                f"{label}: anti_join accepted a semiring with {len(want)} Why slots — "
                "the absence witness has two inequivalent readings there (§2.2)")
    assert subject.encode_rejects_non_ref(), (
        "encoding a Why carrying a non-grammar atom did not raise — RT-M2-07's channel "
        "is open")


def check_differential(subject: Subject, shape: Shape, schemas: dict, ticks: Any,
                       net: dict) -> None:
    """L3.16 — the shipped package agrees with the frozen model, annotation for
    annotation, across the whole stream. Addresses are the one subject-relative atom
    (each side cites its own right-integral address; the model has no canonical encoder
    and must not borrow tannen's), so they are normalised to a placeholder before
    comparison — the m2 `_relabel` rule, streamwise."""
    got, got_dead = run_ticks(subject, shape.plan, schemas, ticks)
    want, want_dead = run_ticks(MODEL, shape.plan, schemas, ticks)
    assert _relabel_addresses(subject.read(got)) == _relabel_addresses(MODEL.read(want)), (
        f"{shape.name}: {subject.name} and the model disagree over the stream")
    assert got_dead == want_dead, (
        f"{shape.name}: ledgers disagree — {sorted(got_dead)} vs {sorted(want_dead)}")


def _relabel_addresses(read: dict) -> dict:
    """Model atoms are drawn from ATOMS; anything else in a support set is a subject-
    minted relation address. Substitute a placeholder for those, keeping structure."""
    known = set(ATOMS)
    return {
        key: (n, antichain(frozenset(a if a in known else "<addr>" for a in support)
                           for support in w))
        for key, (n, w) in read.items()
    }


# ------------------------------------------------------------------------------ the mutants


class _ApplyKeepsZeroRows(Subject):
    """`apply` skips the group-zero drop "for consistency with L1.4's retained
    `(0, {{r}})`". Tannen's own tempting wrong behaviour #1: the frozen retention rule is
    about CONSTRUCTION, and importing it into `apply` leaves a cancelled row haunting
    every integral — the reference never has it."""
    name = "apply-keeps-zero-rows"

    def apply(self, base, delta, dead):
        dead = frozenset(dead)
        merged = {k: (row, ann) for k, (row, ann) in base.rows.items()}
        for k, (row, ann) in delta.rows.items():
            merged[k] = (row, self.a_add(merged[k][1], ann) if k in merged else ann)
        pairs = []
        for _, (row, (n, w)) in sorted(merged.items()):
            if n < 0:
                raise ModelConeRefusal(f"over-retraction at {row!r}")
            if (n, w) == ZERO:
                continue
            pairs.append((row, (n, surviving(w, dead))))
        return MRel(base.schema, pairs, add=self.a_add)


class _NoLedger(Subject):
    """`apply` never valuates: the cumulative `Why` is served as the answer, so a
    retraction leaves every dead citation standing."""
    name = "no-ledger"

    def apply(self, base, delta, dead):
        return Subject.apply(self, base, delta, frozenset())


class _JoinBothSidesOld(Subject):
    """The classic bilinear off-by-one: ΔA⋈B_old ⊎ A_old⋈ΔB, which silently drops the
    ΔA⋈ΔB term and is wrong exactly when both operands move in one tick."""
    name = "join-both-sides-old"

    def join_delta(self, a_old, a_new, d_a, b_old, b_new, d_b, on):
        return self.union(self.join(d_a, b_old, on), self.join(a_old, d_b, on))


class _AntiJoinEatsDelta(Subject):
    """Feeds raw deltas to `anti_join` "like the linear rules do": presence is judged by
    the sign of the count instead of by the bag image of an integral. Tannen's own
    tempting wrong behaviour #2 — the D0109/D0114 mutant: absence against a retraction
    is a guess, and the refusal this defeats is the executor's tripwire."""
    name = "antijoin-eats-delta"

    def anti_join(self, a, b, on):
        keys = tuple(sorted(on))
        present = {tuple(row[k] for k in keys) for row, ann in b if ann[0] > 0}
        witness = frozenset({frozenset({b.address()})}) if len(b) else None
        out = []
        for row, ann in a:
            if tuple(row[k] for k in keys) in present:
                continue
            out.append((row, self.combine_witness(ann, witness) if witness else ann))
        return MRel(a.schema, out, add=self.a_add)


class _GroupInverseWrong(Subject):
    """A subtractive aggregate over a broken inverse: retracted contributions are folded
    back IN instead of out. The declared group laws are what L3.8 tests directly, and
    this is the mutant that dies only because they are."""
    name = "group-inverse-wrong"

    def g_inv(self, a):
        return a


class _DiffForgetsTheRetractionWitness(Subject):
    """`diff` emits retractions witnessed by `one` instead of by what they retract — so
    a retraction is 'witnessed' by the empty derivation, and the round trip smears every
    Why it touches down to `{∅}`."""
    name = "diff-forgets-the-retraction-witness"

    def diff(self, new, old):
        pairs = []
        for k in sorted(set(new.rows) | set(old.rows)):
            row = (new.rows.get(k) or old.rows[k])[0]
            na = new.rows[k][1] if k in new.rows else ZERO
            oa = old.rows[k][1] if k in old.rows else ZERO
            if na == oa:
                continue
            w = na[1] if k in new.rows else WHY_ONE
            pairs.append((row, (na[0] - oa[0], w)))
        return MRel(new.schema, pairs, add=self.a_add)


class _WhySlotFirstMatch(Subject):
    """The M2 locator as shipped (RT-M2-04): the FIRST `Why` found, checked in a fixed
    order, is the only one the doors ever see. Not a hypothetical — this is the shipped
    behaviour kept as the mutant the closure must kill, the `antijoin-disjunctive`
    precedent exactly."""
    name = "why-slot-first-match"

    def why_slots(self, spec):
        all_slots = spec_slots(spec)
        return all_slots[:1]


class _AntiJoinDeltaMaintained(Subject):
    """`anti_join` maintained by diff-and-apply "like distinct is": sound-looking, and
    wrong at the ∅→non-empty transition, where the new conjunctive witness strictly
    contains the empty-era witness, the dominated set carries no dead atom to filter on,
    and the antichain silently keeps the stale claim. NOT a hypothetical: this model
    itself was written this way first, and the `interleave` stream over `join-then-anti`
    found it during pre-freeze validation. The contagion rule (§4) is the fix; this
    mutant is the defect kept runnable."""
    name = "antijoin-delta-maintained"

    def replays(self, plan):
        return False


class _SelectClampsRetractions(Subject):
    """A linear operator that 'preserves the cone' by dropping retraction rows from a
    delta — plausible exactly because L1.9 taught that operators keep the cone, and
    wrong because deltas are not in the cone and were never claimed to be."""
    name = "select-clamps-retractions"

    def select(self, r, predicate):
        return MRel(r.schema,
                    [(row, a) for row, a in r if predicate(row) and a[0] >= 0],
                    add=self.a_add)


MUTANTS = {
    m.name: m for m in (
        _ApplyKeepsZeroRows(), _NoLedger(), _JoinBothSidesOld(), _AntiJoinEatsDelta(),
        _GroupInverseWrong(), _DiffForgetsTheRetractionWitness(), _WhySlotFirstMatch(),
        _AntiJoinDeltaMaintained(), _SelectClampsRetractions(),
    )
}

#: Which check each mutant must be caught by — the pairing is part of the freeze
#: (D0094 §2). A mutant may incidentally fail other families too; the matrix asserts the
#: named one kills it.
CAUGHT_BY = {
    "apply-keeps-zero-rows": "check_convergence",
    "no-ledger": "check_convergence",
    "join-both-sides-old": "check_bilinear_join",
    "antijoin-eats-delta": "check_integrated_ops",
    "group-inverse-wrong": "check_integrated_ops",
    "diff-forgets-the-retraction-witness": "check_delta_algebra",
    "why-slot-first-match": "check_doors",
    "antijoin-delta-maintained": "check_graph_convergence",
    "select-clamps-retractions": "check_linear_rules",
}


# ------------------------------------------------------------------------------ the harness


def _profile(max_examples: int) -> Any:
    from hypothesis import HealthCheck, settings

    return settings(
        max_examples=max_examples, deadline=None, derandomize=True,
        report_multiple_bugs=False,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )


def run_family(subject: Subject, family: str, max_examples: int = 25) -> None:
    """Run one model-checked family against `subject`; raise on the first counterexample.
    Shapes are bound by factory closures, never default arguments (D0116)."""
    from hypothesis import given

    profile = _profile(max_examples)

    def drive(strategies: dict, prop: Any) -> None:
        profile(given(**strategies)(prop))()

    def worlds(prop: Any, names: str = "ab") -> None:
        def bound(w: tuple) -> None:
            schemas, small, big, lost = w
            prop(schemas, small, big, lost)
        drive(dict(w=two_worlds(names=names)), bound)

    if family == "check_delta_algebra":
        worlds(lambda sc, sm, bg, lo: check_delta_algebra(subject, sc, sm, bg, lo))
    elif family == "check_linear_rules":
        worlds(lambda sc, sm, bg, lo: check_linear_rules(subject, sc, sm, bg, lo))
    elif family == "check_bilinear_join":
        worlds(lambda sc, sm, bg, lo: check_bilinear_join(subject, sc, sm, bg, lo))
    elif family == "check_integrated_ops":
        worlds(lambda sc, sm, bg, lo: check_integrated_ops(subject, sc, sm, bg, lo))
    elif family == "check_convergence":
        def conv(s: tuple) -> None:
            schemas, ticks, net = s
            check_convergence(subject, schemas, ticks, net)
        drive(dict(s=stream_tables(names="a")), conv)
    elif family == "check_graph_convergence":
        for shape in SHAPES:
            def bound(s: tuple, sh: Shape = shape) -> None:
                schemas, ticks, net = s
                check_graph_convergence(subject, sh, schemas, ticks, net)
            drive(dict(s=stream_tables(names="".join(shape.tables))),
                  (lambda f: (lambda s: f(s)))(bound))
    elif family == "check_doors":
        check_doors(subject)
    elif family == "check_differential":
        for shape in SHAPES:
            def bound(s: tuple, sh: Shape = shape) -> None:
                schemas, ticks, net = s
                check_differential(subject, sh, schemas, ticks, net)
            drive(dict(s=stream_tables(names="".join(shape.tables))),
                  (lambda f: (lambda s: f(s)))(bound))
    else:
        raise AssertionError(f"unknown family {family!r}")


#: Every model-checked family. `check_differential` is deliberately outside — it is
#: L3.16's own oracle, not a family a mutant aims at (the m2 rule).
FAMILIES = (
    "check_delta_algebra",
    "check_linear_rules",
    "check_bilinear_join",
    "check_integrated_ops",
    "check_convergence",
    "check_graph_convergence",
    "check_doors",
)
