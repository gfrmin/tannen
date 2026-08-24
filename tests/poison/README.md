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
