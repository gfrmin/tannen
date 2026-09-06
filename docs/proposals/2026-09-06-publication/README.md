# Publication package — everything the door needs, drafted and rehearsed

D0115 (the Tier-C door `external-bytes`) is **already owner-signed and `accepted`** —
flipped from `blocked-on-owner` at the M1 sitting, `65b68a3`, and verified today:

```
$ ssh-keygen -Y verify -f allowed_signers -I owner@tannen -n tannen-decision \
    -s decisions/0115-*.yaml.sig < decisions/0115-*.yaml
Good "tannen-decision" signature for owner@tannen with ED25519 key SHA256:ekIiIR2jBgCirZr4tcnbhWjepAaTr7udxjlqGsa0MKs
```

So the decision is made. This package is the execution: the four things that signature
covers, drafted by the builder, rehearsed end to end, and waiting on the owner's key.
Owner rulings taken 2026-09-06: **excise all 12 sibling snapshots from history**, and
licence the result **Apache-2.0**.

## Why a rewrite at all — the fact that breaks D0115's mechanism (a)

D0115 recommends mechanism (a): keep the snapshots, exclude them from the *published tree*,
let `check_concepts.py` degrade to hash-pinned citation. Measured, that redacts nothing.
`concepts/snapshots/**` entered at the **root commit** `5c3a474` and was touched in exactly
one commit ever, so the 594 lines sit in the tree of every commit. Deleting them at HEAD
leaves them one `git show 5c3a474` away, and CI's `fetch-depth: 0`, the receipt chain and
`required_tags` all mean the history is what gets published.

Mechanism (a) is still needed — it is what lets the registry verify without the bytes —
but it is the *consequence* of the excision, not a substitute for it.

## Contents

| Path | What it is | Applied? |
|---|---|---|
| `patches/01-check-concepts-degraded-pins.patch` | mechanism (a) + the pin count D0115 makes non-optional | no — custody-set |
| `patches/02-check-receipts-rewrite-map.patch` | the receipt chain survives a declared rewrite without any receipt being edited | no — custody-set |
| `patches/03-owner-edits-at-the-sitting.md` | `policy.yaml` ×2, `tag-roles.yaml` ×2, `.pre-commit-config.yaml` (optional) | no — signed files |
| `LICENSE.draft` | Apache-2.0, verbatim (`sha256:cfc7749b…`, two independent local copies agree byte-for-byte) | no — a licence at the root **is** the grant |
| `NOTICE.draft`, `README.md.draft`, `CONTRIBUTING.md.draft` | the root files a public repo needs; none exists today | no |
| `fixture-candidates/README.md` | `tests/poison/check-concepts/governance/policy.yaml` | no — author-key territory |

Nothing here is applied. That is the same discipline the M3 red team used for
`oracle-shadow-spoofed`, and the reason the gate is green at every commit in this package.

## Rehearsed, not asserted

`scripts/…` was never touched; the whole rewrite ran in a disposable clone
(`rehearse_rewrite.sh`, 14 steps). Results:

**The rewrite itself.** 77 commits in, 77 out, none dropped; a complete 77-pair
`commit-map` with zero `000…0` entries. The 12 sibling files are absent from every commit
of every ref; `concepts/snapshots/semiring-relations/tannen-BRIEF-s4-s6.md` (this project's
own excerpt) survives, which keeps the byte-verifying path in `check_concepts.py`
non-vacuous in the published tree.

**The tags.** All 8 are annotated and SSH-signed. After the rewrite, every one reports
`object CHANGED / signature BROKEN` — including `brief-freeze`, whose tag-object hash
`c219e63819beb4052b326e47b9cbd5d208779cda` is pinned in `governance/tag-roles.yaml`.
Re-creating them works: the four builder tags were re-signed with the real builder key at
their **original tagger dates** via `GIT_COMMITTER_DATE`, and all four verify with dates
unchanged, so `bless_epoch` and D0036's delegation-precedes-signature ordering are
undisturbed.

**The receipt chain.** Against the rewritten history the shipped guard reports five
`history the owner attested to is gone` failures. With patch `02` and a signed
`receipts/REWRITE-2026-09-06.md`, all five clear and the guard prints
`N commit(s) remapped by signed rewrite attestation(s)` — **with all five receipts and
their signatures byte-identical**. Three negative controls, each watched going red:

| Probe | Result |
|---|---|
| attestation removed | red again — the five "gone" failures return |
| attestation present but unsigned | red — *"unsigned, it is the rewriting party vouching for itself"* |
| attestation signed but map tampered | red **twice**: the signature fails, and the remapped commit is reported absent |

**No regression.** Patch `02` against the real, un-rewritten tree prints exactly what the
shipped guard prints: `check_receipts: OK — 5 receipt(s); chain unbroken to HEAD`.

**Patch `01`, eight probes.** Baseline `13 by bytes` green; one snapshot absent →
`12 by bytes + 1 by pin`, green; **the published configuration** (all 12 gone) →
`1 by bytes + 12 by pin`, green, where the *shipped* guard reports 12 failures — that
difference is what the patch buys. Then the vacuity cases, all red: a concept record
truncated away (`pins = 11, expected 13`), the expectation key deleted from policy,
`policy.yaml` deleted outright, `concepts/` emptied. The shipped poison fixture still fails
and still carries its marker.

**One correction to the plan this package executes.** Its acceptance test included
`git log --all -p -S 'renavon' -- concepts/` → empty. That is **false** after the rewrite,
and the next section is why.

## What excision does NOT remove — read before signing

The 594 lines of borrowed *text* go. The *citations* stay, because they are the point of
BRIEF §2. A public reader still learns, from `concepts/*.yaml`:

- four repository URLs — `gfrmin/pkm`, `gfrmin/proplang`, `gfrmin/life-agent`, and
  **`renavondata/renavon-monorepo`**;
- nine document paths, including
  `docs/architecture/decisions/002-pipeline-rigour-stance.md`;
- section titles quoted verbatim — the renavon row's is
  `"[withdrawn: D0180]"`,
  which is an internal ADR heading;
- five pinned commit SHAs of private repositories, and 13 content hashes.

And `BRIEF.md` — frozen at `brief-freeze`, constitutional, unamendable — names all four in
its §1 constellation table, describing the last as *"The business; funds and supplies the
empirical substrate"*. Publishing tannen publishes that sentence whatever happens to
`concepts/`.

**Open question for the owner, and the only one left.** If naming
`renavondata/renavon-monorepo` and quoting an ADR heading is itself too much, the renavon
`source` entry comes out of `concepts/provenance-ref-grammar.yaml` as well. Consequences,
so it is a priced choice and not a mood: the concept keeps its pkm source and stays
`S-pending`; `expected_citation_pins` becomes **12**, not 13; and the registry loses one of
the two owners BRIEF §2 names for that row, which is a weakening of the citation discipline
rather than a tidy-up. Recommended only if the answer to "may this repo name that
repository in public" is no — it is a different question from "may this repo quote 58 lines
of it", and the first was never asked.

## Sitting runbook

Ordered. Each step's output feeds the next; steps 1–4 are reversible, step 5 is not.

1. Fresh attention receipt at the **pre-rewrite** HEAD.
2. Apply `patches/01`, `patches/02`, and the `policy.yaml` / `tag-roles.yaml` edits from
   `patches/03` (`trust_root.object` is filled in at step 6, not now).
3. Install `LICENSE`, `NOTICE`, `README.md`, `CONTRIBUTING.md` at the root.
4. Install the poison fixtures: `fixture-candidates/` here, and the M3 red team's
   `docs/redteam/fixture-candidates/oracle-shadow-spoofed/`.
5. Delete the 12 snapshots, commit, then rewrite **on a fresh full clone** — never in
   place: `~/git/tannen` is bare with four live worktrees.
   ```
   git filter-repo --invert-paths \
     --path concepts/snapshots/credence-functor-seam \
     --path concepts/snapshots/derive-decide-split \
     --path concepts/snapshots/exactness-and-the-door \
     --path concepts/snapshots/frozen-oracle-protocol \
     --path concepts/snapshots/pkm-determinism \
     --path concepts/snapshots/pkm-event-identity \
     --path concepts/snapshots/provenance-ref-grammar
   ```
6. Re-create all 8 tags at their original tagger dates — owner: `brief-freeze`,
   `m0/m1/m2-close`; builder: the four `*-laws-freeze`. Then read off the new
   `brief-freeze` tag object and finish `tag-roles.yaml`.
7. Write `receipts/REWRITE-<date>.md` with the **complete** `commit-map` (all 77 pairs, not
   just the five receipt HEADs — the rehearsal emitted only the five, and that is enough
   for the guard but not enough for an auditor), and owner-sign it under namespace
   `tannen-rewrite`.
8. `gen_custody.py`; owner-sign `custody.sha256` and `policy.yaml`.
9. `make verify` and `scripts/custodian.sh`, both green, on the rewritten history.
10. Owner signs D0176.

Then, and only then: `gh repo create`, push `master` first, push `--tags`, confirm the
default branch, watch CI's first-ever run, and clone the published repo into a scratch
directory to run `make verify` there — the first time this gate has ever run on a machine
that is not this one.

## The bytes are not lost

The 12 excised files are preserved outside git at
`~/git/tannen/.reference/snapshots/`, mirroring their tracked layout, alongside the four
sibling clones already in `~/git/tannen/.reference/`. An authorised clone that drops them
back into `concepts/snapshots/` gets byte verification again; patch `01` is written so both
configurations are legal and the difference is counted rather than assumed.
