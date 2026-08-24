# OPENING — the opening-sitting checklist (owner, ~10 minutes)

Exactly four owner steps (BRIEF §9.2; decision D0027). Everything else in this
project runs without you until the M5 close, except what the five Tier-C doors gate
(`governance/tier-c.yaml`). Run everything from the repo root. Precondition:
`make verify` is green before you start.

## 0. Inspect the trust root (read-only, ~5 minutes, before signing anything)

Everything after this sitting trusts what you are about to sign, so this is the one
occasion where genuine attention matters most. From a **clean clone** — not the
builder's working tree:

```sh
git clone ~/git/tannen /tmp/tannen-inspect && cd /tmp/tannen-inspect && uv sync --frozen
less scripts/custodian.sh            # read it end to end — it is sized for exactly this
bash scripts/custodian.sh --check-only   # watch every guard FAIL its poison fixture
```

Expect: frozen hashes verify, `m0-laws-freeze` verifies (builder-signed), "policy.yaml
unsigned (expected before the opening sitting)", each of the four guards "fails its
poison as required", exit 0. Then read `DELEGATIONS.md` in full — it is the text your
step-3 signature makes binding. Signs nothing, configures nothing: this inspection *is*
the attention the signatures attest. Return to the real repo root for steps 1–4.

## 1. Keys

Generate a hardware-backed owner key (touch = presence; BRIEF §9.1). If you have no
FIDO2 key plugged in, substitute `-t ed25519` and accept the weaker custody.

```sh
ssh-keygen -t ed25519-sk -f ~/.ssh/tannen_owner -C "tannen owner key"
printf 'owner@tannen %s\n' "$(cut -d' ' -f1,2 ~/.ssh/tannen_owner.pub)" >> allowed_signers
sed -i '/TODO-owner/d' allowed_signers
grep -v '  allowed_signers$' MANIFEST.sha256 > MANIFEST.tmp \
  && sha256sum allowed_signers >> MANIFEST.tmp && mv MANIFEST.tmp MANIFEST.sha256
```

(`allowed_signers` and its manifest row are author-key territory — this edit is yours
alone to make; CLAUDE.md hard rules.)

## 2. policy.yaml values, then sign it

Set per-milestone budget envelopes, the spot-check rate K, and (if you disagree with
the defaults) licence/external-surface rules. Zeros are valid — raising any envelope
above zero is Tier-C door 1, which this signature is.

```sh
$EDITOR governance/policy.yaml
ssh-keygen -Y sign -f ~/.ssh/tannen_owner -n tannen-policy governance/policy.yaml
```

If you also want nonzero *operational* ceilings now, edit `budget.yaml` too (the guard
enforces ceilings ≤ envelopes).

## 3. brief-freeze signature

Commit the sitting, then sign the tag **with the delegation text quoted as the tag
message** (the proplang pattern — the attestation and the instruction travel together):

```sh
git add -A && git commit -m "opening sitting: owner key, signed policy, first receipt"
git -c gpg.format=ssh -c user.signingkey="$HOME/.ssh/tannen_owner" \
    tag -s brief-freeze -F DELEGATIONS.md
git -c gpg.ssh.allowedSignersFile="$PWD/allowed_signers" verify-tag brief-freeze
```

The file you are quoting ratifies the pre-existing `m0-laws-freeze` tag **by explicit
hash enumeration** (its "Founding ratification" section; D0035) and states the standing
rule that from here on delegation precedes signature. This is the one retroactive
blessing there will ever be — read that section before signing.

## 4. Custodian cron + the first receipt

```sh
bash scripts/custodian.sh    # verifies the custody floor, then writes and signs
                             # receipts/<today>.md — touch your key when it blinks
git add receipts MANIFEST.sha256 allowed_signers governance/policy.yaml.sig
git commit -m "first attention receipt"
( crontab -l 2>/dev/null; \
  echo '0 9 * * 1 cd '"$PWD"' && bash scripts/custodian.sh >> ~/.cache/tannen-custodian.log 2>&1' \
) | crontab -
```

A cron run only produces a receipt when you are there to touch the key — an unattended
machine writes no receipt, the receipt goes stale, and Tier-B consent suspends
(BRIEF §9.1). That is the design, not a failure.

## Done — confirm

```sh
make verify && make digest
```

The digest's "Requires owner" section should now be empty except for genuinely queued
Tier-C doors. One such door is already queued for this sitting: the custodian
tag-ordering guard (`docs/proposals/2026-08-24-custodian-tag-ordering.md`, D0036) —
apply it while the owner key is out, or veto it; either resolves the queue entry.
Afterwards (builder task, not yours): the next session re-pins
`concepts/semiring-relations.yaml` from `commit: null` to the brief-freeze tag.
