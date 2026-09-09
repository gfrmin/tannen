# M3 boundary sitting — proposals (opened at Session A, 2026-09-04)

This directory is the M3 sitting's staging area. It exists from the milestone's first
session because its absence is a recorded defect class: the M2 sitting's step 6 installs
the custodian by diffing against the *previous* milestone's proposals dir, and
`docs/proposals/2026-08-31-m2-boundary-sitting/` shipped no `custodian.sh` — so the step
printed "already applied — skipped" and the fixture the sitting itself installed never
got its poison line (D0152 item 6, the M1→M2 pass's single critical finding left
half-installed). The queue for the sitting is decision record **D0154**; the sitting's
driver is drafted near the boundary, as at M2 (D0143), and joins this directory then.

Nothing here enforces anything. Every file is a draft the owner installs (or declines)
at the sitting, under the owner's key — `scripts/custodian.sh` is custody-set,
author-key territory (BRIEF §9.1, CLAUDE.md hard rules).

## `custodian.sh` — the draft, hunk by hunk

The live `scripts/custodian.sh` plus seven delimited hunks (`--- M3 DRAFT HUNK n ---`),
each mapped to a D0154 queue item. Diff against the live file to review; the diff is the
hunks and this header, nothing else — measured, not asserted: `diff -u` against live
removes exactly seven lines, and each is a line some hunk replaces.

> **Rebased 2026-09-08 (D0196).** The 2026-09-04 draft was written against the
> pre-publication custodian. Installed verbatim at step 6 it would have reverted three
> publication-sitting changes — `FOUNDING_TAGS` to its pre-rewrite pin, the inline
> receipt-chain loop over D0176's delegation to `check_receipts.py`, and three `poison`
> invocations whose fixtures are still on disk. That last one compounds: hunk 1c would
> then have `bad`-ed three fixtures at **step 7**, where tolerances stop and the driver's
> `custodian --check-only || die` is unconditional. The sitting would have died in its
> irreversible middle over a floor its own new guard reddened.

| Hunk | D0154 item | Source record | What it does |
|---|---|---|---|
| 1a/1b/1c | (1) | D0152 item 6 | 1b adds the missing `poison` line for `tests/poison/oracle-shadow-model/` (RT-M2-01), invocation matching `tests/test_governance_scripts.py::test_oracle_shadow_model_fails_its_poison` — no `-I -P` (the attack **is** PYTHONPATH), `-B` (sealed-directory bytecode), no `-k` (the widened guard aborts at collection). 1a+1c add the derived half — D0152's named fix, D0095 half (2): `poison()` records which `tests/poison/` directories its invocations reach, and a completeness pass refuses any installed fixture no line exercises. Had it existed on 2026-09-03, the sitting would have failed loudly instead of finishing sooner.  **The success line is conditional, and that was not free:** the first spelling printed "every installed fixture is exercised" even on a run that had just reported an uncovered one — D0177's shape inside the guard written to close D0152's. Caught by running 1c against a fabricated orphan, not by reading it (D0196).  **1a also refuses a named fixture that is not on disk**, hunk 1c's mirror image: most guards return 0 over an absent tree, so before this the custodian announced "PASSED its poison fixture — the guard is weakened" when the corpus was simply short a directory. Found by adding hunk 5's invocation ahead of its fixture (D0199). |
| 2 | (2), third clause | D0152 item 3, D0177 | **Mostly landed already.** D0177 brought the live file to checking `ssh-keygen -Y sign`'s exit status and removing the receipt on failure, at the publication sitting. The remaining delta is two lines: the `.sig` is removed too (a stale signature must not outlive the file it signed), and the exit is non-zero — a half-written receipt left behind is what step 0 of the driver reads as a RESUMED sitting and skips its gate for (D0148 item 5), so this has to stop the run, not merely colour it. |
| 3 | (4) | D0146 item 2 | Excludes `__pycache__` from the step-2 `find`, matching `check_manifest.py`'s sealed-path rule, so a stray `.pyc` under `tests/poison/` no longer reddens the floor 37 minutes into `make verify` with a message that invites a manifest row for a gitignored file. |
| 4 | (3) | D0153 | The receipt's `previous receipt` line survives a same-day re-run: `prev` excludes the file being written, instead of `sort \| tail -1` picking the receipt itself and the guard dropping the line silently. **And a second defect found while rebasing (D0196): `prev_head` is never assigned anywhere in the live file** — its only occurrence is the `${prev_head:-…}` read, because the loop that set it was deleted when the chain check was delegated to `check_receipts.py`. Every receipt since records *no* previous HEAD; `receipts/2026-09-07.md` reads `at (none recorded)`. `check_receipts` parses only `- HEAD:`, so nothing noticed. The hunk now reads the previous HEAD from the chosen file. |
| 5 | (7) | D0154 item 7 | The `poison` line for `check_laws.py` — the only custody-set guard with neither a fixture nor an invocation (`grep check_laws scripts/custodian.sh` is empty in the live file), and the guard that decides whether a retired law still carries its claim forward. Its fixture is staged at `docs/redteam/fixture-candidates/check-laws-dropped-successor/` (D0199) and installs at **step 5**, before this file installs at step 6 — so until the sitting runs, this line correctly refuses. |

Driver territory rather than custodian territory, and **now drafted** — see
`boundary_sitting.sh` below and its own table: D0152 items 1 (the retarget guard testing
the pre-state), 2 (step 4f's skip-guard subset), 4 (no lock) and 5 (the installed fixture's
README prose); D0154 items 7 (the `check_laws` fixture, at step 5) and 9 (the stale "712
tests").

Two entries on the original list have moved since it was written. **D0154 item 6
(`required_tags` + `m3-laws-freeze`) is CLOSED** — the publication sitting added it at
`governance/tag-roles.yaml:47`, so no driver step offers it. **D0148 item 5's ordering
question is deliberately still not drafted**: D0148 says fixing it changes the order the
receipt-then-tag argument depends on (D0071), which is a judgement for the owner and not an
edit a builder should slip into a driver. D0154 item 8 (the `event()` schema follow-up)
stays deferred by D0171 ruling (4).

## What installing the `check_laws` fixture does to the real suite

`tests/poison/` holds deliberately broken trees — fixtures the custody guards are *run
against*, not tests. Nothing under it had ever matched `test_*.py`, so nothing was ever
collected and the question had never come up. Hunk 5's fixture is the first whose payload
does, and `pyproject.toml` sets `testpaths = ["tests"]` with no `python_files` override.

Measured in the kept rehearsal clone, with the fixture installed exactly as step 5 leaves it:
the real suite goes **842 nodes to 843**. The extra node is `test_l1_7_a_law_that_was_retired`,
whose body is a docstring — so it passes for free, permanently, while the file's own docstring
says it is "parsed statically and never executed".

**Renaming the payload out of `test_*.py` is the obvious fix and it is wrong.** It was drafted,
applied and reverted: `check_laws` finds law *definitions* by globbing `test_*.py`, so a
renamed tree defines no laws at all, and the fixture's documented positive control —
`successor: "L1.7"`, a law the tree *does* define, must return OK — flips to FAIL. The negative
case still fails, still printing the marker `which no law file defines` that the custodian
greps for, so the custodian would have gone on reporting `guard 'check_laws' fails its poison
as required` over a fixture that had quietly stopped testing the successor rule and started
testing "this tree contains no law files". One fixture, one reason, collapsed into a tautology
that still ticks green — and only the *positive* control could see it.

Fixed structurally instead: `norecursedirs` in `pyproject.toml` skips any `poison` directory.
Measured against the installed layout — 843 back to 842, exactly one node removed and none
added — so the driver's `VERIFY_ETA` figure of 842 is now true on both sides of the ceremony.
It costs a descriptor move (`pyproject.toml` is in `HARNESS_FILES`, so all 52 laws went STALE
and the evidence was regenerated) and it buys the class rather than the instance: the next
poison payload will be broken *on purpose*, and collecting one is a red suite that says nothing
about this repository. Recorded as D0200.

---

# `boundary_sitting.sh` — the M3 driver

> **READY — all five paths green, including the full non-FAST gate and the `--from head` run
> that finally executes step 0's precondition gate (2026-09-09).**
> Runs are not coverage (`docs/SITTING.md`): only a green run clears the driver. The two full
> rows ran with **no** `TANNEN_SITTING_FAST`, so every `make verify` leg and both rounds of
> commit hooks executed — **two** legs on every path, at steps 9 and 11. An earlier draft of
> this banner said the `--from head` row runs three; it does not, and the correction matters —
> see "step 0's gate establishes nothing" below. The three FAST rows say nothing about those
> legs and are kept because each one found a distinct defect.
>
> | Path | Verdict | Found |
> |---|---|---|
> | **full accept, no FAST** | **18/18 ok, RC=0, 144m43s** | step 5's guaranteed `check_decisions` failure reported as an anomaly; the poison payload collected by the real suite |
> | **`--from head`, full accept** | **20/20 ok, RC=0, 146m36s** | step 0's gate reports `check_manifest: FAIL` — the driver's own custody drift; and the harness rehearses the *M2* driver unless `TANNEN_REHEARSE_DRIVER` is set |
> | FAST accept | 19/19 ok, RC=0 | — |
> | FAST accept (first pass) | 1 FAIL | D0199's binding named the pre-move fixture path |
> | `--abort-at 19 --abort-step 9` | 10/10 ok, RC=0 | `die()` told a dirty tree it was clean |
> | `--answers n` | 8/8 ok, RC=0 | the verdict asserted a fully-declined sitting completes |
>
> Measured in the full run: driver exit 0 in **100 minutes**; two `make verify` gates at
> **18m12s** and **18m49s** (841 passed / 1 skipped / 1 xfailed each); zero
> `[TANNEN_SITTING_FAST] NOT RUN:` lines anywhere in the transcript; `m3-close` minted at step
> 10 and verified as `owner@tannen`; custody re-signed; the receipt taken before the tag.
> **The sitting makes TWO commits**, step 9's and step 11's, so budget two rounds of hooks.
> The `--from head` run costs 146m36s against the worktree run's 144m43s. That ~2 minutes is
> **not** an extra gate — it is step 0's aborted gate plus two more verdict checks. Measured
> from the stamped transcript: step 0's gate runs from elapsed second 0 to elapsed second 0.
> Its own two real gates ran **840 passed, 1 skipped, 1 xfailed** in 19m42s (step 9) and
> 18m25s (step 11) — 840 rather than the worktree run's 841 because `norecursedirs` now
> excludes the poison payload. That fix is visible in a verdict rather than argued for.
>
> Expected non-fatal lines, so a real anomaly stays distinguishable. On either decline path the
> driver prints `sitting: STOP — the tree is not clean…`, which is step 10's D0051 guard
> working. And on every accept path, step 5's `check_decisions` prints
> `FAIL (3 violation(s))`: step 5 installs a poison fixture, so the custody floor is red until
> step 7 re-signs it, and `DECISIONS.md` is stale until step 9 regenerates. The verdict does
> **not** simply tolerate that line — it is the same line D0199's binding defect surfaced on, so
> the harness asserts the block carries those three known violations and nothing else, and
> suppresses it only while that holds.
>
> On a `--from head` run there is a second such line, and only there: step 0's precondition
> gate prints `check_manifest: FAIL (1 violation(s))` naming `custody drift:
> scripts/boundary_sitting.sh`. The driver under test has just been copied over a custody-set
> member and is not re-signed until step 7, so the gate is correct and the driver answers
> `green except the custody set, which is this sitting's step 7 — continuing`. **The owner's
> own `cp` produces exactly this**, so it is what a real sitting shows. Same discipline: the
> harness asserts that drift is the *only* violation in the block and suppresses nothing else
> — a frozen-path violation there is a stop, not a note. Both tolerances now also say when
> they were **not** exercised, so a run that never reached the gate cannot report the same
> green as one that inspected a real block and found it clean.
>
> **THE COVERAGE GAP THE FIRST FOUR RUNS LEFT, AND HOW IT CLOSED — stated because a green run
> that skipped a step is not the same as one that ran it.** The first four runs above execute
> in `--from worktree` mode, which
> applies the working tree as a patch — a tracked modification — so step 0's clause (a) sets
> `RESUMED=1` on every one of them and the precondition gate is **skipped, not exercised**.
> Measured in each kept clone: the transcript carries "so this is a RESUMED sitting", never
> the gate offer. Closing it needs `--from head`, which clones a committed repo; head mode
> does not copy untracked files, so it can only run once this work is committed. That is also
> the order the owner will use, since a sitting starts from a committed tree.
>
> **`--from head` needs `TANNEN_REHEARSE_DRIVER`, and silently tests the wrong file without
> it.** In worktree mode the harness picks up the working tree's driver; in head mode it uses
> the *committed* `scripts/boundary_sitting.sh`, which is still byte-identical to the M2 copy.
> Measured: the first `--from head` attempt printed `driver under test:
> scripts/boundary_sitting.sh, unmodified since HEAD` and was rehearsing the M2 driver. The
> harness invokes it as `boundary_sitting.sh m3`, so `MILESTONE` is correct and only the
> `$PROPOSALS_M2` paths are wrong — which is D0152 item 6 exactly, and it could well have run
> green. The invocation that closes the gap is:
>
> ```
> TANNEN_REHEARSE_DRIVER=$PWD/docs/proposals/2026-09-04-m3-boundary-sitting/boundary_sitting.sh \
>     scripts/rehearse_sitting.sh --from head --answers y --keep
> ```
>
> Step 0's clause (a) filters `scripts/boundary_sitting.sh` out of its own dirty check for this
> reason, so the harness copying the driver in does not itself read as a resumed sitting.
>
> **Closed 2026-09-09** on `45f4dfe`: `RESUMED=0`, the gate ran, and running it is what
> surfaced the `check_manifest` line described above — a line no rehearsal had ever printed,
> because no rehearsal had ever reached the gate that prints it.

The committed `scripts/boundary_sitting.sh` is byte-identical to the M2 sitting's copy
(blob `ff043f9`, and `governance/custody.sha256:17` matches its bytes). The owner copies
this file over it as step 0 of D0154's queue; that `cp` is expected custody drift, tolerated
in `unexpected_failures()` by name until step 7 re-signs.

## What this copy changes versus the committed driver

Five of the rows below are defects the M2 sitting left behind. **Two of them would have
stopped this sitting**, and both were reproduced against the current tree rather than
reasoned about.

| Change | Why |
|---|---|
| `MILESTONE` default `m2` → `m3`; new `PROPOSALS_M3` | The milestone rolled. The old default is not cosmetic: `m2-close` exists, so an argument-less run sets `RESUMED=1` from step 0 clause (c), skips the precondition gate, and step 11 then finds both m2 tags already required and prints nothing — the silent-wrong-milestone failure its own comment warns about. |
| **Step 5's D0141 retarget guard tests the POST-state** | **D0152 item 1.** The guard asked whether D0141 still *mentions* the candidate path — and the replacement text this same block writes says "retargeted from `docs/redteam/fixture-candidates/oracle-shadow-model/`". It was satisfied by the sentence recording that the work was done, so it re-armed on its own success. Reproduced: the guard fires today, and its python then finds **0** matches for the text it means to replace, so `\|\| die` stops the sitting mid-step-5. That is where both of D0153's concurrent runs stopped. Now it asks whether the record *names the installed path*. |
| **Step 6 diffs against `$PROPOSALS_M3/custodian.sh`** | **D0152 item 6**, and at M3 worse than the skip it caused at M2. Measured: the live custodian and the M1 draft now differ, so the step takes the *else* branch and offers a draft **older** than what is installed — reverting `FOUNDING_TAGS` to its pre-rewrite pin, restoring an inline receipt loop D0176 delegated away, and deleting three poison invocations whose fixtures are still on disk. Hunk 1c would then redden those three at step 7, where tolerances stop. |
| **Step 4f's guard tests all three files its decline branch reverts** | **D0152 item 2, D0153 artifact 1.** The guard read `Makefile`; the revert wrote `Makefile`, `ci.yml` and `test_law_validation.py`. Any state where the first landed and the others did not read as "already applied" for ever — which is exactly the tree we are in, and why ci.yml's comment was lost by a concurrent run and never re-offered. The apply block is now per-file and idempotent, and refuses only a file in neither the pre- nor post-state. |
| **An `flock` on a lockfile keyed to the worktree** | **D0152 item 4.** A boundary sitting is a one-run ceremony and nothing said so. Two accidental concurrent runs produced all three of D0153's artifacts. FD 9 is held for the life of the process, so the kernel releases it on exit, `die`, or kill — there is no stale lock to clean up. A rehearsal clone has a different path and so a different lock. |
| `VERIFY_ETA` re-measured; `842 tests`, not `712` | **D0154 item 9.** The suite grew 18% since the promise was written, and D0069 is the reason it matters: an owner watching a still terminal against a stale promise concludes it hung and kills the driver, which has now happened twice. Step 0's "the gate takes the better part of a minute — 174 tests" is moved to the past tense rather than deleted: the failure it describes is forty times *easier* to hit now. |
| **New: a step breadcrumb at `$TANNEN_SITTING_SCRATCH/steps`** | `say()` appends every header it prints. A `die` is `exit 1` with no trap, so this is the only thing that can state how far a run got — to the owner, and to the harness, which must not learn the driver's state by parsing the driver's prose (BRIEF §2). Step 0's header is renamed `Step 0 — …` so an abort inside it is distinguishable from a run that wrote no breadcrumb. |
| **New: `die()` says where it stopped and what to undo** | Two regimes, and they differ either side of step 9's commit: after it the tree is clean and there is nothing to undo; before it every edit is in the working tree and the custody floor is RED by construction. An owner stopped mid-ceremony should not have to work out which one they are in. |
| **New: `TANNEN_SITTING_FAST=1`** | Every rehearsal to date cost one to two hours, which is why the abort path had never once been executed. This skips the three long gates and the commit hooks and runs every step in ~10 minutes. Each skip prints a `[TANNEN_SITTING_FAST] NOT RUN:` line and the harness counts them, so a fast run cannot be mistaken for a full one. `check_decisions` is skipped **whole** — it has no cheap half, and the one env var that would shorten it is RT-08, which disables binding resolution *while still printing green*. |
| **New: `TANNEN_SITTING_STOP_AFTER=<step>`, exit 3** | A partial run inspected in minutes rather than hours, and it cannot read as green: the harness checks the status. Called after all 26 steps. |
| **New step 3b — the push clause** | **D0195 item (3).** `in_repo_mechanics` grants Tier A over pushing to a *private* origin and excludes every other, and this origin is public: read literally, the act this repo performs after every commit is excluded from the tier that authorises it. D0195 offers two shapes and says the choice is the owner's, so the step offers both rather than choosing. |
| **New step 4k — `rehearse_sitting.sh` into the custody set** | **RT-M3-06.** The driver is custody-set; the harness whose whole purpose is to run it before the owner's key does is in neither the custody set nor the manifest, and D0068 makes a green rehearsal the driver's precondition. `check_drift.py` is also outside the set; no record asks for it, so it is named but not offered. |
| **New step 4l — a fixture whose README says it is not installed** | **D0152 item 5.** `tests/poison/oracle-shadow-model/README.md` still opens "**needs patch**", says it is "staged here and not in `tests/poison/`" from inside `tests/poison/`, and offers two commands whose `PYTHONPATH` names a deleted directory. Frozen *and* custody-set, so this is the only place it could be corrected. The dated "Verified" transcript is **left intact** — it is evidence of a run actually made, and rewriting it would falsify the record; only its header changes, to say why its paths differ. |
| Step 5 gains `check-laws-dropped-successor`, a fourth README-row block, and a rows file | **D0154 item (7), drafted by D0199.** `scripts/check_laws.py` was the only custody-set guard with neither a fixture nor a `poison` line. Step 5's opening notes are rewritten: "nine of the ten" is wrong at M3, and the M2-era claim that a sitting installing no new fixture is one whose red team found nothing would read false here in both directions — the M3 red team found six things, and its fixture-shaped critical landed early, at publication. |
| Step 8's APPLIED-BY table names D0154, D0171, D0176, D0195 | The queue is exactly those four (measured; every other Tier-C record is already accepted). The M2 table named D0061/D0095/D0108 and would have fallen through to "APPLIED-BY: NOTHING" for all four. **D0171's entry says its ruling (2) rests on a premise RT-M3-03 falsified** — amending costs nothing while it is unsigned and a supersession afterwards. |
| Step 11's prose: the lag is **one**, not two | `m3-laws-freeze` was added to `required_tags` at the publication sitting, so D0154 item 6 is closed. The loop is derived and needed no change — which is the point: the prose rotted and the mechanism did not. |
| Step 9's commit message no longer says "tag-signer rule" | That was the M1/M2 act. It now names what this sitting actually did. |
| **New: step 5 retargets D0199's binding, as it already does D0141's** | Found by rehearsing, not reading. D0199's binding named `docs/redteam/fixture-candidates/check-laws-dropped-successor/governance/laws.yaml`, and step 5 `git mv`s that tree into `tests/poison/` — so the binding stops resolving the instant the fixture lands. Exactly D0141's shape one milestone on, and the remedy is D0152's ruling for D0141: retarget in the same breath as the move, never drop. An installed fixture is sealed and manifested, so a binding pointing at it still names a real file. |
| **New: a prompt-index breadcrumb at `$TANNEN_SITTING_SCRATCH/prompts`** | `--abort-at N` takes a 1-based *prompt* index, and nothing anywhere mapped an index to a step — the publication harness has the operator assert one and checks the assertion, which means choosing N at all meant counting `confirm` sites by hand and hoping none of the conditional ones fired. The driver knows as it happens, so it writes `<index> <step>`. Both `confirm` **and** `pause` count: the publication driver has no `pause`, so porting its arithmetic unexamined would be off by one per pause. |

## What changed in `scripts/rehearse_sitting.sh`

| Change | Why |
|---|---|
| `--abort-at N [--abort-step ID]` | The path an owner most wants rehearsed — something looks wrong in the irreversible middle, they answer `n` — and the one that had never been executed for either driver. `--answers n` declines the *first* prompt, so it stops before the sitting has done anything. |
| **…but the publication harness's semantics do NOT transfer** | Every confirm in `publication_sitting.sh` is `confirm … \|\| die`, so one `n` is exit 1 and its verdict asserts that. **Measured here: zero of 42 confirms die on decline** — declining is a supported answer and every step reverts its own edits. So `--abort-at N` means *decline one prompt*, and a ported verdict asserting exit 1 would have failed on every run that worked. The verdict now measures the exit status and branches on it. The one prompt that does stop this sitting is step 9's commit: declining it leaves the tree dirty and step 10 refuses to tag over it (D0051, RT-M2-06 D2). |
| The prompt map's awk forces a **string** comparison | `prev` is assigned from `$2`, a field, so awk keeps it a "strnum"; against the constant `""` both coerce to numbers, and step 0's id is literally `0`, so `0 != 0` is false and the first group vanished. Prompts 1–3 were invisible. |
| The expected `sitting: STOP` is suppressed on a decline run | It was being reported as an unexpected failure line — the run's whole purpose flagged as an anomaly, which teaches an operator to skim the one section where genuine anomalies appear. |
| The milestone in flight is **derived from tags**, not defaulted to `m0` | `MILESTONE=m0` named a milestone finished since the first sitting, so every unargumented rehearsal ever run either took D0120's refusal branch or silently skipped steps 10 and 11. Now: the highest `mN` with a `laws-freeze` tag and no `close` tag. Derived, per D0171 ruling (3). |
| `root_state()` — isolation as a positive control | The header promised "nothing here touches the real repo" and nothing checked it. Now the real repository's HEAD and working tree are snapshotted before the run and compared after, on every path including the abort. Tested in four directions: it detects a tracked modification and a stray untracked file, and tolerates a builder drafting under `docs/` and a `.venv/` write. |
| `last_step` / `reached_step` read the driver's breadcrumb | Not a grep of the transcript: that would be a second copy of the driver's step vocabulary living in the harness (BRIEF §2), and when the publication harness tried it the pattern was wrong, matched nothing, and killed the harness mid-verdict under `set -e` (D0184). Hence `\|\| true` at every bare substitution. |
| **The Tier-C check split into two named facts** | It was one check piping `check_decisions` into `grep -q "0 queued"`, so *any* failure of that guard printed `FAIL no Tier-C door is left unsigned`. On 2026-09-09 it did exactly that: every door was signed, and the real defect was D0199's moved binding. A check that names the wrong thing sends you to the wrong file. Now: `check_decisions is green` and `no Tier-C door is left queued`, from one run, plus the offending binding lines printed by name. |
| The verdict prints the prompt map | So the next run's `--abort-at N` is chosen from a measurement. |
| The gate check is FAST-aware | Under `TANNEN_SITTING_FAST` the verdict would otherwise spend forty minutes proving a gate green that the driver had just skipped. |
| **Step 5's guaranteed `check_decisions` failure is named, not tolerated** | Step 5 installs a poison fixture, so the custody floor is red until step 7 re-signs it and `DECISIONS.md` is stale until step 9 — the failure is a certainty, and it was being reported in the section whose goal is to be empty. Adding the line to the tolerance list would have been the wrong fix: it is the **same line D0199's binding defect surfaced on**, so a blanket skip would have hidden the only defect these rehearsals have caught. The verdict asserts the block carries the three known violations and nothing else, and suppresses the line only while that holds. Verified against the kept transcript and against a doctored copy carrying rehearsal 1's actual D0199 violation — named, red, and left visible. |
| **Step 0's `check_manifest` failure is named, not tolerated** | Only a `--from head` run reaches step 0's gate, so this line first appeared on 2026-09-09 and landed in the section whose goal is to be empty. It is the harness's own doing — the driver under test is copied over `scripts/boundary_sitting.sh`, a custody-set member, and step 7 is where that gets re-signed — and the owner's `cp` does the same thing, so it is faithful rather than an artifact. Tolerated only while the custody drift on that one path is the block's *only* violation; an injected `frozen path BRIEF.md does not match its manifest hash` was watched being caught, named, and disarming the suppression. |
| **Neither tolerance may pass vacuously** | Both the step-5 and step-0 blocks above were written to pass when their failure is absent — so a run that never reached the gate reported the same green as one that examined a real block. That is the sixth guard in this driver and harness to measure a proxy instead of the state. Each now counts its input first and prints which case it is in. |
| **The verdict says which path step 0 took** | Which path step 0 took is a fact about what the run *covered*. In `--from worktree` mode the tree is applied as a patch, so `RESUMED=1` and the precondition gate is skipped on every worktree run ever made; a verdict silent about that lets a green run imply coverage it does not have. It now says so, or confirms `RESUMED=0`. |

## Which steps a rehearsal actually exercises

Measured from a kept clone's transcript, not asserted. The driver has **26** `say "Step …"`
headers — an earlier draft of this file said 24, and the figure was never recounted after the
three new steps landed. Step 0 is the precondition gate and applies nothing. Of the remaining
25, eleven do live work at M3 and fourteen are already-applied no-ops that run only their
"already applied — skipped" branch, which is the sitting staying safe to re-run rather than
dead weight.

| | Steps |
|---|---|
| **Live work** | 3b, 4f, 4k, 4l, 5, 6, 7, 8, 9, 10, 11 |
| Already applied — skip branch only | 1, 2, 3, 4, 4b, 4c, 4d, 4e, 4g, 4h, 4i, 4j, 5b, 8b |
| **Skipped for a different reason** | **0** — see the `RESUMED` gap in the banner above |

Step 10 is on the live list on the verdict's evidence (`m3-close was minted by THIS run`,
`verifies as owner@tannen`), not on the transcript's: `git tag -s` prints nothing a text scan
can key on, so a scan alone would call it skipped. Worth stating because it is the same trap
one layer up — the absence of a line is not evidence of absence.

## The queue, as drafted into this driver

| Step | Item | What it does |
|---|---|---|
| 3b | D0195 (3) | Offers two shapes for `policy.yaml`'s push clause; re-signs it either way. |
| 4f | D0152 (2), D0153, D0195 (2) | Re-offers ci.yml's lost `check_laws` paragraph **and** corrects its header, which claims the file has never run and that a remote is an unopened door. One frozen file, one edit, one manifest row. |
| 4k | RT-M3-06 | `scripts/rehearse_sitting.sh` into `governance/tier-c.yaml`'s custody set. |
| 4l | D0152 (5) | Six corrections to an installed fixture's README, including the package-qualified-import recommendation now on its **third** consecutive boundary. |
| 5 | D0154 (7) / D0199 | Installs `check-laws-dropped-successor/` and its README row. |
| 6 | D0154 (1)(2)(3)(4)(7) | Installs the rebased custodian, seven hunks. **Two of them exceed what D0171 ruling (4) proposes** — hunks 3 and 4 are items 4 and 3, which that ruling defers. D0171 is unsigned so nothing is in force, and the install is whole-file: the step states the conflict and lets the owner decide. |
| 8 | D0154, D0171, D0176, D0195 | The four Tier-C signatures, each with an APPLIED-BY line naming the step that executed it, or saying nothing did. |

Steps 1, 2, 3, 4, 4b–4j, 5b and 8b are **already-applied no-ops** at M3, verified by evaluating
each step's own detector against the tree. They are kept, not deleted: the loop is idempotent,
and skipping by detection is how the sitting stays safe to re-run.

## Step 0's gate establishes nothing, and the verdict must not imply otherwise

`docs/SITTING.md:36-38` already measured this and D0151 recorded it; this section exists
because a later session (this one) re-derived the opposite and had to be corrected by the
transcript. **`check_manifest.py` is the FIRST recipe line of the `verify` target.** The `cp`
that installs the driver is custody drift on a custody-set member, so `check_manifest` fails,
`make` stops, and `check_decisions`, the pytest suite, the laws report and `lint-imports`
never run. Measured in the kept `--from head` transcript: the gate announces "about 35
minutes" and runs from **elapsed second 0 to elapsed second 0**. The two real gates are at
826s (step 9) and 3577s (step 11).

So `--from head` closes the RESUMED coverage gap in the sense that step 0's code path is
*entered* — which is how the tenth defect surfaced — and does **not** close it in the sense
that anything is verified there. The driver's own line, `green except the custody set, which
is this sitting's step 7 — continuing`, is true and reads like something stronger: it means no
unexpected failure appeared in a run that got three lines in.

**The precondition is established before the `cp` or not at all** — which is why
`docs/SITTING.md:23` puts `make verify` first, and why step 0's offer does not replace it.

## The floor audit, and what it refused to change

`FLOOR-AUDIT.md` in this directory answers the owner's ruling (1) of 2026-09-09: which custody
guards does a public remote make redundant? **None.** Thirty-five substitution claims across
seven mechanism families, each adversarially refuted; zero survived. The decisive measurement
is that `grep -rn 'git push' scripts/ Makefile` returns nothing — the sitting signs the custody
set, the receipt and the close tag against a tree the remote has never seen, so the window
holding every irreversible act is the one window no remote can witness. The ceremony still
shortens by ~35 minutes and one owner signature per boundary, by deriving `required_tags`
instead of maintaining it by hand, which deletes step 11 outright. Recorded as D0202.

## What is NOT in this driver, and why

- **`docs/specs/m3.md`'s falsified passages** (D0171 ruling 1, RT-M3-03, and RT-M3-01's
  residue) and **the package-qualified import in the frozen M3 law files** (RT-M3-04's real
  fix). Both need *new frozen prose that nobody has drafted*, and a driver step that offered
  an edit it did not have would be worse than no step. They are Session-A-shaped work.
- **D0148 item 5** — the receipt is written and signed before the owner is asked to commit,
  so an abandoned decline leaves a signed receipt that step 0 reads as `RESUMED`. D0148 says
  outright that fixing it changes the order the receipt-then-tag argument depends on (D0071),
  which is the owner's judgement and not a quiet edit.
- **D0154 items 5 and 8**, deferred by D0171 ruling (4).
