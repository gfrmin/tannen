# The freeze gate proves the laws do not run, not that they could ever pass

**Status: proposed, scheduled for M2 (decision D0094). Not binding.** Written at the M1
laws freeze, immediately after D0093 found an unsatisfiable axiom in an already-frozen law
file. It generalises that defect rather than restating it.

## The hole

BRIEF §8's frozen-oracle protocol freezes a milestone's laws before its implementation
exists, so the implementation cannot be written to fit weakened laws. The price is that
**every law is a skip at the moment it becomes unrewritable**:

```
$ uv run pytest tests/laws/m1 -q
12 skipped in 0.10s
```

That output is byte-identical whether the laws are correct, mutually contradictory, or
nonsense. Session A's completion check — "every law a SKIP, zero passes, zero errors"
(`docs/specs/m1.md`, the Session A plan) — is a check that the laws **do not run**. Nothing
anywhere checks that they **could ever pass**.

D0093 is what that hole produces: `test_l1_2_multiplicity_axioms` asserted
`(multiplicity(a) > 0) == (a != zero)`, which is unsatisfiable for any product semiring and
directly contradicted another test twelve lines below it in the same file. Both were frozen
into `MANIFEST.sha256` in the same commit. The gate was green throughout.

## Why the existing guards could not catch it

- `check_manifest.py` verifies frozen bytes are unchanged. Bytes, not meaning.
- `tannen laws report` reports evidence freshness for descriptors. A pending milestone
  (D0090) has no evidence by definition, so there is nothing to be fresh or stale.
- `check_decisions.py` resolves bindings. A `manifest:` binding resolves iff the row
  exists — again, bytes.
- pytest collects the module and skips it at `importorskip`, before any assertion runs.

Each guard is doing its job. None of them is a satisfiability check, because none was ever
meant to be.

## What the repo already does right, twice, without generalising it

1. **`tests/laws/m1/_fragment.py`** is a reference oracle frozen beside the laws that
   imports nothing from tannen. L1.16 is differentially checked against DuckDB through it —
   so exactly one M1 law family has an independent model, and it is not the family that
   broke. The pattern exists; it was not applied to the algebra.
2. **`unenforced_reason`** makes a decision record's missing binding *visible and counted*,
   and D0044's ratchet forces the count down. Laws have no equivalent field, so "nobody
   validated this law family" is not merely unenforced — it is unrepresentable, and
   therefore silent.

The proposal below is those two mechanisms, applied to laws.

## The proposal

### 1. Freeze a model beside the laws

Each algebraic law family gets `tests/laws/<milestone>/_model.py`: a naive, self-contained
transcription of the spec's definitions, frozen inside the seal. D0089 already settles both
the location and the precedent — shared law helpers are frozen inside the seal, not parked
outside it — so this needs no new mechanism.

The model is **not** the implementation and must not become it:

- it imports nothing from `tannen`, exactly as `_fragment.py` does not;
- it may be naive, quadratic, and partial, because nothing ships it;
- Session B may not import it, and the seal already prevents adding anything beside it.

The one written ad hoc for D0093 was ninety lines and found the defect on its first run.

### 2. The freeze gate gains a second assertion

Today Session A's gate is *every law SKIPs against the package*. It becomes:

| | against the package | against the model | against a stated mutant |
|---|---|---|---|
| model-checked law | SKIP | **PASS** | **FAIL** |
| machinery law | SKIP | — | — |

The mutant half is D0092's discipline generalised: a law that passes against a deliberately
broken model is not testing what it claims. It is the same argument that made the
receipt-clock regression test worth rewriting — pass-before/fail-after is the only evidence
that an assertion discriminates. Both halves would have caught D0093 immediately: the
corrected axiom passes against the model exhaustively over a 45-element product domain, and
the frozen one fails on twelve of those elements.

### 3. Make the gap countable

Every frozen law file declares one of:

```yaml
validated_by: tests/laws/m1/_model.py      # and a recorded pass/mutant-fail transcript
validation_reason: >-                       # why this family cannot be model-checked
  L1.11 is about the quarantine machinery; a model of it would BE the implementation,
  which is what the A/B separation exists to prevent.
```

`scripts/check_laws.py` fails any law file under a sealed milestone directory carrying
neither. **`unvalidated` then joins `unenforced` and `residue` as a ratchet metric** in the
digest, and must trend down like the others.

This is the load-bearing part, and it is the part that would have caught D0093 with no
cleverness at all. The Session A plan listed three executed pre-freeze validations —
antichain-`Why` as a commutative semiring (L1.1), 22 shapes against DuckDB (L1.16), and the
sibling-import probe. `BagSemiring` was introduced in the same plan's Call 2 and no
validation covered it. Under rule 3, `test_l1_semiring.py` would have been forced to declare
a `validation_reason` for L1.2, and **there is no honest one to write** — the family is pure
algebra over finite domains, the single easiest thing in the milestone to model-check.

### Scope, stated honestly

Not every law is model-checkable. L1.11 (quarantine), L1.12 (the registry), L1.13–L1.14
(derivation identity and the rebuilders), L1.15 (replay) and L1.17 (the harness subject) are
about machinery; a model of them is the implementation, and writing it in Session A destroys
the adversarial separation the protocol exists for. Those declare a reason. The rule does
not make them safe — it makes their unsafety **counted** instead of invisible, which is the
same bargain `unenforced_reason` strikes and the reason that field works.

Candidates for M2, on this reading: L2's semiring/provenance laws are model-checkable; the
executor and store laws are not.

## What this does not fix

A model that is wrong in the same way the law is wrong catches nothing. Two mitigations,
neither complete: the model is transcribed from the **spec** rather than from the law, so it
takes a second independent error to line up; and the mutant requirement means a law that
asserts nothing at all still fails, because it passes against the mutant too. D0093 itself
is evidence the first mitigation bites — the spec's §2.1 axiom list was correct, and it was
the law that had drifted from it.
