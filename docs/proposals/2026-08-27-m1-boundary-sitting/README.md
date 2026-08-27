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

## What this sitting resolves that the driver does NOT automate

Two items in D0105's queue are deliberately hand steps, not driver code, because
automating them would mean writing bash that edits decision-record YAML and re-signs it
programmatically — more moving parts than two small, well-understood edits are worth:

- **Item 2**: land RT-M1-05's patch
  (`docs/redteam/fixture-candidates/check-decisions-file-skip/rt-m1-05-check-decisions.patch`)
  and the `check-decisions-file-skip` fixture together, in the same commit the custody
  re-signature covers. See D0103 for why the builder session that wrote the patch could
  not commit it alone.
- **Item 3**: the two binding upgrades D0070 left drafted — see
  `signed-record-binding-upgrades.md` in this directory for exactly what changed, what
  didn't, and the one discrepancy found (D0070 said three upgrades were pending; only two
  were found live).

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
