# M4 boundary sitting — proposals (opened at Session A, 2026-09-11)

This directory is the M4 sitting's staging area. It exists from the milestone's first
session because its absence is a recorded defect class: the M2 sitting's custodian step
diffed against the previous milestone's proposals directory, that directory shipped no
`custodian.sh`, and the fixture the sitting itself installed never got its poison line
(D0152 item 6). The sitting's driver is drafted near the boundary, as at M2 and M3, and
joins this directory then.

Nothing here enforces anything. Every file that lands here is a draft the owner installs, or
declines, at the sitting, under the owner's key.

## The queue

The M4 boundary queue is every record `blocked-on-owner`, at any tier — ROADMAP.md §3 is the
query, and it is the one to read, because the digest's "Requires owner" section filters Tier
C and cannot see a Tier-A item that needs the key. At Session A it holds:

| Record | Tier | Ask |
|---|---|---|
| D0214 | C | Upgrade a Tier-C record's bindings in the same step that flips its status, before signing |
| D0215 | C | Stop storing a clock- and tag-dependent verdict in a hash-checked projection |
| D0217 | A | Wire `gen_roadmap.py` into pre-commit and make; the sitting's tier filter |
| D0228 | C | Whether, and on what terms, the store may write to a real R2 bucket |
| D0229 | A | Five custody-set items Session A found |

Added after Session A, by the owner's D0238 ruling of 2026-09-12 (D0240, D0241): D0241 joins
the queue, and two drafted patches land in this directory — `policy-envelope-sentence.md`
(the sentence claiming SpendGuard enforces the envelope operationally, which is false of the
SpendGuard that shipped) and `check-manifest-current-envelope.md` (D0229 item (5), the
comparison against every envelope rather than the current one). Both are custody-set files;
both are preconditions to the first nonzero envelope, so they belong to the pre-budget
sitting below as much as to this one.

Added again the same day by the owner's ruling on D0240/D0241 (D0242, D0244): D0242 and D0243
join the queue, and `check-manifest-current-envelope.md` now carries a **second** change — the
pre-budget lock, which refuses a nonzero envelope or ceiling while `governance/laws.yaml` lacks
the superseded entry retiring L4.4's third node, or while the clamp is absent from
`src/tannen/cli.py`. It is folded into that patch rather than drafted separately so the sitting
pays one custody regeneration and one signature; the two changes are signed, or declined,
together. The builder half of the same ruling already landed as `tests/test_spend_preconditions.py`
(D0243), which pins all four preconditions — including the two this sitting itself applies, and
which the folded guard therefore cannot honestly test about itself.

The mandatory extra sitting BRIEF §9.1 names — before any nonzero budget — is separate, and
its input is docs/specs/m4.md §4: which oracles M4 invokes, how they are priced, and what a
ceiling is a count of.

## Owed to the M4 driver, not yet drafted

Carried in from M3 and from the roadmap; each belongs in this milestone's copy of the driver.

- **Delete step 11** once `required_tags` is derived (D0205).
- **Move the receipt behind the commit confirm** — D0201 ruling (4), implemented by moving the
  confirm earlier (D0201's own reading).
- **Wire the roadmap** — D0217's pre-commit hook and make target.
- **Bootstrap an ssh-agent before offering `ssh-add`.** Measured on the owner's machine at the
  M3 sitting: no agent runs by default, the driver's bare `ssh-add` fails, and the failure is
  accepted silently, which leaves the passphrase prompt on every signature. The preflight
  should also tell "key not loaded" apart from "no agent at all" — they have different remedies.

## What Session A froze, for the sitting's reference

docs/specs/m4.md and `tests/laws/m4/` at the `m4-laws-freeze` tag: laws L4.1–L4.25, the
boundary model, its adapter, the frozen loader, and the `capture/1` schema and vectors. The
nine M3 law files are superseded forward there, not edited; their manifest note names the
successors.

---

# `boundary_sitting.sh` — the M4 driver (drafted 2026-09-13, D0247)

> **NOT CLEARED.** These bytes have had `TANNEN_SITTING_FAST` rehearsals only (verdicts below),
> which skip both `make verify` legs, the commit hooks and step 5's `check_decisions`. Only a
> full, green `--from head` rehearsal clears the driver, and it clears the bytes it ran (D0068).
> Clearance is recorded in ONE file, `CLEARED.sha256` beside this README, which
> `sitting-preflight.sh` and `gen_agenda.py` both read; it does not exist yet, so the preflight
> refuses and the agenda's banner says NOT CLEARED. The owner's choice of verification level for
> this drafting session was FAST only (interview of 2026-09-13).

Built on the M3 driver, which is byte-identical to the live `scripts/boundary_sitting.sh`. The
owner installs it the way `docs/SITTING.md` says: `make verify` first, then the `cp`, then
`bash scripts/boundary_sitting.sh m4`. Run `sitting-preflight.sh` before either.

## The step map — every queue item, and who owns what was not drafted

| Step | Item | What it does |
|---|---|---|
| 0 | M3 owings | M3's three-regime gate, unchanged; the queue shown is `ROADMAP.md` §3 (any tier), not the digest's Tier-C section; **ssh-agent bootstrap** — exit 2 (no agent) is told apart from exit 1 (key not loaded), an agent the run starts is stopped on exit, a failed `ssh-add` is reported |
| 1 | **RT-M4-02, first** (D0246 A2), D0229 (2), D0248 | `doorway-guard.patch`: `scripts/check_doorway.py` (derived network set + os shell-outs), its unit tests, the Makefile line, the tier-c.yaml custody/guard/forbidden rows, the `shell-no-subprocess` contract. Watched green on the tree and red on its fixture before "keep?" |
| 1b | safety net | `sign_tier_c_records`, unchanged |
| 2 | D0240 (1) | `policy-envelope-sentence.patch`, then policy.yaml re-signed |
| 3 | D0240 (3), D0244 (1), D0243 | `check-manifest-current-envelope.patch` (the current envelope + the pre-budget lock), then `check-manifest-shell-contract.patch` only on top of it and only if step 1 landed; then D0243's strict node rewritten to the set that is still open |
| 4 | D0205, D0229 (4) | `required-tags-derived.patch`; declined → offers `m4-laws-freeze` into the hand list under step 7's signature |
| 4b | D0215 | `decisions-verdict-out.patch`, DECISIONS.md regenerated in the same step |
| 4c | D0217 (1)(2) | `roadmap-wiring.patch` (hook, make target, and the `tests/test_roadmap.py` toggle it would otherwise redden), ROADMAP.md regenerated |
| 4d | D0229 (1) | `delegations-marker.patch` |
| 4e | D0229 (3b) | `poison-readme-corrections.patch` |
| 5 | fixtures | `doorway-network-residue`, `tag-roles-derived` (bundle generated here), `oracle-shadow-cross-file` — each offered only if its guard landed; README row and suite rows wired per installed fixture; the binding-resolve check |
| 6 | trust root | the custodian **assembled** from `custodian-hunks/` for the fixtures actually installed (`custodian.sh` here is the all-accepted assembly, for review only) |
| 7 | custody | unchanged — and now the sitting's only custody signature |
| 8 | the queue, D0217 (3), D0214's recommendation | every record `blocked-on-owner` **at any tier**; `queue_upgrades.py` upgrades its bindings (each gated on its artefact having landed) before Tier C is signed; Tier A is accepted by a status flip, unsigned; APPLIED-BY computed from the tree |
| 8b | D0214 | `upgrade_binding.py`: the nine upgrades on D0131/D0154/D0171/D0176/D0195, edit-then-re-sign one at a time |
| 8c | **RT-M4-07**, D0249 | the findings-ledger gate (inline; `ledger_gate.py` verbatim) |
| 9 | D0201 (4) | gate → **confirm commit** → custodian (receipt) → digest → regenerate → commit; nothing to commit ⇒ no receipt |
| 10 | close | clean tree + ledger gate, else refused; the tag message quotes the ledger's hash and open rows; check_tag_signers + custodian after minting |
| 11 | fallback | runs only if D0215 was declined |

**Not in this driver, and who owns each:**

- **D0228** — the owner's values (bucket, task-scoped credential, the policy line). No draft can be written; step 8 recommends leaving it blocked.
- **The superseding L4.9** deriving from step 1's guard, and **D0240 item (2)**'s CLI clamp with its successor law — M5 Session A (D0241: a successor law has no legal home inside M4).
- **RT-M4-01** — the pre-budget sitting, with a fresh spend namespace for the first nonzero ceiling (D0246 A5). Its fixture `spend-fold-forged-reservation` has no guard, so it is not offered.
- **RT-M4-03, RT-M4-05** — builder work. **RT-M4-04** — a future session; `code-address-closure` has no guard.
- **`scripts/check_drift.py`** — still outside the custody set; no record asks for it.

## What changed versus the M3 driver, and why

| Change | Why |
|---|---|
| **Every M0–M3 re-application step removed** (M3's 2, 3, 3b, 4–4l, 5b, 8b) | Each detector was evaluated against the tree on 2026-09-13: 40 checks, every one an already-applied skip **but one**. M3 step 4b still compares `ci.yml` with the M0 proposal copy that step 4f of the same driver made stale, so the installed driver, re-run today, **offers to install the M0-era ci.yml over the corrected file**. A step re-offering finished work is not a guard — it is a pointer into an older proposals directory (D0152 item 6's class). The copy reads one directory. |
| Owner edits are **`git apply` patches** (`offer_patch` / `keep_or_revert`) | `git apply --check` and `-R --check` compute "applies / already applied / neither", which M3 re-implemented per step in anchored heredocs and got wrong once (D0152 item 2). A kept patch refreshes MANIFEST rows only where one already exists, derived from the patch — never creating one (M3 4f's warning). **Measured:** all nine patches apply in driver order, each alone on HEAD, and each with every other applied; every one is detected as applied afterwards. |
| **Queue at any tier**; Tier A accepted unsigned | D0217 (3). Three of the ten queue records are Tier A and the M3 filter could not see them. A reversible record needs no signature; unsigned, its bindings stay builder-upgradable (D0214's cost). |
| **Bindings upgraded before signing** | D0214's recommendation. `queue_upgrades.py` gates each of 16 upgrades on a detector that its artefact landed; its measurement corrected two of D0214's own claims (item (1): `governance/laws.yaml` never joined the custody set, `conftest.py` did; item (8): `required_tags` is not complete). |
| **Receipt behind the commit confirm** | D0201 ruling (4), as that record reads it: the confirm moves earlier, so the receipt stays inside the commit and ahead of the tag, and a declined commit leaves no signed receipt. |
| **Step 11 deleted**, fallback only | D0205 derives the tags; D0215 removes the only tag-dependent line from a tracked projection (measured: CONCEPTS.md byte-identical on regeneration, ROADMAP.md tag-free by construction). The close is checked in seconds by check_tag_signers and the custodian. |
| **ssh-agent bootstrap** | The M3 sitting measured no agent by default, a failing bare `ssh-add`, and a passphrase per signature. |
| **Custodian and suite rows assembled per installed fixture** | M3 warned "decline the fixture, decline the custodian too". The dependency is computable, so it is computed; two POISON rows as patches would share context and fail as a subset, so they are inserted by anchor. |
| **D0243's strict node rewritten at step 3** | D0244 (3). Written from what landed, never from the node's own detector. Every change to `check_manifest.py` lands in step 3, because D0243 reads any byte change there as the envelope fix. |
| **The close tag quotes the findings ledger** | RT-M4-07, D0249. `ledger_gate.py` is embedded verbatim — `awk "/<<'LEDGER_GATE'/{f=1;next} /^LEDGER_GATE\$/{f=0} f" boundary_sitting.sh \| diff - ledger_gate.py` is empty. |
| `PROPOSALS`, `_M1`, `_M2`, `_M3` → `PROPOSALS_M4` | One directory, one line to re-point next milestone. |

## Sequencing that nothing but this file enforces

- Guards before their fixtures (steps 1, 4 → 5), fixtures before the custodian that names them (5 → 6), the custodian before the custody signature (6 → 7), the ledger before the tag (8c → 10).
- `make-fixture.sh` runs **after** the move and **before** `add_manifest_rows`: the bundle and `allowed_signers` must carry rows, or the sealed directory reddens.
- `decisions-verdict-out.patch` leaves `check_decisions` red until DECISIONS.md is regenerated — step 4b regenerates in the same breath, and step 9 again after the receipt.
- The shell contract's shape row is mandatory once applied (`check_manifest` then refuses a missing contract), so it is offered only when step 1 kept the contract.

## The drafts and their proposals

| Draft | Proposal / evidence |
|---|---|
| `doorway-guard.patch`, `doorway/`, `check-manifest-shell-contract.patch` | `doorway-guard.md` (D0248) |
| `policy-envelope-sentence.patch`, `check-manifest-current-envelope.patch`, `roadmap-wiring.patch`, `delegations-marker.patch`, `poison-readme-corrections.patch` | `policy-envelope-sentence.md`, `check-manifest-current-envelope.md`, `ownertext.md` |
| `required-tags-derived.patch` + `docs/redteam/fixture-candidates/tag-roles-derived/` | `required-tags-derived.md` |
| `decisions-verdict-out.patch` | `decisions-verdict-out.md` |
| `docs/redteam/fixture-candidates/oracle-shadow-cross-file/` | `oracle-shadow-cross-file.md` |
| `queue_upgrades.py`, `upgrade_binding.py` | `binding-upgrades.md` |
| `docs/redteam/LEDGER.yaml`, `ledger_gate.py` | `ledger-gate.md` (D0249) |
| `custodian-hunks/`, `suite/`, `poison-readme-row-*.md`, `custodian.sh` | this README |
| `sitting-preflight.sh`, `gen_agenda.py` → `AGENDA.md` | this README |

Two measured corrections to documents in this directory, recorded here rather than by editing
them: `check-manifest-current-envelope.md`'s row (b) now FAILS where its table says PASS — the
table predates the lock fold, and with both M5 owings landed it passes (`ownertext.md`); and its
code omits `from collections.abc import Iterable`, which the patch adds.

## Rehearsals — FAST only, so these bytes are NOT cleared

Every run below set `TANNEN_SITTING_FAST=1`, ran in `--from worktree` mode (so step 0 took the
RESUMED path and its precondition gate was not exercised), and used
`TANNEN_REHEARSE_DRIVER` pointed at this directory's copy. FAST skips both `make verify` legs,
the commit hooks and step 5's `check_decisions`; the harness's own post-run `check_decisions`
still runs in the clone.

**What the first accept run found, all fixed before the runs that follow it:**

- **Step 5 moved `doorway-network-residue` and left three records binding its old path** (D0245,
  D0246, D0248 — all Tier A, unsigned). The driver exited 0 and every driver-side check passed;
  the harness's own `check_decisions` in the clone failed on exactly those three bindings, plus
  two `tests/test_governance_scripts.py` nodes (D0063, D0177) that were the same fact seen twice —
  with the real-tree `check_decisions` case deselected, that file ran 33 passed in the kept clone.
  Step 5's binding check is skipped whole under FAST, so no line of the driver could see it. M3
  retargeted D0141 and D0199 by name; `retarget_bindings` now derives every unsigned record bound
  under the candidate directory, refuses a signed one before writing anything, and refuses a
  target that still does not resolve. Watched: three records retargeted (target lines only), a
  planted `.sig` refused with nothing written, an absent target refused with nothing written, a
  re-run a no-op.
- **The harness exited without a verdict** after writing `check_decisions.txt` — no `rehearsal:`
  line, no process left, nothing in the journal, and `set +e` is in force at that line, so the
  cause is not found. The harness is custody-set and was not edited; later runs wrap it in an
  exit-status line so a silent exit is visible.
- **Step 8 kept every binding upgrade unseen.** `queue_upgrades.py` prints one `upgraded: …` line
  per upgrade and the record's path last; the driver compared the WHOLE output to the path, never
  matched, and so neither showed the diff nor asked "Keep these binding upgrades?" while 16
  upgrades landed; the driver now compares the last line. The evidence is the branch, not the
  prompt text: `confirm` uses `read -p`, which prints nothing when stdin is not a terminal, so NO
  prompt reaches a rehearsal transcript (the thirteen "Accept …?" prompts count zero too). Run
  one shows zero "upgrades kept" notes and each record's path echoed by the non-matching branch;
  run two, on the fixed bytes, shows eight "upgrades kept" notes — one per record with upgrades —
  and five "nothing landed".
- **Step 8c opened the editor on "y".** It asked "Edit the ledger?", so an accept-everything run
  handed the ledger to `$EDITOR` (the harness's BRIEF shim, which failed harmlessly). It now asks
  whether the dispositions stand, and `n` opens the editor.
- Two prompts were spelled `if ! confirm`, which `gen_agenda.py` reads as having no decline arm
  and so told the owner that answering y to "Keep these binding upgrades?" restored the backup.
  Both are spelled positively now; AGENDA.md regenerated.

| Run | Driver sha256 | Verdict |
|---|---|---|
| FAST accept (first) | `4faf018…` | **FAIL.** The driver exited 0 over 4158 transcript lines: m4-close minted and verified, receipt signed, custodian green, nothing uncommitted. The clone's `check_decisions` was red on the three bindings step 5 broke (fixed above), and the harness exited before printing its verdict. |
| FAST accept (second) | `5057e6c…` | **"the sitting completes"**, harness exit 0. Every check ok, including the clone's `check_decisions` (green, 0 queued) and every step recorded through the last. Step 5 retargeted D0245/D0246/D0248, and the other two fixtures had nothing to retarget. Step 8 showed 8 "upgrades kept" and 5 "nothing landed". Two lines were listed as unexpected failures, and both were the driver's own watched-failing demos: step 1's guard on its poison, and step 3's custody-drift-only `check_manifest`. Their summary lines are now restated once the expected outcome is confirmed, which changes the bytes for the runs below. |
| FAST decline-all | `1ae556f…` | **"the sitting completes"**, harness exit 0. Step 9's tree was dirty, and the declined commit took NO receipt. Step 10 refused to tag the uncommitted tree: `sitting: STOP`, `reached: step 10`, exit 1, with the undo given. The unexpected-failure section was empty. |
| FAST abort at step 9 | `1ae556f…` | **"the sitting completes"**, harness exit 0. `--abort-at 47 --abort-step 9`: prompt 47 fell in step 9, the commit confirm, and the prompt map agrees. The declined commit took no receipt, then step 10 refused the dirty tree: `sitting: STOP`, exit 1, with the undo given. m4-close was not minted, and the unexpected-failure section was empty. |

## Found while drafting, for the owner

- **The harness's decline-path explanation is stale.** `scripts/rehearse_sitting.sh` still says a
  fully declined sitting stops at step 10 because "step 9's receipt is written unconditionally".
  This driver implements D0201 ruling (4): a declined commit takes no receipt. The decline run
  still stops at step 10, but the reason is that the sitting's own edits leave the tree dirty.
  The check is right and the sentence is wrong. A sitting with nothing to commit would now
  close without a receipt, and the harness would call that a failure. The harness is
  custody-set, so it was not edited.

- **RT-M2-03** has no record after D0141 and is absent from both the M3 and M4 status audits — a
  finding that may simply have been dropped, which is RT-M4-07's exact shape. The ledger records
  it `deferred` for that reason; rule on it at step 8c rather than inherit it.
- The runner door for the derived scan hides three imports, not one: `hypothesis` and `pytest`
  (plugin.py) and `jsonschema` (evidence.py).
- Two limits of `check_doorway.py` found by reading it, not yet measured: the shell-out rule
  matches the literal name `os` (so `import os as o; o.system(...)` passes), and the process rule
  is by module NAME, not closure (a stdlib module that spawns a child itself is not refused on
  that ground). Recorded in D0248 item (5); neither blocks installing it, since each is strictly
  more than L4.9 checks today.
- `test_check_passes_on_real_tree` (D0177's binding) was not confirmed against the D0215 patch in
  a drafting clone — it timed out at 590s. The rehearsal verdict's own `check_decisions` covers it.
