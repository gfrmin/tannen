# M5 gate-sitting prep — the session brief

Builder-only. **The gate stays shut.** This session writes the sitting's materials; it never
performs the sitting and never takes the measurement.

Drafted at the close of M5 Session B1 (D0263, D0264, D0265) so the prep session starts from
what B1 measured instead of re-deriving it.

## State

M5 Session B1 closed at `924ef46` on `m5`, pushed, CI green: the CLI spend clamp (D0263),
`tannen.dogfood` (D0264), and D0265 filed `blocked-on-owner`. `make verify` green — 1254
passed, 11 skipped, 3 xfailed; M0–M4 fresh, L5.1–L5.10 frozen awaiting their corpus.

Work in the existing `m5` worktree. One worktree per milestone; do not create another.

## The gate

`governance/tier-c.yaml` `renavon-first-contact` is unopened. **Read nothing from the Renavon
monorepo, `.reference/` included** — not to measure it, not to survey exports, not "just to
check". If you think you need a Renavon byte to make progress, you are in B2 and you stop.

## Read first

- `docs/specs/m5.md` §0.2, §2, §3, §8
- decisions D0255–D0257, D0261, D0262, D0263–D0265
- `tests/laws/m5/test_l5_authorisation.py` — the judge of the record you draft
- `tests/laws/m5/test_l5_replay.py` — the fresh-interpreter law that constrains where the
  vertical may live
- `docs/proposals/2026-09-11-m4-boundary-sitting/` — the shape precedent for sitting materials

## Already measured (B1, 2026-09-16)

Do not re-derive these. Do re-run any you intend to rely on.

- **L5.10 spawns a fresh interpreter that inherits ENV, not `sys.path`.** A conftest
  `sys.path.insert` makes the pytest parent pass and the child FAIL (assertion at line 72).
  `PYTHONPATH=<root>/.dogfood` makes both pass — 123 passed, only L5.8 failing, which is the
  shut door refusing an unauthorised corpus by name. So "make `.dogfood/` importable" is an
  ENVIRONMENT act; the library is untouched and no superseding law is needed. D0265's option
  (c) says otherwise and is wrong; correcting it is item 1 below.
- **`Makefile` and `conftest.py` are both in `governance/custody.sha256`**, so any automatic
  PYTHONPATH wiring is an owner-signed act — drafted here as a patch, never applied.
- **`.gitignore` is builder-editable.** `.dogfood/` is already ignored; the repository root is
  not, and a sitting commits with `git add -A`. An unpublished vertical therefore belongs
  inside `.dogfood/`, never loose at the root.
- **`lint-imports`' `no-cross-repo` contract has `source_modules = ["tannen"]`**, so a vertical
  anywhere outside `src/tannen/` is invisible to the Tier-C guard that forbids importing
  `renavon` — the exact shortcut a byte-for-byte re-implementation is tempted into.

## Produce, in this order

### 1. A record correcting D0265 by measurement

D0265's option (c) claims that making `.dogfood/` importable changes `run`'s contract and needs
a superseding law. It does not. D0045: never edit D0265 — write a new record.

Carry two things the original lacks:

- the guard-coverage comparison — `src/tannen/` vs tracked-outside vs untracked, against the
  doorway law, the `no-cross-repo` contract, and `test_no_pii`. The doorway column is a red
  herring (L5.2's own limits already exclude the pipeline module as "the operator's code"); the
  cross-repo column is the one that bites;
- the sequencing point: ask (6) is better answered AFTER the measurement, because the selection
  rule minimises parser LOC × distinct operators, so the disclosure at stake is by construction
  the smallest parser in the candidate set. Decide with the number, not with a worry.

### 2. The unsigned Tier-C record that opens the door

In exactly the shape L5.8 accepts: a file under `decisions/`, `tier: C`, `status: accepted` on
signature, `links` naming the door id **read from** `governance/tier-c.yaml`, signed by
`owner@tannen` under namespace `tannen-decision`.

It carries D0257's five asks and D0265's sixth as fields the record **states**, not as prose the
owner has to reconstruct into a decision.

Watch L5.8 accept it, and refuse it unsigned, in a scratch repository COPY under an ephemeral
owner key. The real `allowed_signers` is author-key territory and is never touched. B1's
scratch-copy method is in D0264 if you want the shape.

### 3. The PYTHONPATH patch, for the owner to sign at the same sitting

One sitting, two signatures — the door and the wiring — or B2 is blocked again a week later.

Choose `Makefile` or `conftest.py` and say why in the record. It must make BOTH the pytest
parent and L5.10's fresh interpreter see `.dogfood/`, and be **inert when `.dogfood/` is
absent**: CI must stay exactly as it is today, 10 skipped. Drafted as a patch, never applied.

Skipping it is survivable but should be a stated choice, not an oversight: without it, forgetting
the environment variable makes the gate red, never falsely green.

### 4. An unfrozen guard: the vertical imports nothing from the constellation

The compensating control for the gap in the table above — it applies whichever home the owner
picks. The forbidden list is DERIVED from `governance/importlinter.toml`'s `no-cross-repo`
contract, never hand-written (D0211; D0171 ruling (3)).

It must skip cleanly with no corpus present, and you must watch it FAIL against a planted
`import renavon` before trusting it green (produce the failure).

Unfrozen on purpose: it is a compensating control, not a law, so it needs no freeze and can be
tightened once the real vertical exists.

### 5. The measurement recipe

The steps that take `measurement/1` over the candidate sources ON the owner's machine AFTER the
signature, and write `.dogfood/measurement.json`. **It must not run here.**

State plainly that L5.4 then selects the vertical and nobody chooses it.

## Hard constraints

Nothing spends; every ceiling stays zero. No network from any test. Frozen paths are read-only.
Custody-set files are drafted as patches, never applied. Never `--no-verify`; never set
`TANNEN_CHECK_DECISIONS_NESTED`. Carry `TANNEN_NO_EVIDENCE=1` on ad-hoc pytest. Run
`make projections && .venv/bin/python -I -P scripts/gen_roadmap.py` before `git add`. A commit is
~15–20 min of hooks and `make verify` ~30–45 min: run each setsid-detached into a log, never two
at once, and never edit the tree while they run. Scrub absolute paths from tracked files.

## Done

The full verification list green (CLAUDE.md), the sitting's materials complete enough that the
owner's part is read–answer–sign, and a one-page agenda saying in what order.

**Do not open the gate. Do not start B2.**
