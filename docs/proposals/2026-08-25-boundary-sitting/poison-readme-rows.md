
## Added at the M0→M1 boundary sitting (2026-08-25)

Every row below is a red-team finding that became a fixture, which is the standing
exception in BRIEF §9.1: the builder drafts from the finding, the owner installs. The
first four fixtures above prove their guard *runs*; these prove it still has the specific
tooth the red team had to file off to get past it.

| Fixture | Guard | Intended violation | Marker |
|---|---|---|---|
| `lint-imports-kernel/` | `lint-imports` against the **real** contracts | a tree shadowing `tannen` that imports everything all three contracts forbid | `tannen.kernel is not allowed to import os` (+ `datetime`, `pkm`) |
| `check-decisions-ratchet/` | `scripts/check_decisions.py` | two unbound records against a baseline digest recording `unenforced=0` | `RATCHET BREACH` |
| `check-decisions-nested-hatch/` | `scripts/check_decisions.py` | a pytest binding whose node does not collect | `binding does not resolve` |
| `check-decisions-unsigned-tier-c/` | `scripts/check_decisions.py` | a Tier-C record marked `accepted` with no owner signature | `Tier-C record accepted without an owner signature` |
| `check-manifest-sealed/` | `scripts/check_manifest.py` | a file inside a sealed directory carrying no manifest row | `unmanifested file in sealed path` |
| `check-manifest-unsigned-policy/` | `scripts/check_manifest.py` | a declared owner-signed artifact whose signature was deleted | `missing owner signature` |
| `custodian-tag-signer/` | `scripts/check_tag_signers.py` | one bundle, two teeth: a builder-signed `*-close` tag, in a repo whose trust root is gone | `tag signed by the wrong principal` / `required tag missing` |

`custodian-tag-signer/` is the only fixture that is not a tree of ordinary files: its
violation is a *signed git object*, so it ships as a one-file `repo.bundle` that
`scripts/check_tag_signers.py --repo` knows how to clone. `make-fixture.sh` regenerates
it; the builder key signs the poison tag, and it is deliberately a tag no real milestone
will ever be named (`poison-m9-close`).
