# DELEGATIONS — standing delegations (BRIEF §9)

Drafted at Session 0 (2026-08-24), quoting BRIEF §9's standing-delegation clause.
**Status: drafted, not yet binding.** These delegations become binding when the owner
signs the `brief-freeze` tag with this file quoted as the tag message
(`docs/OPENING.md`, step 2) — the proplang tag-message pattern: the delegation is
recorded verbatim in the signed tag, so the attestation and the instruction travel
together.

## The standing delegations (BRIEF §9, verbatim basis)

> Standing delegations, recorded once in-repo (the proplang tag-message pattern):
> builder key signs law-freeze tags and implementation commits; budget file authorises
> oracle spend up to its ceiling without asking; goldens regenerate freely when the
> descriptor moved with them.

Expanded, with the custody semantics adopted from the `frozen-oracle-protocol` concept
(pinned in `concepts/frozen-oracle-protocol.yaml`):

1. **Builder key signs law-freeze tags and implementation commits.** The builder signs
   its own commits with the builder key and never touches the owner's key. Per-milestone
   `<milestone>-laws-freeze` tags are builder-signed under this standing delegation,
   with this delegation cited in the tag message; the signature truthfully attests
   builder action under recorded instruction and cannot mint an owner attestation.
   Owner countersignature is required only at the M0 opening (`brief-freeze`) and the
   M5 close (Tier C: opening-closing-signatures).
2. **The budget file authorises oracle spend up to its ceiling without asking.**
   `budget.yaml` is the whole authorisation; spend beyond any ceiling is Tier C. All
   ceilings are zero until the owner raises them.
3. **Goldens regenerate freely when the descriptor moved with them.** A golden
   regeneration accompanied by the corresponding descriptor change is a Tier-A act
   (one-command, reviewable diff); a golden change without a descriptor change remains
   a CI failure (BRIEF §5.2).

## Keys

Signing principals are distinct by design (decision D0015): `builder@tannen` and
`owner@tannen`. Author-signed artifacts (attention receipts per BRIEF §9.1, the
`brief-freeze` tag, the M5 close) verify only against `owner@tannen`.

- **Builder key** (`builder@tannen`): `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIw1aGU616gN1UKSQw9xiZHxKNRStcJRF9NtkJjXVnuc`
  (generated Session 0; public half in `allowed_signers`; private half never enters the repo).
- **Owner key** (`owner@tannen`): not yet supplied — `allowed_signers` carries a
  TODO-owner placeholder until the opening sitting; hardware-backed (touch = presence)
  per BRIEF §9.1.
