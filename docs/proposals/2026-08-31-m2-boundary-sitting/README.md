# M2→M3 boundary sitting — the materials the owner applies

Staged here because most of it edits something the builder may not: a custody-set path, a
Tier-C record's signature, the trust root's derived tag list. `boundary_sitting.sh` (this
directory's own copy) applies the mechanical parts in order; **`D0131` is the deciding
document** — read it first, with `D0138` beside it, the way `CONFERRAL.md` was the deciding
document at M0→M1 and `D0105` at M1→M2. Everything else about how a boundary sitting works is
unchanged from `docs/SITTING.md`.

> ## ⚠ STILL NOT READY TO RUN — two inputs outstanding
>
> Updated 2026-09-01. **The red team has run** (`docs/redteam/2026-09-01-m2-boundary.md`,
> D0141 — eight findings, one critical), and its results are folded in below. What remains:
>
> 1. **The queue's ready text is not drafted** — D0131 items 2/3/4/6/8 (item 3 now corrected by
>    RT-M2-02), D0123's binding upgrades, and D0138's two. See **Still to draft** below.
> 2. **This driver has not been rehearsed** (D0068). Run
>    `TANNEN_REHEARSE_DRIVER=docs/proposals/2026-08-31-m2-boundary-sitting/boundary_sitting.sh bash scripts/rehearse_sitting.sh --milestone m2`
>    on both `--answers y` and `--answers n` before the owner's key is anywhere near it. Four
>    defects found by RT-M2-06 are fixed in this copy and **none of those fixes has been
>    exercised end to end**.
>
> One thing the red team says should happen *before* the sitting, not at it: RT-M2-01's
> `src/tannen/laws/plugin.py` widening is builder-landable, and until it lands the
> `oracle-shadow-model/` fixture cannot be installed — installing it first would leave the
> custodian permanently red.

## The clock

`scripts/_gov.py:303` computes receipt freshness as *the first boundary tag on or after the
receipt, plus seven days*. That resolves to **2026-09-07**, and it cannot be moved by minting a
later tag — `later[0]` is already fixed at 2026-08-31. After that date the receipt is stale,
Tier-B silence-as-consent is suspended, and work pauses at the next milestone boundary. The
repo's three remaining Tier-B records (D0006, D0014, D0020) reached `veto_by` on 2026-08-31;
from 2026-09-01 they read `accepted (veto lapsed)` **only while the receipt is fresh**, and
revert to `provisional — BLOCKED` if it goes stale.

## Before running anything

**Rehearse first** (D0068). `scripts/rehearse_sitting.sh` runs this copy end to end against a
disposable clone with a throwaway key, and reports whether the mechanics hold:

```
TANNEN_REHEARSE_DRIVER=docs/proposals/2026-08-31-m2-boundary-sitting/boundary_sitting.sh \
    bash scripts/rehearse_sitting.sh --milestone m2
```

**`--milestone m2` is load-bearing, not decoration.** `scripts/rehearse_sitting.sh` defaults to
`MILESTONE=m0`, where the clone already carries `m0-close` and already lists both m0 tags in
`required_tags` — so **step 10 skips** (`$MILESTONE-close already exists`) and **step 11's
`MISSING_TAGS` is empty**, and the two steps that mint the owner-only close tag and then edit,
re-manifest, re-generate and re-sign the custody set never run at all. The verdict then prints
green off the tag the clone was cloned with: a post-condition whose answer does not depend on the
run it is checking. Run the decline path too (`--answers n`).

A green rehearsal proves step order, shell quoting, the gates and idempotence. It proves nothing
about custody — its signatures are structurally correct and attest to nothing.

**Then, for real:**

```
cp docs/proposals/2026-08-31-m2-boundary-sitting/boundary_sitting.sh scripts/boundary_sitting.sh
bash scripts/boundary_sitting.sh m2
```

The `cp` is deliberate and is step 0 of the queue — `scripts/boundary_sitting.sh` is a
custody-set member, so this one copy is expected drift, tolerated by literal name in the copy's
own `unexpected_failures()`. It stops meaning anything the moment step 7 re-signs the custody
set. **Pass `m2`**: the argument drives step 10 and step 11, and a sitting driven at the wrong
milestone skips both without printing anything that looks wrong.

## What this copy changes versus the committed driver

The committed `scripts/boundary_sitting.sh` is byte-identical to the M1 sitting's copy. Four of
the eight changes below are defects that sitting left behind, all filed at the time.

| Change | Why |
|---|---|
| `MILESTONE` default `m1` → `m2`; new derived `NEXT_MILESTONE` | The milestone rolled. `NEXT_MILESTONE` is computed from it so the closing note cannot drift out of step again — see the last row. |
| `VERIFY_ETA` "15-20 minutes" → **"35-40 minutes"** | Re-measured, not guessed. M2's suite is 712 tests against M1's 537; `make verify` was timed end to end on 2026-08-31 at 35-40 minutes, of which pytest alone is 21m40s (1300.60s, D0139). An owner watching a still terminal for forty minutes against a twenty-minute promise concludes it is hung — which is what happened at the M0 sitting, twice, before the driver reached its first question (D0069). |
| New `PROPOSALS_M2`, with `PROPOSALS` and `PROPOSALS_M1` left pointed at the old directories | M1's own precedent: the earlier directories' comparisons are already-applied no-ops, and re-pointing them would offer the owner a second time what they already installed. |
| **`readme_row_absent()` replaces three `grep -q '<fixture>'` guards** | **D0131 item (1), and it is the item that would otherwise have been lost.** The old guard asked whether the fixture's name appears *anywhere* in `tests/poison/README.md`. Step 5 appends `$PROPOSALS_M1/poison-readme-rows.md`, whose **prose** names `check-decisions-file-skip` while explaining that its row comes at step 5b — so by step 5b the grep matched, the step read "already added", and the row has never once been offered. The sentence stating why the row was absent is what guaranteed it stayed absent. The new helper anchors on a table row (`^\| \`name/\` \|`), which prose never produces. |
| **New `manifest_row_current()`, called on step 4b's skip branch** | **D0122 item (4).** Step 4b's own failure advice sends the owner to an editor *outside* the driver; on the re-run the "already applied" grep is true, the skip branch is taken, and `regen_manifest_row` is never reached — so `BRIEF.md`'s bytes and its `MANIFEST.sha256` row disagree in silence until step 9's gate fails on a frozen path, one full sitting after the mistake. The branch now checks the row and offers to regenerate it. |
| **Step 0's gate offer is skipped on a RESUMED sitting** | **D0122 item (5).** Steps 1–8 flip record statuses, write `.sig` files, amend frozen text and move fixtures — all of which is custody drift or a stale projection by the time it is done. `unexpected_failures()` tolerates exactly two patterns plus this file's own name, by design, so on a resumed sitting the gate an owner is invited to run "before signing anything" goes red over the work they already did and `die()` stops them. The driver now detects a dirty tree, says so, and defers to step 9's gate — the one that must be green. |
| **Step 0's `RESUMED` test rewritten** | **RT-M2-06 D1 — a defect in the first version of this copy.** It asked "is anything other than this file dirty", so a single stray untracked file set `RESUMED=1`, **skipped the `make verify` precondition entirely**, and told the owner "this is a RESUMED sitting" on no evidence — a fresh sitting could begin over a red gate with the one check against that silently off. Resumption is now decided by artifacts only a sitting creates (a `.sig`, a receipt, the close tag) or a *tracked* modification; stray dirt is reported, never acted on. Tested across seven cases including the close-tag-on-a-clean-tree false negative (D3). |
| **Step 10 refuses to tag a dirty tree; step 9's commit status is checked** | **RT-M2-06 D2, the highest-cost defect and pre-existing since M1.** `commit_with_hook_retry`'s status was never read and there is no `set -e`, so a declined commit — or a hook that stayed red — fell through to step 10, which tagged the **pre-sitting HEAD**. `git tag -s` and `verify-tag` both succeed on it. Worse, the tag message quotes `sha256sum` of `DELEGATIONS.md` and `governance/custody.sha256` read from the **working tree**, so the project's first owner-signed close tag would attest hashes absent from the commit it names — falsifying the exact D0051 property those lines exist to provide. |
| **Step 2 anchors on the guard's message, not its docstring** | **RT-M2-06 D4.** The probe grepped `"affirmative signature only"`, whose only match is the module docstring at `check_decisions.py:13`; the enforcement is at 292-307. Delete the enforcement, keep the docstring, and the step reported "present — skipped". This is the same prose-versus-enforcement bug `readme_row_absent` was written to fix — **fixed in one place and left in another.** Now anchored on `Tier-C record accepted without an owner signature`, the message the guard emits. |
| `cd "$(dirname "$0")/.."` gains `|| exit 1` | **RT-M2-06 D5** (SC2164). There is no `set -e`, so a failed `cd` continued in the wrong directory with every relative path — and `ssh-keygen -Y sign`, `git tag -s` — resolving against the wrong tree. |
| Closing note `"M1 Session A"` → `"${NEXT_MILESTONE^^} Session A"` | **D0122 item (5).** The one line an owner reads *last* named the milestone that had just ended, while every neighbouring line interpolated `$MILESTONE`. |
| Step 5's prose rewritten; `FIXTURES` gains `check-decisions-file-skip` and a marked red-team slot | The M1 prose said the RT-M1-05 guard fix "is not committed yet". It is: `scripts/check_decisions.py` carries `RT-M1-05` and `tests/poison/check-decisions-file-skip/` is installed and exercised by the custodian. Only its README row was ever missing. Listing it keeps the loop's skip-by-name idempotence honest about the corpus it indexes. |

### Verified, not asserted

Both new helpers were exercised against the live tree and from the failing side before this
directory was written:

```
readme_row_absent   lint-imports-kernel        old=present(skips)  new=present(skips)
readme_row_absent   oracle-shadow              old=present(skips)  new=present(skips)
readme_row_absent   check-decisions-file-skip  old=present(skips)  new=ABSENT(offers row)
```

Exactly one fixture changes verdict, and it is the one D0131 item (1) is about; the two whose
rows genuinely exist are untouched. `manifest_row_current` returns current for an unmodified
manifested file, and **stale** both when the bytes drift and when the row is absent — checked in
a sandbox, since the true case alone would not have distinguished a working check from one that
always returns true.

## Red-team findings

**The pass has run.** `docs/redteam/2026-09-01-m2-boundary.md`, record **D0141**: eight findings
— one critical, five high, one medium-high, one informational. **Nothing was closed**, so every
item below is input to this sitting.

Two of them change what this sitting must do, and should be read before anything else:

- **RT-M2-02 corrects D0131 item 3, which is already on this sitting's list.** Signing
  `governance/laws.yaml` does not close the hole: `conftest.py:24` is what *decides which file
  is the registry*, so a second registry beside it reproduces the whole attack with
  `laws.yaml` byte-identical and the pin test passing unmodified. **`conftest.py` and
  `scripts/check_laws.py` must go into the custody set too** — `check_laws.py` is the only guard
  in neither the manifest nor custody, while eight sibling scripts are custody-set.
- **RT-M2-06 is about this driver.** Four of its defects are fixed in this copy (see the table
  above); the rest are cheap and listed in the report.

**Fixture candidates** (staged outside `tests/poison/`, as always):

| Candidate | Closes | Bites today? |
|---|---|---|
| `oracle-shadow-model/` | **RT-M2-01 (critical)** | **no — needs patch.** The shipped oracle check pins the single name `_fragment`; M2 added `_model` and `_subject`. The `src/tannen/laws/plugin.py` widening is **builder-landable** (no manifest row, not custody-set) — land it first, then this fixture bites and can be installed |

**Three findings falsify frozen prose** and each needs a decision record, not an edit:
`docs/specs/m2.md:58`, `:97-100`/`:116`, and `:234`. Per D0106 ruling 2 they are superseded
forward.

**Most of the remaining fixes are builder work, not sitting work** — `MANIFEST.sha256` has zero
`src/` rows and the custody set no `src/` path, so RT-M2-01's plugin widening, RT-M2-03's
citation kind, RT-M2-04's `why_slots`, and RT-M2-07's `_Why.encode` gate can all land in an
ordinary session. **What genuinely needs the owner** is: the custody-set additions above
(RT-M2-02), the `tests/poison/` installation, `Makefile`/CI wiring, `governance/tier-c.yaml`
(including sealing `tests/`, which every reproduction of RT-M2-01 depends on), and the
projection fix (RT-M2-05), which touches `check_decisions.py` and `gen_projections.py`.

**Do not install fixtures under `tests/poison/` outside the sitting** — that is the owner's act,
and a fixture whose guard patch has not landed leaves the custodian permanently red against a
guard that is not shipped (D0104's note on `check-decisions-file-skip`).

## Still to draft

Ready text for the queue, none of which exists yet:

- **D0131 item 2** — D0117's evidence-record quantity. `governance/schemas/evidence-record.schema.json`
  is frozen, inside a sealed directory, *and* custody-set: three separate reasons the builder
  cannot touch it.
- **D0131 item 3, AS CORRECTED BY RT-M2-02** — `scripts/check_laws.py`, `governance/laws.yaml`
  **and `conftest.py`** into the custody set. The two-file version does not work: `conftest.py`
  chooses which file is the registry, so signing `laws.yaml` alone is decorative (RT-M2-02
  variant C, reproduced with `laws.yaml` byte-identical). Note the cost to state plainly —
  custodying `laws.yaml` makes D0128's Session-B `pending`→`superseded` promotion an owner act,
  which is the one thing D0128 designed to be a builder two-line move; if that is unacceptable,
  drop `laws.yaml` and take the `check_supersessions` hardening instead, but `conftest.py` and
  `check_laws.py` are non-negotiable either way. **Do NOT freeze
  `tests/test_law_validation.py`** — it changes every milestone and freezing it halts Session B.
- **D0131 item 4** — gate wiring: `check_laws.py` into `Makefile` and `.github/workflows/ci.yml`;
  the `unvalidated` ratchet metric into `scripts/gen_projections.py` and `scripts/check_decisions.py`.
  RT-M2-02 raises the priority: today `check_laws.py`'s only path into the gate is a subprocess
  launched from `tests/test_law_validation.py` — the very file an attacker edits.
- **D0131 item 6** — `ALLOWED_SKIP_REASON_PREFIXES` and D0124's chosen fix.
- **D0131 item 8** — D0106 items 1 and 3 (optional `bindings_count`; the governance/kernel
  line-count ratio as a defect signal).
- **D0123** — the batch of binding upgrades to the now-fourteen signed Tier-C records, applied in
  the same pass that re-signs them.
- **D0138 item 1** — rename `test_a_survivors_witness_can_give_an_unwitnessed_row_a_bag_image` to
  something that says what it now asserts, retarget D0110's binding, re-sign D0110.
  **The rename and the re-signature must land in the same step**: D0110 is Tier C and
  owner-signed, the signature covers the record's whole bytes (D0063 ruling 2), and between the
  two acts `check_decisions.py` sees a signed Tier-C record binding a node that does not collect.
- **D0138 item 2** — a `check_manifest.py` guard that every repo-relative path in
  `MANIFEST.sha256`'s own comment block resolves. D0135 is the finding it would have caught.

## What the sitting ends with

The receipt, then `m2-close`, in that order — so the clock starts against a boundary tag rather
than stopping. Then M3 Session A, fresh session, new worktree.
