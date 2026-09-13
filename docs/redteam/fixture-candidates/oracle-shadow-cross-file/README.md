# `oracle-shadow-cross-file/` — a successor law must not disarm the guard for the law it supersedes

**Item:** D0229 item (3)(a); `docs/proposals/2026-09-04-m3-boundary-sitting/SUPERSESSIONS.md`,
"What is genuinely owner-only", item (a). Not a red-team finding. It pins a property that the
M4 Session A supersession established and that nothing on the custody floor watches.

**Status: DRAFT candidate. Its guard is already shipped, so it installs as a plain `git mv`
at the M4 boundary sitting** (owner key, Tier-C `trust-root-changes`), together with its
custodian line and its `tests/test_governance_scripts.py` DEDICATED test
(`docs/proposals/2026-09-11-m4-boundary-sitting/oracle-shadow-cross-file.md`).

**Guard:** `src/tannen/laws/plugin.py`'s oracle-shadow check (`_oracle_shadow_problem` →
`_substituted_callables`). At the end of collection it reads `sys.modules` once for every bare
stem under `tests/laws/m*/_*.py` and compares the CODE each answers with against a fresh load
of the frozen file.

## What it proves

`tests/laws/m4/test_l4_differential_superseding.py` (frozen, L4.22) supersedes
`tests/laws/m3/test_l3_differential.py` (L3.16) forward. It binds the same oracle,
`_delta_model`, from the frozen bytes by file location through `tests/laws/m4/_frozen_bind.py`.
That loader **borrows** the bare names `_delta_model` and `_delta_subject` for the load and
**puts back** whatever it found.

If a successor loader instead KEPT the frozen module under the bare name, it would overwrite a
decoy in `sys.modules` after the superseded M3 file had already bound that decoy. The guard reads
`sys.modules` only at the end of collection, so it would see the honest module and stay silent.
The M3 differential would then run against a stub, and the run would be green.

**This is invisible to every single-file invocation.** Every oracle-shadow poison line collects
one law file. A loader that keeps the name leaves each of those lines biting while it disarms
the guard for any run that collects both files, which is what `make verify` does. The property
needs a fixture whose invocation collects the superseded file and its successor **together**,
superseded **first**.

The decoy is `oracle-shadow-spoofed/`'s, byte for byte in substance: a spoofed `__file__` and a
stub `check_differential`. What differs is the invocation, and that is this fixture's one
reason. Until it is installed, the property is held only by assertion 2 of the unfrozen
`tests/test_governance_scripts.py::test_a_superseded_law_binds_its_oracle_from_the_frozen_bytes`.

## How it is exercised

From the repo root, with the fixture installed at `tests/poison/oracle-shadow-cross-file/`:

```sh
env -u TANNEN_CHECK_DECISIONS_NESTED TANNEN_NO_EVIDENCE=1 \
    PYTHONPATH=tests/poison/oracle-shadow-cross-file \
    .venv/bin/python -B -m pytest -p bootstrap_shadow_cross_file \
    tests/laws/m3/test_l3_differential.py tests/laws/m4/test_l4_differential_superseding.py \
    -q --collect-only -p no:cacheprovider
```

It must exit non-zero with `answers with different code`.

**The file order is the attack.** Measured with a keep-the-name loader and the M4 file collected
first: the M3 file binds the honest module (a probe on the collected item reports
`bound decoy: False`), nothing is shadowed, and the run exits 0. That is correct behaviour, but it
detects nothing, so an invocation in that order could never catch the disarm.

The run deviates from `poison()`'s usual form exactly as `oracle-shadow-spoofed/` does:
- **No `-I -P`.** The attack *is* PYTHONPATH.
- **`-B`.** The decoy is imported from inside a sealed directory.
- **The literal venv interpreter.**

Two further deviations are new here, and both concern the weakened case only:
- **`--collect-only`.** The guard's tooth is at collection, so nothing is lost. A weakened guard
  otherwise runs all 28 nodes (measured 12.66s) instead of returning in about a second.
- **`TANNEN_NO_EVIDENCE=1`.** A weakened full run would otherwise write an M4 evidence record from
  a stubbed differential. The guard is checked unconditionally under that variable (plugin.py,
  `pytest_collection_modifyitems`), so setting it removes no tooth.

## Watched failing, 2026-09-13

Run in a scratch clone of the M4 worktree at `5762439`, with its own venv (verified: `tannen`
and `tannen.laws.plugin` resolve inside the clone), the fixture placed at its installed path,
and `TANNEN_NO_EVIDENCE=1`. The real tree was never poisoned.

| # | Run | Expected | Measured |
|---|---|---|---|
| 1 | the invocation above, shipped loader | non-zero, guard's text | **exit 1**, `answers with different code for ['check_differential']`, ~1-2s |
| 1b | the same without `--collect-only` | non-zero | **exit 1**, aborts at collection, ~1s |
| 2 | **negative control:** `_frozen_bind.m3()` made to KEEP the bare names (clone only) | exit 0, the disarm | **exit 0**, `28 tests collected`; full run **`28 passed in 12.66s`** |
| 2c | the keep-the-name loader, M3 file alone | still non-zero | **exit 1**, same text: the single-file line cannot see row 2 |
| 3 | M3 file alone, shipped loader (the decoy arrives) | non-zero | **exit 1**, same text |
| 4 | the loader restored, both files | non-zero again | **exit 1** |
| 5 | shipped loader, M4 file collected FIRST | non-zero (borrow-and-restore is order-robust) | **exit 1** |
| 6 | keep-the-name loader, M4 file FIRST | exit 0, decoy never bound | **exit 0**; probe `bound decoy: False` |
| 7 | control: both files, no decoy | exit 0 | **exit 0**, `28 tests collected` |

Rows 2 and 2c together are the reason this fixture exists: the same broken loader passes the
two-file run and fails the one-file run. Session A's measurement of the same disarm, over a
wider collection, was 52 passed, exit 0.

## Install obligation

Installing is:
1. `git mv` this directory to `tests/poison/oracle-shadow-cross-file/`;
2. a `MANIFEST.sha256` row per file;
3. the `poison oracle-shadow-cross-file` line in `scripts/custodian.sh`;
4. a DEDICATED entry and test in `tests/test_governance_scripts.py`, landed in the same step so
   `test_every_installed_fixture_is_exercised_by_this_suite` stays green;
5. a `tests/poison/README.md` row.

Installed without step 3, the custodian's completeness pass reddens the floor. Without step 4,
the suite does.
