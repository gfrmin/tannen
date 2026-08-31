"""tannen on the stand — the IMPLEMENTATION half of M2's provenance laws
(docs/specs/m2.md §9). FROZEN at m2-laws-freeze.

`_model.py` holds the checks; this file is the adapter that puts the shipped package
behind the same interface, so one assertion text runs against both. Splitting them is what
lets `tests/test_law_validation.py` run every check against the model and its mutants
without importing tannen at all (D0094 §2).

`pytest.importorskip("tannen.sources")` is M2's SENTINEL. M1's package is importable
already, so a law that touched only `tannen.kernel` would RUN at the freeze commit and
fail — the frozen-oracle protocol needs it to skip until the milestone exists. The
sentinel is the module M2 introduces: while there is no `tannen.sources`, M2 is
unimplemented and every law here is a visible skip. It is NOT a check that cannot fail —
the model half runs unconditionally from `tests/test_law_validation.py`, so the assertions
are exercised at every commit including this one.

TannenSubject deliberately does NOT subclass `_model.Subject`. Inheriting would make a
forgotten method silently fall back to the model, and the law would then report the model
passing while wearing tannen's name — the exact vacuous green
`docs/proposals/2026-08-29-a-check-that-cannot-fail.md` catalogues. The `REQUIRED` check
below is what replaces inheritance.
"""

from __future__ import annotations

from typing import Any

import pytest

sources = pytest.importorskip(
    "tannen.sources",
    reason="M2 sources not implemented yet (law suite frozen ahead of Session B)",
)
ops = pytest.importorskip("tannen.kernel.ops")
rel_mod = pytest.importorskip("tannen.kernel.rel")
semiring = pytest.importorskip("tannen.kernel.semiring")
algebra = pytest.importorskip("tannen.kernel.algebra")

import _model as M  # noqa: E402  (the model half, frozen beside this file)

Rel = rel_mod.Rel
RelError = rel_mod.RelError
Why = semiring.Why

#: `aggregate` accepts only a law-checked algebra (BRIEF §5.6), so the fragment's one
#: monoid declares its witnesses here rather than being conjured at the call.
SUM = algebra.Monoid("sum", lambda a, b: a + b, 0, witnesses=tuple(range(-12, 13)))


class TannenSubject:
    """The shipped package behind `_model.Subject`'s interface."""

    name = "tannen"
    refusal = RelError

    def rel(self, schema: Any, pairs: Any) -> Any:
        # Model annotations are already `(int, antichain of frozensets of refs)` — the
        # in-memory shape of a ZxWhy element — so they cross unchanged. That the two
        # representations coincide is not luck: §2 pins the encoding of both.
        return Rel(schema, [(row, (count, Why.of(*why))) for row, (count, why) in pairs])

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


TANNEN = TannenSubject()

_missing = [name for name in M.REQUIRED if name not in vars(TannenSubject)]
assert not _missing, (
    f"TannenSubject does not define {_missing} — it does not inherit from _model.Subject "
    "on purpose, so a missing method is a hole here and never a silent fallback to the model"
)
