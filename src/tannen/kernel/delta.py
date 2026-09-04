"""The delta calculus (docs/specs/m3.md §3–§4) — DBSP's `negate`/`diff`/`apply` over
`Rel`, plus the derived per-operator rules.

**A delta is a `Rel` over the same semiring as the relation it changes** (§3.1, D0156).
There is no `Delta` type: `Rel` already constructs negative ℤ counts, the `rel/1`
canonical form already encodes them, and the witnessed-row invariant (docs/specs/m2.md
§3, D0110) already gives `(-1, {{r}})` a home while refusing `(-1, ∅)` — a retraction
owes provenance exactly as an arrival does.

Delta-capability is DECLARED, per component (§2.1): a semiring is delta-capable when
every leaf of its product structure declares `negate`. `B` declares none — symmetric
difference is not subtraction and inventing it would be the silent coercion the doors
exist to refuse — so `product(Z, B)` is refused by name here rather than half-working.

Pure, and pure in the strong sense the milestone needs: **every relation these functions
read arrives as an argument**. No prior state is captured, nothing is memoised, no clock
and no IO (contracts `kernel-no-io` / `kernel-no-clock`). State is the executor's
business (`tannen.incremental`), because state is a stored value.

Two locators drive everything structural: `why_slots` (docs/specs/m3.md §2.2, in
`semiring`) finds every provenance component, and `group_slots` here finds every
component that can subtract. Between them a nested product is handled without any
function in this module knowing that `ZxWhy` is a pair.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any

from tannen.kernel import ops
from tannen.kernel.algebra import AbelianGroup
from tannen.kernel.encoding import encode_canonical
from tannen.kernel.outcome import OperatorError
from tannen.kernel.rel import Rel
from tannen.kernel.semiring import SemiringError, Why, is_bag_semiring, why_slots

__all__ = [
    "LINEAR_RULES",
    "apply",
    "at_slot",
    "diff",
    "group_aggregate_delta",
    "group_slots",
    "is_delta_semiring",
    "join_delta",
    "linear_delta",
    "negate",
    "replace_delta",
    "surviving",
]


# ------------------------------------------------------------------ structural locators


def group_slots(semiring: Any) -> tuple[tuple[str, ...], ...]:
    """Every GROUP component's location in `semiring`, as `why_slots`-shaped paths.

    A leaf is a group component when it declares `negate` and is not a `Why`: `Why` also
    declares `negate`, but as a FIXED POINT (§2.1) — it is a join-semilattice under `add`
    with no inverse, so its witnesses never move backwards and it is filtered by the
    valuation instead of subtracted. `ZxWhy` holds `(("left",),)`; `Z` holds `((),)`;
    `B` and `Why` hold `()`.

    This is the locator `apply`'s cone check and group-zero drop read (§3.3), so neither
    step has to know the shape of the annotation it is looking at.
    """
    left = getattr(semiring, "left", None)
    right = getattr(semiring, "right", None)
    if left is not None and right is not None:
        return tuple(("left",) + path for path in group_slots(left)) + tuple(
            ("right",) + path for path in group_slots(right)
        )
    if semiring.name == "Why":
        return ()
    return ((),) if callable(getattr(semiring, "negate", None)) else ()


def is_delta_semiring(semiring: Any) -> bool:
    """Whether `semiring` can carry deltas: EVERY leaf declares `negate` (§2.1).

    Structural and recursive, so `product(ZxWhy, ZxWhy)` qualifies and `product(Z, B)`
    does not — the answer is about the whole structure, never about the outermost node.
    """
    left = getattr(semiring, "left", None)
    right = getattr(semiring, "right", None)
    if left is not None and right is not None:
        return is_delta_semiring(left) and is_delta_semiring(right)
    return callable(getattr(semiring, "negate", None))


def _component(semiring: Any, path: tuple[str, ...]) -> Any:
    for step in path:
        semiring = semiring.left if step == "left" else semiring.right
    return semiring


def at_slot(annotation: Any, path: tuple[str, ...]) -> Any:
    """The component of `annotation` at a `why_slots` / `group_slots` path.

    The read half of the locators, public because the executor needs it too: reading "how
    many copies did this delta move" out of an annotation is the same structural question
    whatever the product shape, and a second spelling of it in the shell would be the
    duplication that becomes drift (BRIEF §2)."""
    for step in path:
        annotation = annotation[0] if step == "left" else annotation[1]
    return annotation


def _write(annotation: Any, path: tuple[str, ...], value: Any) -> Any:
    if not path:
        return value
    if path[0] == "left":
        return (_write(annotation[0], path[1:], value), annotation[1])
    return (annotation[0], _write(annotation[1], path[1:], value))


# ---------------------------------------------------------------------------- the doors


def _delta_capable(semiring: Any, name: str) -> Any:
    if not is_delta_semiring(semiring):
        raise SemiringError(
            f"{name}: {semiring.name} is not delta-capable — a component declares no "
            "negate, and subtraction is declared, never assumed (docs/specs/m3.md §2.1)"
        )
    return semiring


def _paired(name: str, left: Rel, right: Rel) -> Any:
    if not isinstance(left, Rel) or not isinstance(right, Rel):
        raise OperatorError(
            f"{name}: both arguments are Rels — a delta is a Rel over the same semiring "
            "(docs/specs/m3.md §3.1), never a wrapper type"
        )
    if left.annotations.name != right.annotations.name:
        raise OperatorError(
            f"{name}: semirings differ ({left.annotations.name!r} vs "
            f"{right.annotations.name!r}); a delta is annotated like what it changes"
        )
    if left.schema != right.schema:
        raise OperatorError(
            f"{name}: schemas differ ({left.schema!r} vs {right.schema!r})"
        )
    return _delta_capable(left.annotations, name)


def _key_of(row: Mapping[str, Any], keys: tuple[str, ...]) -> tuple[bytes, ...]:
    return tuple(encode_canonical(row[k]) for k in keys)


# ------------------------------------------------------------------------ the valuation


def surviving(why: Any, dead: Iterable[str]) -> frozenset[frozenset[str]]:
    """M2 §4's valuation, verbatim and now code: a support set survives iff it is
    DISJOINT from `dead` (docs/specs/m3.md §3.3 step 3, §5).

    A support set is a conjunction — every ref in it had to hold — so one dead ref kills
    the whole set, and the row keeps whatever other derivations it has. This is the one
    mechanism by which a semilattice that cannot subtract still reaches the reference's
    `Why` after a retraction (§5's residue theorem, L3.11).

    An antichain filtered by a predicate is still an antichain, so nothing is renormalised
    when nothing was dropped; when something was, `Why.of` rebuilds through the same door
    every other `Why` goes through — including the ref gate (§2.3).
    """
    dead = frozenset(dead)
    if not dead:
        return why
    kept = [support for support in why if not (support & dead)]
    if len(kept) == len(why):
        return why
    return Why.of(*kept)


# ------------------------------------------------------------------- negate, diff, apply


def negate(rel: Rel) -> Rel:
    """The delta that retracts `rel` outright (§3.1): every group component inverted,
    every `Why` kept.

    Witnesses are KEPT and not dropped, because `Why` is a fixed point of negation
    (§2.1): the retraction of a row is witnessed by the derivation of the row it
    retracts, which is both what D0110 demands of any retained annotation and what makes
    the ledger able to name what died (§6).
    """
    S = _delta_capable(rel.annotations, "negate")
    out = {key: (row, S.negate(annotation)) for key, row, annotation in rel._items()}
    return Rel._build(rel.schema, S, rel.annotations_reason, out)


def diff(new: Rel, old: Rel) -> Rel:
    """The delta that moves `old` to `new` (§3.2).

    Per canonical row: group components take the group difference `add(a_new,
    negate(a_old))`; `Why` components take **`new`'s where the row occurs in `new`,
    `old`'s where it does not**, so a pure retraction is witnessed by what it retracts
    and every other row speaks with the new relation's voice. A row whose annotation is
    identical in both is omitted. A row present in both whose group components agree but
    whose `Why` moved is emitted with zero group components and the new `Why` — the
    "annotation moved" delta, which is how a replacement operator's re-cited address
    propagates (§4, §6), and which `Rel` retains for exactly the reason frozen L1.4 gives.

    `diff` never consults the bag image, so it is total over cone and non-cone operands
    alike: deltas can be diffed.
    """
    S = _paired("diff", new, old)
    new_rows = {key: (row, annotation) for key, row, annotation in new._items()}
    old_rows = {key: (row, annotation) for key, row, annotation in old._items()}
    out: dict[bytes, tuple[dict, Any]] = {}
    for key in set(new_rows) | set(old_rows):
        in_new = key in new_rows
        na = new_rows[key][1] if in_new else S.zero
        oa = old_rows[key][1] if key in old_rows else S.zero
        if na == oa:
            continue
        row = new_rows[key][0] if in_new else old_rows[key][0]
        out[key] = (row, _diff_annotation(S, na, oa, in_new))
    return Rel._build(new.schema, S, new.annotations_reason, out)


def _diff_annotation(semiring: Any, na: Any, oa: Any, in_new: bool) -> Any:
    left = getattr(semiring, "left", None)
    right = getattr(semiring, "right", None)
    if left is not None and right is not None:
        return (
            _diff_annotation(left, na[0], oa[0], in_new),
            _diff_annotation(right, na[1], oa[1], in_new),
        )
    if semiring.name == "Why":
        return na if in_new else oa
    return semiring.add(na, semiring.negate(oa))


def apply(base: Rel, delta: Rel, dead: Iterable[str] = frozenset()) -> Rel:
    """`base` moved by `delta` under the ledger's `dead` set — pointwise addition
    followed by three normalisation steps IN THIS ORDER (§3.3, D0157):

    1. **the cone check** — a row whose group component leaves the non-negative cone is
       an over-retraction, refused by name with the row and the shortfall. This is where
       m1 §4.4's promised loud break lands: at the operation whose arguments made the
       question askable, not at a distant `to_bag`. The cone is read through the bag
       image, which is the same notion `to_bag`, `distinct`, `aggregate` and `anti_join`
       already use — one meaning of "really there", not a second one written here.
    2. **the group-zero drop** — a row zero in EVERY group component is not emitted,
       `(0, {{r}})` included: `(1, {{r}}) + (-1, {{r}})` cancels out of the relation,
       because the reference (one-shot ingest of the net rows) has no such row and byte
       identity is the law (§5). The criterion is the group components and deliberately
       not the bag image: a positive count whose `Why` is empty must fall through to
       step 3's alarm rather than be dropped as bag-empty. **Construction is untouched**
       — a caller-built `(0, {{r}})` is still retained (frozen L1.4, D0093); `apply` is
       a new operation choosing what to EMIT, which no frozen node constrains.
    3. **the valuation** — every surviving row's every `Why` is filtered by
       `surviving(·, dead)`, over the ENTIRE result and not only the rows the delta
       touched: uniform, deterministic, and unoptimised on purpose (BRIEF §10).

    A row whose count survives but whose every witness died is then refused by the
    witnessed-row invariant at construction. That is unreachable when the calculus is
    right and it is the calculus's own alarm when it is not — which is why nothing here
    catches it.

    `apply(R, ∅, dead)` is `R` byte-identically for any `R` this calculus produced under
    `dead`: normalisation is idempotent (BRIEF L2 at the calculus level, L3.2).
    """
    S = _paired("apply", base, delta)
    if not is_bag_semiring(S):
        raise SemiringError(
            f"apply: {S.name} declares no bag structure, so 'inside the cone' is not a "
            "proposition about it (docs/specs/m1.md §2.1, m3 §3.3)"
        )
    dead = frozenset(dead)
    groups = group_slots(S)
    whys = why_slots(S)
    merged: dict[bytes, tuple[dict, Any]] = dict(
        (key, (row, annotation)) for key, row, annotation in base._items()
    )
    for key, row, annotation in delta._items():
        if key in merged:
            merged[key] = (merged[key][0], S.add(merged[key][1], annotation))
        else:
            merged[key] = (row, annotation)
    out: dict[bytes, tuple[dict, Any]] = {}
    for key, (row, annotation) in merged.items():
        cancelled = True
        for path in groups:
            component = _component(S, path)
            value = at_slot(annotation, path)
            try:
                component.multiplicity(value)
            except SemiringError as exc:
                raise SemiringError(
                    f"over-retraction: row {row!r} was driven to {value!r} in the "
                    f"{component.name} component of {S.name} — a delta retracted more "
                    "copies than the relation had, which leaves the non-negative cone "
                    f"({exc}); refused at the apply that made the question askable "
                    "(docs/specs/m3.md §3.3 step 1; L3.4)"
                ) from exc
            if value != component.zero:
                cancelled = False
        if groups and cancelled:
            continue
        for path in whys:
            annotation = _write(annotation, path, surviving(at_slot(annotation, path), dead))
        out[key] = (row, annotation)
    return Rel._build(base.schema, S, base.annotations_reason, out)


# ------------------------------------------------------------------- the derived rules
#
# §4's table, as functions. Every relation a rule reads is an argument, including the ones
# a given spelling does not happen to use: the signatures are the ones the LAW quantifies
# over, so the rejected spellings (both-old-sides for the join, replacement where the
# subtractive form belongs) are expressible and die as mutants rather than as typos.

#: The linear operators: their delta rule IS the operator (§4). `distinct`, `aggregate`
#: and `anti_join` are absent on purpose — they are non-monotone and maintained by
#: replacement, and a raw delta never takes operand position at one of them (§3.4).
LINEAR_RULES: dict[str, Callable[..., Any]] = {
    "select": ops.select,
    "project": ops.project,
    "map_rows": ops.map_rows,
    "union": ops.union,
}


def linear_delta(operator: str, *arguments: Any) -> Rel:
    """Δout = op(Δin) — a linear operator is its own delta rule (§4).

    DBSP's rule for linear operators, and it needs no new code because the M1 semiring
    rules are SIGN-BLIND: they use `add` and `mul` only, never the bag image, so the
    shipped operators already compute their own delta form. `arguments` are the
    operator's own, with the delta in the relation position(s).
    """
    rule = LINEAR_RULES.get(operator)
    if rule is None:
        raise OperatorError(
            f"linear_delta: {operator!r} is not a linear operator — {sorted(LINEAR_RULES)} "
            "are their own delta rule; distinct/aggregate/anti_join are maintained by "
            "replacement over integrals (docs/specs/m3.md §4)"
        )
    return rule(*arguments).unwrap()


def join_delta(
    a_old: Rel, a_new: Rel, d_a: Rel, b_old: Rel, b_new: Rel, d_b: Rel, on: Iterable[str]
) -> Rel:
    """The PINNED two-term bilinear rule (§4, D0159):

        Δout = join(ΔA, B_old) ⊎ join(A_new, ΔB)

    On the group components this equals `A_new ⋈ B_new − A_old ⋈ B_old` outright, and
    its equivalence to the three-term expansion `ΔA⋈B_old ⊎ A_old⋈ΔB ⊎ ΔA⋈ΔB` is a law
    clause rather than a comment (L3.6). It is pinned because the both-old-sides spelling
    `ΔA⋈B_old ⊎ A_old⋈ΔB` is the classic off-by-one — it drops the same-tick co-arrival
    term — and that spelling is kept as the mutant `join-both-sides-old`.

    `a_old` and `b_new` are read by neither term and are taken all the same: the
    signature is the one the law quantifies over, so every candidate spelling is
    expressible here and the wrong ones die in daylight instead of being unwritable.
    """
    keys = tuple(sorted(on))
    return ops.union(
        ops.join(d_a, b_old, keys).unwrap(), ops.join(a_new, d_b, keys).unwrap()
    ).unwrap()


def replace_delta(out_new: Rel, out_old: Rel) -> Rel:
    """The delta rule for a non-monotone operator: **replacement** (§4).

    DBSP's `op^Δ = D ∘ op ∘ I` for the non-linear operators, taken literally and
    unoptimised (BRIEF §10). The caller recomputes the operator over the new input
    INTEGRAL — which is the new output integral — and this is the `D` that hands the
    parent a delta. `distinct` and `aggregate` never extend a support set, so the nodes
    above them stay safely delta-maintained; `anti_join` does, which is why replacement
    is contagious upward there (§4's contagion rule, D0163).
    """
    return diff(out_new, out_old)


def group_aggregate_delta(
    in_old: Rel,
    in_new: Rel,
    by: Iterable[str],
    group: AbelianGroup,
    value_of: Callable[[dict], Any],
    into: str,
    out_old: Rel,
) -> Rel:
    """`aggregate` maintained SUBTRACTIVELY over a declared `AbelianGroup` (§4, L3.8) —
    and it returns the new output **integral**, not a delta.

    Each touched group's folded value is maintained rather than recomputed: arriving
    contributions are folded in with `group.op`, retracted ones with `group.inverse`,
    once per copy the delta moves. This is where BRIEF P5's "abelian group for
    subtractability" engages — the first consumer `tannen.kernel.algebra.AbelianGroup`
    has had, whose declared `inverse` is load-bearing here and whose laws were checked
    when it was constructed, not when it is used.

    The output ANNOTATIONS are recomputed from `in_new` exactly as `ops.aggregate`
    computes them (the group's added annotations, collapsed): support is not subtractable
    and it is not what the group maintains. The subtractive and replacement forms must
    therefore agree byte-identically, and that agreement is the law (D0160) — which is
    also why the return shape is the integral: it is what `ops.aggregate` returns, and a
    comparison of two different shapes would prove nothing.
    """
    S = _paired("group_aggregate_delta", in_new, in_old)
    if not isinstance(group, AbelianGroup):
        raise OperatorError(
            f"group_aggregate_delta: {group!r} is not a tannen.kernel.algebra."
            "AbelianGroup — the subtractive form needs a declared inverse, with its "
            "laws checked over witnesses at construction (BRIEF §5.6, m3 §4)"
        )
    if not isinstance(into, str) or not into:
        raise OperatorError("group_aggregate_delta: into must be a non-empty column name")
    keys = tuple(sorted(by))
    if into in keys:
        raise OperatorError(
            f"group_aggregate_delta: into {into!r} collides with by {keys!r}"
        )
    missing = [column for column in keys if column not in in_new.schema]
    if missing:
        raise OperatorError(
            f"group_aggregate_delta: {missing} not in the schema {in_new.schema!r}"
        )
    slots = group_slots(S)
    if len(slots) != 1:
        raise SemiringError(
            f"group_aggregate_delta: {S.name} carries {len(slots)} group components, and "
            "the number of copies a delta moves is read from exactly one. Refused until "
            "a law decides which (docs/specs/m3.md §4)"
        )
    count = slots[0]

    old_folded = {_key_of(row, keys): row[into] for row, _ in out_old}
    contributions: dict[tuple[bytes, ...], Any] = {}
    for row, annotation in diff(in_new, in_old):
        moved = at_slot(annotation, count)
        if not moved:
            continue  # an annotation-moved delta changes no fold (§3.2)
        key = _key_of(row, keys)
        acc = contributions.get(key, group.identity)
        contribution = value_of(row)
        step = contribution if moved > 0 else group.inverse(contribution)
        for _ in range(abs(moved)):
            acc = group.op(acc, step)
        contributions[key] = acc

    members: dict[tuple[bytes, ...], list[tuple[dict, Any]]] = {}
    for _, row, annotation in in_new._items():  # canonical order, as ops.aggregate folds
        members.setdefault(_key_of(row, keys), []).append((row, annotation))
    pairs = []
    for key, rows in members.items():
        folded = group.op(
            old_folded.get(key, group.identity), contributions.get(key, group.identity)
        )
        total = rows[0][1]
        for _, annotation in rows[1:]:
            total = S.add(total, annotation)
        head = rows[0][0]
        pairs.append(({**{k: head[k] for k in keys}, into: folded}, S.collapse(total)))
    schema = tuple(sorted(keys + (into,)))
    return Rel._from_pairs(schema, S, in_new.annotations_reason, pairs)
