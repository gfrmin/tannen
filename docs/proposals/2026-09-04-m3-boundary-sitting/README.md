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

The live `scripts/custodian.sh` plus four delimited hunks (`--- M3 DRAFT HUNK n ---`),
each mapped to a D0154 queue item. Diff against the live file to review; the diff is the
hunks and this header, nothing else.

| Hunk | D0154 item | Source record | What it does |
|---|---|---|---|
| 1a/1b/1c | (1) | D0152 item 6 | 1b adds the missing `poison` line for `tests/poison/oracle-shadow-model/` (RT-M2-01), invocation matching `tests/test_governance_scripts.py::test_oracle_shadow_model_fails_its_poison` — no `-I -P` (the attack **is** PYTHONPATH), `-B` (sealed-directory bytecode), no `-k` (the widened guard aborts at collection). 1a+1c add the derived half — D0152's named fix, D0095 half (2): `poison()` records which `tests/poison/` directories its invocations reach, and a completeness pass refuses any installed fixture no line exercises. Had it existed on 2026-09-03, the sitting would have failed loudly instead of finishing sooner. |
| 2 | (2), third clause | D0152 item 3 | Checks `ssh-keygen -Y sign`'s exit status. The live line ignores it and prints "written and author-signed" regardless, failing in the direction of appearing to have worked on the one artifact the Tier-B silence-consent clock rests on. On failure the half-written receipt is removed — a receipt with no `.sig` is also what makes the next driver run believe it is resumed (D0148 item 5), so leaving it would trade one queue item for another. |
| 3 | (4) | D0146 item 2 | Excludes `__pycache__` from the step-2 `find`, matching `check_manifest.py`'s sealed-path rule, so a stray `.pyc` under `tests/poison/` no longer reddens the floor 37 minutes into `make verify` with a message that invites a manifest row for a gitignored file. |
| 4 | (3) | D0153 | The receipt's `previous receipt` chain line survives a same-day re-run: `prev` now excludes the file being written and reads its HEAD from the chosen file, instead of `sort | tail -1` picking the receipt itself and the guard dropping the line silently. |

Not drafted here (driver territory, not custodian territory — they join the M3 driver
when it is drafted): D0152 items 1 (retarget guard testing pre-state), 2 (step 4f's
skip-guard subset), 4 (no lock; `flock` beside the transcript), 5 (the installed
fixture's README prose); D0148 item 5's ordering question; D0154 items 6
(`required_tags` + `m3-laws-freeze`), 7 (a poison fixture for `check_laws.py`), 8
(the `event()` schema follow-up), 9 (stale "712 tests" transcript lines).
