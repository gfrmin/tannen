# CLAUDE.md — operating manual for agents working in tannen

This file is the **how**. The **what and why** live in [`BRIEF.md`](./BRIEF.md) — the
constitution, frozen at the `brief-freeze` tag. This file defers to it and does not restate
it; where they appear to disagree, the brief wins and the discrepancy is a bug to report.

## Orientation (read in this order, every fresh session)

1. `BRIEF.md` §1–§2 (what this is; the concept registry and its grades) — always.
2. The brief section for the layer you are touching (§4 calculus, §5 defaults, §6 laws,
   §7 governor seam, §8 milestones).
3. The generated `DECISIONS.md` projection (or `make digest` output) and the current milestone's plan doc.
4. `CONCEPTS.md` if your work touches anything adopted from another repo.

## Hard rules (Tier C — stop and ask the owner; full list in BRIEF §9–§10)

- Never add a dependency on, or import from, any other repo of the constellation
  (pkm, life-agent, credence, proplang, the Renavon monorepo). In either direction.
- Never spend beyond `budget.yaml`. Never delete or overwrite store content.
- Never edit a frozen path (anything listed in `MANIFEST.sha256`).
- Never change BRIEF §3 (principles), §10 (non-goals), or an owned concept's definition.
- Never implement the Governor (§7) — the seam and its Grade-S wire schema only.
- `scripts/custodian.sh`, `allowed_signers`, `tests/poison/` and their `MANIFEST.sha256`
  entries are **author-key territory** (BRIEF §9.1): only the owner edits them.
- On a **stale attention receipt** (BRIEF §9.1), treat all Tier-B decisions as blocked
  and pause work at the next milestone boundary.

## The build protocol (per milestone; BRIEF §8)

Two sessions, adversarially separated:

- **Session A — spec & freeze.** Plan mode. Write the milestone spec
  (`docs/specs/<milestone>.md`), then the law/property files for the milestone. Add them to
  `MANIFEST.sha256`. Builder-signs the `<milestone>-laws-freeze` tag under the standing
  delegation in `DELEGATIONS.md`. Session ends.
- **Session B — implement.** A fresh session. Frozen paths are read-only (pre-commit
  enforces; do not work around it). Implementation is done when the frozen suite is green
  and `tannen laws report` shows fresh evidence for every law in the milestone set.

If the frozen laws turn out to be wrong: do not edit them. Record the defect in
a Tier-B decision record, write the corrected law as a *new* file, freeze it, and mark the
old one superseded in the manifest notes. The record of the mistake is part of the record.

## Decisions (BRIEF §9)

Every non-trivial choice is one new schema-validated record under `decisions/`
(`<seq>-<slug>.yaml`: id, tier, decision, rationale, reversibility, status, `veto_by` for
Tier B, bindings). Never hand-edit `DECISIONS.md` — it is generated. Bind the record to
the artifact that enforces it wherever one exists; an unbound record will be flagged
`unenforced` in the report, which is acceptable only with a stated reason.

- **Tier A**: decide, record, proceed. Includes: pinning ambiguous operator semantics via a
  property test; selection-rule outcomes; test design; module layout; in-stack dependencies.
- **Tier B**: decide provisionally, record with a veto-by date (one review cycle), proceed.
  Never block on Tier B.
- **Tier C**: stop; add to the digest under "requires owner"; work on something else.

`make digest` renders the week's Tier-B queue, Tier-C blocks, and the laws/evidence
summary into `digest/<date>.md`. Generate it at the end of any session that closed a phase.

Amendments of 2026-08-24 (BRIEF §9.1–§9.2) refine the above additively: tiers classify
by reversibility (A absorbs former B; B is vestigial external-surface only; C is the five
one-way doors, affirmative signature only); Tier-B silence-consent is valid only under a
fresh attention receipt; the digest is exception-only (risk-flagged + K sampled); consult
`governance/policy.yaml` before asking anything it answers; no Tier-C request halts work —
queue it, continue elsewhere, batch to the next boundary sitting.

## Correct-by-default is a review gate

Before merging any API surface, check it against BRIEF §5 point by point. If the shortest
spelling of a thing can violate a discipline, the API is wrong, not the caller. New
defaults discovered during work are proposed as Tier-B additions to the §5 catalogue.

## Conformance to other repos (BRIEF §2)

- `CONCEPTS.md` rows pin owner + document + section + commit SHA + grade + local artifact.
- Grade S: vendor the owner's frozen vectors under `conformance/vectors/<concept>/`;
  tests assert parse-all-positives / reject-all-negatives / round-trip. If the owner has
  not yet published vectors, pin the prose section and mark the row `S-pending` — do not
  write the vectors on the owner's behalf.
- Paraphrasing an owned definition anywhere in this repo is a CI failure by design. Cite.

## Verification (run before ending any implementation session)

```
uv run pytest                     # unit + law suites
uv run tannen laws report         # evidence freshness for current descriptors
uv run python scripts/check_manifest.py    # frozen paths intact
uv run python scripts/check_concepts.py    # concept records ↔ vendored artifacts complete; projections fresh
uv run python scripts/check_decisions.py   # records schema-valid; bindings resolve; veto clocks computed
uv run lint-imports               # kernel has no IO; no cross-repo imports
```

CI runs the same five. A session that leaves any of them red leaves a note at the top of
the generated decision report saying so and why (via a decision record).

## Session discipline

- One milestone in flight, ever. One worktree per milestone.
- Fresh session per phase; do not carry a spec session into implementation.
- Start by reading (Orientation above); end by adding decision records, regenerating projections, and, if a phase
  closed, generating the digest.
- Small PRs; every PR description states which laws it moves from red to green, or which
  brief section it executes.
