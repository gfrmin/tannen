# M0→M1 boundary sitting — the conferral brief

**Purpose.** This is the document to read, or to hand to someone else to read, *before*
running `scripts/boundary_sitting.sh`. `docs/SITTING.md` says how a sitting is run; the
four proposals each argue one item in depth. Neither answers the question a person
actually has at a sitting: *what am I being asked to decide, what happens if I say no,
and where should I be suspicious?*

Everything below is staged and green. The repo passes `make verify` with all of it
**unapplied**, so nothing here is load-bearing until the owner's key makes it so. Declining
any single item leaves the others intact.

Written by the builder, against its own interest where the two conflict. Two items (§1,
§2) are places where the builder is asking for constraints on itself; §1 is also a refusal
of an instruction the owner already gave.

---

## Context a reviewer needs first

**The enforcement surface is one machine.** There is no git remote. CI has never run.
`make verify` on this laptop is the entire gate, and until this sitting the guards
composing it were themselves unfrozen — a builder could soften a check and its own test in
one commit. That is the background fact that makes the custody set (§1) the highest-value
item on the list, above any further guard.

**Two guards written on 2026-08-24 were broken by the red team the same day.** RT-15
against the tag-signer guard (it pinned *which object* the trust root is; nothing required
it to exist at all, so `git tag -d` erased it with every guard green). RT-08 against an
escape hatch (an inherited environment variable switched off all 18 pytest bindings while
printing `18 pytest binding(s) green`). Self-review found neither. Treat any claim below
of the form "this closes X" as a claim to be tested, not accepted.

**The digest's owner queue is a query over Tier-C records only.** Anything needing the
owner that is not filed Tier C is invisible in it. That is why this sitting's work appears
as D0060 and D0061 rather than as a note.

---

## 1. Sign a custody set, not `MANIFEST.sha256` — **a refusal of D0060 item 5**

**What was queued.** "SIGN MANIFEST.sha256 and add it to `required_signatures` — the
largest single improvement available, since every seal added today is otherwise only as
strong as the builder's honesty."

**Why it is refused.** The manifest **grows at every law freeze**. CLAUDE.md's build
protocol has Session A write the milestone's law files, add them to `MANIFEST.sha256`, and
builder-sign `<milestone>-laws-freeze` under `DELEGATIONS.md` delegation 1 — without the
owner. An owner signature over the manifest therefore puts the owner's key in the path of
every milestone's Session A: five more interruptions, each one mid-milestone rather than at
a boundary, spending precisely the attention the standing delegation exists to conserve.
It would have failed on contact at M1 Session A, which is the next session.

**What replaces it (D0061).** `governance/tier-c.yaml` gains a `custody` block enumerating
the *stable* subset — `BRIEF.md`, `CLAUDE.md`, `DELEGATIONS.md`, `Makefile`,
`.pre-commit-config.yaml`, `ci.yml`, `allowed_signers`, the governance configs and schemas,
**every guard in `scripts/`**, both sitting drivers, and all of `tests/poison/`.
`scripts/gen_custody.py` generates `governance/custody.sha256` from that list; the owner
signs that file (namespace `tannen-custody`); the custodian verifies its hashes with
`sha256sum` and its signature with `ssh-keygen -Y verify`, **without invoking any Python
guard** — because every Python guard is inside the set it is checking.

**The second thing it buys.** RT-01's finding was that a manifest *row* can be deleted,
silently unfreezing its path, because nothing enumerates what the manifest should contain.
The custody set is that enumeration. A declared pattern matching no file is reported as a
hole, not skipped. Signing the manifest would not have fixed this; a signature over a
whitelist still says nothing about what the whitelist omits.

**The cost, which is the point.** After signing, any edit to a listed path turns the gate
red until a sitting re-signs. Guard changes batch to boundary sittings from here.
`pyproject.toml` is deliberately excluded so dependency work does not halt mid-milestone;
its import contracts are covered instead by the contract-shape check inside
`check_manifest` (itself a custody-set member).

**Known redundancy.** Ten or so paths now appear in both `MANIFEST.sha256` and
`custody.sha256`. Both are generated from the files as they are, so they cannot silently
disagree — one of them fails first. The redundancy buys two different properties:
pre-commit rejection (manifest) and owner attestation (custody). A reviewer may
reasonably argue for splitting the manifest in two instead of overlapping them.

**What it does NOT fix, stated plainly.** `MANIFEST.sha256`'s rows for law files and specs
remain covered only by the seal rule and the builder's honesty. A builder that edits a
frozen law *and* its row in one commit still satisfies `sha256sum -c`. The structural fix
— anchoring the custody set to the tree of the most recent owner-signed boundary tag — is
named in the signer-role proposal and deliberately deferred; it wants its own sitting.

> **Question worth conferring on:** is the custody set the right shape, or should
> `MANIFEST.sha256` be *split* into a builder manifest and an owner manifest rather than
> shadowed by a second file? The split is cleaner conceptually and a larger change.

---

## 2. Tier-C records must carry an owner signature (RT-06)

**The hole.** BRIEF §9.2 says Tier C is "affirmative owner signature only, never silence".
No artifact checked that. `tier: C` is a value in a YAML file the builder writes, and a
Tier-C record that says `accepted` appeared in **no section** of the owner's digest — the
queue only surfaces `blocked-on-owner`. A one-way door could be walked through by
assertion.

**The fix.** Records of `tier: C` with status `accepted` must have a detached owner
signature (namespace `tannen-decision`) that verifies. Two records exist in that state
today and are signed at step 1 of the sitting: **D0036** (the custodian tag-ordering guard,
which you applied at the opening sitting) and **D0049** (close tags stay owner-signed).

**The tension, unresolved.** D0045 says the decision text is immutable but its *bindings*
are mutable — a binding is the present-tense attachment, upgraded as remedies land. A
signature over the whole record file pins the bindings too, so a later binding upgrade
needs a re-signature. At Tier-C volume — five doors, owner-touched by definition — that
seems the cheap side of the trade, but it is a genuine cost and an alternative exists:
sign the *digest* instead, one signature per sitting covering the batch.

> **Question worth conferring on:** per-record signature, or per-digest batch attestation?
> The first is precise and re-signs on binding drift; the second is one signature and
> attests to a projection rather than to the records themselves.

**Sequencing oddity you will see.** The driver signs these records, then **pauses and hands
back to a builder session** to land the guard. The guard cannot land first: it would turn
the gate red before the signatures existed, and the pre-commit hook would block the
builder's own commit. The alternative is a grandfather enumeration in the style of
`FOUNDING_TAGS`, which is the pattern this repo already uses for exactly one founding
oddity — and using it twice starts to look like a habit.

---

## 3. The custodian replacement (trust root)

`scripts/custodian.sh` is author-key territory. The replacement is offered as a
**whole-file diff** rather than as prose patches, because this is the guard of the guards
and a reviewer should see every line they are vouching for. Six changes:

| # | Change | Closes |
|---|---|---|
| 1 | check 1b: `sha256sum -c governance/custody.sha256` | D0061, RT-14 |
| 2 | check 2: `DELEGATIONS.md`, `tier-c.yaml`, `tag-roles.yaml`, `check_tag_signers.py` must be manifested | RT-13, D0051 |
| 3 | check 3b: invoke `scripts/check_tag_signers.py` | D0050, RT-15 |
| 4 | check 4: an absent signature is a **downgrade** once an owner key is enrolled, not a pre-state | RT-04 |
| 5 | check 4: the same rule applied to `custody.sha256` | D0061 |
| 6 | check 5: nine new poison lines, one per new tooth | D0059 |

Change 4 is worth dwelling on: the custodian verified `policy.yaml.sig` **only if it
existed**, so deleting the signature returned the repo to its pre-opening custody state in
silence, printing `policy.yaml unsigned (expected before the opening sitting)` and exiting
0. The premise written into D0048 — "the builder cannot edit policy.yaml; any edit
invalidates the signature" — was true only while the signature was required to exist.

---

## 4. Binding strength as a schema field (D0052)

A binding either prevents or detects a violation, or it merely records that someone meant
to. `check_decisions` could not tell the difference: a drafted proposal awaiting your key
counted exactly like a frozen path. Twelve bindings are marked `documentary` by this
patch; the rest remain `enforced` by default, so older records keep their meaning.

**The hazard, which is why this is one script and not two steps.** Do not add
`documentary` to the ratchet's comparisons on the day the field lands. Until the schema
allows the field every record counts as `documentary=0`; a digest generated in that state
sets a **zero baseline**, and the first honestly-marked documentary binding after it reads
as a ratchet breach. The ratchet would then be punishing accurate self-reporting. Order:
land the field → mark honestly → one digest with true numbers → *then* ratchet.

This generalises: **a metric must be true for one digest before it is enforced from the
next.** Worth adding to BRIEF §9.1 if the pattern recurs — flagged, not proposed, since
§9.1 is owner text.

---

## 5. `in_repo_mechanics` in policy (D0048, D0053)

At the close of M0 the builder asked "shall I merge `m0` into `master`?" — a question
answerable from policy, about reversible in-repo work that is Tier A by BRIEF §9.2. The
asking was the defect. Deference spends the same owner attention that over-acting would.

The clause states the authority (merges, worktrees, branching, projections, pushing to an
**already configured private origin**) and fences it (`excludes`: any tag, any frozen or
signed file, **adding** a remote or changing its visibility). The repo has no remote at
all today, so the push permission is currently vacuous and the first push this project
ever makes necessarily requires adding a remote first — which stays Tier C.

---

## 6. Seven poison fixtures

Each is a red-team finding turned into a fixture the custodian runs, requiring the guard
to **fail** for a named marker. All seven have been verified to do so. One note against
the builder's own convenience: `custodian-tag-signer/repo.bundle` carries a
**builder-signed tag**, and the builder generated it. Creating tags in *this* repo is
outside Tier A (D0053), but this tag lives in a throwaway repo shipped as an opaque
bundle. `make-fixture.sh` is idempotent — delete the bundle and re-run it at the sitting
if you would rather that signature came from your own invocation.

---

## 7. `m0-close`, last

Step 10 of 11, deliberately. The rule requiring owner-signed closes is installed, and its
poison fixture watched failing, *before* the first close tag is signed — so the first
owner-signed close this project mints is validated by the very rule it obeys, in the same
custodian run that proves the rule bites. A guard should be born having already caught
something real.

The tag message quotes `DELEGATIONS.md` in full **and its sha256** (D0051), plus the
custody file's hash. Step 11 then adds `m0-close` to `required_tags` and re-signs the
custody set: a tag that exists but is not required can be deleted in silence (RT-15).

**Receipt before close, not after.** The attention receipt is taken at step 9. Because
`m0-close` is then dated after it, `receipt_state` starts a real seven-day clock —
Tier-B silence-as-consent lapses on 2026-09-01 unless a fresh receipt lands. Today the
clock is *stopped*: no boundary tag postdates the 2026-08-24 receipt, so it reads FRESH
indefinitely. The stopped clock is the anomaly; starting it is the point.

---

## What is NOT being asked

- **No spend.** Every envelope in `policy.yaml` stays zero. That door opens at M4.
- **No external surface.** No remote, no publishing, no cross-repo anything.
- **No constitution change.** BRIEF §3 and §10 are untouched.
- **No M1 content.** The milestone's laws are Session A's work, in a fresh session.

## What stays open after this sitting

Named so the boundary is not mistaken for a clean close:

- **RT-07** — the ratchet's baseline is a hand-editable comment in a digest file that no
  guard validates (digests are unmanifested and their `input-hash` header is never checked).
- **RT-10** — a binding is satisfied by a target that *exists*; nothing relates the target
  to the decision. `strength` grades honesty, it does not verify relevance.
- **RT-11** — digest visibility is compositional: `tier`, `risk_flags` and the sample are
  all builder-side inputs.
- **RT-12** — records are declared append-only and nothing enforces it; no chain, no hash,
  no signature except now at Tier C.
- **RT-14 residue** — one poison tooth per guard, and guards have many teeth. The custody
  set raises the cost of filing one off; it does not enumerate them.
- **RT-09** — the law descriptor does not address the harness, so evidence survives the
  harness being weakened. Deferred to the *start* of M1 by design: fixing it moves every
  descriptor and invalidates all existing evidence.
- **The structural fix** — anchoring the custody set to the tree of the last owner-signed
  boundary tag, which would close the loop the custody set only narrows.

## What a reviewer should try to break

Five attacks, with the answer the builder believes is true. A reviewer's job is to find
where these answers are wrong — the last two are the ones the builder is least sure of.

1. **Delete `governance/custody.sha256.sig`.** *Answered:* step 7 adds `custody.sha256` to
   `required_signatures`, so `check_manifest` fails with `missing owner signature` and the
   custodian's `require_sig` fails independently. This is RT-04's fix applied to the new
   file, and it is why the entry is added in the same step as the signature rather than
   later.
2. **Edit `governance/tier-c.yaml` to delete the `custody` block.** *Answered, by two
   independent paths:* the file is manifested (`check_manifest` fails on the stale row) and
   it is itself in the custody set, so `sha256sum -c governance/custody.sha256` fails inside
   the custodian without any Python guard being consulted. Note the near miss:
   `check_custody` returns silently when no block is declared, so the Python guard alone
   would **not** have caught this. The custodian's own hash pass is what does.
3. **Rename a Tier-C record, or flip its status to `rejected` and back.** *Answered:* the
   signature is a detached `.sig` beside the file, so a rename orphans it and the check
   reports the signature missing; a status flip changes the signed bytes, so the old
   signature no longer verifies. Both fail closed.
4. **`scripts/boundary_sitting.sh` is in the custody set and must change at the next
   boundary.** *Answered, but it is a cost not a fix:* the sitting that edits it also
   regenerates and re-signs the custody set at step 7, so it resolves within the same
   sitting. A builder editing it *between* sittings reddens the gate until the next one —
   which is the general cost of §1, landing here on a file that will genuinely change.
5. **Add a new guard that is not in the custody set, and route enforcement through it.**
   *Believed closed, and this is why `Makefile` and `.pre-commit-config.yaml` are in the
   set:* every call site that decides what the gate runs is covered, so a new
   `scripts/check_foo.py` cannot be reached without an edit the owner signs for. The
   builder is not confident this enumeration of call sites is complete — `pyproject.toml`
   is outside the set and configures `lint-imports`, and `uv` resolves entry points from
   it. **This is the item most worth a second pair of eyes.**

A sixth, which the builder cannot answer at all: none of this constrains what happens
before a commit exists. Every check runs on a working tree the builder controls, on a
machine with no second observer. The custody set makes weakening a guard *visible at the
next gate run*; it does not make it impossible, and no arrangement inside this repo can.
