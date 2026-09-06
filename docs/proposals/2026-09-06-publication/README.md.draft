# tannen

A small semantic kernel plus an embedded Python DSL for defining data pipelines as
compositions of pure, total, versioned transformations over content-addressed values —
with semiring-annotated collections (incrementality and provenance as two instances of
one mechanism), memoized Merkle derivation graphs, and executable laws that record their
own evidence.

It is **not** an orchestrator, a scheduler, a distributed system, a SQL parser, or a
decision-maker. See [`BRIEF.md`](./BRIEF.md) §1 for where the line is drawn and §10 for
the non-goals, which are constitutional and do not move.

## The unusual part

Most of this repository is not the kernel. It is the machinery that decides what may
enter the kernel, and the evidence that the machinery ran.

- **Laws are frozen before the code that satisfies them.** Each milestone is two
  adversarially separated sessions: one writes the specification and the property tests
  and signs a freeze tag; a later one implements against them and may not edit a frozen
  path. A law found wrong is never edited — it is superseded forward, and the mistake
  stays in the record.
- **Every non-trivial choice is a schema-validated record** under `decisions/`, bound to
  the artifact that enforces it. [`DECISIONS.md`](./DECISIONS.md) is a generated
  projection of those records and is never hand-edited.
- **The guards are themselves attacked.** `tests/poison/` holds deliberately broken trees;
  a guard that passes its poison fixture is reported as weakened, not as green. Each
  milestone boundary gets a red-team pass whose findings live in `docs/redteam/` —
  including the ones still open.
- **The custody floor is signed.** Tags, an owner-signed policy file, an owner-signed
  custody manifest and a chain of owner-signed attention receipts; `scripts/custodian.sh`
  checks them together.

If you want to know whether any of this works, the honest answer is in
`docs/redteam/` — start with the most recent report, and note what it says is still open.

## Running it

```
uv sync --frozen
make verify          # the whole gate: guards, laws, import contracts, custodian
uv run pytest        # unit and law suites
uv run tannen laws report
```

`make verify` is the same gate CI runs. A clone without tags will fail it, deliberately:
the tag set is part of the custody floor, and a checkout arriving without tags is
indistinguishable from one where they were deleted. Clone with full history and tags.

## Reading it

1. [`BRIEF.md`](./BRIEF.md) §1–§2 — what this is, and the concept registry.
2. [`CLAUDE.md`](./CLAUDE.md) — the operating manual: how work is done here.
3. [`DECISIONS.md`](./DECISIONS.md) — the decision log.
4. [`CONCEPTS.md`](./CONCEPTS.md) — what is adopted from elsewhere, and at what grade.

## Provenance of this history

This repository's history was rewritten once, on the date recorded in
`receipts/REWRITE-*.md`, to remove verbatim excerpts of private repositories that had been
vendored under the citation discipline of BRIEF §2. That rewrite is declared rather than
hidden: the attestation is owner-signed, carries the complete old→new commit map, and the
receipt chain is verified through it. Decision D0176 says why.

## Contributing

See [`CONTRIBUTING.md`](./CONTRIBUTING.md). Short version: this repository is
governance-gated, and a pull request that changes behaviour without a decision record is
incomplete rather than unwelcome.

## Licence

Apache License 2.0 — see [`LICENSE`](./LICENSE) and [`NOTICE`](./NOTICE).
