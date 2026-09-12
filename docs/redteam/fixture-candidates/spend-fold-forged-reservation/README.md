# Fixture candidate — spend-fold forged reservation/capture (RT-M4-01)

**Finding:** RT-M4-01 (`docs/redteam/2026-09-12-m4-boundary.md`), high, inert today.
**Status: DRAFT, no guard exists yet — do not install.**

A poison fixture must FAIL against the guard it poisons (BRIEF §9.1). The guard this fixture
would poison — one that authenticates the `reservation/1`/`capture/1` values SpendGuard's fold
reads, so a value written by the pipeline through the public `Oracles.store` property cannot be
mistaken for one the `Oracles` context minted — **does not exist**. A fixture belongs with its
guard, not ahead of it (the RT-M3-02 lesson, D0174). So this directory records what the fixture
must prove, against the day the pre-budget sitting decides how to close RT-M4-01.

## What the fixture must demonstrate

Two payloads, both reproduced in the report against a throwaway store with an in-memory budget
(`budget.yaml` untouched, every ceiling zero):

1. **Ceiling erosion.** A reservation whose capture never wrote (a failed transport) is charged
   its `worst_case` by the honest fold. Planting a `capture/1` that agrees on `_SETTLES`
   `(kind, oracle, input_key, scope, unit)` and carries `price: 0` makes `spent()` read 0 for that
   reservation — `settled[ref] = 0` replaces the worst-case fallback — so a call the ceiling would
   deny is admitted. The fixture asserts the guard REFUSES to fold a capture the Oracles context
   did not mint.

2. **Irreversible scope denial.** A `reservation/1` whose `worst_case` is not a non-negative
   integer makes `spent()` raise `SpendDenied` for the whole scope, permanently (write-once
   store). The fixture asserts the guard either rejects such a value at the fold or never admits it
   to the store's spend namespace.

## Why it can't be a fixture yet, and what it waits on

The remedy is a design question, not a builder one-liner (report §RT-M4-01): making a fold input
unforgeable in a store the pipeline must also write to, without a secret the pipeline lacks, needs
one of — a reservation namespace the pipeline cannot write, a separate reservation store, or a
signed fold. The pre-budget sitting BRIEF §9.1 mandates is where that is decided, because it is
the moment a nonzero ceiling first makes the hazard live. When the guard lands, this fixture is a
`git mv` into `tests/poison/`, a manifest row per file, a `poison` line in `scripts/custodian.sh`,
and a `tests/poison/README.md` row (owner-key, Tier-C `trust-root-changes`).

`src/tannen/oracles/context.py` is unfrozen and uncustodied; frozen L4.5
(`tests/laws/m4/test_l4_spend.py`) constrains only the honest reserve-then-settle path, so an
input-authentication guard neither edits it nor contradicts it.
