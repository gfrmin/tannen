# Signed-record binding upgrades carried forward from D0070

D0070 (2026-08-25): five Tier-C records were signed at the M0→M1 sitting (D0036, D0047,
D0049, D0060, D0063); a binding upgrade to a signed record cannot be applied between
sittings (the signature covers the record's whole bytes, so any edit breaks it), so
upgrades any of them still want are *drafted* now and *applied* at the next sitting, in
the same pass that re-signs them. D0070's text says "the upgrades three of them want are
drafted rather than applied" without naming which three or where the drafts live.

Checked live against this milestone's actual state (2026-08-27), not assumed:

- **D0036** — already upgraded, at the *opening* sitting (predates D0070, which was
  written after). Not one of the three; nothing to do here.
- **D0047** — its one binding (`file: DELEGATIONS.md`) carries no "upgrade drafted"
  language and none was found. Nothing to do here.
- **D0049** — **PENDING.** Its documentary binding
  (`docs/proposals/2026-08-24-custodian-close-tag-signer.md`) says verbatim: "Upgrades to
  a manifest binding on scripts/custodian.sh once the owner applies it." The patch it
  describes — custodian check 3's `*-close` case — is already live in the committed
  `scripts/custodian.sh` (confirmed: the poison lines `check_tag_signers_principal` /
  `check_tag_signers_required` are present and green). The upgrade is mechanical: add a
  `manifest: scripts/custodian.sh` binding to D0049 and re-sign.
- **D0060** — its bindings are documentary *by nature* ("a queue cannot enforce itself"),
  not pending; the guard binding is already enforced. Nothing to do here.
- **D0063** — **PENDING.** Its documentary binding
  (`docs/proposals/2026-08-25-boundary-sitting/brief-9.1-amendment.md`) says verbatim:
  "Upgrades to a manifest binding on BRIEF.md once applied." Checked directly:
  `grep -c "Metric calibration" BRIEF.md` returns 0 — **the amendment itself was never
  applied**, not just the binding. Step 4b of `scripts/boundary_sitting.sh` exists
  specifically to apply it and evidently was declined or not reached when the M0→M1
  sitting ran. This is broader than a binding upgrade: apply the amendment (step 4b,
  unmodified — it is still correct and still pending), THEN add the manifest binding.

**Only two upgrades are positively identified here, not three.** D0070's count is taken
at face value above rather than guessed at; if a third exists, it was not found by
checking each of the five records' current binding lists directly (2026-08-27) — worth a
question to the owner before this sitting closes rather than a silent gap, since D0070's
own text is specific about the number.

## What the sitting does with this

Both are ordinary Tier-C re-signs, not new decisions: `scripts/boundary_sitting.sh`'s
step 1 (Tier-C safety net) or step 8 (the queue) will not catch these, because both
records are `status: accepted` already, not `blocked-on-owner` — they are not questions
this sitting is convened to *answer*, they are upgrades to records already answered.
Apply them as their own small pass, after step 4b (which must run first for D0063's case)
and before step 9's gate-and-receipt:

1. Run step 4b as written (applies BRIEF §9.1's amendment — unmodified from the M0→M1
   draft, still correct).
2. Add the `manifest: BRIEF.md` binding to D0063, `manifest: scripts/custodian.sh` to
   D0049.
3. `rm decisions/0049-*.yaml.sig decisions/0063-*.yaml.sig` and re-sign both
   (`tannen-decision` namespace) — the same act step 1/8 already perform for other
   records, just invoked by hand for these two since neither is `blocked-on-owner`.
4. `regen_manifest_row` is not needed for the records themselves (decisions/*.yaml is not
   in the custody set); it *is* needed for BRIEF.md once step 4b's edit lands, and step 4b
   already does that.
