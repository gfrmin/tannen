
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
