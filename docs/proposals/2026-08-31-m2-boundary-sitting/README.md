# M2→M3 boundary sitting — the materials the owner applies

Staged here because most of it edits something the builder may not: a custody-set path, a
Tier-C record's signature, the trust root's derived tag list. `boundary_sitting.sh` (this
directory's own copy) applies the mechanical parts in order; **`D0131` is the deciding
document** — read it first, with `D0138` beside it, the way `CONFERRAL.md` was the deciding
document at M0→M1 and `D0105` at M1→M2. Everything else about how a boundary sitting works is
unchanged from `docs/SITTING.md`.

> ## ✅ READY TO RUN — rehearsed green on every path
>
> Updated 2026-09-02, third pass. The red team has run
> (`docs/redteam/2026-09-01-m2-boundary.md`, D0141 — eight findings, one critical) and its
> queue is drafted into the driver as steps 4e, 4f, 4g, 4h, 4i, 4j, 5 and 8b. Two queued
> items closed themselves as builder work and need nothing from you.
>
> **The driver has now completed a green run on the shape you will use.**
> `--from worktree --answers y`, 2026-09-02: **13 of 13 verdict checks**, `rehearsal: the
> sitting completes`, 106 minutes. `m2-close` minted by that run and verifying as
> `owner@tannen`; custody set signed; a fresh attention receipt taken and signed; the
> custodian green with **no tolerances**; the clone's own `make verify` green end to end;
> nothing left uncommitted; no Tier-C door left unsigned. `--from head --answers y` reached
> the same place independently, and `--from head --answers n` covered the decline path.
>
> **It took six runs to get there, and that is the point of rehearsing** (D0068, D0147,
> D0148, D0149). The finished driver failed its first three runs, one defect each, and every
> one of them was an *interaction* — a step versus a file it never names — that reading and
> per-step sandboxing had both missed: step 5's `git mv` orphaning D0141's binding; step 4g's
> guard patch reddening four cases of `tests/test_tier_c_signatures.py`, a file it never
> mentions; and `DECISIONS.md` left stale at step 11's closing gate. **A run stops at its
> first failure, so each run tested only as far as it got — the count of runs is not
> coverage, and only a green run clears the driver.**
>
> **One expected failure line, and you should see it.** At step 5 the transcript prints
> `check_decisions: FAIL (2 violation(s))` — D0063's binding on `tests/test_governance_scripts.py`,
> and `DECISIONS.md` stale — because mid-sitting the tree is legitimately dirty. **Two is
> correct; more than two is new and worth stopping for.**
>
> **Two things the runs corrected in this README's own earlier text**, kept because a
> retracted claim is easier to trust than a quietly deleted one:
>
> - The `--from head --answers n` path was described here as *cheap*. It is not: it costs
>   about an hour, because only step 9's **commit** sits behind a `confirm` — its gate,
>   custodian and digest run whatever you answer. Its non-zero exit is also **not** a defect;
>   it is step 10 refusing to tag a tree whose signed receipt is uncommitted (D0051), which
>   is the guard working. (D0148)
> - Run 3 was described as failing because *both* of the projection's clock-dependent inputs
>   arrive after it is generated. Only one does. Step 9 regenerates **twice** — once at its
>   top and again via `make digest` at its end, after the receipt is written and signed — so
>   the close tag is the sole input arriving after the last regeneration. The step-11 fix is
>   unchanged; the reason for it is narrower and stronger. (D0148)
>
> **A coverage note that is in the harness, not in either driver.** Under `--from worktree`
> the harness enrols a throwaway key, rewrites `MANIFEST.sha256`, regenerates
> `governance/custody.sha256` and re-signs it before the driver starts, and those four edits
> stay uncommitted — so the `RESUMED` test sees tracked modifications and reports a resumed
> sitting, **correctly, on the evidence in front of it**. `--from worktree` therefore can
> never exercise the `RESUMED=0` branch, which is precisely the RT-M2-06 D1 fix; only
> `--from head`, which commits the fixture's edits, leaves a clean tree. Both were run.

## Run the gate BEFORE you copy the driver in

```
make verify
cp docs/proposals/2026-08-31-m2-boundary-sitting/boundary_sitting.sh scripts/boundary_sitting.sh
bash scripts/boundary_sitting.sh m2
```

The `cp` is custody drift on a custody-set path, and `check_manifest.py` is the first recipe
line of `make verify` — so after the copy the gate fails at line one and `make` stops before
`check_decisions`, the pytest suite, the laws report or `lint-imports` ever run. Step 0's own
gate offer therefore cannot establish the precondition it exists for: at rehearsal it
advertised 35-40 minutes and returned in **zero seconds**, then correctly reported no
unexpected failures — over a run that had executed three lines. Take the offer anyway (on a
re-run with the driver already installed it runs in full and means what it says), but the
green gate this sitting rests on is the one you take BEFORE the copy. (D0151)

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
run it is checking.

**Three runs, and each covers something the others cannot.** All three were run green on
2026-09-02; re-run them after ANY edit to the driver, and pass `--keep` or the clone and
its transcript are deleted on exit and only the verdict summary survives.

```
# 1. RESUMED=0 + the decline path — head mode commits the fixture's own edits, so the
#    tree is clean and step 0's precondition gate runs. Budget ~1h: `n` declines step 0's
#    gate but step 9's gate, custodian and digest are NOT behind a confirm and run anyway.
#    Expect a non-zero exit: step 10 correctly refuses to tag over an uncommitted receipt.
… scripts/rehearse_sitting.sh --milestone m2 --from head --answers n --keep

# 2. the same RESUMED=0 entry with the gate ACCEPTED. ~2h: step 0's gate, step 9's gate,
#    and the verdict's own make verify.
… scripts/rehearse_sitting.sh --milestone m2 --from head --answers y --keep

# 3. the shape you will actually run — entering at RESUMED=1, as you will. ~1h45m.
… scripts/rehearse_sitting.sh --milestone m2 --answers y --keep
```

The thirteen verdict checks key off whether the run mints `m2-close`, **not** off the mode,
so runs 2 and 3 are both scored on all thirteen. Run 3 matters for its entry shape, not for
extra coverage.

**The test count you should see, because three different numbers are in play.** The gate
runs **715 passed / 1 skipped / 1 xfailed** before the sitting and **716** after it — step 5b
lands the RT-M1-05 guard patch together with its fixture, and that fixture is a test. The
driver's own `waiting` lines still say *"712 tests"*; that figure is stale and deliberately
left alone, because editing the driver invalidates the green rehearsals and costs about four
hours to re-prove, to correct a parenthetical nobody acts on. The ETA beside it — 35-40
minutes — is current and is the number that matters. Rising from 715 to 716 across the
sitting is expected, not drift.

**Never edit the driver or the harness while a run is executing it.** `bash` reads a script
incrementally by byte offset, so an edit mid-run kills the running shell with a syntax error
on a line that is perfectly valid — and takes the verdict's failure-analysis section with it
(D0149).

Read each verdict **and** the "Unexpected failure lines" section beneath it — a driver that
prints FAIL and carries on is worse than one that stops.

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
| **Seven new steps: 4e, 4f, 4g, 4h, 4i, 5's fixture, 8b** | The queue, drafted. See **The queue, as drafted into this driver** below for what each does and the three judgement calls inside them. |
| **Step 9's binding-count ETA is derived, not written** | Same class as `VERIFY_ETA`, fixed structurally rather than re-measured. The line promised *"about 10 minutes (54 pytest bindings)"*; the real number is now 73, and that literal is what got the driver killed at the real M1 sitting once already (D0069, one step further in). It is now read off `decisions/` at run time by `grep -A1 'type: pytest'` over unique targets, so it cannot go stale — the same move D0142 made on the oracle set, for the same reason: a hand-maintained constant in a governance script is a constant that is one milestone behind at every boundary. |
| **Step 4f does NOT call `regen_manifest_row Makefile`** | Custody membership and `MANIFEST.sha256` rows are **independent sets**, and this is where that bites. The Makefile is custody-set with **no** manifest row (nor have `.pre-commit-config.yaml`, `governance/policy.yaml`, `scripts/_gov.py`, `check_decisions.py`, `gen_projections.py`). Calling `regen_manifest_row` on it would not refresh a row — it would **create** one, silently enlarging the frozen-path set at a sitting. Caught by checking rather than by pattern-matching the neighbouring line, which did call it, correctly, on `ci.yml`. |
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

## The queue, as drafted into this driver

Every item below is a step in this directory's `boundary_sitting.sh`, in dependency order.
Each one guards its own idempotence, shows a diff, asks once, and reverts everything it
touched if the answer is no. Each was applied in a sandbox and **watched refusing a second
application**, because a step that silently applies twice is worse than one that fails.

| Step | Item | What it does |
|---|---|---|
| **4e** | D0131 item 3, **as RT-M2-02 corrects it** | `conftest.py` and `scripts/check_laws.py` into the custody set. **Not `governance/laws.yaml`** — see below. |
| **4f** | D0131 item 4 | `check_laws.py` into `Makefile` (CI inherits it via `make verify`); `ci.yml`'s comment block and `tests/test_law_validation.py`'s docstring move with it. |
| **4g** | RT-M2-05 | `check_decisions.py` learns to compare `DECISIONS.md`'s date-dependent claims against what today computes — **and `tests/test_tier_c_signatures.py`'s throwaway projection moves with it**, or four of that file's cases go red (D0147). |
| **4h** | D0123 / D0131 item 7 | Three binding upgrades — D0110, D0108, D0095 — each edit-then-sign, one record at a time. |
| **4i** | D0131 item 8 = D0106 item 1 | Optional `bindings_count` on the decision schema, the check that reads it, and its regression test — all three together. |
| **4j** | D0131 item 2 = D0117 | Optional `examined` `{law_nodes, test_cases}` on the evidence schema, plus `build_record` and the plugin that fill it. Schema first — proven, not assumed. |
| **5** | RT-M2-01 | Installs `oracle-shadow-model`, this milestone's poison fixture, and its README row — then **retargets D0141's binding** to the installed path, because the `git mv` orphans it (D0147). |
| **8b** | D0138 item 1 | Renames the alarm node, retargets **three** bindings, re-signs D0110. |

**D0110 is signed twice in one sitting, and that is intended.** Step 4h upgrades its
`src/tannen/kernel/rel.py` binding and re-signs; step 8b then retargets its alarm-node
binding and re-signs again. They are separate queued items (D0123 and D0138 item 1) and
either can be declined on its own, so merging them to save a passphrase would cost you that
choice. The two edits do not touch the same binding, and step 8b's guard expects exactly one
target naming the old node — which is still true after 4h.

### The three judgement calls inside them

**D0131 item 3 does not include `governance/laws.yaml`, and that is a decision.** RT-M2-02
showed the naive form buys nothing: `conftest.py:24` is
`SUPERSEDED_REGISTRY = ROOT / "governance" / "laws.yaml"`, and that line does not read the
registry — **it chooses which file is the registry**. Reproduced with `laws.yaml`
byte-identical, its signature verifying, and the pin in `tests/test_law_validation.py`
passing unmodified. So the set is the two files that decide *where* the registry lives.
Leaving `laws.yaml` out preserves what D0128 was designed for — a `pending`→`superseded`
promotion stays a two-line builder move rather than becoming an owner act at a sitting. The
residual attack is then not "edit a line" but "invent a successor law and a decision
record", which `check_laws.py` already refuses unless both exist, and which leaves a trail.
Step 4e says how to add `laws.yaml` by hand if you want the stronger property anyway.

**`tests/test_law_validation.py` is deliberately not frozen.** It is the file the attack
also edits, which makes freezing it tempting — but it changes at every milestone by design
(it pins the current registry's single entry by name), and custodying it would halt
Session B until a sitting. Step 4f is the answer instead: give the guard its own way into
the gate so it no longer arrives only as a subprocess of the file under attack.

**D0106 item 3 — the mechanics/kernel line-count ratio — is NOT a step, and declining it is
the recommendation.** Four reasons, three of them measured:

1. **D0106 disqualifies it itself**: *"Filed as a proposal, not a ruling, because unlike (1)
   and (2) the reviewer offered it as a suspicion to test, not a decided rule."* D0116 is the
   governing precedent — adding a ratcheted metric to a confirm-and-diff sequence
   "would present a decision as a formality".
2. **The number is not defined.** Faithful readings of the one sentence give **1.45, 2.48,
   2.79, 3.52 and 4.06**. One of its three named arms (`tests/poison/`) contains a binary git
   bundle whose line count is 8 or 12 depending on the implementation.
3. **The naive ratchet is provably wrong.** Measured across every boundary tag, the ratio
   goes 384.50 → 316.00 → 11.69 → 11.71 → 2.74 → 2.89 → 2.79. It *rises* at
   `m1-close → m2-laws-freeze` purely because Session A adds guards against a frozen kernel.
   A gate on it fires at every laws-freeze, forever, unless "measure at `*-close` only" is
   decided first — which item 3 does not say. It also fell from 384 to 2.79 while mechanism
   *tripled*, because the denominator was the kernel being written.
4. **BRIEF §9.1's metric-calibration rule forbids enforcing it here anyway**: land the
   measurement, publish one digest carrying true values, and only then compare.

And one mechanical trap worth recording even though nothing acts on it: the third metric
must go on **its own comment line with its own regex**, never by extending `METRICS_RE`
(`_gov.py:22`). Every existing digest carries two fields — including
`tests/poison/check-decisions-ratchet/digest/2020-01-01.md`, which is `MANIFEST.sha256` row
35 *and* custody-set, so the builder can never regenerate it. Extending the regex in place
silently disarms the whole ratchet: measured, the poison fixture stops emitting
`RATCHET BREACH` and three `tests/test_governance_ratchet.py` nodes go red.

### Two items that left the queue without needing you

- **D0131 item 6 (D0124)** — closed as **builder work** on 2026-09-01, no signature involved.
  The tripwire was live: `binding_violation(root, "pytest", "tests/test_operating_manual.py")`
  returned a violation against the real tree, because `sorted(KNOWN_DIVERGENCES)[:]` is empty
  and pytest skips an empty parameter set with a reason no allow-list entry matches. D0124
  offered two fixes; the allow-list was **not** widened — that list is the guard's whole
  discrimination, and admitting a pytest-generated string would admit every future empty
  parametrize including the real defects. The parametrized test became one that asserts the
  map is empty *and* that any entry names a real command, so the check states its input set
  rather than vanishing with it. Seven passes, zero skips, guard verdict `None`.
- **RT-M2-01** — the guard half closed as builder work (D0142); only the fixture install at
  step 5 is yours. `src/` carries no manifest row and no custody entry.

### Before you start: five seconds that can save the sitting

```
find tests/poison -name __pycache__ -type d      # must print nothing
```

`scripts/custodian.sh:66` enumerates `find tests/poison -type f` and requires a manifest row
for **every** result, with no `__pycache__` exclusion — while `check_manifest.py:113` skips
those paths by name. So a stray `.pyc`, which any import from `tests/poison/` without `-B`
creates, leaves `check_manifest` green and the custodian red. The driver's
`unexpected_failures()` does not tolerate a `not manifested:` line, so step 0's gate would
stop the sitting over build debris — and the message reads as "add a manifest row", which
would be wrong twice (the file is gitignored, and its name carries the interpreter version).
Cost this pass 37 minutes of gate. The one-line exclusion is queued for M3 rather than added
here: `custodian.sh` is the trust root, and step 6 would need a newly tuned copy for it
(D0146).

### One follow-up this pass deliberately did not ship

**D0130's `event()` counts are the answer D0117 really wants, and they are not safe yet.**
They are reachable — `hypothesis.statistics.collector` from a `trylast` hookwrapper yields
exact integers — but hypothesis writes its **own internal retry notes into the same
undifferentiated dict** (`control.py:294-311` plus five internals sites). Wired in, M2's
laws yield `{'overlap: partial': 1700, 'table a: empty': 378, …}` — exactly what D0117
asks for — while M0's yield a wall of version-dependent strategy `repr`s. There is no
marker separating a law's declared shape from hypothesis's bookkeeping, and
`describe_statistics`'s own docstring disclaims format stability. Step 4j ships the
countable tier instead and says so; the non-degeneracy split is its own record.

## What the sitting ends with

The receipt, then `m2-close`, in that order — so the clock starts against a boundary tag rather
than stopping. Then M3 Session A, fresh session, new worktree.
