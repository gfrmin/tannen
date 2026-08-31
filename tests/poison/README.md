# tests/poison — the poison corpus (BRIEF §9.1: guard liveness)

One deliberately violating fixture per guard. `scripts/custodian.sh` (and
`tests/test_governance_scripts.py`) run every guard against its fixture and require it
to FAIL, for the intended reason (a marker string in its output). A guard that passes
its poison is weakened, and the custodian says so — this is how a silently disabled or
softened check is caught.

AUTHOR-KEY TERRITORY (CLAUDE.md hard rules): this directory and its MANIFEST.sha256
rows are owner-edited only, with one standing exception recorded in BRIEF §9.1:
**red-team findings at each milestone boundary become poison fixtures** — the builder
drafts the fixture from the finding, and it lands via the boundary sitting where the
owner re-signs the manifest.

| Fixture | Guard | Intended violation | Marker |
|---|---|---|---|
| `check-manifest/` | `scripts/check_manifest.py` | manifested file whose bytes drifted | `frozen path modified` |
| `check-concepts/` | `scripts/check_concepts.py` | vendored snapshot ≠ recorded sha256 | `snapshot content drifted` |
| `check-decisions/` | `scripts/check_decisions.py` | binding target that does not exist | `binding does not resolve` |
| `lint-imports/` | `lint-imports` (import-linter) | forbidden import inside the checked package | `BROKEN` |

Fixture trees are minimal: they carry only what the guard needs to reach the intended
violation (schemas fall back to the real repo's frozen ones). Collateral violations
(e.g. a fixture tree lacking CONCEPTS.md) are expected; the marker check is what pins
the intended tooth.

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
## Added at the M1 boundary sitting (2026-08-27)

One fixture, from the M1 red-team pass (`docs/redteam/2026-08-26-m1-boundary.md`,
RT-M1-01). `check-decisions-file-skip/` (RT-M1-05) is deliberately not in this table —
its guard fix is not applied by the time step 5 runs (D0103); it's added by step 5b
instead, in `poison-readme-row-file-skip.md`, right after that step lands the patch.

| Fixture | Guard | Intended violation | Marker |
|---|---|---|---|
| `oracle-shadow/` | `src/tannen/laws/plugin.py`'s collection-time oracle-shadow check | a decoy `_fragment` module primed into `sys.modules` via a `-p`-loaded bootstrap plugin before the frozen `tests/laws/m1/test_l1_duckdb.py`'s bare `import _fragment as F` runs | `RT-M1-01` |

This fixture proves the check added this session runs against the **real** frozen law
file, the same way `lint-imports-kernel/` runs against the repo's real import contracts —
not a copy, so it goes silent exactly when the check is neutered. It defends against one
exploitation of the naming hazard, not the hazard itself; the real fix (a package-qualified
import in the frozen file) is queued for a future sitting, since `test_l1_duckdb.py` is
frozen and manifested (`m1-laws-freeze`).
