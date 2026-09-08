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

Not drafted here (driver territory, not custodian territory — they join the M3 driver
when it is drafted): D0152 items 1 (retarget guard testing pre-state), 2 (step 4f's
skip-guard subset), 4 (no lock; `flock` beside the transcript), 5 (the installed
fixture's README prose); D0148 item 5's ordering question; D0154 items 6
(`required_tags` + `m3-laws-freeze`), 7 (a poison fixture for `check_laws.py`), 8
(the `event()` schema follow-up), 9 (stale "712 tests" transcript lines).
