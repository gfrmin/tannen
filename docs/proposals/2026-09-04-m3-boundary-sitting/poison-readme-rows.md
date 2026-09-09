
## Added at the M3 boundary sitting (2026-09-04)

One fixture, and **not** from the M3 boundary red-team pass. That pass
(`docs/redteam/2026-09-05-m3-boundary.md`) found six things, and its one fixture-shaped
critical — RT-M3-04, the `_delta_model` decoy that set `__file__` to the frozen path —
landed early, at the publication sitting of 2026-09-07, as `oracle-shadow-spoofed/`. What
installs here is the older gap: **D0154 item (7)**, one of the three items D0171 ruling (4)
keeps in this sitting.

| Fixture | Guard | Intended violation | Marker |
|---|---|---|---|
| `check-laws-dropped-successor/` | `scripts/check_laws.py`, driven with `--root` | `governance/laws.yaml` retires a law node with `successor: "L9.99"`, which no law file in the tree defines — D0106 ruling 2's supersede-forward rule with nothing carrying it forward | `which no law file defines` |

`scripts/check_laws.py` was the **only** custody-set guard with neither a fixture under
`tests/poison/` nor a `poison` line in the custodian: `grep check_laws scripts/custodian.sh`
returned nothing. The M2 sitting put it in the custody set (D0131 items 3–4, step 4e), which
made it a guard the owner signs for, and this sitting is the first at which the custodian can
say it has teeth.

**What was missing was never the test.** `tests/test_law_validation.py` already refuses a
supersession whose successor no law defines, with a tmp_path tree and a non-zero exit. But
that file is unfrozen and uncustodied — an ordinary file any builder may weaken, with no
signature over its bytes — so the claim rested on something the custody floor cannot see.
What this fixture adds is the FLOOR exercising the guard, on every custodian run, under the
owner's signature. RT-M3-02 names the same shape one layer down: "pinned by one unsealed
test and by no frozen law".

The tree carries no `MANIFEST.sha256`, deliberately: no law file then counts as frozen, so
`check_declarations` requires nothing and the fixture fails for exactly one reason. Its
positive control is in the fixture's own README — with `successor: "L1.7"`, a node the tree
does define, the same guard exits 0.

Ordering is load-bearing and already correct: this fixture installs at **step 5**, and the
custodian line that names it (hunk 5) installs at **step 6**. Reverse them and hunk 1a — new
in this milestone's custodian — refuses the named fixture as NOT INSTALLED, which is the
right answer and would still stop the sitting at step 7.
