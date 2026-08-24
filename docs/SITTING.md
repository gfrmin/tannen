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

## Preconditions

- `make verify` green. Nothing is signed over a red gate — a signature over a red gate
  attests to something nobody checked.
- The digest's "Requires owner" section read. It is a query over **Tier-C** records, so
  anything that needs the owner must be filed Tier C or it is invisible there.
- The red-team report for the closing milestone written, and its fixtures drafted under
  `docs/redteam/fixture-candidates/`.

## Afterwards (builder work, not yours)

Upgrade the bindings the sitting made enforceable (D0045: the decision is immutable, the
binding is its present-tense attachment), add the new fixtures to
`tests/test_governance_scripts.py`, regenerate the projections, and open the next
milestone's Session A in a fresh session.
