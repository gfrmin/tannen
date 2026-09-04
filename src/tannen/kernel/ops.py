"""The operators (docs/specs/m1.md §4, §4.1, §5). Each ships a type rule and a semiring rule;
the semiring rule IS the provenance rule when S carries a Why component (BRIEF P4).

Every operator takes `Rel | Ok | Quarantine` inputs and returns `Ok | Quarantine`:

1. a `Quarantine` input propagates untouched (a node that failed upstream);
2. an ill-typed call raises `OperatorError` at the call — refused by name, never repaired;
3. row-wise failures in user code (`Exception`, never `BaseException`) quarantine the row;
4. the result carries every input's quarantined rows and the union of operator names.

Projection SUMS (bag semantics); `distinct` is how you spell the other one. `aggregate`
folds each group in canonical-encoding order (§4.1), so a non-commutative monoid still
gives a deterministic answer.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from itertools import chain
from typing import Any

from tannen.kernel.algebra import Monoid
from tannen.kernel.encoding import decode_canonical, encode_canonical
from tannen.kernel.outcome import QUARANTINE_SCHEMA, Ok, OperatorError, Outcome, Quarantine
from tannen.kernel.rel import Rel
from tannen.kernel.semiring import Why, is_bag_semiring, why_slots

__all__ = [
    "OPERATORS",
    "OperatorError",
    "aggregate",
    "anti_join",
    "distinct",
    "join",
    "map_rows",
    "project",
    "select",
    "union",
]

#: The eight names. BRIEF §4 lists seven; `map/project` is split because the type rules differ.
OPERATORS: tuple[str, ...] = (
    "select", "project", "map_rows", "union", "join", "distinct", "anti_join", "aggregate",
)

Merged = dict[bytes, tuple[dict, Any]]
QRow = tuple[dict, Any]


# ------------------------------------------------------------------ inputs and outputs


def _take(name: str, *args: Any) -> tuple[list[Rel], list[Rel], frozenset[str]] | Quarantine:
    """Unwrap operator arguments. A `Quarantine` anywhere propagates, naming this operator."""
    rels: list[Rel] = []
    carried: list[Rel] = []
    operators: set[str] = {name}
    for arg in args:
        if isinstance(arg, Quarantine):
            return Quarantine(
                reason=arg.reason,
                detail=f"{name}: an input was quarantined at node level — {arg.detail}",
                provenance=arg.provenance,
                operators=arg.operators | {name},
            )
        if isinstance(arg, Ok):
            rels.append(arg.rel)
            carried.append(arg.quarantined)
            operators |= arg.operators
        elif isinstance(arg, Rel):
            rels.append(arg)
        else:
            raise OperatorError(f"{name}: {type(arg).__name__} is neither a Rel nor an Outcome")
    return rels, carried, frozenset(operators)


def _put(acc: Merged, S: Any, key: bytes, row: dict, annotation: Any) -> None:
    if key in acc:
        acc[key] = (acc[key][0], S.add(acc[key][1], annotation))
    else:
        acc[key] = (row, annotation)


def _quarantine_row(name: str, row: dict, exc: Exception) -> dict:
    return {
        "detail": str(exc) or type(exc).__name__,
        "operator": name,
        "reason": type(exc).__name__,
        "row": dict(row),
    }


def _finish(
    name: str,
    source: Rel,
    schema: tuple[str, ...],
    acc: Merged,
    carried: list[Rel],
    bad: list[dict],
    operators: frozenset[str],
) -> Ok:
    S, reason = source.annotations, source.annotations_reason
    rel = Rel._build(schema, S, reason, acc)
    # _from_pairs, not the public constructor: a source decoded by Rel.from_value carries no
    # annotations_reason even under Z, and the public constructor would refuse that here.
    quarantined = Rel._from_pairs(
        QUARANTINE_SCHEMA,
        S,
        reason,
        chain(chain.from_iterable(carried), ((row, S.one) for row in bad)),
    )
    return Ok(rel=rel, quarantined=quarantined, operators=operators)


# ------------------------------------------------------------------------ type rules


def _columns(name: str, columns: Any, what: str) -> tuple[str, ...]:
    try:
        cols = tuple(columns)
    except TypeError as exc:
        raise OperatorError(f"{name}: {what} must be an iterable of column names") from exc
    if not cols:
        raise OperatorError(f"{name}: {what} may not be empty")
    if any(not isinstance(c, str) for c in cols):
        raise OperatorError(f"{name}: {what} are str column names, got {cols!r}")
    if len(set(cols)) != len(cols):
        raise OperatorError(f"{name}: duplicate column in {what} {cols!r}")
    return cols


def _in_schema(name: str, columns: tuple[str, ...], rel: Rel, side: str = "the schema") -> None:
    missing = [c for c in columns if c not in rel.schema]
    if missing:
        raise OperatorError(f"{name}: {missing} not in {side} {rel.schema!r}")


def _same_semiring(name: str, left: Rel, right: Rel) -> None:
    if left.annotations.name != right.annotations.name:
        raise OperatorError(
            f"{name}: semirings differ ({left.annotations.name!r} vs {right.annotations.name!r}); "
            "annotate both sides the same way, by name (§4)"
        )


def _key_of(row: dict, keys: tuple[str, ...]) -> tuple[bytes, ...]:
    return tuple(encode_canonical(row[k]) for k in keys)


def _conjoin_witness(semiring: Any, path: tuple[str, ...], annotation: Any, witness: Any) -> Any:
    """MULTIPLY `witness` into the `Why` component `path` names, so every support set
    gains it (docs/specs/m2.md §6, D0132).

    `mul` and not `add`: the claim an absence witness makes is a CONJUNCTION — this row's
    own derivation held AND the right relation lacked this key at that version. `add`
    reads as *or*, which leaves the citation standing as an independent derivation of a
    row it cannot derive, and then §5 predicts a row survives the deletion of the very
    source row it came from.

    The slot is a `why_slots` path (docs/specs/m3.md §2.2), walked recursively, so a
    `Why` nested anywhere in a single-slot product is reached — the M2 spelling only knew
    depth-one slots. It ENRICHES an annotation and never decides whether a row is there —
    presence is the bag image, a separate question with a separate answer (see
    `anti_join`).
    """
    if not path:
        return semiring.mul(annotation, witness)
    if path[0] == "left":
        return (_conjoin_witness(semiring.left, path[1:], annotation[0], witness), annotation[1])
    return (annotation[0], _conjoin_witness(semiring.right, path[1:], annotation[1], witness))


def _callable(name: str, fn: Any, what: str) -> None:
    if not callable(fn):
        raise OperatorError(f"{name}: {what} must be callable, got {fn!r}")


# ------------------------------------------------------------------------ operators


def select(rel: Any, predicate: Callable[[dict], bool]) -> Outcome:
    taken = _take("select", rel)
    if isinstance(taken, Quarantine):
        return taken
    (source,), carried, operators = taken
    _callable("select", predicate, "predicate")
    kept: Merged = {}
    bad: list[dict] = []
    for key, row, annotation in source._items():
        try:
            keep = predicate(dict(row))
        except Exception as exc:
            bad.append(_quarantine_row("select", row, exc))
            continue
        if keep:
            kept[key] = (row, annotation)
    return _finish("select", source, source.schema, kept, carried, bad, operators)


def project(rel: Any, columns: Iterable[str]) -> Outcome:
    taken = _take("project", rel)
    if isinstance(taken, Quarantine):
        return taken
    (source,), carried, operators = taken
    cols = _columns("project", columns, "columns")
    _in_schema("project", cols, source)
    schema = tuple(sorted(cols))
    S = source.annotations
    acc: Merged = {}
    for _, row, annotation in source._items():
        out = {c: row[c] for c in schema}
        _put(acc, S, encode_canonical(out), out, annotation)  # projection SUMS
    return _finish("project", source, schema, acc, carried, [], operators)


def map_rows(rel: Any, f: Callable[[dict], Mapping[str, Any]], schema: Iterable[str]) -> Outcome:
    taken = _take("map_rows", rel)
    if isinstance(taken, Quarantine):
        return taken
    (source,), carried, operators = taken
    declared = tuple(sorted(_columns("map_rows", schema, "declared schema")))
    _callable("map_rows", f, "f")
    expected = frozenset(declared)
    S = source.annotations
    acc: Merged = {}
    bad: list[dict] = []
    for _, row, annotation in source._items():
        try:
            out = f(dict(row))
            if not isinstance(out, Mapping) or frozenset(out) != expected:
                raise OperatorError(f"map_rows: f returned {out!r}, not a row over {declared!r}")
            key = encode_canonical(dict(out))  # CanonicalEncodingError: a float, a tuple, ...
        except Exception as exc:  # a wrongly shaped or unencodable row quarantines, per row
            bad.append(_quarantine_row("map_rows", row, exc))
            continue
        _put(acc, S, key, decode_canonical(key), annotation)
    return _finish("map_rows", source, declared, acc, carried, bad, operators)


def union(a: Any, b: Any) -> Outcome:
    taken = _take("union", a, b)
    if isinstance(taken, Quarantine):
        return taken
    (left, right), carried, operators = taken
    _same_semiring("union", left, right)
    if left.schema != right.schema:
        raise OperatorError(f"union: schemas differ: {left.schema!r} vs {right.schema!r}")
    S = left.annotations
    acc: Merged = {}
    for key, row, annotation in chain(left._items(), right._items()):
        _put(acc, S, key, row, annotation)
    return _finish("union", left, left.schema, acc, carried, [], operators)


def join(a: Any, b: Any, on: Iterable[str]) -> Outcome:
    taken = _take("join", a, b)
    if isinstance(taken, Quarantine):
        return taken
    (left, right), carried, operators = taken
    keys = _columns("join", on, "on")
    _same_semiring("join", left, right)
    _in_schema("join", keys, left, "the left schema")
    _in_schema("join", keys, right, "the right schema")
    clash = (set(left.schema) & set(right.schema)) - set(keys)
    if clash:
        raise OperatorError(
            f"join: non-key columns {sorted(clash)} appear on both sides — rename before "
            "joining; nothing is suffixed silently (§4)"
        )
    schema = tuple(sorted(set(left.schema) | set(right.schema)))
    S = left.annotations
    index: dict[tuple[bytes, ...], list[tuple[dict, Any]]] = {}
    for _, row, annotation in right._items():
        index.setdefault(_key_of(row, keys), []).append((row, annotation))
    acc: Merged = {}
    for _, lrow, lann in left._items():
        for rrow, rann in index.get(_key_of(lrow, keys), ()):
            out = {**lrow, **rrow}
            _put(acc, S, encode_canonical(out), out, S.mul(lann, rann))
    return _finish("join", left, schema, acc, carried, [], operators)


def distinct(rel: Any) -> Outcome:
    taken = _take("distinct", rel)
    if isinstance(taken, Quarantine):
        return taken
    (source,), carried, operators = taken
    S = source.annotations
    if not is_bag_semiring(S):
        raise OperatorError(f"distinct: {S.name} declares no bag structure (docs/specs/m1.md §2.1)")
    acc: Merged = {key: (row, S.collapse(annotation)) for key, row, annotation in source._items()}
    return _finish("distinct", source, source.schema, acc, carried, [], operators)


def anti_join(a: Any, b: Any, on: Iterable[str]) -> Outcome:
    """Presence is decided by the BAG IMAGE of a right row's annotation, never by the raw
    annotation — that was the bug. A right row of `(0, {{ref}})` (net count zero, still
    witnessed, retained per §3) has no bag image and must NOT block a matching left row:
    `Why` explains an answer, it never supplies one. The rule is symmetric, because L1.2
    (as amended by D0093) is symmetric: `(n, ∅)` has no bag image either, and does not
    block. That is a real disagreement with the projection `(n, w) -> n`, which IS a
    semiring homomorphism; RG&T buys commutation with it for RA+ only, and anti_join is
    outside RA+. This operator follows `to_bag` and `aggregate` rather than the projection,
    so all three agree on what "really there" means. `(0, w)` is not reachable by composing
    operators over well-formed inputs, and `(n, ∅)` is not reachable AT ALL since D0110
    — a retained row is a witnessed row (docs/specs/m2.md §3), so the second half of the
    symmetry is now unconstructible rather than merely unreachable, and the disagreement
    D0107 weighed dissolves instead of having to be decided. Both are checked in
    tests/test_provenance_homomorphism.py rather than asserted here.

    Every surviving row's `Why`, where there is one, gains a witness naming `right`'s own
    content address — the claim being made ("this key was absent from R") is about the
    right relation as a whole at this version, not about any row on it, so no row-level
    ref can express it — UNLESS `right` is empty: against a genuinely empty relation there
    was nothing to check, so nothing to cite, and anti_join is exactly the identity
    (L1.8) — a witness added unconditionally would violate that, since a survivor's
    annotation would then differ from its input's.

    The witness goes in with `mul`, so EVERY support set gains it (docs/specs/m2.md §6,
    D0132). M1 used `add`, which reads as *or* and leaves the citation standing as an
    independent derivation of a row it cannot derive: delete the left source row and the
    absence witness alone still predicts survival, while the left relation is empty and
    the row is gone. The claim is conjunctive — this row's own derivation held AND the
    right relation lacked this key at that version — and `_conjoin_witness` is where that
    is spelled. Because deleting anything the right operand reads MOVES its address, no
    witness of an old output survives into the new one: an anti-join's rows are
    recomputed, never inherited, which is what makes M2 §5's theorem exact for a
    non-monotone operator.
    """
    taken = _take("anti_join", a, b)
    if isinstance(taken, Quarantine):
        return taken
    (left, right), carried, operators = taken
    keys = _columns("anti_join", on, "on")
    _same_semiring("anti_join", left, right)
    _in_schema("anti_join", keys, left, "the left schema")
    _in_schema("anti_join", keys, right, "the right schema")
    S = left.annotations
    slots = why_slots(S)
    if len(slots) > 1:
        raise OperatorError(
            f"anti_join: {S.name} carries {len(slots)} Why slots, and the absence witness "
            "conjoins one address into THE Why — a semiring with two gives that convention "
            "two inequivalent readings. Refused until a law, not an accident of slot order, "
            "decides (docs/specs/m3.md §2.2, D0161; L3.13)"
        )
    # Presence is the BAG image — the same notion `to_bag` (§3.3) and `aggregate` already
    # use — and NOT `annotation != zero`, which was the bug. L1.2 as amended by D0093 is
    # explicit that BOTH `(0, w)` and `(n, ∅)` are non-zero annotations with no bag image,
    # so the rule has to be symmetric: a row with no copies is not there, whichever
    # component zeroed it. A semiring that declares no bag structure keeps the pre-bag
    # rule — anti_join needs only a `Semiring`, and L1.7 enumerates the bag-requiring
    # operators as distinct/aggregate/to_bag. Under `Z` a negative annotation has no bag
    # image and is refused by name here exactly as `to_bag` refuses it (the cone law).
    # THAT REFUSAL DOES NOT EXPIRE — it is RE-COMMISSIONED (docs/specs/m3.md §3.4, the
    # D0109 answer, D0158): a raw delta never takes operand position at an integrated
    # operator. The delta rule for a non-monotone operator is replacement over INTEGRALS
    # (m3 §4), retractions are applied to the right integral BEFORE absence is judged,
    # and the executor keeps every integral inside the cone at every prefix (L3.4) — so
    # a negative reaching this raise marks an executor bug, and the raise is the tripwire
    # proving the executor kept its promise. The question M1 could not answer is not
    # given a meaning; it is made unaskable, and this is the alarm if it is asked anyway.
    is_present = (
        (lambda a: S.multiplicity(a) > 0) if is_bag_semiring(S) else (lambda a: a != S.zero)
    )
    present = {_key_of(row, keys) for _, row, annotation in right._items() if is_present(annotation)}
    slot = slots[0] if slots else None
    witness = Why.of([right.content_address()]) if slot is not None and len(right) > 0 else None
    acc: Merged = {}
    for key, row, annotation in left._items():
        if _key_of(row, keys) in present:
            continue
        if witness is not None:
            annotation = _conjoin_witness(S, slot, annotation, witness)
        acc[key] = (row, annotation)
    return _finish("anti_join", left, left.schema, acc, carried, [], operators)


def aggregate(
    rel: Any, by: Iterable[str], monoid: Monoid, value_of: Callable[[dict], Any], into: str
) -> Outcome:
    taken = _take("aggregate", rel)
    if isinstance(taken, Quarantine):
        return taken
    (source,), carried, operators = taken
    keys = _columns("aggregate", by, "by")
    if not isinstance(monoid, Monoid):
        raise OperatorError(
            f"aggregate: {monoid!r} is not a tannen.kernel.algebra.Monoid — declare the algebra "
            "with its witnesses (§4.3, BRIEF §5.6)"
        )
    _callable("aggregate", value_of, "value_of")
    if not isinstance(into, str) or not into:
        raise OperatorError("aggregate: into must be a non-empty column name")
    if into in keys:
        raise OperatorError(f"aggregate: into {into!r} collides with by {keys!r}")
    _in_schema("aggregate", keys, source)
    S = source.annotations
    if not is_bag_semiring(S):
        raise OperatorError(f"aggregate: {S.name} declares no bag structure (docs/specs/m1.md §2.1)")
    schema = tuple(sorted(keys + (into,)))
    groups: dict[tuple[bytes, ...], list[tuple[dict, Any, Any]]] = {}  # insertion = canonical order
    bad: list[dict] = []
    for _, row, annotation in source._items():
        try:
            value = value_of(dict(row))
        except Exception as exc:
            bad.append(_quarantine_row("aggregate", row, exc))
            continue
        groups.setdefault(_key_of(row, keys), []).append((row, annotation, value))
    acc: Merged = {}
    for members in groups.values():
        values = [v for _, ann, v in members for _ in range(S.multiplicity(ann))]
        total = members[0][1]
        for _, ann, _ in members[1:]:
            total = S.add(total, ann)
        try:
            folded = monoid.fold(values)
            out = {**{k: members[0][0][k] for k in keys}, into: folded}
            key = encode_canonical(out)
        except Exception as exc:  # a fold that fails, or a value with no canonical form
            bad.extend(_quarantine_row("aggregate", row, exc) for row, _, _ in members)
            continue
        _put(acc, S, key, decode_canonical(key), S.collapse(total))
    return _finish("aggregate", source, schema, acc, carried, bad, operators)
