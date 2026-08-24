# M0→M1 boundary sitting — the materials the owner applies

Staged here because each one edits something the builder may not: a frozen path, the
owner-signed policy file, or the trust root. `scripts/boundary_sitting.sh` applies them in
the order below; `docs/SITTING.md` is the prose checklist behind it. Nothing here is live
until the owner applies it — the repo is green with all of it sitting unapplied.

**Read `CONFERRAL.md` first** — it is the deciding document: what is being asked,
what declining costs, what stays open afterwards, and what a reviewer should try to
break. The table below is the applying document.

| File | Applies to | Why the owner |
|---|---|---|
| `custodian.sh` | `scripts/custodian.sh` | Trust root, author-key territory. Offered as a whole-file diff rather than prose patches: this is the guard of the guards, and a reviewer should see every line they are vouching for. Adds the custody-set hash pass, the tag-signer invocation, required (not optional) owner signatures, and a poison line per new fixture. |
| `policy-append.yaml` | `governance/policy.yaml` | Owner-signed; any edit invalidates the signature. The `in_repo_mechanics` clause (D0048, D0053). |
| `apply_binding_strength.py` | `governance/schemas/decision-record.schema.json` + 14 records | The schema is frozen. Idempotent, and lands both halves together: a schema allowing `strength` while no record uses it would report `0 documentary`, a false number rather than no number. |
| `poison-readme-rows.md` | `tests/poison/README.md` | `tests/poison/` is author-key territory. |
| `brief-9.1-amendment.md` | `BRIEF.md` §9.1 | Frozen owner text. Two additive bullets promoted from conferral rulings 2 and 5: metric calibration, and presence-vs-authorisation. |
| `ci.yml` | `.github/workflows/ci.yml` | Frozen. Adds `fetch-depth: 0` — a shallow checkout arrives without tags, which the custody floor refuses (RT-15), and without the history the receipt chain walks. |

Fixture candidates live one directory up, under `docs/redteam/fixture-candidates/`; the
driver `git mv`s them into `tests/poison/` and adds a manifest row per file, because
`tests/poison` is a sealed directory (D0056: every file under a seal carries a row).

## The one step that hands back

`scripts/check_decisions.py` does not yet require Tier-C records to carry an owner
signature (RT-06). That guard cannot land before the signatures exist — it would turn the
gate red before the owner could sign, and the pre-commit hook would block the builder's
own commit. So the driver signs first, then pauses and asks a builder session to land it,
then continues. The fixture `check-decisions-unsigned-tier-c/` installs after that patch.

## Verification after the sitting

`make verify` green, and in particular:

- `custodian: custody set hashes verify (N path(s))` and `governance/custody.sha256
  signature verifies (owner@tannen)`;
- every new fixture reported as `guard '<name>' fails its poison as required`;
- `check_tag_signers: OK` with `m0-close: owner@tannen (class role: owner)`;
- the digest's documentary binding count non-zero — the first honest baseline.
