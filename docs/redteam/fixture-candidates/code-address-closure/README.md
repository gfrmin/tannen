# Fixture candidate — one source, two closures, one node (RT-M4-04)

**Finding:** RT-M4-04 (`docs/redteam/2026-09-12-m4-boundary.md`), medium; inherited from M1.
**Status: DRAFT, no guard exists yet — do not install.**

RT-M3-01's remedy addresses the code a `DeltaNode` names by its SOURCE TEXT
(`_code_address` → `transform.source_text` → `inspect.getsource`). That is blind to a closure's
captured environment, and the same blind spot is in M1's `@transform` (`transform.py:76`). No
existing guard catches it — frozen L4.23 exercises only bodies with distinct source, and the
unfrozen `test_a_map_out_schema_is_part_of_the_declared_node` twin likewise. The guard this
fixture would poison — a closure-aware code address, or a refusal of an un-addressable closure —
does not exist. Its shape is a design question (report §RT-M4-04).

## What the fixture must demonstrate

A pipeline module defining a closure factory (so `inspect.getsource` succeeds — the finding is
invisible from a heredoc, where stdin source is unrecoverable and the closure is refused like a
lambda; see the report's methodology note):

```python
def make(limit):
    def predicate(row):          # named, not a lambda — lambdas are already refused
        return row["x"] < limit
    return predicate
```

Registering `make(10)` and `make(99)` under one predicate name in two sessions must be caught:
they compute differently, yet `source_text` and `_code_address` are identical
(`sha256:601a3a00…`) and the `DeltaNode` descriptor collides (`sha256:adfd307d…`), so the trace
serves the first's answer to the second with `rebuilt=False`. The fixture asserts the guard either
folds the closure's (canonical-encodable) captures into the address, making the two nodes distinct,
or refuses a closure whose captures are not addressable — the way a lambda is refused.

Positive control: two plain named functions with genuinely different source must still be two
nodes and must NOT be refused, so the guard does not become "refuse every closure" by accident.

## Why it can't be a fixture yet, and a note on scope

`__closure__` cells can hold objects with no content address, so the remedy is not a builder
one-liner. It touches unfrozen `src/tannen/incremental.py` AND `src/tannen/transform.py` (the
shared M1 blind spot), and frozen L4.23 does not cover the case — a superseding law is likely
wanted. Because the flaw is M1-inherited and undocumented, the decision record that closes it
should note it in both `transform.py` and the specs, not only `incremental.py`. When the guard
lands, this fixture installs as usual (owner-key, Tier-C `trust-root-changes`).

## Owner review (D0246)

**The obligation runs the other way (A4).** A drafted fixture enforces nothing (D0143), so the
obligation to install this one sits on the decision record that closes RT-M4-04 (the closure-aware
code address, or a refusal of an un-addressable closure): **that record must account for this
candidate**, not this draft.
