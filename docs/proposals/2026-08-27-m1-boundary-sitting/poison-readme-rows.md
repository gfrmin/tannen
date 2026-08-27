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
