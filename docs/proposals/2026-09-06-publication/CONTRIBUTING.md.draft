# Contributing to tannen

This repository is governance-gated. That is not bureaucracy for its own sake — the
subject matter is provenance and custody, and a project about those things that could not
show its own would be arguing against itself. What follows is the short form; the long
form is [`BRIEF.md`](./BRIEF.md) §8–§9 and [`CLAUDE.md`](./CLAUDE.md).

## Before you open a pull request

Run the gate. It is the same one CI runs, and it is not advisory:

```
uv sync --frozen
make verify
```

Clone with **full history and tags**. A checkout without tags fails on purpose: the tag
set is part of the custody floor, and a copy arriving without it is indistinguishable
from one where the tags were deleted.

## What a pull request needs

1. **A decision record** for any non-trivial choice — one new schema-validated file under
   `decisions/`, bound to the artifact that enforces it. Records are append-only: a
   correction is a new record that supersedes, never an edit to an old one. Never
   hand-edit `DECISIONS.md`; it is generated (`make projections`).
2. **A statement of which laws it moves from red to green**, or which section of the brief
   it executes. Put it in the PR description.
3. **Evidence that a new guard can fail.** A test that has never been watched failing is
   not yet a test. If you add one, say in the record how you made it go red and what the
   failure looked like.

## What a pull request may not do

- **Edit a frozen path.** Anything listed in `MANIFEST.sha256` is read-only; pre-commit
  enforces it. A frozen law that turns out to be wrong is superseded forward — write the
  corrected law as a new file and mark the old one superseded. Do not work around the
  hook.
- **Add a dependency on, or an import from, another repository of the constellation**
  (see BRIEF §1) — in either direction. Cross-repo unification happens through the
  concept registry and the Governor seam, never through code.
- **Restate a definition owned elsewhere.** Cite it. `concepts/*.yaml` pins owner,
  document, section, commit and content hash; paraphrasing an owned definition is a CI
  failure by design.
- **Touch author-key territory**: `scripts/custodian.sh`, `allowed_signers`,
  `tests/poison/`, the owner-signed policy and custody files, and their manifest rows.
  Propose changes to these as a patch under `docs/proposals/`; they land only under the
  owner's signature.
- **Implement the Governor** (BRIEF §7). The seam and its wire schema only.

## Reporting a problem with a guard

The most useful contribution this repository can receive is a demonstration that one of
its guards does not do what it claims. `tests/poison/` is where such demonstrations live,
and `docs/redteam/` is where the reasoning lives. If you have one:

- open an issue with the reproduction, or
- open a pull request adding the report under `docs/redteam/` and the fixture as a
  **candidate** under `docs/redteam/fixture-candidates/` — installing it into
  `tests/poison/` requires the owner's key, so please do not attempt it in the PR.

Findings that show a guard is green while the property it guards is violated are the
highest-value class here, and are treated as such.

## Style

Functional where it can be. The kernel imports no IO and no clock — `lint-imports`
enforces both. Match the surrounding code's naming, comment density and idiom rather than
introducing a new one.
