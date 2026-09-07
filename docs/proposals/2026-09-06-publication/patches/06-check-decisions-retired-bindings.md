# Patch 06 — a file binding can be broken by a legitimate deletion, and the record is immutable

**Status: drafted as `06-check-decisions-retired-bindings.patch`, not applied.** Touches
`scripts/check_decisions.py` and `governance/schemas/decision-record.schema.json`, both
custody-set; the driver applies it at step 2 under your confirmation (D0183). Filed by
D0181; watched in every direction in a scratch clone against the real D0115/D0181 pair —
red without a retirement, green with `retired: D0115 <- D0181` printed, red on a stale
retirement, on a wrong target, on a non-accepted retiring record, on an enforced binding.

**This one is not optional if the sitting is to finish.** Runbook step 5 deletes the
sibling snapshots. D0115 — owner-signed, `accepted` — binds to one of them by path. The
moment step 5 runs, `check_decisions` goes red and **stays** red, because D0045 makes
D0115's fields immutable and `binding_violation` has no escape hatch:

```python
if kind == "file":
    return None if (root / target).exists() else f"target does not exist: {target}"
```

Without this patch the sitting reaches step 9 (`make verify` on the rewritten history) and
cannot pass it. That is a step-order defect of exactly the kind D0068 exists to catch, and
it was found the cheap way — by executing the ruling early — rather than at the keyboard
with the owner's key out.

## Observed

```
check_decisions: FAIL (4 violation(s))
  - decisions/0115-publish-the-repository-tier-c-door-external-bytes.yaml: binding does not
    resolve — target does not exist: concepts/snapshots/provenance-ref-grammar/renavon-adr-002.md
  - decisions/0063-conferral-rulings.yaml: binding does not resolve — pytest node fails:
    tests/test_governance_scripts.py
  - decisions/0177-...: binding does not resolve — pytest node fails:
    tests/test_governance_scripts.py::test_check_passes_on_real_tree
```

Three of the four are one fault. `tests/test_governance_scripts.py::test_check_passes_on_real_tree`
runs `check_decisions` against the real tree, so the dangling binding fails the test, and
the test failing breaks the two records that bind to it. **A dangling file binding takes
down every record bound to the governance test suite** — the blast radius is not one record.

## The mechanism

A new optional top-level field. The retirement is itself a record, so the deletion stays
auditable instead of becoming an exception baked into a guard:

```yaml
retires_bindings:
  - record: D0115
    target: concepts/snapshots/provenance-ref-grammar/renavon-adr-002.md
    reason: >-
      Deleted by owner ruling of 2026-09-06 (D0180). The binding was documentary — it named
      where the blocker lived, and the blocker is what was removed.
```

`check_decisions` builds the index, and a `type: file` binding whose target is absent is
satisfied **iff** a retirement names exactly that `(record, target)` pair. Four constraints,
each there to stop the mechanism becoming the hole it patches:

1. **`documentary` bindings only.** Retiring an `enforced` binding is always a violation:
   an enforced binding is the record's claim on reality, and if reality moved, the owner
   re-issues the record. D0115's binding is `strength: documentary`, so the fix is available
   at exactly the strength where it is safe — checked, not assumed.
2. **The retiring record must be `accepted`.** A provisional or blocked record cannot
   quietly satisfy another record's binding.
3. **A retirement whose target still EXISTS is itself a violation** ("stale retirement").
   Otherwise retirements accumulate as dormant permissions, silently covering some *future*
   deletion of the same path — species I of D0116's taxonomy, arriving through the door
   built to fix species I.
4. **Every honoured retirement prints a line.** `retired: D0115 <- D0181 (target absent by
   ruling)`. A binding that resolves invisibly is a binding nobody audits.

Schema: add `retires_bindings` as an array of objects with `record` (`^D[0-9]{4}$`),
`target` and `reason` all required, `additionalProperties: false`.

## While reading this file, a second finding

`supersedes` is already in `decision-record.schema.json` — `{"type": "string", "pattern":
"^D[0-9]{4}$"}`. **No record uses it and no code reads it.** `grep -n supersedes
scripts/*.py` returns nothing; `grep -l '^supersedes:' decisions/*.yaml` returns nothing.
It is a governance mechanism that exists only as a schema key: a reader who found it would
reasonably conclude supersession is handled, and it is not. It would not have helped here
anyway — it is whole-record, and D0115 is not superseded; one of its four bindings points
at a path that no longer exists. Either wire it up or delete it; a declared mechanism that
does nothing is worse than an absent one, because it answers a question it cannot answer.

## Poison fixture

The first case — a dead binding with no retirement — is the existing `check-decisions/`
fixture (marker `binding does not resolve`), unchanged. The inverse is staged as **fixture
candidate 3**, `../fixture-candidates/check-decisions-retired-enforced/`: an accepted record
retiring another's `enforced` binding, which must be refused. Marker `only a documentary
binding may be retired`, watched biting. The driver installs it at step 4.

## Until it is applied

`check_decisions` is red on this one violation and its two knock-ons. D0181 records that,
names the expected failure set exactly, and states the check to run so a *new* failure is
still visible:

```sh
.venv/bin/python scripts/check_decisions.py 2>&1 | grep -c 'binding does not resolve'   # expect 3
```

Anything other than 3, or any violation that is not one of the three quoted above, is new
and is not covered by D0181.
