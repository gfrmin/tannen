# Proposal: policy.yaml states that in-repo mechanics are Tier A (owner-applied)

**Status:** queued for the M0→M1 boundary sitting (decision D0048).
`governance/policy.yaml` is owner-signed (`governance/policy.yaml.sig`, namespace
`tannen-policy`) and the custodian verifies that signature on every run, so the builder
cannot edit it — any edit invalidates the signature. The builder drafts; the owner
applies and re-signs.

## The defect this closes

At the close of M0 Session B the builder asked the owner "shall I merge `m0` into
`master`?". Merging a milestone branch whose gate is green is reversible in-repo work:
Tier A under BRIEF §9.2 — decide, record, proceed. The question was answerable from
policy, and `governance/policy.yaml` already says, in its own header:

> GUARDS CONSUME THIS FILE. Being asked something answerable from it is a bug —
> file the bug as a decision record citing this file.

So the asking was the bug, and this is the record. The failure mode is not laziness but
its opposite: deference costs the owner attention, which is the one resource the whole
autonomy protocol exists to conserve. An owner interrupted for a fast-forward merge is
an owner with less attention left for the five doors that actually need a signature.

Policy today enumerates spend envelopes, licence defaults, external surface and the
spot-check rate. It does not say anywhere that ordinary git mechanics need no approval.
That silence is what the builder filled with deference. Absence of permission is not
absence of authority, but a policy file consulted by an agent under a custody floor will
be read conservatively — so the authority should be stated, not inferred.

## The patch

Append to `governance/policy.yaml`:

```yaml
# In-repo mechanics (BRIEF §9.2 reversibility tiers). Reversible operations on this
# repo's own history are Tier A: the builder performs them and records them, and does
# NOT ask. Asking about anything in `covers` is itself a defect — file it as a decision
# record citing this file.
in_repo_mechanics:
  tier: A
  covers:
    - merging a milestone branch into master once its gate is green
    - creating, deleting or moving worktrees under ~/git/worktrees/tannen/
    - branching, rebasing, fast-forwarding and resetting refs that carry no signature
    - regenerating projections and digests
    - installing or updating dev dependencies already pinned in pyproject.toml
  excludes:
    # These are NOT in-repo mechanics, and nothing here is relaxed by the above.
    - creating, moving or deleting any git tag (custody; DELEGATIONS.md, D0049)
    - any edit to a frozen path, to allowed_signers, to tests/poison/, or to a signed
      file (governance/policy.yaml itself included)
    - any byte leaving the repo boundary — push to a remote included
      (Tier-C door external-bytes)
```

## Why `excludes` is load-bearing

The clause hands over a class of action, so it must also fence it. Tags are the obvious
near-miss: creating a tag is a local, reversible git operation by every mechanical
measure, and it is nonetheless custody, because a tag is where a signature lives. Pushing
is the other: `git push` is one letter from `git merge` in effort and a Tier-C door in
consequence. Stating both here means the clause cannot be stretched by an agent reading
it in good faith at 2am.

## Verification after applying

1. `bash scripts/custodian.sh --check-only` → "policy.yaml signature verifies (owner@tannen)"
   (fails until re-signed; that failure is the proof the signature is load-bearing).
2. `uv run python scripts/check_manifest.py` → still OK (policy envelopes unchanged).
3. Upgrade D0048's binding from the `file` binding on this proposal to
   `config: governance/policy.yaml#in_repo_mechanics.tier`, which resolves only once
   this patch is applied (decision D0045: bindings are the present-tense attachment).
