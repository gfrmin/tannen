# Publication package — everything the door needs, drafted and rehearsed for real

D0115 (the Tier-C door `external-bytes`) is **already owner-signed and `accepted`** —
flipped from `blocked-on-owner` at the M1 sitting, `65b68a3`, and verified:

```
$ ssh-keygen -Y verify -f allowed_signers -I owner@tannen -n tannen-decision \
    -s decisions/0115-*.yaml.sig < decisions/0115-*.yaml
Good "tannen-decision" signature for owner@tannen with ED25519 key SHA256:ekIiIR2jBgCirZr4tcnbhWjepAaTr7udxjlqGsa0MKs
```

So the decision is made. This package is the execution: drafted by the builder, rehearsed
**end to end against a disposable clone with a throwaway owner key** (D0183), and waiting on
the owner's key. Owner rulings taken 2026-09-06: **excise all 12 sibling snapshots from
history**, licence the result **Apache-2.0**, and **withdraw the fourth sibling's citation
entirely** (D0180).

**Run the sitting from this directory:**

```
docs/proposals/2026-09-06-publication/publication_sitting.sh --dry-run   # narrated, nothing signed
docs/proposals/2026-09-06-publication/publication_sitting.sh             # the sitting
```

The driver performs every step under your confirmation — applies the patches, refreshes
every frozen row, executes the withdrawal, installs the fixtures, signs, rewrites, re-tags,
attests, commits and runs the gate — with your key read from `TANNEN_OWNER_KEY` (default
`~/.ssh/tannen_owner`) the way `boundary_sitting.sh` reads it. **10 owner-key touches, 4
builder-key touches**, listed in its header. It never touches `~/git/tannen`'s history: the
rewrite happens in a fresh clone, and that clone is what gets pushed.

## Why a rewrite at all — the fact that breaks D0115's mechanism (a)

D0115 recommends mechanism (a): keep the snapshots, exclude them from the *published tree*,
let `check_concepts.py` degrade to hash-pinned citation. Measured, that redacts nothing.
`concepts/snapshots/**` entered at the **root commit** `5c3a474` and was touched in exactly
one commit ever, so the 594 lines sit in the tree of every commit. Deleting them at HEAD
leaves them one `git show 5c3a474` away, and CI's `fetch-depth: 0`, the receipt chain and
`required_tags` all mean the history is what gets published.

Mechanism (a) is still needed — it is what lets the registry verify without the bytes —
but it is the *consequence* of the excision, not a substitute for it. And the same fact
applies one level down: the fourth sibling's section title, pinned commit and content hash
sat in every past version of the *record* that cited it, so withdrawing the citation at HEAD
(D0180) buys nothing in the published history unless the rewrite scrubs those strings too.
It now does (below).

## Contents

| Path | What it is | Applied by |
|---|---|---|
| `publication_sitting.sh` | the driver (D0182, rewritten under D0183 to perform rather than narrate). `--dry-run` narrates every step. | you run it |
| `rehearse_publication.sh` | the harness: runs the driver against a disposable clone with a throwaway owner key, then judges what it left behind (30+ checks). Modelled on `scripts/rehearse_sitting.sh`. | builder, before every change to the driver |
| `rehearse_rewrite.sh` | the earlier, narrower rehearsal of the rewrite mechanics alone (14 steps, three negative controls) | superseded by the above for the sitting; kept as the record |
| `patches/01-check-concepts-degraded-pins.patch` | mechanism (a) + the pin count D0115 makes non-optional | driver, step 2 |
| `patches/02-check-receipts-rewrite-map.patch` | the receipt chain survives a declared rewrite without any receipt being edited — **now skips `REWRITE-*` in its receipt loop**, a bug the full rehearsal found | driver, step 2 |
| `patches/03-owner-edits-at-the-sitting.md` | `policy.yaml`, `tag-roles.yaml`, and the three edits the rehearsal added: manifest rows, `FOUNDING_TAGS`, `DELEGATIONS.md` | driver, steps 2 and 6 |
| `patches/04-custodian-receipt-signing.patch` | **D0177**: the custodian prints `author-signed` when `ssh-keygen` failed | driver, step 0 |
| `patches/05-check-concepts-brief-row-fidelity.patch` | **D0180**: `brief_row` read at last — two teeth, and the `brief_row_divergence` declaration | driver, step 2 |
| `patches/06-check-decisions-retired-bindings.patch` | **D0181, a PREREQUISITE**: `retires_bindings`, honoured only from an accepted record, only for a documentary binding, only while the target is absent, printed every time | driver, step 2 |
| `patches/07-custodian-delegates-receipt-chain.patch` | **D0183**: the custodian carried its own copy of the receipt-chain check; it now delegates to `check_receipts.py` | driver, step 0 |
| `probes/brief_row_fidelity.py` | the measurement behind patch 05; the driver re-runs it at step 2b and stops unless both teeth read 8/8 | driver, step 2b |
| `fixture-candidates/` | three poison trees and one file, each watched biting; the spoofed-oracle candidate under `docs/redteam/` is the fourth | driver, step 4 |
| `LICENSE.draft`, `NOTICE.draft`, `README.md.draft`, `CONTRIBUTING.md.draft` | the root files a public repo needs (Apache-2.0 verbatim, `sha256:cfc7749b…`) | driver, step 3 |

Nothing here is applied to the tracked tree. The `.md` beside each `.patch` is its rationale
and its watched-failing measurements.

## Rehearsed for real

`rehearse_publication.sh` clones this tree, enrols a throwaway `owner@tannen` beside the real
one, syncs a venv, arms the pre-commit hooks, snapshots every tag and receipt, and runs the
driver with `y` to every prompt and the throwaway key in `TANNEN_OWNER_KEY`. Then it judges
the result — every tag exists, verifies and keeps its tagger date; the trust root is
repinned; no sibling snapshot path and none of the three withdrawn strings is in any commit
of any ref; the attestation verifies under `tannen-rewrite`; `check_receipts`,
`check_manifest`, `check_concepts` (`1 by bytes + 11 by pin`), `check_tag_signers`, the
custodian and the brief_row probe are green on the rewritten history; the pin count in
policy equals the measured count; nothing is left uncommitted in either clone; and the real
repository's HEAD and tree are untouched (a positive control, not a promise).

**What a green run proves:** step order, quoting, every patch applying and every frozen row
refreshed, the rewrite, the re-tagging, the attestation, and a green gate on rewritten
objects. **What it cannot prove:** custody — the throwaway key attests to nothing; GitHub's
first CI run. Read green as "the mechanism works", never as "the sitting happened".

### Before you start: one `ssh-add` (D0185)

Measured 2026-09-07 with a throwaway passphrase-protected key, three ways.
`ssh-keygen -Y sign -f <encrypted key>` prints `Enter passphrase for …` on the terminal
**every time** — ten times for the owner key across ninety-five minutes. With the key in
ssh-agent the **identical** invocation signs silently, because ssh-keygen finds it there;
`-f` keeps pointing at the private path and nothing in the driver changes. (These are SSH
signatures, so this is ssh-agent — not gpg-agent, and no pinentry is involved.)

Measured against the real keys, without signing anything with them: `~/.ssh/tannen_owner`
**is** passphrase-protected; `~/.ssh/tannen_builder` is not, as `DELEGATIONS.md` intends.

```sh
ssh-add ~/.ssh/tannen_owner     # once; then all 14 key touches are silent
ssh-add -l                      # confirm
```

Do **not** use `ssh-add -t` — the sitting runs about 95 minutes. The driver's precondition
now reports which of the two paths you are on, per key, before anything is signed; the
rehearsal harness deliberately clears `SSH_AUTH_SOCK` so it always exercises the key file.

**Every run is a fresh clone**, and this matters for reading the list below. The harness
makes a new `mktemp -d` and a new `git clone --no-hardlinks` on each invocation and deletes
both on exit unless `--keep`; the driver applies all seven patches itself at step 2, from the
package. So the clean full run was **not the tail of the run that found the defects** — it
was the whole sitting, precondition to close, in a clone built minutes earlier with every fix
already in the artifacts. What that is *not* is a plateau: it is one run at full fidelity.
Fast run 4 was also green, and full run 1 then found two more defects — because fast mode
skips exactly the hooks and gates where they bit. The fidelity above this one has never run
at all: the real key, GitHub, CI.

**The runs, in order** (2026-09-07; transcripts kept outside the repository):

1. **Negative control** — the committed driver of `424b21e`, run for real: **stopped at
   step 1 after 46 minutes.** Its 45-minute precondition gate crossed midnight; the
   custodian wrote and signed `receipts/2026-09-07.md` and the driver looked for the 09-06
   one it had named at start. D0182's dry-run had reached "the sitting is closed" on that
   same driver.
2. **Partial run to step 4** (minutes): found that moving the spoofed-oracle fixture into
   `tests/poison/` left **D0179's file binding dangling** — the shape D0181 is about.
3. **Mechanics-only runs** (`TANNEN_SITTING_FAST=1`, gates and hooks skipped, ~1 min each):
   the pure-deletion commit is **pruned** by `--invert-paths` and reported as a lost commit;
   patch 02 verified the attestation **as a receipt**; the custodian's **own** receipt loop
   rejected the attestation; `FOUNDING_TAGS` and `DELEGATIONS.md` enumerate `m0-laws-freeze`
   **by tag object**; the withdrawn citation's three specifics were **still in history**;
   the driver's scratch files inside the rewrite clone made filter-repo **refuse** and would
   have been **swept into the published commit**. Green on the fourth run.
4. **Full run, first attempt** (real gates, real hooks): step G's `make verify` green on
   the patched tree in 42 min (831 passed, 1 skipped, 1 xfailed; 52 laws fresh;
   `check_decisions` printing the honoured retirement, all three new poison lines biting);
   receipt, commit A, rewrite, re-tagging, attestation, custody and D0176 all through —
   **stopped at commit C, 87 minutes in, by the hooks.** `tests/test_conformance.py`
   asserted every cited snapshot *exists* (the published configuration has 11 by pin), and
   the receipt-clock test parsed the attestation's `REWRITE-` stem as a date. Both are
   builder-editable tests; both fixed and watched in both directions (the conformance
   suite now counts pins against the same expectation `check_concepts.py` reads).
5. **Full run, clean** (`tannen-pubrehearsal-YzMdLq`): **the sitting completes.** Driver
   exit 0 after 752 lines and **94 minutes**; **51 of 51** verdict checks ok; no unexpected
   failure line in the transcript. Precondition through step 4 — seven patches, the
   withdrawal, four root files, three fixtures — **8 seconds**; step G's gate 34 min; the
   receipt 7 s; commit A 13 min; **the entire irreversible middle — rewrite, eight tags
   re-signed at their original tagger dates, attestation, custody, D0176 — 4 seconds**;
   commit C 13.5 min; step 9's gate on the rewritten history 34 min. Both gates
   `832 passed, 1 skipped, 1 xfailed`. On the rewritten objects: `check_manifest` OK;
   `check_concepts` OK (8 records, **1 by bytes + 11 by pin**); `check_decisions` OK
   (182 records, 93 pytest bindings, the retirement printed, 0 unenforced);
   `check_tag_signers` OK (8 tags, trust root repinned); `check_receipts` OK (6 receipts,
   **chain unbroken through 84 remapped commits**); `check_laws` OK; 52 laws fresh; the
   custodian green with no tolerances; both clones clean. `~/git/tannen` HEAD and tree
   untouched — the isolation control, run rather than asserted.

Everything the earlier `rehearse_rewrite.sh` measured still holds and is kept below as the
record; the full rehearsal is what found the gaps between its pieces.

### The rewrite mechanics (from `rehearse_rewrite.sh`, 2026-09-06)

**The rewrite itself.** 77 commits in, 77 out, none dropped; a complete 77-pair
`commit-map` with zero `000…0` entries. The 12 sibling files are absent from every commit
of every ref; `concepts/snapshots/semiring-relations/tannen-BRIEF-s4-s6.md` (this project's
own excerpt) survives, which keeps the byte-verifying path in `check_concepts.py`
non-vacuous in the published tree.

**The tags.** All 8 are annotated and SSH-signed. After the rewrite, every one reports
`object CHANGED / signature BROKEN` — including `brief-freeze`, whose tag-object hash
`c219e63819beb4052b326e47b9cbd5d208779cda` is pinned in `governance/tag-roles.yaml`.
Re-creating them at their **original tagger dates** via `GIT_COMMITTER_DATE` keeps
`bless_epoch` and D0036's delegation-precedes-signature ordering undisturbed.

**The receipt chain.** Against the rewritten history the shipped guard reports five
`history the owner attested to is gone` failures. With patch `02` and a signed
`receipts/REWRITE-<date>.md`, all five clear and the guard prints
`N commit(s) remapped by signed rewrite attestation(s)` — **with all five receipts and
their signatures byte-identical**. Three negative controls, each watched going red:

| Probe | Result |
|---|---|
| attestation removed | red again — the five "gone" failures return |
| attestation present but unsigned | red — *"unsigned, it is the rewriting party vouching for itself"* |
| attestation signed but map tampered | red **twice**: the signature fails, and the remapped commit is reported absent |

**Patch `01`.** Baseline green; the published configuration (all sibling snapshots gone) →
`1 by bytes + 11 by pin`, green, where the *shipped* guard reports 11 failures. Four
vacuity cases red: a concept record truncated away, the expectation key deleted from
policy, `policy.yaml` deleted outright, `concepts/` emptied.

**Patches `05` and `06`**, each in a scratch clone, both directions — see their `.md`.

## What excision does NOT remove — read before signing

The 594 lines of borrowed *text* go, and now so do the fourth sibling's **section title,
pinned commit and content hash**, from every past version of the record, of `CONCEPTS.md`
and of this README (`--replace-text`, each replaced by `[withdrawn: D0180]`; the driver reads
the three strings off the pre-rewrite record at run time, so no file in this package carries
them). The *citations* of the other three siblings stay, because they are the point of
BRIEF §2: a public reader still learns three repository URLs (`gfrmin/pkm`,
`gfrmin/proplang`, `gfrmin/life-agent`), eight document paths, section titles quoted
verbatim, three pinned commit SHAs of private repositories, and 12 content hashes.

**What survives of the fourth sibling, by construction.** The repository slug and the
document path: owner-signed, immutable D0115 names the slug, and D0176 names both in the
course of explaining that excision does not remove them — the publication record is what
publishes the residue. Scrubbing them would mean rewriting a signed, immutable attestation,
the same objection that keeps the five receipts byte-identical. And `BRIEF.md` names all
four siblings in its §1 constellation table; **publishing tannen publishes that sentence.**
What the ruling buys is not anonymity; it is that no internal document title, private commit
SHA or content hash leaves with it. The bare name occurs in places that are frozen,
constitutional, or load-bearing (re-measure:
`git grep -ic renavon | awk -F: '{s+=$2} END {print s" in "NR}'`), and every one is
explained in D0180.

## Sitting runbook — the driver's order, and why

Each step's output feeds the next. Everything through step A is reversible; step 5 is not.
The full gate runs at **G**, after the patches and before the rewrite: a patch that breaks a
governance test must surface while the tree can still be thrown away, not at step 9 with
the history already rewritten. The receipt (**1**) is taken after custody is re-signed,
because the custodian that writes it checks the floor first.

| Step | What the driver does | Key |
|---|---|---|
| P | `custodian.sh --check-only`; records the pre-rewrite HEAD; reports each key's passphrase path (D0185) | |
| 0 | patches **04** and **07** to `custodian.sh` (author-key); row refreshed | |
| 2 | patches 01, 02, 05, 06; both schema rows; patch 03's `policy.yaml` and `tag-roles.yaml` edits; `licence_defaults` → **Apache-2.0**, both keys (D0176 ruling 2); pin count **measured** and written | |
| 2b | D0180's withdrawal: source entry out, snapshot `git rm`'d, divergence declared, D0181 retires D0115's binding, pins re-measured (**12**), probe must read 8/8 | |
| 3 | the four root files | |
| 4 | the four poison fixtures, their rows, custodian lines, README rows, pytest mirror; D0179's binding follows the moved README | |
| G | `gen_custody`; custody and policy signed; custodian; **`make verify`** (~45 min) | owner ×2 |
| 1 | attention receipt at the pre-rewrite HEAD (the receipt's date is read *here*, not at start) | owner ×1 |
| A | commit (hooks ~20 min) | |
| 5 | fresh `--no-local` clone; `filter-repo --invert-paths … --replace-text …`; commit-map checks (no dropped commits, pairs = commits) — **no deletion commit first**: it would be pruned as empty | |
| 5c | the clone gets a venv, hooks, `gpg.format ssh`; `publish_shape` gives it **exactly one branch, `master`** (D0186 — a clone of a worktree has none, and filter-repo drops the remote-tracking refs) | |
| 6 | all 8 tags re-created at their original dates from their original messages (signature block stripped), verified; `trust_root.object` repinned; `FOUNDING_TAGS` and `DELEGATIONS.md` follow `m0-laws-freeze`; rows refreshed; `check_tag_signers` | owner ×4, builder ×4 |
| 7 | `receipts/REWRITE-<date>.md`: the complete commit map **and** the tag map, signed under `tannen-rewrite` | owner ×1 |
| 8 | `gen_custody`; custody signed (policy unchanged since G) | owner ×1 |
| 10 | D0176 signed as it stands (`blocked-on-owner`; the flip is a new record you write) | owner ×1 |
| C | commit in the clone (hooks ~20 min) | |
| 9 | **`make verify`** and the custodian on the rewritten history (~45 min) | |

Then, and only then — narrated by the driver, never run by it: `gh repo create`, push
`master` (the clone's only branch, so it becomes the default), push `--tags`, confirm the
default branch, watch CI's first-ever run, and clone the published repo into a scratch
directory to run `make verify` there — the first time this gate has ever run on a machine
that is not this one.

**Why the branch shape needs a step at all (D0186).** The driver clones `$PWD`, a *worktree*,
so the clone carries only that worktree's branch — and `git filter-repo` drops the
remote-tracking refs rather than converting them. Measured on a kept rewrite clone:
`refs/heads/m3` and eight tags, no `master`. The push documented here would have failed with
`src refspec master does not match any` at the last step of the sitting, and the natural
recovery would have made `m3` the public default branch. `publish_shape` creates `master`,
checks it out and removes the milestone branch, so the published repository carries one
branch. Nothing is lost: every milestone branch is an ancestor of master, and every milestone
is marked by a signed tag that is published.

## After the push: adopting the published history (D0187)

`adopt_published_history.sh --from <url> --ci-green` points this repository at the published
history. Run it **after the push and after CI is green** — it refuses without `--ci-green`,
which is you saying you looked.

It is a remap, not a fetch-and-reset: the published repository has one branch and no
`m0`/`m1`/`m2`/`m3` refs to reset to, so every historical branch resolves through the signed
commit map in `receipts/REWRITE-<date>.md` — whose signature is verified under
`tannen-rewrite` before a single pair is trusted. `master`, and any branch sitting on its tip,
takes the published head instead: the sitting's own two commits exist only there and have no
pre-publication counterpart to map from.

Every pre-publication ref is copied under `refs/backup/pre-publication-<date>/` **before**
anything moves, so every SHA named in the decision records stays resolvable and the whole
thing is one `update-ref` per branch away from undone. It refuses on any dirty worktree —
`git branch -f` will not move a checked-out branch, so the script resets from inside the
worktree, which would discard uncommitted work. It reports the shared stash stack and never
touches it.

Rehearsed by `rehearse_adoption.sh` against a bare clone with four worktrees and a real signed
map: 40/40, including `check_receipts`, `check_tag_signers` and the custodian run on the
adopted repository.

**One line only you can settle**, and it is not a licence any more (D0184): the driver now
executes D0176 ruling (2) at step 2, so `governance/policy.yaml` says `licence_defaults`
Apache-2.0 for both keys and agrees with the `LICENSE` at the root — under your step-G
signature, since no guard reads either key. What remains is that `~/git/tannen` keeps the
un-rewritten history: whether the bare repo adopts the published one is a separate decision
the driver does not make. Taking it costs a backup ref (`git tag
backup/pre-publication-<date> master`) and a reset of the four worktrees; the excised bytes
are unaffected either way, since they live outside git at `~/git/tannen/.reference/`.

## The bytes are not lost

The 12 excised files are preserved outside git at
`~/git/tannen/.reference/snapshots/`, mirroring their tracked layout, alongside the four
sibling clones already in `~/git/tannen/.reference/`. An authorised clone that drops them
back into `concepts/snapshots/` gets byte verification again; patch `01` is written so both
configurations are legal and the difference is counted rather than assumed. The private
tree this sitting runs in keeps all of them but one (12 by bytes); the published clone keeps
tannen's own (1 by bytes + 11 by pin).
