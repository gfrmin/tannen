# Proposal: two additive bullets for BRIEF §9.1 (owner-applied; frozen path)

**Status:** queued for the M0→M1 boundary sitting (conferral rulings 2 and 5, D0063).
`BRIEF.md` is frozen and is owner text; the builder drafts, the owner applies and
regenerates the manifest row. Additive only — no existing sentence changes.

Both bullets record a distinction the owner made in conferral that no artifact currently
states. Rules kept only in a decision record are rules the next session may not read;
§9.1 is where the custody floor is defined, and both of these are custody-floor rules.

## Insert after the "Exception-only digest" bullet

```markdown
- **Metric calibration.** A ratcheted metric must be TRUE for one digest before it is
  ENFORCED from the next. A metric added and ratcheted in the same breath establishes its
  baseline in the state where nothing has been measured yet, so the first honest
  measurement reads as a breach — the ratchet then punishes accurate self-reporting,
  which inverts it. Land the measurement, publish one digest carrying true values, and
  only then compare against it.
```

**Why it is worth constitutional weight rather than a note in D0052.** The hazard is
generic to every future ratcheted metric, not to the binding-strength field that found
it, and it is invisible at the moment of the mistake: the digest that sets the false
baseline looks exactly like a correct one. It surfaces one cycle later, in a red gate
that blames the session that told the truth.

## Insert after the "Attention receipts" bullet

```markdown
- **Two speech acts, never substituted.** A signature over a *projection* (a digest) is
  PRESENCE: "I saw what I was shown." A signature over a *record* (a Tier-C decision) is
  AUTHORISATION: "this door opens." The two may not stand in for one another. Batch
  attestation over a digest is a fine receipt and a terrible authorisation, because a
  digest is composed by the party it measures — tier, risk flags and the sample are all
  builder-side inputs — so a record hidden from every projection would inherit consent it
  was never shown for. Authorisation attaches to the artifact of record, never to a
  report about it.
```

**Why here.** §9.1 already defines receipts as presence. It does not say what a receipt
is *not*, and the cheaper design — one signature per sitting over the digest — is the
obvious economy an unwary future session would propose, since it costs the owner less
attention and looks equivalent. It is not equivalent, and the reason (RT-11: digest
visibility is compositional and builder-side) belongs next to the definition it
constrains.

## After applying

1. Regenerate `BRIEF.md`'s row in `MANIFEST.sha256` (it is frozen).
2. `BRIEF.md` is in the custody set, so `governance/custody.sha256` must be regenerated
   and re-signed — the sitting's step 7 does both, so apply this before it.
3. No decision record changes: D0052 and D0063 already carry the reasoning, and this
   amendment is the promotion they asked for.
