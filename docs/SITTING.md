# SITTING — the boundary-sitting checklist (owner, ~30 minutes per milestone)

The opening sitting (`docs/OPENING.md`) happens once. A **boundary sitting** happens at
each milestone boundary (BRIEF §9.1 point 3) and does four kinds of work, in this order:

1. **Signs what only affirmative signature can settle** — the Tier-C records, and the
   artifacts whose signature the guards require.
2. **Applies what the builder drafted but may not apply** — patches to frozen paths, to
   `governance/policy.yaml`, and to the trust root (`scripts/custodian.sh`,
   `allowed_signers`, `tests/poison/`).
3. **Installs the red team's findings as poison fixtures** — the standing exception in
   BRIEF §9.1 point 5: the builder drafts the fixture from the finding, the owner
   installs it.
4. **Takes an attention receipt and mints the close tag** — in that order, so the
   receipt's consent clock starts running against a boundary tag rather than stopping.

**Driver:** `bash scripts/boundary_sitting.sh [milestone]` walks every step, pauses for
each confirmation, shows the diff of every author-territory edit before it lands, and
signs nothing itself. It is safe to re-run — completed steps are detected and skipped —
and it is *designed* to be stopped: one step hands back to a builder session and waits.

Read the script before running it. Its own bytes are in the custody set, so a change to
it is a change you will be asked to sign for.

## Why the close tag is last

The order is load-bearing, and it is the whole argument of the M0 sitting:

> the first owner-signed close tag this project ever mints is validated by the very rule
> that requires closes to be owner-signed, in the same custodian run that proves the rule
> bites against a fixture.

A guard should be born having already caught something real. So: install the rule,
install its poison, watch the poison fail, *then* sign the tag the rule is about.

## The five things a sitting signs

| Artifact | Namespace | Why a signature and not a check |
|---|---|---|
| Tier-C decision records | `tannen-decision` | BRIEF §9.2: a one-way door is opened by affirmative signature, never by silence. Without this a record grants itself the door by writing `accepted` in its own status field (RT-06). |
| `governance/policy.yaml` | `tannen-policy` | The guards consume it for spend envelopes and external surface. Required, not verified-if-present: deleting the signature would otherwise return the repo to its pre-opening custody state in silence (RT-04). |
| `governance/custody.sha256` | `tannen-custody` | The bytes of the trust root and of every guard. See below. |
| `receipts/<date>.md` | `tannen-receipt` | Presence. Tier-B silence-as-consent is valid only under a fresh receipt (BRIEF §9.1). |
| `<milestone>-close` | git tag | The boundary itself. The builder signs the `*-laws-freeze` tags that *start* the consent clock, so the close that anchors presence stays the owner's (D0049). |

Since D0064 the first row is enforced, which changes how a Tier-C record reads between
sittings. `blocked-on-owner` is its resting state — not a flag that something went wrong,
but the honest description of a door nobody has walked through yet — and the guard refuses
any Tier-C record claiming otherwise without a signature beside it. So accepting and
signing are one act (step 8 does them together and rolls back if the signature does not
happen), and a record you decline stays queued to the next sitting without reddening
anything. Nothing about leaving one queued blocks other work; that is §9.2's non-blocking
rule, and it is why the queue can be read at leisure.

Signatures cover a record's whole bytes, so a later binding upgrade (D0045) invalidates
one and it is re-signed at the next sitting. That cost was accepted deliberately: on a
one-way door, re-attesting after the enforcement changes is content, not ceremony.

## The custody set, and why `MANIFEST.sha256` is not signed

The obvious move — sign the manifest — is wrong, and worth stating so it is not
re-proposed each sitting. `MANIFEST.sha256` is builder-maintained and **grows at every
law freeze**: `DELEGATIONS.md` delegation 1 has the builder freeze each milestone's laws
without the owner. An owner signature over the manifest would therefore put the owner's
key in the path of every milestone's Session A — spending exactly the attention the
delegation exists to save.

So the owner signs `governance/custody.sha256` instead: a generated, positive enumeration
(declared as `custody.set` in `governance/tier-c.yaml`) of the stable subset — the trust
root, the guards, the poison corpus, the gate's own call sites. It changes only when the
custody floor changes, so it costs one signature per sitting.

It also answers the biggest red-team finding in the direction the manifest cannot. A
manifest **row** can be deleted, silently unfreezing its path, because nothing enumerates
what the manifest should contain (RT-01). The custody set *is* that enumeration: a
pattern that matches nothing is reported as a hole, not skipped.

**The cost, stated plainly:** after a sitting, any edit to a custody-set path turns the
gate red until the next sitting re-signs. For the guards that is the intended property —
you cannot weaken the custody floor without the owner noticing. It means guard changes
batch to boundary sittings like every other Tier-C act. `pyproject.toml` is deliberately
outside the set so dependency work does not halt mid-milestone; its import contracts are
covered instead by the contract-shape check inside `check_manifest`.

## Two standing rules the sitting enforces

**The floor may depend only on tools the OS provides and paths named literally**
(D0063 ruling 3). The custodian's checks use `sha256sum`, `ssh-keygen`, `git` and `grep`;
where a Python guard is unavoidable it is the venv interpreter at a literal path in
isolated mode, never `uv run` and never a console entry point. The custody set covers a
guard's code; this covers its resolution, and resolution is enforcement.

**Presence and authorisation are different speech acts** (D0063 ruling 2, BRIEF §9.1). A
signature over a projection — a digest — says "I saw what I was shown". A signature over a
record says "this door opens". Batch attestation over a digest is a fine receipt and a
terrible authorisation, because the digest is composed by the party it measures. Never let
one substitute for the other.

## The receipt chain

Each receipt records the HEAD it was taken at, and each HEAD must be an ancestor of the
next and of the current HEAD (D0063 ruling 4). Owner-signed receipts are the only artifact
in this repo a builder cannot forge, so requiring ancestry across them makes history
rewritten *between* sittings detectable. Two consequences worth knowing before you sign:
`git commit --amend` or a rebase across a receipt boundary turns the gate red, and a
shallow clone cannot answer the ancestry question at all — which is why CI fetches full
history and tags.

## Preconditions

- `make verify` green. Nothing is signed over a red gate — a signature over a red gate
  attests to something nobody checked.
- The digest's "Requires owner" section read. It is a query over **Tier-C** records, so
  anything that needs the owner must be filed Tier C or it is invisible there.
- The red-team report for the closing milestone written, and its fixtures drafted under
  `docs/redteam/fixture-candidates/`.
- **`bash scripts/rehearse_sitting.sh` green** (D0068). It runs the whole driver against a
  disposable clone with a throwaway key, answering every prompt from a file, and asserts
  what a finished sitting leaves behind: the close tag signed and verifying, the custody
  set signed, a fresh signed receipt, the custodian green with no tolerances, `make verify`
  green, nothing uncommitted, no Tier-C door left unsigned — and that no step went quiet for
  more than 25 seconds without first saying how long it would be (D0069). **Budget about two
  hours** for the accept-everything path: it runs two full gates and a thirteen-minute
  binding sweep. A driver with a defect in it usually dies inside the first twenty minutes,
  so a bad run is cheap and only a good one is slow. **Pass `--keep`**, or the clone and its
  transcript are deleted on exit and all that survives is the verdict's summary.

  It is the difference between finding a defect here and finding it with your key on the
  table — the first three attempts at the M0 sitting each stopped on one this would have
  caught (D0065, D0066, D0067, D0069), and the M2 driver's first three runs each found a
  further defect that close reading and per-step sandboxing had both missed (D0147). The M2
  driver went green on its sixth run, on all three paths (D0148, D0149).

  **Two things learned there that apply to every sitting from now on.** A run stops at its
  first failure, so each run tests only as far as it gets: **the count of runs is not
  coverage, and only a green run clears the driver.** And **never edit the driver or the
  harness while a run is executing it** — `bash` reads a script incrementally by byte offset,
  so an edit mid-run kills the running shell with a syntax error on a line that is perfectly
  valid, and takes the verdict's failure analysis with it (D0149).

  Run it after ANY edit to the driver, and read a green result for what it is: proof of
  mechanism, not of custody. It signs with a throwaway key, because the real key is
  passphrase-protected and unattended signing is what that passphrase prevents; and it
  answers `y` to everything, so it rehearses the path where you agree. Nothing rehearses
  judgement.

## Afterwards (builder work, not yours)

Upgrade the bindings the sitting made enforceable (D0045: the decision is immutable, the
binding is its present-tense attachment), add the new fixtures to
`tests/test_governance_scripts.py`, and open the next milestone's Session A in a fresh
session.

**The projections are not one of them, and listing them here was the bug.** `DECISIONS.md`
renders the attention-receipt verdict, whose inputs are the latest receipt AND the first
boundary tag on or after it (`scripts/_gov.py:303`) — and the sitting creates both, after
the point where it last regenerated. Left to afterwards, the closing commit carries a
projection asserting the PREVIOUS boundary's freshness, which is what RT-M2-05 found in the
tree M1 left behind. The M2 driver copy regenerates at its step 11, between the close tag
and the closing gate, and `scripts/boundary_sitting.sh` inherits that when the copy replaces
it at the sitting (D0147).

**One of those upgrades cannot be done afterwards.** An owner signature covers a decision
record's whole bytes, so editing a binding on a **signed Tier-C record** breaks its
signature, and `check_decisions` reads a signed-but-unverifying Tier-C record exactly as it
reads an unsigned one — accepted without authority, which is a red gate. There is no
builder fix; only your key clears it. So a binding upgrade to a signed record is *drafted*
between sittings and *applied* at the next one, in the same pass that re-signs it. Upgrades
to unsigned records (every Tier-A and Tier-B record, and a Tier-C record still queued)
carry no such constraint and are done immediately. Ask before applying one to a signed
record; the cost of getting this wrong is a red gate that waits for a sitting (D0070).
