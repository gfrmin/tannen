# M1→M2 boundary sitting — the materials the owner applies

Staged here because most of it edits something the builder may not: a custody-set path,
a Tier-C record's signature, the trust root's derived tag list. `boundary_sitting.sh`
(this directory's own copy) applies the mechanical parts in order; `D0105` is the
deciding document — read it first, the same way `CONFERRAL.md` was the deciding document
at the M0→M1 sitting. This directory's own driver copy replaces the M0-era one for two
reasons the copy's own comments explain (a much longer VERIFY_ETA, and an M1-specific
fixture list); everything else about how a boundary sitting works is unchanged from
`docs/SITTING.md`.

## Before running anything

**Rehearse first.** `scripts/rehearse_sitting.sh` runs this copy end to end against a
disposable clone, with a throwaway key, and reports whether the mechanics hold:

```
TANNEN_REHEARSE_DRIVER=docs/proposals/2026-08-27-m1-boundary-sitting/boundary_sitting.sh \
    bash scripts/rehearse_sitting.sh
```

A green rehearsal proves the driver's own mechanics (step order, shell quoting, gates,
idempotence) — never that the sitting itself is a good idea, and never custody (the
rehearsal's signatures are structurally correct and attest to nothing real). Read a green
run as "this will not stop on a shell defect", not as "the sitting happened".

**Then, for real:**

```
cp docs/proposals/2026-08-27-m1-boundary-sitting/boundary_sitting.sh scripts/boundary_sitting.sh
bash scripts/boundary_sitting.sh m1
```

The `cp` is deliberate and is step 0 of D0105's queue — `scripts/boundary_sitting.sh` is
a custody-set member, so this one copy is expected drift, tolerated by name in the
copy's own `unexpected_failures()`. It stops meaning anything the moment step 7 re-signs
the custody set, same as every other custody-set edit a sitting makes.

## What this copy changes versus the committed driver

| Change | Why |
|---|---|
| `MILESTONE` default `m0` → `m1`; `VERIFY_ETA` "a minute" → "15-20 minutes" | M1's suite is much larger than M0's (537 tests vs. M0's 174); "a minute" would read as hung. |
| `PROPOSALS_M1` variable added, alongside the unchanged `PROPOSALS` (still the M0→M1 dir) | Steps 3/4/4b's M0-era artifact comparisons are already-applied no-ops for M1 and stay pointed at the old directory; only what THIS milestone adds — the custodian diff, the poison README row — needs a new path. |
| Step 5's `FIXTURES` list gains `oracle-shadow` | RT-M1-01's fixture, drafted and verified this session (D0102). `check-decisions-file-skip` (RT-M1-05) is deliberately absent — see D0105 item 2. |
| Step 5 gains a second poison-README block, gated on `oracle-shadow` rather than `lint-imports-kernel` | The existing block's guard condition is already true for M1 (the M0 row is already there), so it would silently skip the new row without a parallel check. |
| Step 6 compares against `$PROPOSALS_M1/custodian.sh`, not `$PROPOSALS/custodian.sh` | The M0 draft is already installed; comparing against it again would read "already applied" and never offer the one new poison line. This directory's `custodian.sh` is the live file plus that one line — the diff the owner reviews should show only the addition. |
| `unexpected_failures()` gains one more tolerated pattern: `custody drift: scripts/boundary_sitting\.sh` | The precondition for running THIS copy at all (see "Before running anything") produces exactly this drift, before step 7 can resign it. Scoped by literal path, not by pattern, so it hides no other guard's drift. |
| Step 11 adds `m1-laws-freeze` to `required_tags`, not only `$MILESTONE-close` | D0095: `m1-laws-freeze` was minted at M1 Session A's freeze and has been missing from `required_tags` ever since — a structural lag the builder cannot fix (the file is frozen and custody-set). Both tags land in one motion so the lag does not repeat at M1→M2. |
| New **step 4c**, after step 4b: applies D0070's two drafted binding upgrades to D0049 and D0063, and re-signs both | D0105 item 3 — see below. Gated on step 4b (BRIEF.md must already say "Metric calibration") since D0063's upgrade depends on it. |
| New **step 5b**, after step 5: applies RT-M1-05's patch and installs its fixture | D0105 item 2 — see below. |

## What this sitting resolves that the driver now automates (added 2026-08-27, second pass)

Both of D0105's two hand-step items are now driver code (steps 4c and 5b) — same
confirm-and-diff idiom as every other step, nothing landing without the owner reading
the diff and typing `y`. What follows is what each does and why, kept for the reasoning
a bash comment can't carry:

- **Item 2 (step 5b)**: land RT-M1-05's patch
  (`docs/redteam/fixture-candidates/check-decisions-file-skip/rt-m1-05-check-decisions.patch`)
  and the `check-decisions-file-skip` fixture together, in the same commit the custody
  re-signature covers. See D0103 for why the builder session that wrote the patch could
  not commit it alone. The fixture install moves only its `decisions/` and `tests/`
  subdirectories into `tests/poison/` — the `.patch` file itself stays put, because D0103
  and D0104 both carry a binding to it at that path (the same fragility that broke
  D0104's binding to `oracle-shadow/_fragment.py` when step 5 moved that fixture whole).
  Verified live (2026-08-27) before scripting it: the patch applies cleanly, the fixture
  fails with the right marker (`unexplained skip`) once patched, and running it pollutes
  `tests/poison/` with an unmanifested `__pycache__` unless the invocation sets
  `PYTHONDONTWRITEBYTECODE=1` — `-B` on the outer interpreter does **not** suffice here,
  unlike `oracle-shadow`'s poison line, because `check_decisions.py` runs pytest as a
  *subprocess*, and `-B` only affects the process it is given to, not one spawned after.
  `custodian.sh`'s new `check_decisions_file_skip` poison line uses the env var for
  exactly this reason. **A second, independent hazard found rehearsing this (rehearsal
  #8, after the `PYTHONDONTWRITEBYTECODE` fix already held):** the fixture's test file
  was originally named `test_mixed.py`, which is the FIRST file in the entire
  `tests/poison/` corpus to match pytest's default `test_*.py` discovery glob —
  `pyproject.toml`'s `testpaths = ["tests"]` carries no exclusion for `tests/poison/`,
  so once installed, the bare `pytest -q` inside `make verify` swept it into the main
  suite too, both changing the project's pass/skip counts and writing an unmanifested
  `__pycache__` from an invocation the poison line's own env var never touched. Every
  earlier fixture avoided this by accident of naming, not by design. Fixed by renaming
  the file to `mixed_cases.py` (an explicit pytest target still collects a file
  regardless of its name — only no-args directory-walk discovery cares about the
  pattern) rather than adding a repo-wide `--ignore=tests/poison`, which would have had
  to be proven safe against every *existing* poison line's own `--root`-scoped pytest
  subprocess calls (several of which run with `cwd` already inside `tests/poison/`) —
  a wider, riskier change for the same fix.
- **Item 3 (step 4c)**: the two binding upgrades D0070 left drafted — see
  `signed-record-binding-upgrades.md` in this directory for exactly what changed, what
  didn't, and the one discrepancy found (D0070 said three upgrades were pending; only two
  were found live). **A third thing was found while scripting this, not counted among
  D0070's three**: `decisions/0049-close-tags-stay-owner-signed.yaml` has a real
  corruption — a missing newline before its third binding (`- type: manifest, target:
  DELEGATIONS.md`) folds that whole entry into the SECOND binding's `detail:` prose
  instead of parsing as its own list item. Confirmed with a plain YAML parse
  (`len(bindings)` came back 2, not 3) and confirmed nowhere else in `decisions/*.yaml`
  carries the same defect. The signed `.sig` verifies against exactly this broken
  content, so it predates this session and has stood, unnoticed, since whichever sitting
  added that binding. Step 4c restores it (a one-line textual fix, verified against the
  real files before this driver copy shipped) in the same edit that adds the new
  `manifest:scripts/custodian.sh` binding, then re-signs. Worth the owner's eye at the
  sitting: the diff step 4c shows is not just an addition.

## Verification after the sitting

`make verify` green, and in particular:

- `custodian: custody set hashes verify (N path(s))` and `governance/custody.sha256
  signature verifies (owner@tannen)`;
- `oracle-shadow` (and, once item 2 lands, `check-decisions-file-skip`) reported as
  `guard '<name>' fails its poison as required`;
- `check_tag_signers: OK` with `m1-close: owner@tannen (class role: owner)`;
- `governance/tag-roles.yaml`'s `required_tags` lists both `m1-laws-freeze` and
  `m1-close`;
- `uv run python scripts/check_decisions.py` reports `0 queued` Tier-C doors (D0061 and
  D0095 resolved one way or the other at step 8);
- `grep -c "Metric calibration" BRIEF.md` returns 1 (D0063's amendment finally applied).
