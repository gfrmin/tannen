# Proposal: install `oracle-shadow-cross-file/` — the anti-disarm poison fixture (D0229 item (3)(a))

**Status:** queued for the M4 boundary sitting, step 5 (fixture) and step 6 (custodian hunk).
The fixture is `docs/redteam/fixture-candidates/oracle-shadow-cross-file/`; its README carries
the argument and the full watched-failing record. Its guard (`src/tannen/laws/plugin.py`'s
oracle-shadow check) is already shipped, so it installs as a plain move.

`tests/poison/**/*` and `scripts/custodian.sh` are custody-set (Tier-C `trust-root-changes`), so
the install is owner work. `tests/test_governance_scripts.py` is in neither set, but the new test
must land **in the same step** as the move. Otherwise
`test_every_installed_fixture_is_exercised_by_this_suite` goes red ("installed but NO test
exercises it"), or, if the test lands first, it names a directory that is not there.

## 1. The custodian line (hunk for `scripts/custodian.sh`, beside `poison oracle-shadow-spoofed`)

```bash
# --- M4 DRAFT HUNK (D0229 item (3)(a)) -----------------------------------------
# The anti-disarm property of the M4 supersession, which no single-file line can see. The
# superseded tests/laws/m3/test_l3_differential.py and its successor
# tests/laws/m4/test_l4_differential_superseding.py are collected TOGETHER, superseded
# FIRST, under oracle-shadow-spoofed's code decoy. A successor loader that KEPT the frozen
# module under the bare name would overwrite the decoy before the guard reads sys.modules at
# the end of collection. The guard would then stay silent while the M3 file ran a stub:
# exit 0, measured, and the M3-only line above still bites over the same broken loader.
# Deviations are oracle-shadow-spoofed's (no -I -P, the attack IS PYTHONPATH; -B, sealed
# directory; the literal venv interpreter), plus two for the WEAKENED case only:
# --collect-only (the tooth is at collection; a weakened guard would otherwise run 28 nodes)
# and TANNEN_NO_EVIDENCE=1 (a weakened full run would write an M4 record from a stubbed
# differential; the guard is checked unconditionally under that variable). Order matters:
# with the M4 file first, nothing is ever shadowed and nothing can be detected.
poison oracle-shadow-cross-file "answers with different code" \
    env -u TANNEN_CHECK_DECISIONS_NESTED TANNEN_NO_EVIDENCE=1 \
    PYTHONPATH=tests/poison/oracle-shadow-cross-file \
    "$PY" -B -m pytest -p bootstrap_shadow_cross_file \
    tests/laws/m3/test_l3_differential.py tests/laws/m4/test_l4_differential_superseding.py \
    -q --collect-only -p no:cacheprovider
# --- end M4 DRAFT HUNK ---------------------------------------------------------
```

**Marker:** `answers with different code`, the guard's own tooth text, as for
`oracle-shadow-spoofed`. `poison()` records `tests/poison/oracle-shadow-cross-file` from the
`PYTHONPATH=` argument, so the completeness pass counts it covered.

## 2. `tests/test_governance_scripts.py`: a DEDICATED test, not a POISON row

It needs DEDICATED for the same reason as its three oracle-shadow siblings: `PYTHONPATH` is the
attack, so it cannot take POISON's `-I -P` shape. Add to the `DEDICATED` map:

```python
    "oracle-shadow-cross-file": "test_oracle_shadow_cross_file_fails_its_poison",
```

and beside `test_oracle_shadow_spoofed_fails_its_poison`:

```python
def test_oracle_shadow_cross_file_fails_its_poison() -> None:
    """D0229 item (3)(a): the M4 supersession's anti-disarm property, on the custody floor.

    tests/laws/m4/test_l4_differential_superseding.py binds L3.16's oracle from the frozen
    bytes and must BORROW the bare name `_delta_model` and put it back. A loader that kept
    the name would overwrite a decoy before the oracle-shadow guard reads sys.modules at the
    end of collection — silencing it for the superseded M3 file, which had already bound
    the decoy. Only a run collecting BOTH files, superseded first, can see that: measured
    with a keep-the-name loader, this invocation exits 0 (28 passed on a full run) while
    the M3-only invocation still aborts.

    Same deviations from POISON as test_oracle_shadow_spoofed_fails_its_poison, plus
    `--collect-only` and TANNEN_NO_EVIDENCE=1 so a weakened guard neither runs the stubbed
    differential nor writes an evidence record for it. The marker is the guard's own text.
    """
    env = {k: v for k, v in os.environ.items()
           if k != "TANNEN_CHECK_DECISIONS_NESTED" and not k.startswith("TANNEN_EVIDENCE")}
    env["PYTHONPATH"] = str(REPO_ROOT / "tests" / "poison" / "oracle-shadow-cross-file")
    env["TANNEN_NO_EVIDENCE"] = "1"
    result = run(
        [str(REPO_ROOT / ".venv" / "bin" / "python"), "-B", "-m", "pytest",
         "-p", "bootstrap_shadow_cross_file",
         "tests/laws/m3/test_l3_differential.py",
         "tests/laws/m4/test_l4_differential_superseding.py",
         "-q", "--collect-only", "-p", "no:cacheprovider"],
        env=env,
    )
    combined = result.stdout + result.stderr
    assert result.returncode != 0, (
        f"oracle-shadow-cross-file PASSED its poison — the successor disarmed the guard:\n{combined}"
    )
    assert "answers with different code" in combined, combined
```

## 3. `tests/poison/README.md` row (step 5)

```
| `oracle-shadow-cross-file/` | `src/tannen/laws/plugin.py`'s oracle-shadow check, over the M4 supersession (D0229 item 3(a)) | the superseded M3 differential and its M4 successor collected together under a code decoy — a successor that kept the bare name would silence the guard, invisible to any single-file run | `answers with different code` |
```

## Watched failing (2026-09-13, scratch clone at `5762439`, `TANNEN_NO_EVIDENCE=1`)

| Run | Measured |
|---|---|
| The invocation, shipped loader | **exit 1**, `answers with different code for ['check_differential']`, ~1-2s wall |
| Negative control: `_frozen_bind.m3()` keeps the bare names (clone only) | **exit 0**, 28 collected; full run `28 passed in 12.66s` |
| Same keep-the-name loader, M3 file alone | **exit 1**: the single-file line cannot see the disarm |
| M3 file alone, shipped loader | **exit 1**: the decoy arrives |
| Loader restored | **exit 1** again |
| Shipped loader, M4 file first | **exit 1** (borrow-and-restore is order-robust) |
| Keep-the-name loader, M4 file first | **exit 0**, M3 file bound the honest module: why the order is fixed |
| Both files, no decoy | **exit 0**, 28 collected |

The DEDICATED test text above was run as written, pasted into the scratch clone's
`tests/test_governance_scripts.py`: `1 passed in 0.78s` with the shipped loader, and **FAILED**
(`oracle-shadow-cross-file PASSED its poison — the successor disarmed the guard`) with the
keep-the-name loader. Both the paste and the loader edit were reverted in the clone.
