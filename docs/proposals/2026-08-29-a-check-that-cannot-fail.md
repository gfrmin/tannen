# Proposal: BRIEF §5 gains a twelfth entry — a check that cannot fail is not a check

**Status:** queued for the owner (D0116). `BRIEF.md` is frozen and custody-set; the
builder drafts, the owner applies and regenerates the manifest row. Additive only — no
existing entry changes. §5 is not a Tier-C door (those are §3 and §10), so this is an
owner-applied amendment, not a door request.

## The class

An artifact whose value is that it *fails* when something is wrong, and which cannot fail.
It reads as green, and the green is produced by something other than the property it
claims to check. Absence of a signal gets read as presence of the property.

This is not a hypothetical hazard. It is **the dominant defect class in this repository**,
and the instances were each found by a different accident rather than by any mechanism:

| # | Artifact | Why it could not fire | Found by |
|---|---|---|---|
| D0093 | frozen law `test_l1_2_multiplicity_axioms` | axiom unsatisfiable for any product semiring — could never *pass* | writing a throwaway model by hand |
| D0114 | frozen law `test_l1_9_..._non_negative_cone` | generator draws `min_value=1` and no operator subtracts — could never *fail* | reasoning about an unrelated fix |
| D0091 | the ratchet tests | debt borrowed from the live repo; silent once it hit zero | the debt hitting zero |
| RT-10 | `bindings[]` generally | a binding resolves by pointing at anything that exists | red team |
| D0106 ① / D0049 | one binding | a missing newline folded it into a sibling's prose; still valid YAML, still resolving | a hand YAML parse while scripting a sitting |
| D0108 | CLAUDE.md's `lint-imports` line | no `--config`, so it reads zero contracts; "passes vacuously" is in its own title | running the documented command |
| D0112 ① | `tests/test_no_pii.py` | the detector's input set (`git ls-files`) excluded the detector, which was untracked | the sitting rehearsal's post-commit gate |
| D0112 ② | that detector's headline assertion | filter built from `{kind for _, kind in pairs}` — backwards unpack, so it held `Pattern` objects and matched no kind | asking why a failure report named two failures and not three |
| D0112 ④ | the regression test for D0112 ③ (fixtures whose `git -C <tmp>` wrote to the real index under a hook) | its reproduction exported `GIT_WORK_TREE` too, which a hook does not, sending `add -A` back at the victim's own tree so the fixture's file was never reached | **removing the fix and watching the test, per D0111** |

Seven of the nine are in artifacts written *to close* an earlier instance of the same
class. D0112 ② is the sharpest for showing the machinery's blind spot: its decision record
declared the binding `strength: enforced`, and `check_decisions.py` was fully satisfied —
the test existed, collected, and passed. It simply could not fail.

D0112 ④ is the sharpest for the opposite reason, and it is the argument for the mechanism
below rather than for more care. It is one recursion deeper than any other row: a
regression test, written the same hour, by someone who had just spent a day on this exact
class, to close a defect *of* this exact class — and it was born unable to fail. Nothing
about knowing the pattern prevented it. What caught it was thirty seconds of mechanical
procedure: delete the fix, run the test, require red. The rate at which this class is
produced does not seem to fall with attention. Only the rate at which it is *caught* does,
and only when something forces the failure to be observed.

## Why the existing machinery cannot catch it

- `check_decisions.py` resolves a `pytest:` binding by collecting the node and confirming
  it is not skipped. A test that passes unconditionally satisfies that completely.
- `strength: enforced` is a **schema field with no verifier**. Its own description says the
  target "mechanically prevents or detects violation of this decision". Nothing checks that
  claim; the author asserts it and the guard records it.
- `unenforced_reason` and D0044's ratchet count bindings that are *absent*. A binding that
  is present and inert is counted as enforced — the metric moves the wrong way when the
  defect appears.
- The frozen-oracle protocol proves a milestone's laws do not RUN before implementation
  (`docs/proposals/2026-08-26-law-validation-ratchet.md`). Nothing proves they could ever
  fail afterwards.

Each guard is doing its job. None of them is a vacuity check, because none was meant to be.

## Insert as §5 entry 12

```markdown
12. **A check that cannot fail is not a check.** Every artifact whose value is a failure —
    a law, a guard, a poison fixture, a `pytest:` binding recorded `enforced` — ships with
    the failure it detects: a fixture that violates it, a mutant it rejects, or a recorded
    transcript in which it actually failed. The failure is produced **at the layer that
    makes the claim**, not at a component beneath it: watching a scanner find a planted
    secret says nothing about the assertion that filters its output. A check's **input set
    is part of the check** — it asserts its own input is non-empty and contains the case it
    exists for, because the commonest way to be green is to have looked at nothing.
    `enforced` therefore means *watched failing*; a binding that cannot name its watched
    failure is `documentary`, which is an honest word and not a lesser one.
```

**Why it belongs in §5 rather than in a decision record.** §5's stated job is to make
violations *unwritable* rather than merely detectable, and the entries are all of the form
"the lazy path is the correct path" — raising is safe, lineage without asking, evidence is
automatic. This one is the same shape applied to the verification layer: the lazy path
today is to write an assertion, see green, and stop, and that path is indistinguishable
from success. Eight instances say the discipline does not survive as a habit. It has
survived as a rule everywhere the repo made it one (D0092's pass-before/fail-after
rewrite; D0111's fixture-driven detector tests; the poison corpus, which is exactly this
rule applied to the custodian).

## The mechanism, staged

Proposed for whoever implements it; **not applied here**, because it changes what an
existing schema field means across 273 bindings.

1. `bindings[]` gains an optional `watched_failing`: a pytest node id or fixture path
   demonstrating the bound artifact failing. `check_decisions.py` resolves it exactly as
   it resolves the binding itself.
2. Once backfilled, it becomes **required** for `strength: enforced`. Optional-first is
   D0106 ①'s own staging for `bindings_count`, and it keeps every existing record valid
   without a mass edit.
3. `unwatched` joins `unenforced` and `residue` as a digest ratchet metric.

**BRIEF §9.1's metric-calibration rule governs step 3**: land the measurement, publish one
digest carrying true values, and only then ratchet — otherwise the baseline is set in the
state where nothing has been measured and the first honest count reads as a breach.

**Its limit, stated rather than discovered later.** `watched_failing` can point at anything
that resolves — RT-10, one level up. It does not prove the watch is real. What it does is
convert silence into a claim, which is the bargain `unenforced_reason` already strikes, and
the repo's own evidence is that the bargain works: a claim someone has to write is a claim
someone can read and dispute, and "there is no honest reason to write here" is exactly what
made D0093's absence visible in the ratchet proposal.

## What this does not fix

A fixture that is wrong in the same way the check is wrong catches nothing — the mutant
half of the law-validation ratchet is the same bargain and carries the same hole. And
nothing here reaches the case where the *specification* is wrong and the check faithfully
enforces it. This closes "green for no reason", not "green for the wrong reason".
