    "oracle-shadow-cross-file": "test_oracle_shadow_cross_file_fails_its_poison",
# --- function ---
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
