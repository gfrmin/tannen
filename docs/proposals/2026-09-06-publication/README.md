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
Owner rulings taken 2026-09-06: **excise all 12 sibling snapshots from history**, licence
the result **Apache-2.0**, and — the question this package left open, now closed —
**withdraw the fourth sibling's citation entirely** (D0180). The last is already executed
in the tracked tree; what it could and could not reach is measured under "What excision
does NOT remove".

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
| `patches/04-custodian-receipt-signing.md` | **D0177**, found while running this package's own merge gate: the custodian prints `author-signed` when `ssh-keygen` failed, leaves an unsigned receipt behind, and exits 0. It fires only when the custodian runs **bare** — which is what step 1 of the runbook below does. | no — author-key |
| `patches/05-check-concepts-brief-row-fidelity.md` | **D0180**, found while executing this package's own ruling: `brief_row` claims to carry the BRIEF §2 row a concept answers to, and **no guard reads it**, so a record can misreport who owns a concept with the gate green. Reproduce with `probes/brief_row_fidelity.py`. | no — custody-set |
| `patches/06-check-decisions-retired-bindings.md` | **D0181, and a PREREQUISITE not an improvement.** Step 5 deletes snapshots; owner-signed immutable D0115 binds to one by path; `check_decisions` resolves file bindings by bare existence with no escape hatch. Without this the sitting cannot pass step 9. | no — custody-set |
| `probes/brief_row_fidelity.py` | the measurement behind patch 05; re-run it at the sitting rather than trusting its table | n/a — wired into no gate |
| `publication_sitting.sh` | the driver for this sitting (D0182). Every prior sitting had one; this had prose. `--dry-run` narrates every step without signing or writing. | no — a driver in `scripts/` is custody-set |
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

> **Re-measured 2026-09-06 after the ruling**, in a fresh `git archive` tree, because
> arithmetic on someone else's measurement is not a measurement. Every figure in the
> paragraph above was taken at 13 pins and is kept as the record. At 12, re-run:
> baseline `OK — 8 records, 12 pin(s) verified by bytes + 0 by pin`; **the published
> configuration** (the 11 sibling snapshots gone, tannen's own excerpt kept)
> `OK — 8 records, 1 pin(s) verified by bytes + 11 by pin`, where the *shipped* guard
> reports `FAIL (11 violation(s))`. All four vacuity cases re-run and still red: a record
> truncated away → `pins accounted for = 11 … expects 12`; the expectation key deleted;
> `policy.yaml` deleted; `concepts/` emptied. The tree restores to green afterwards.

**One correction to the plan this package executes.** Its acceptance test included
`git log --all -p -S '<the fourth sibling>' -- concepts/` → empty. That was **false** when
written, and the next section is why. It became true for `concepts/` only once the citation
itself was withdrawn on 2026-09-06 — the rewrite alone never bought it.

## What excision does NOT remove — read before signing

The 594 lines of borrowed *text* go. The *citations* stay, because they are the point of
BRIEF §2. A public reader still learns, from `concepts/*.yaml`: three repository URLs
(`gfrmin/pkm`, `gfrmin/proplang`, `gfrmin/life-agent`), eight document paths, section
titles quoted verbatim, four pinned commit SHAs of private repositories, and 12 content
hashes.

**Ruled 2026-09-06: the fourth sibling's citation is withdrawn — and it is a STEP OF THIS
SITTING, not something already done.** The `source` entry comes out of
`concepts/provenance-ref-grammar.yaml` (D0180), taking with it — entirely, from the tracked
tree — the org slug, the internal ADR path, the verbatim ADR heading, the pinned private
commit and its content hash. `expected_citation_pins` then becomes **12**; it is **13**
today.

It is not already done because **it cannot be committed** (D0181). The citation and the
bytes are coupled by `check_concepts.py`'s orphan check, and the file is bound by
owner-signed, immutable D0115, so withdrawing the citation reddens `check_concepts` and
deleting the file reddens `check_decisions` — and both are `always_run` pre-commit hooks.
It was executed, measured and reverted; `patches/06` is what unblocks it. Doing it early
would also buy nothing: the excerpt is in **80 of 80 commits** and only the rewrite removes
it. The concept keeps its pkm source, stays `S-pending`, and afterwards is narrower than the
BRIEF §2 row it quotes; that divergence is declared in the record's own `notes` and enforced
by `patches/05`, because no guard can see it today.

**What the ruling could not reach, measured rather than asserted.** After the excision the
string still occurs **54 times across 23 files** that cannot change, and every one is
protected, load-bearing, or both. (Grand total across the tree is 69 in 31: the rest is this
package and D0180 describing the ruling — an audit trail that explains what it removed has to
name it. Re-measure, don't trust:
`git grep -ic renavon | awk -F: '{s+=$2} END {print s" in "NR}'`.)

| Where | Hits | Why it stays |
|---|---|---|
| `governance/importlinter.toml` | 2 | the *forbidden module names* of the `no-cross-repo` contract — deleting the string deletes the guard |
| `governance/tier-c.yaml` | 5 | `renavon-first-contact` is the **id of one of the five Tier-C doors**; two more are the mirrored forbidden-import list |
| `BRIEF.md` | 8 | frozen + custody-set; §10 non-goals, the §9.2 door list, and **M5 is "dogfood one Renavon vertical"** — the project's purpose |
| `CLAUDE.md`, `tests/poison/lint-imports-kernel/` | 2 | the hard rule and the fixture proving the guard bites |
| `docs/specs/m0.md`, `m2.md`, `m3.md` | 3 | frozen at Session A |
| 11 decision records | 19 | **immutable (D0045)**; `0115` is owner-signed |
| `DECISIONS.md` | 12 | generated *from* those records — regenerating reproduces every one |
| `scripts/boundary_sitting.sh` + 2 archived copies | 3 | custody-set, and the copies' value *is* byte-correspondence to it |

Two of those deserve to be read twice before signing. First, **the publication record is
what publishes the residue**: D0176 quotes the org slug and the ADR path in the course of
explaining that excision does not remove them, so writing the finding down made it
permanent. Scrubbing it would mean rewriting a signed, immutable attestation — the same
objection that made this package refuse to re-sign the five receipts. Second, `BRIEF.md`
names all four siblings in its §1 constellation table, describing the fourth as *"The
business; funds and supplies the empirical substrate"*. **Publishing tannen publishes that
sentence.** What the ruling buys is not anonymity; it is that no internal document path,
heading, or private commit SHA leaves with it.

## Sitting runbook

Ordered. Each step's output feeds the next; steps 1–4 are reversible, step 5 is not.

0. Apply `patches/04` **first**. Step 1 is the step D0177 corrupts, and an unsigned
   receipt written there would be believed for the rest of the sitting.
1. Fresh attention receipt at the **pre-rewrite** HEAD.
2. Apply `patches/01`, `patches/02`, `patches/05`, **`patches/06`**, and the `policy.yaml` /
   `tag-roles.yaml` edits from `patches/03` (`trust_root.object` is filled in at step 6,
   not now; `expected_citation_pins` is **12** — re-measure with the one-line grep in
   `patches/03` rather than trusting it).
   **`patches/06` is load-bearing for step 5, not a nicety**: deleting a snapshot breaks
   owner-signed immutable D0115's file binding, and without the retirement mechanism the
   gate at step 9 cannot go green. Add the `retires_bindings` entry to D0181 when it lands.
2b. **Execute D0180's withdrawal — now unblocked, and ordered here on purpose.** Remove the
   fourth sibling's `source` entry from `concepts/provenance-ref-grammar.yaml`, delete
   `concepts/snapshots/provenance-ref-grammar/renavon-adr-002.md` (bytes preserved at
   `~/git/tannen/.reference/snapshots/`), add the `brief_row_divergence` declaration from
   `patches/05`, and add the `retires_bindings` entry from `patches/06`. **Only now** set
   `expected_citation_pins` to what you measure — 12. Setting it before this step reddens
   the guard `patches/01` exists to make honest.
   Confirm with `probes/brief_row_fidelity.py` (8/8 -> 7/8 -> 8/8 once declared) and
   `make verify`.
   With `patches/05` also add the `brief_row_divergence` declaration it specifies to
   `concepts/provenance-ref-grammar.yaml`, or the tooth correctly reddens the tree on the
   divergence D0180 created — run `probes/brief_row_fidelity.py` to see it before and after.
3. Install `LICENSE`, `NOTICE`, `README.md`, `CONTRIBUTING.md` at the root.
4. Install the poison fixtures: both candidates in `fixture-candidates/` here (candidate 2
   only after `patches/05` — its tooth does not exist before then), and the M3 red team's
   `docs/redteam/fixture-candidates/oracle-shadow-spoofed/` (its guard patch **is already
   landed**, D0179, so this one is install-ready).
5. Delete the remaining sibling snapshots, commit, then rewrite **on a fresh full clone** —
   never in place: `~/git/tannen` is bare with four live worktrees.
   (Step 2b already removed the fourth sibling's ADR excerpt from the tracked tree, so 11
   remain here. All 12 are still in the history, so the `--path` list below is unchanged —
   and it is the rewrite, not either deletion, that actually removes the bytes.)
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
