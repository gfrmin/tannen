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

## Added at the M2 boundary sitting (2026-08-31)

One fixture, from the M1→M2 red-team pass (`docs/redteam/2026-09-01-m2-boundary.md`,
RT-M2-01 — that pass's one **critical** finding).

| Fixture | Guard | Intended violation | Marker |
|---|---|---|---|
| `oracle-shadow-model/` | `src/tannen/laws/plugin.py`'s collection-time oracle-shadow check, as widened by D0142 | a decoy `_model` module primed into `sys.modules` via a `-p`-loaded bootstrap plugin before the frozen `tests/laws/m2/test_l2_differential.py`'s bare `import _model as M` runs | `RT-M2-01` |

This is `oracle-shadow/`'s sibling one milestone on, and the pair is the point. That
fixture pinned `_fragment`; the guard it proved pinned `_fragment` too, by name. M2 then
added `tests/laws/m2/_model.py` — bare-imported by five frozen law files — and the guard
did not cover it, so a decoy `_model` stubbing `check_differential` made **L2.9, BRIEF §6's
kill criterion, vacuous while all 113 M2 law nodes passed** and `check_manifest` reported
the seals unbroken. Reproduced live before the widening, and again after it.

The fix (D0142) does not add a second name to the guard; it derives the set from the tree —
every `tests/laws/m*/_*.py` — so M3's oracle is covered the day it is frozen rather than at
the sitting after. **This row therefore documents a class that is closed, not an instance.**
The fixture still earns its place: it is the only thing that keeps the derivation honest if
someone later replaces it with a list.

Its guard patch **is already shipped** (`src/tannen/laws/plugin.py` carries no manifest row
and no custody entry, so it was builder work), which is why this fixture installs at step 5
with the rest rather than waiting for a step-5b-style pairing — the opposite of
`check-decisions-file-skip/`, whose patch touched a custody-set file and had to land beside
it. The order is not reversible: installing this fixture before D0142 shipped would have
left the custodian permanently red against a guard that did not exist.

| `check-decisions-file-skip/` | `scripts/check_decisions.py` | a whole-file pytest binding whose target has one passing test and one unexplained `pytest.mark.skip` | `unexplained skip` |

This fixture proves RT-M1-05's fix: before it, a file-level binding with one skipped
test among several passing ones read as fully enforced (`pytest_violation` called a run
"skipped" only when *nothing* in it passed). Lands together with the guard patch it
proves — installing the fixture before the patch would leave the custodian red against
a guard that isn't shipped yet, which is why this row and `oracle-shadow/`'s were never
one table addition (see D0105 item 2).

## Added at the publication sitting (2026-09-07)

Three fixtures and one file, each the poison for a guard patch that landed at the same
sitting (D0183; `docs/proposals/2026-09-06-publication/fixture-candidates/README.md`).
`check-concepts/governance/policy.yaml` is the file: after patch 01 that fixture failed for
two reasons, and the policy narrows it back to the one it names.

| Fixture | Guard | Intended violation | Marker |
|---|---|---|---|
| `check-concepts-brief-row/` | `scripts/check_concepts.py`, tooth 2 of patch 05 (D0180) | a record whose `brief_row` quotes a row naming two owners while `sources` cites one, with no `brief_row_divergence` — against its own one-row constitution excerpt | `brief_row` |
| `check-decisions-retired-enforced/` | `scripts/check_decisions.py`, patch 06 (D0181) | an accepted record retiring another's `enforced` file binding, which must be refused | `only a documentary binding may be retired` |
| `oracle-shadow-spoofed/` | `src/tannen/laws/plugin.py`'s oracle-shadow check as sharpened by RT-M3-04 (D0179) | a decoy `_delta_model` that sets `__file__` to the frozen path — the M2-era identity test passed it outright | `answers with different code` (the guard's own text; the fixture README's `RT-M3-04` never appears in the output) |
