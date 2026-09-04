"""tannen on the stand — the IMPLEMENTATION half of M3's delta-executor laws
(docs/specs/m3.md §9). FROZEN at m3-laws-freeze.

`_delta_model.py` holds the checks; this file is the adapter that puts the shipped package
behind the same interface, so one assertion text runs against both.

`pytest.importorskip("tannen.incremental")` is M3's SENTINEL — the module M3 introduces.
While it does not exist, M3 is unimplemented and every law here is a visible skip; the
model half runs unconditionally from `tests/test_law_validation.py`, so the assertions
are exercised at every commit including the freeze commit. `tannen.kernel.delta` is
importorskip'd too: it is also new at M3, and an adapter that errored on it instead of
skipping would turn the pre-implementation suite red for the wrong reason.

This adapter is written against docs/specs/m3.md §1's package surface BEFORE Session B
implements it — that is the frozen-oracle protocol working as designed, and it is the
same bet `_subject.py` made at M2 (its m3 name is `_delta_subject.py`) with `tannen.sources`. The names pinned here:

  tannen.kernel.delta.negate(rel) -> Rel
  tannen.kernel.delta.diff(new, old) -> Rel
  tannen.kernel.delta.apply(base, delta, dead) -> Rel        (§3.3's pinned order)
  tannen.kernel.delta.join_delta(a_old, a_new, d_a, b_old, b_new, d_b, on) -> Rel
  tannen.kernel.delta.group_aggregate_delta(in_old, in_new, by, group, value_of,
                                            into, out_old) -> Rel
  tannen.kernel.semiring.why_slots(S) -> tuple of paths (tuples of "left"/"right")

TannenSubject deliberately does NOT subclass `_model.Subject` — the `REQUIRED` check
below is what replaces inheritance (the m2 rule, verbatim).
"""

from __future__ import annotations

from typing import Any

import pytest

incremental = pytest.importorskip(
    "tannen.incremental",
    reason="M3 delta executor not implemented yet (law suite frozen ahead of Session B)",
)
delta_mod = pytest.importorskip("tannen.kernel.delta")
ops = pytest.importorskip("tannen.kernel.ops")
rel_mod = pytest.importorskip("tannen.kernel.rel")
semiring = pytest.importorskip("tannen.kernel.semiring")
algebra = pytest.importorskip("tannen.kernel.algebra")
outcome = pytest.importorskip("tannen.kernel.outcome")

import _delta_model as M  # noqa: E402  (the model half, frozen beside this file)

Rel = rel_mod.Rel
RelError = rel_mod.RelError
SemiringError = semiring.SemiringError
OperatorError = outcome.OperatorError
Why = semiring.Why

#: The one monoid and the one group these laws fold with, law-checked at construction
#: (BRIEF §5.6). The group is L3.8's subject: its declared `inverse` is what the
#: subtractive aggregate leans on, and M3 is the first consumer `AbelianGroup` has had.
SUM = algebra.Monoid("sum", lambda a, b: a + b, 0, witnesses=tuple(range(-12, 13)))
SUM_GROUP = algebra.AbelianGroup(
    "sum", lambda a, b: a + b, 0, lambda a: -a, witnesses=tuple(range(-12, 13)))

_SEMIRINGS = {"Z": semiring.Z, "B": semiring.B, "Why": semiring.Why}


def _semiring_of(spec: Any) -> Any:
    if isinstance(spec, tuple) and spec[0] == "product":
        return semiring.product(_semiring_of(spec[1]), _semiring_of(spec[2]))
    return _SEMIRINGS[spec]


def _element_of(spec: Any, value: Any) -> Any:
    """A model-shaped nested annotation crosses to tannen unchanged: `Why` elements are
    antichains of frozensets on both sides (m2 pinned the coincidence), products are
    tuples on both sides."""
    return value


class TannenSubject:
    """The shipped package behind `_model.Subject`'s interface."""

    name = "tannen"
    refusal = RelError
    cone_refusal = SemiringError

    def rel(self, schema: Any, pairs: Any) -> Any:
        return Rel(schema, [(row, (count, Why.of(*why))) for row, (count, why) in pairs])

    def ingest(self, schema: Any, entries: Any) -> Any:
        return Rel(schema, [(row, (count, Why.of({atom}))) for row, count, atom in entries])

    def source_delta(self, schema: Any, entries: Any) -> Any:
        return Rel(schema, [(row, (count, Why.of({atom}))) for row, count, atom in entries])

    def read(self, r: Any) -> dict:
        return {tuple(sorted(row.items())): annotation for row, annotation in r}

    def bag(self, r: Any) -> list:
        return sorted(r.to_bag(), key=repr)

    def address(self, r: Any) -> str:
        return r.content_address()

    def select(self, r: Any, predicate: Any) -> Any:
        return ops.select(r, predicate).unwrap()

    def project(self, r: Any, columns: Any) -> Any:
        return ops.project(r, tuple(sorted(columns))).unwrap()

    def map_rows(self, r: Any, f: Any, schema: Any) -> Any:
        return ops.map_rows(r, f, schema).unwrap()

    def union(self, a: Any, b: Any) -> Any:
        return ops.union(a, b).unwrap()

    def join(self, a: Any, b: Any, on: Any) -> Any:
        return ops.join(a, b, tuple(sorted(on))).unwrap()

    def distinct(self, r: Any) -> Any:
        return ops.distinct(r).unwrap()

    def anti_join(self, a: Any, b: Any, on: Any) -> Any:
        return ops.anti_join(a, b, tuple(sorted(on))).unwrap()

    def aggregate_sum(self, r: Any, by: Any, column: str, into: str) -> Any:
        return ops.aggregate(r, tuple(sorted(by)), SUM, lambda row: row[column], into).unwrap()

    # -- the delta calculus (tannen.kernel.delta, docs/specs/m3.md §3–§4)

    def negate(self, r: Any) -> Any:
        return delta_mod.negate(r)

    def diff(self, new: Any, old: Any) -> Any:
        return delta_mod.diff(new, old)

    def apply(self, base: Any, delta: Any, dead: Any) -> Any:
        return delta_mod.apply(base, delta, frozenset(dead))

    def join_delta(self, a_old: Any, a_new: Any, d_a: Any, b_old: Any, b_new: Any,
                   d_b: Any, on: Any) -> Any:
        return delta_mod.join_delta(a_old, a_new, d_a, b_old, b_new, d_b,
                                    tuple(sorted(on)))

    def aggregate_subtractive(self, in_old: Any, in_new: Any, by: Any, column: str,
                              into: str, out_old: Any) -> Any:
        return delta_mod.group_aggregate_delta(
            in_old, in_new, tuple(sorted(by)), SUM_GROUP, lambda row: row[column],
            into, out_old)

    # -- the contagion rule (§4, §7). The adapter is `run_ticks`'s caller-side policy,
    # and the rule is the spec's: a node replays iff an anti_join lies at or below it.
    # The shipped executor's own embodiment of the rule is L3.15's business.
    def replays(self, plan: Any) -> bool:
        def contains_anti(p: Any) -> bool:
            if not isinstance(p, tuple):
                return False
            if p[0] == "anti_join":
                return True
            return any(contains_anti(part) for part in p[1:])
        return contains_anti(plan)

    # -- the doors (§2.2, §2.3)

    def why_slots(self, spec: Any) -> tuple:
        return tuple(semiring.why_slots(_semiring_of(spec)))

    def unwitnessed_refused(self, spec: Any, position: tuple) -> bool:
        s = _semiring_of(spec)
        annotation = _element_of(spec, M.poke_empty_why(M.spec_one(spec), position))
        try:
            Rel(("k",), [({"k": 1}, annotation)], annotations=s,
                annotations_reason="M3 door law: probing the witnessed-row refusal")
        except RelError:
            return True
        return False

    def anti_join_multi_why_refused(self, spec: Any) -> bool:
        s = _semiring_of(spec)
        one = _element_of(spec, M.spec_one(spec))
        reason = "M3 door law: probing anti_join over a multi-Why semiring"
        a = Rel(("k", "x"), [({"k": 1, "x": 1}, one)], annotations=s,
                annotations_reason=reason)
        b = Rel(("k", "y"), [({"k": 2, "y": 1}, one)], annotations=s,
                annotations_reason=reason)
        try:
            ops.anti_join(a, b, ("k",)).unwrap()
        except OperatorError:
            return True
        return False

    def encode_rejects_non_ref(self) -> bool:
        try:
            Why.encode(frozenset({frozenset({"not-a-ref"})}))
        except SemiringError:
            return True
        return False


TANNEN = TannenSubject()

_missing = [name for name in M.REQUIRED if name not in vars(TannenSubject)]
assert not _missing, (
    f"TannenSubject does not define {_missing} — it does not inherit from _model.Subject "
    "on purpose, so a missing method is a hole here and never a silent fallback to the model"
)
