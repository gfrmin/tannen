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

## Four species, and only one of them is decidable

**Added 2026-08-30, after review.** The rows above are not one shape, and sorting them
decides which mechanism can find them. The sort is unflattering to the cheapest mechanism.

| | species | how it is green | decidable by inspecting the source? |
|---|---|---|---|
| **I** | **empty input** — the assertion never executes | zero iterations, or zero tests collected | **yes** — a computed collection with no non-emptiness guard is a syntactic pattern |
| **II** | **the input excludes the case** — non-empty, but the falsifying case is not drawable from it | the check looked at plenty of things, none of them the thing | no |
| **III** | **the assertion executes and cannot fail** — the predicate is not the property | incomparable types compared, a filter that matches nothing, an axiom no value satisfies | no |
| **IV** | **the check is never reached** — an early return or abort upstream of it | the loop is fine; control flow never arrives | no — it takes a run, and a run that reports what it examined |

Where the instances land: D0108, D0091 and D0106 ① are **I** (`lint-imports` with no config
reads zero contracts; the ratchet's debt list went empty; a missing newline folded a binding
out of the input). D0114 and D0112 ① are **II** (the generator cannot draw a negative; the
detector read 300 tracked files and was itself untracked). D0093, RT-10 and D0112 ② are
**III** (an unsatisfiable axiom; a binding predicate satisfied by anything that exists; a
`str` compared against a compiled `Pattern`). D0112 ④ is **II** at one remove — the
reproduction was over-specified, so the input it built was not the case the assertion was
about. Species **IV** has one instance and it is not in the table because it is not tannen's
code: life-agent's PII guard, borrowed for D0115's audit, returned exit 2 having scanned
**nothing** on its first two runs — a NUL byte in one tracked file trips a `return` above the
scan loop. Both runs were read as clean.

**The cost of that sort, stated plainly.** Of the four defects in D0112 — the guard written
*because* of this class — a species-I detector would have caught **none**, and ① is the
instructive one. Its loop over `tracked_files()` would indeed have appeared on the sweep's
unguarded list, so the sweep would have pointed at the right file. But the guard it asks
for is *proof the collection is non-empty*, and that collection held 309 files: the demand
is satisfied — `assert len(names) > 100` passes — and the test stays exactly as vacuous,
because the file under test was not among the 309. **Satisfying the detector would not have
fixed the defect**, which is a stronger statement than failing to flag it. ② had a
populated collection and an executing assertion comparing a `str` to a compiled `Pattern`.
③ was not an assertion problem at all: the fixtures wrote into the repository under test,
which is a different defect that happened to sit in the same file. ④ is species II. The one
species that can be swept mechanically is the one that has cost this repository the least.

The fix that did work on ① is a *membership* assertion, not a non-emptiness one —
`assert "tests/test_no_pii.py" in tracked_files()` — and no static rule could have named
that file, because which case a check exists for is not a syntactic property.

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
from success. Nine instances say the discipline does not survive as a habit. It has
survived as a rule everywhere the repo made it one (D0092's pass-before/fail-after
rewrite; D0111's fixture-driven detector tests; the poison corpus, which is exactly this
rule applied to the custodian).

## The mechanism, in the order the evidence supports

### First, and mostly: the negative control

**Remove the fix, run the check, require red.** Thirty seconds, at construction time.

This is what actually found D0112 ②, ③ and ④ — each of them in about that long, and none
of them by any other means. It is species-independent, and that is the whole of its value:
it does not ask what the check *looks at*, which is the question every static approach is
stuck with. It asks whether the check's **answer depends on the thing it claims to check**.
A check that stays green when its subject is broken has told you it is vacuous without you
having to work out which of the four species it is, or whether it is a species nobody has
named yet.

Formalising it is the staged change below. Proposed for whoever implements it; **not applied
here**, because it changes what an existing schema field means across 273 bindings.

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

### Second, and only second: a static sweep, where there is no fix to remove

Species I is syntactically decidable, so it can be swept. Two shapes:
`@pytest.mark.parametrize` over a *computed* collection (empty → zero tests collected →
green), and a `for` loop whose body asserts (empty iterable → zero assertions → green). For
each, the question is whether anything proves the collection non-empty — an `assert`, an
`assert len(...)`, an `if not X: raise`, or a visibly non-empty literal.

**Where this earns its place, and it is narrower than it first looks.** The negative control
needs a fix to delete. Some checks have none: a law frozen before its implementation exists,
or a guard whose subject is a vendored corpus. "Remove the fix" from
`tests/laws/m0/test_l0_encoding.py` means emptying `golden-vectors.json` — a frozen Grade-S
conformance file. There the syntactic question is the only cheap one available, and it is
worth having. Everywhere else it is a supplement, and per the cost note above it is a
supplement that would have caught none of the four defects in D0112.

**Run over this repository 2026-08-30**: 31 sites, 11 without a visible guard, of which 3
are detector limitations (literals it could not resolve), 1 is guarded from another file
(`test_conformance.py:51` iterates `record["sources"]`, which the concept-record schema pins
at `minItems: 1`), and 1 is by design (`KNOWN_DIVERGENCES`, which the sitting empties on
purpose). It rediscovered D0114 unaided, which is the calibration that makes the rest
believable. Two real findings survive, both in this document's appendix.

**Its own first pass reported 24 rather than 11**, because it recognised a guard spelled
`assert` and not one spelled `if not X: raise` — the disease, in the detector, on the first
run. If it is ever promoted to a standing test it must be watched failing and must assert
its own input set is non-empty, or it becomes the tenth row of the table above.

## What this does not fix

A fixture that is wrong in the same way the check is wrong catches nothing — the mutant
half of the law-validation ratchet is the same bargain and carries the same hole. And
nothing here reaches the case where the *specification* is wrong and the check faithfully
enforces it. This closes "green for no reason", not "green for the wrong reason".

## Appendix: what the 2026-08-30 sweep left standing

**A frozen Grade-S corpus loaded with no guard, beside one that has it.**
`tests/laws/m0/test_l0_encoding.py:26` loads `GOLDEN_VECTORS` from `golden-vectors.json`
and parametrises over it with no non-emptiness check. Its sibling
`tests/laws/m0/test_l0_evidence.py:23-26` carries exactly that check, spelled `if not
POSITIVE or not NEGATIVE: raise RuntimeError(...)`. An emptied or truncated vector file
turns L0.2's golden conformance into zero collected tests and a green run. Both files are
frozen, so this cannot be fixed in place — it is D0103's supersession question again, or a
non-frozen guard alongside. This is the case that justifies the sweep existing at all:
there is no fix here to remove.

**Two generators that draw the degenerate case far more often than anyone intended.**
`tests/laws/m1/_fragment.py` and `tests/test_provenance_homomorphism.py` both draw row
lists with `max_size` and no `min_size`, and the resulting empty-result rate on L1.16 runs
to 84% on one shape. The finding is real; the fix is **not** a floor assertion on a random
process, and it is not `min_size=1` either. It is generator shaping, it belongs to the M2
ratchet, and it is argued in `docs/proposals/2026-08-26-law-validation-ratchet.md` and
recorded as D0118. What that finding exposes underneath it — that an evidence record has no
field in which any of this could be visible — is D0117, and is the more important of the two.
