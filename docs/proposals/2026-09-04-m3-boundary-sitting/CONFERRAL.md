# M2→M3 boundary sitting — the conferral brief

**Written 2026-09-05, at `7d57ff0`, by the builder that wrote M3's implementation.**
Treat every claim of the form "this is closed" as a claim to be tested. The last two
boundary red teams each found something self-review had missed, one of them critical.

`docs/SITTING.md` says how a sitting is run. The queue is **D0154**. This document
answers the question neither does: *what am I being asked to decide, what is not ready,
and where should I be suspicious?*

---

## Rulings (2026-09-05) — the conferral is closed; this section is the outcome

Recorded in full as **D0171** (unsigned until the sitting). Everything below this section
is left exactly as it was written, so the questions and the answers can be read against
each other — the M0 conferral's precedent.

| # | Ruling | Landed as |
|---|---|---|
| 1 | **`advance`/`record`: the reading stands** — recording is caller policy, consistent with M1's rebuilder split. But m3 §7's sentence is false as written, so **supersede the prose forward** under D0128 rather than gloss it. *"The gap between what's frozen and what's true is exactly where the next D0049 will hide."* | owner act at the sitting |
| 2 | **`derivation_id` stays order-insensitive; no widening at M4.** A caller passing operands in the wrong order is a type-system problem misfiled as an identity problem. Revisit only with evidence. | no change — §4 stands |
| 3 | **Standing rule: no guard may depend on a hand-maintained enumeration** of milestones, tags, fixtures or laws. Derive; where derivation may over-fire, derive **and** assert. One audit item, not four. | D0172 — seven lists, two defects, one closed |
| 4 | **D0154 splits by consequence.** Floor-integrity items (1, 7, and 2's receipt clause) go in *this* sitting; 3, 4, 5, 6, 8, 9 wait. *An unexercised custody fixture is a silent floor failure, which is the category the floor exists for.* | §3's table, re-ordered at the sitting |
| 5 | **The mechanics ratchet is a measurement to fix, not a metric to drop.** Normalise per milestone, or measure at boundaries only. | D0173 + `mechanics_metric.py` |

Also recorded as advice rather than ruling: **bring D0115 (publish) forward** rather than
leaving it behind nine queue items — a remote is a real external witness, and it is the
one change that *reduces* the machinery instead of adding to it.

**Two premises of the conferral message are corrected in D0171,** because both bear on
ruling 5 and one makes its own case stronger. The repo is **twelve days old**, not three
months (first commit `5c3a474`, 2026-08-24; 74 commits). And **three** milestones are
closed — M3 is implemented and not yet closed; `m3-close` is what this sitting mints.

**What the audit found that this document did not ask about.** Ruling 3's sweep turned up
a defect worse than any enumeration lag: `governance/laws.yaml` — the file whose only job
is to decide which law nodes run — is **outside the law descriptor's subject**. Appending
to it leaves `harness_subject` byte-identical, so retiring a law node invalidates no
evidence record. That is RT-09, the finding L1.17 exists to close, one file over, and it
has been true since M2. The enumeration that lagged is the parametrize **inside frozen
L1.17 itself**. D0172 (A) has the measurement and the cost of the fix.

---

## 1. The short version

**M3 is implemented and green.** 38 M3 law nodes, zero skips; 52/52 laws across M0–M3
carry fresh passing evidence; every `make verify` step green; no frozen path touched.
Recorded as **D0170**.

**The sitting cannot be scheduled yet.** Two builder tasks stand before it, and neither
is optional:

| # | Task | Why it blocks | Whose |
|---|---|---|---|
| A | **The M2→M3 red team** | BRIEF §9.1 point 5 mandates one at every boundary. D0104 requires a fresh context that did not write the implementation. | Builder, **fresh session** |
| B | **The M3 sitting driver** | `scripts/boundary_sitting.sh` is today *byte-identical* to the M2 draft. It is the M2 driver. | Builder, then rehearsal |

**Two rulings are needed from you** (§4), both places where M3's implementation is
*narrower* than frozen prose and neither repairable by the builder.

**Nothing in this directory enforces anything.** The repo is green with every draft here
unapplied. Declining any item leaves the others intact.

---

## 2. Why the red team is not in this document

The honest answer is that this session cannot perform it. D0104 fixed the rule after the
M0→M1 pass: a boundary red team runs in a fresh context that did not write the
milestone's implementation. This context wrote M3's implementation, and is additionally
barred from dispatching subagents, so the M1→M2 method (D0141: six pre-registered probes,
each a fresh context, every exploit re-run by the dispatcher) is unavailable here too.

The tempting move is to self-review and call the result a red team. That is refused,
because the record says what it would be worth:

- **RT-M1-01** — the oracle-shadow hazard. Self-review did not find it.
- **RT-M2-01** (critical) — its own partial closure coming due. A decoy module made
  BRIEF §6's differential kill-criterion law *vacuous* while all 113 M2 law tests passed
  and `check_manifest` reported seals unbroken. Self-review did not find that either,
  and the fix for it is item (1) of the queue below, **still not installed**.

So: **schedule the sitting only after a fresh session has run the M2→M3 pass.** Its
findings become `RT-M3-xx`, become poison fixtures (D0021), and join the queue. Two
places to point it, from this session's own vantage:

- `tannen.incremental` (725 lines) and `tannen.kernel.delta` (465) are new public
  surface that no adversarial reader has seen.
- `src/tannen/laws/` is inside `implementation_subject`, so it is *both* the machinery
  that records proof and part of what the proof is about. D0169 (§5) is one defect found
  there this session by accident. Nobody has looked on purpose.

---

## 3. What needs your key — D0154's nine items, re-measured today

Every item below was verified open on 2026-09-05, not carried forward on trust. The
measurement is quoted so you can falsify it in one command.

| # | Item | Verified today |
|---|---|---|
| 1 | **The custodian never runs the fixture the M2 sitting installed.** `tests/poison/oracle-shadow-model/` (RT-M2-01's fixture, the M1→M2 pass's one critical finding) has no `poison` line. | `grep -c oracle-shadow-model scripts/custodian.sh` → **0**. It is the only one of **14** fixtures without an invocation. The custody floor reports "intact" without ever exercising it. |
| 2 | D0152 items 1–5: the retarget guard that re-arms on its own success; step 4f's skip-guard reading a file its decline branch reverts; the receipt signed without checking `ssh-keygen -Y sign`'s exit status; no lock on a single-run ceremony; the installed fixture's README still opening "**needs patch**". | Unchanged — `scripts/boundary_sitting.sh` is byte-identical to the M2 draft. |
| 3 | `custodian.sh:268` picks the previous receipt with `tail -1`, so a same-day re-run silently drops the chain line. `check_receipts` parses only `- HEAD:` and notices nothing. | Unchanged. |
| 4 | `custodian.sh:66` and `check_manifest.py:113` disagree about `__pycache__`. A stray `.pyc` under `tests/poison/` reddens the floor ~37 minutes into `make verify`, with a message that invites the wrong fix. | Unchanged. |
| 5 | **A declined sitting is not a no-op.** The receipt is written and signed before you are asked to commit anything, so abandoning a decline leaves a signed receipt untracked — which the next run reads as `RESUMED=1` and skips the precondition gate. | Unchanged. Moving the receipt behind a confirm reorders the receipt-then-tag argument (D0071), which is why it is yours. |
| 6 | `governance/tag-roles.yaml` `required_tags` **lags for the third time**. | `git tag` lists `m3-laws-freeze`; `required_tags` does not. Minted under delegation 1 at `f5d94c2`; the builder may not add the row. |
| 7 | `scripts/check_laws.py` has **no poison fixture**. | `grep -c check_laws scripts/custodian.sh` → **0**; no `tests/poison/*` directory targets it. It is the only custody-set guard with no fixture — and it is the guard that can retire a frozen law. |
| 8 | D0117's `event()` follow-up. Any clean answer touches `governance/schemas/evidence-record.schema.json`: frozen, sealed and custody-set. | Unchanged. |
| 9 | The driver's transcript hardcodes "712 tests". | The suite now collects **829**. Two sites: `boundary_sitting.sh:66` and `:74`. |

**Item 1 is the only one with a ready draft.** `custodian.sh` in this directory is the
live file plus four delimited hunks, each mapped to an item above (hunks 1a/1b/1c → item
1, hunk 2 → item 2's receipt clause, hunk 3 → item 4, hunk 4 → item 3). The README here
walks them. It has been reviewed by nobody but its author.

---

## 4. The two rulings M3 needs from you

Both are places where the implementation is **narrower than the frozen prose**, both
were found by implementing rather than by reading, and neither can be repaired by the
builder. Recorded in full as **D0167**.

### Ruling 1 — §7 says "replaying a stream hits traces". It does not, by default.

`advance` **consults** the trace and by default does **not write** one; `record=True` is
the caller's act.

This is forced, not chosen. Frozen `test_l3_15_a_tampered_trace_raises` calls
`traces.record(done.step_id, <garbage>)` *after* a successful `advance` and *outside* its
`pytest.raises` block. `TraceStore.record` raises on a conflicting re-record — so an
`advance` that recorded under `step_id` would make that line raise and turn a frozen law
into an error rather than a pass.

The reading taken: recording is a *policy*, exactly as M1 already makes it one between
`AlwaysRebuild` and `VerifyingTrace`; `advance` takes the same choice as a flag,
defaulting off. Consequently `rebuilt` reports whether a step's output was **new to the
store**, not whether a function ran.

**What you are ruling on:** whether that reading stands, or whether the frozen node is
wrong and should be superseded forward (the D0128 mechanism). Superseding is yours;
editing a frozen law is nobody's.

### Ruling 2 — a binary node's operand order is not part of its step id.

`advance(node, None, [a, b])` and `advance(node, None, [b, a])` share a `step_id` while
computing different things.

This is **inherited, not invented**: `derivation_id` is order-insensitive by frozen M1
design (m1 §8, L1.13), M1's own `Node(transform, inputs)` has the identical property, and
m3 §7 pins the formula ("sorted delta refs"). It is pinned by a test that says in its own
name that a decision is being reversed if the formula changes.

**What you are ruling on:** whether this is acceptable as inherited, or whether M4 should
carry a widening of `derivation_id`. Changing it means changing frozen M1 semantics.

---

## 5. Where to be suspicious

**The defect this session found is in the machinery that records proof.** D0169: the law
locator read only the leading number of a test's name, so `test_l3_1_through_4_…`
resolved to L3.1 alone and **seven laws the frozen m3 §10 table declares were invisible**
to discovery, to the report and to the evidence stream. `docs/specs/m3.md` §11's own
completion criterion — "fresh evidence for L3.1–L3.16" — was not merely unmet but
*unmeetable*. `make verify` could not have been green at `d7dd372`, Session A's tip, and
that was measured in a throwaway worktree at that commit rather than argued.

Nothing failed loudly. The M3 laws passed. `check_laws` passed. The report printed nine
cheerful M3 rows. The only thing that could tell was
`test_discovery_matches_the_frozen_spec_table` — **and it was parametrised over a
hand-written `["m0","m1","m2"]`, so the one milestone whose laws were newest was the one
milestone it did not check.**

That is the same shape a fourth time:

> An enumeration extended by hand at every boundary is a milestone behind at every
> boundary.

D0095 (`required_tags`), D0131 item 5 (`required_tags` again), D0142 (the oracle map),
now this. Item 6 of the queue is `required_tags` **for the third occurrence**, still
enumerated, still owner territory. The general fix — derive the set — is D0095 half (2)
and has been available since M0.

**The question worth putting to the red team:** what else in this repo is checked only by
a test parametrised over a hand-written list?

---

## 6. The order things must happen in

1. **A fresh session runs the M2→M3 red team.** Findings → `RT-M3-xx` → poison fixtures →
   the D0154 queue.
2. **The builder drafts the M3 driver** from the live one: retune M2's steps, fix the 712
   count, and carry D0152 items 1/2/4/5, D0148 item 5 and queue items 6–9 as steps.
3. **Rehearse it end to end** before it touches your key (D0068). The rehearsal is not
   ceremony: D0147, D0148, D0149, D0150 and D0151 are five defects that *only executing
   the driver* could find, including one that made a filed, ready, owner-blocked item
   unreachable for two sittings running.
4. **The sitting.** Your key: the custodian hunks, `required_tags`, the two rulings in §4,
   and whatever the red team adds.
5. **`m3-close`**, owner-signed (D0049). The standing delegation does not cover it.

---

## 7. What is green, so you can check the floor before reading any of the above

```
uv run pytest tests/laws/m3                  # 38 passed, zero skips
uv run tannen laws report                    # OK — 52 law(s) carry fresh passing evidence
uv run python scripts/check_manifest.py      # frozen paths intact; seals unbroken
```

Attention receipt: **fresh** (2026-09-03, valid to 2026-09-10). Tier-B silence-consent is
therefore live, and no Tier-C item above blocks other work — BRIEF §9.2's non-blocking
rule holds, which is why M3 shipped with all nine queue items open.

One caveat on reproducing the gate: `make verify` **cannot be run as one command in this
environment** — background processes are reaped after ~10–15 minutes. Its steps run
individually; the pytest step splits into chunks. That is an environment fact, not a
repo one, and it is recorded in D0170 so the next reader does not read a chunked run as
a partial one.
