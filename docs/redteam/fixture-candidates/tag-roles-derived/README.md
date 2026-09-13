# Fixture candidate — a required tag the hand list never learned (D0205, D0229 item 4)

**Guard:** `scripts/check_tag_signers.py`, as patched by
`docs/proposals/2026-09-11-m4-boundary-sitting/required-tags-derived.patch`.
**Status: DRAFT — installs at the M4 boundary sitting, in the same sitting as the patch.**

## What it proves

`required_tags` in `governance/tag-roles.yaml` was a hand-maintained list, and it lagged by one
milestone at every boundary: at M4 Session A it lacked `m4-laws-freeze`, the fifth recurrence of
D0095 (RT-M4-06). The patch derives the list from `docs/specs/*.md` instead
(`docs/proposals/2026-09-04-m3-boundary-sitting/TAG-ROLES-DERIVED.md` gives the rule and its
non-circularity argument).

This tree carries specs `m0`…`m4` and — once `make-fixture.sh` has run — a bundle holding every
tag the rule derives **except `m3-close`**, each signed by the principal its class requires, with
the trust-root pin naming the bundle's own `brief-freeze`. The guard must fail with
`required tag missing: m3-close`, and that must be its only violation. One fixture, one reason.

The negative control is the point. The **shipped** guard run against this tree passes, because
its hand list (empty here) contains nothing to miss. That passing run is the lag, demonstrated.

## How it is exercised

```
bash tests/poison/tag-roles-derived/make-fixture.sh     # at the sitting, before manifesting
.venv/bin/python -I -P scripts/check_tag_signers.py \
    --root tests/poison/tag-roles-derived --repo tests/poison/tag-roles-derived/repo.bundle
```

The custodian's `poison` line uses the second command with the marker
`required tag missing: m3-close`. The marker names the tag, not only the message class: the
sibling fixture `custodian-tag-signer/` already produces `required tag missing: brief-freeze`,
and a marker that could be satisfied by that fixture's tooth would not test this one.

## Why it is generated, and with which keys

A bundle is opaque, so it is made at the sitting where it can be watched being made (conferral
ruling 6). Neither real key is used: `make-fixture.sh` mints two throwaway ed25519 keys, enrols
their public halves here as `owner@tannen` and `builder@tannen`, signs, and deletes the private
halves. The tag list is derived from this directory's specs the way the guard derives it; the
only name written in the script is the one left out.

**Generate before manifesting.** `repo.bundle`, `allowed_signers` and `governance/tag-roles.yaml`
are written by the script, so their manifest rows must be taken after it runs, or the sealed
directory holds unmanifested files and `check_manifest` goes red.

## The obligation (D0246 A4's direction)

A candidate enforces nothing (D0143). The obligation to install it sits on the record that
closes D0229 item (4) — the derivation landing — not on this draft: if the patch is installed and
this fixture is not, that record must say why.
