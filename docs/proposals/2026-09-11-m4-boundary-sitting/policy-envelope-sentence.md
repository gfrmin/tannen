# Proposal: policy.yaml says what SpendGuard actually enforces

**Status:** queued for the M4 boundary sitting, and for the mandatory pre-budget sitting
BRIEF §9.1 requires before any nonzero envelope. Owner ruling of 2026-09-12, recorded as
decision D0240 item (1); the defect it closes is D0238.

`governance/policy.yaml` is owner-signed (`governance/policy.yaml.sig`, namespace
`tannen-policy`), the custodian verifies that signature on every run, and the file is in
`governance/tier-c.yaml`'s `custody.set`. The builder cannot edit it — any edit invalidates
the signature and the custody hash together. The builder drafts; the owner applies and
re-signs.

## The defect this closes

Lines 9-12 say, of the per-milestone spend envelopes:

> `budget.yaml`'s operational ceilings may never exceed the current milestone's envelope;
> check_manifest enforces the zero-state consistency and SpendGuard enforces it
> operationally from M4.

The second clause is false of the SpendGuard that shipped at M4. `Oracles(store,
mode=SPEND, budget=load_budget(x))` admits a call iff **the budget the caller names** has
room. Nothing ties that budget to the checked-in `budget.yaml` or to this file's
`budget_envelopes`, and a budget naming a fresh `scope` starts its fold from zero.

D0238 queued this as a gap in SpendGuard and recommended superseding the frozen spend laws
so that SpendGuard would take an envelope. The owner ruled against that, and the reason is
the correction:

> A budget file is an *authorisation*, and authorisations are properties of the caller, not
> of the library. SpendGuard's job is to enforce the rule "admit iff ceiling > 0 and spent +
> worst case fits" against whatever authorisation it is handed — and it does that correctly.
> A library that reads the constitution to decide whether you may make a network call is the
> wrong shape.

Making the library consult this file would couple the kernel's spend primitive to this
repository's governance layout — the repo-unification BRIEF §10 forbids in every other
direction. So the sentence is the defective artifact, not the laws and not the guard.

## The patch

Replace lines 9-12 of `governance/policy.yaml` (the comment block above
`budget_envelopes:`) with:

```yaml
# Per-milestone spend envelopes (USD). Raising any value above zero is Tier-C door 1
# (affirmative signature). budget.yaml's operational ceilings may never exceed the
# CURRENT milestone's envelope, and scripts/check_manifest.py is what enforces that:
# mechanically, over the checked-in file, at every gate. (That guard compares against the
# maximum envelope over all milestones rather than the current one — D0229 item (5), a
# separate patch in this directory, applied in the same sitting.)
#
# WHAT SPENDGUARD DOES AND DOES NOT DO. Owner ruling of 2026-09-12 (D0240), replacing a
# sentence here that claimed the second half and was false of the SpendGuard that shipped
# at M4. SpendGuard enforces default-deny against THE BUDGET ITS CALLER SUPPLIES. It does
# not read this file and it must not: a library that consults the constitution to decide
# whether a call may be made couples the kernel's spend primitive to this repository's
# governance layout, which BRIEF §10 forbids in every other direction. Supplying a budget
# other than the checked-in budget.yaml is therefore an OWNER act, not a builder act, and
# nothing in the library prevents it. `tannen run` is not a library: it is clamped to the
# checked-in budget.yaml, with any other file requiring an explicit --budget-override
# (D0240 item (2); deferred to M5 Session A by D0241, because a law retiring L4.4's third
# node has no legal home inside M4).
```

Nothing else in the file changes. `budget_envelopes` keeps its keys and its zeros.

## What this does not do

It does not close the gap D0238 found — it states correctly where the gap is and who may
close it. After this patch the position is: the envelope binds `budget.yaml` mechanically;
the CLI is clamped (at M5); and the library admits against what its caller hands it, which
is a caller's authority and an owner's act. A reader who wants the library itself to refuse
an over-envelope budget is asking for option (a) of D0238, which this ruling declined.

## Verification, after the owner applies it

```
.venv/bin/python -I -P scripts/gen_custody.py     # custody.sha256 now covers the new bytes
bash scripts/custodian.sh --check-only            # re-sign policy.yaml.sig, then this is OK
.venv/bin/python -I -P scripts/check_manifest.py  # required signatures present; custody current
```

`scripts/gen_custody.py` regenerating the hash does **not** re-sign it: the signature is the
owner's act at the sitting, and a regenerated file under a stale signature is the alarm the
arrangement exists to raise.
