"""The guards guard, and the poison proves it (BRIEF §9, §9.1).

Success path: every check script exits 0 against the real tree. Liveness: every guard
exits non-zero against its tests/poison/ fixture AND emits the fixture's intended
marker — the same matrix scripts/custodian.sh enforces, exercised here from pytest so
plain `uv run pytest` catches a weakened guard too.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def run(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=REPO_ROOT, capture_output=True, text=True, **kwargs)


CHECKS = ["check_manifest.py", "check_concepts.py", "check_decisions.py"]


@pytest.mark.parametrize("script", CHECKS)
def test_check_passes_on_real_tree(script: str) -> None:
    result = run([sys.executable, f"scripts/{script}"])
    assert result.returncode == 0, result.stdout + result.stderr


#: Named exactly as scripts/custodian.sh names them, so a failure here and a failure there
#: are recognisably the same fact. The custodian is the floor and this is not a substitute
#: for it — it runs the same matrix from plain `uv run pytest`, which is what CI and a
#: builder run far more often than they run the custodian.
#:
#: The four original entries prove their guard runs at all. The rest were installed at the
#: M0 boundary sitting from the red-team pass (D0059) and prove a guard still has the
#: specific tooth a finding had to file off; a guard that loses one of these is weakened in
#: a way the first four cannot see.
POISON = [
    ("check_manifest", ["scripts/check_manifest.py", "--root", "tests/poison/check-manifest"],
     "frozen path modified"),
    ("check_concepts", ["scripts/check_concepts.py", "--root", "tests/poison/check-concepts"],
     "snapshot content drifted"),
    ("check_decisions", ["scripts/check_decisions.py", "--root", "tests/poison/check-decisions"],
     "binding does not resolve"),
    ("check_manifest_sealed",
     ["scripts/check_manifest.py", "--root", "tests/poison/check-manifest-sealed"],
     "unmanifested file in sealed path"),
    ("check_manifest_signature",
     ["scripts/check_manifest.py", "--root", "tests/poison/check-manifest-unsigned-policy"],
     "missing owner signature"),
    ("check_decisions_ratchet",
     ["scripts/check_decisions.py", "--root", "tests/poison/check-decisions-ratchet"],
     "RATCHET BREACH"),
    ("check_decisions_pytest",
     ["scripts/check_decisions.py", "--root", "tests/poison/check-decisions-nested-hatch"],
     "binding does not resolve"),
    ("check_decisions_tier_c",
     ["scripts/check_decisions.py", "--root", "tests/poison/check-decisions-unsigned-tier-c"],
     "Tier-C record accepted without an owner signature"),
    ("check_tag_signers_principal",
     ["scripts/check_tag_signers.py", "--root", "tests/poison/custodian-tag-signer",
      "--repo", "tests/poison/custodian-tag-signer/repo.bundle"],
     "tag signed by the wrong principal"),
    ("check_tag_signers_required",
     ["scripts/check_tag_signers.py", "--root", "tests/poison/custodian-tag-signer",
      "--repo", "tests/poison/custodian-tag-signer/repo.bundle"],
     "required tag missing"),
    # Installed at the M1 boundary sitting (RT-M1-05, D0103). The fixture proves the
    # patch that landed with it: a whole-FILE pytest binding whose run mixes passes with
    # one unexplained skip used to report enforced, because `pytest_violation` called a
    # run skipped only when NOTHING in it passed. Most bindings in decisions/*.yaml name
    # a file rather than a node, so that was the common case, not the corner.
    ("check_decisions_file_skip",
     ["scripts/check_decisions.py", "--root", "tests/poison/check-decisions-file-skip"],
     "unexplained skip"),
]


@pytest.mark.parametrize("name, args, marker", POISON, ids=[p[0] for p in POISON])
def test_guard_fails_its_poison(name: str, args: list[str], marker: str) -> None:
    # TANNEN_CHECK_DECISIONS_NESTED is unset for every poison run, not only the three that
    # obviously need it. check_decisions sets it for the pytest runs it spawns to resolve
    # bindings — so when THIS suite is reached through such a run, an inherited value would
    # switch off the very checking the fixture is meant to trip, and the guard would pass
    # its poison while reporting green. That is RT-08 exactly, arriving through the one
    # channel `-I` does not close (it ignores PYTHON* variables, not arbitrary ones), and
    # the custodian unsets it for the same reason. A poison run must not be silenceable.
    env = {k: v for k, v in os.environ.items() if k != "TANNEN_CHECK_DECISIONS_NESTED"}
    # The env VARIABLE, not the -B flag, and it is set for every row rather than the one
    # that needs it today. check_decisions.py resolves a pytest binding by spawning pytest
    # as a SUBPROCESS; -B sets sys.dont_write_bytecode on the process it is given to and
    # does not survive that fork, while run_pytest's env={**os.environ, ...} forwards this.
    # Without it the file-skip fixture's tree gets imported and leaves __pycache__ inside
    # tests/poison/ — a sealed directory where every file needs a manifest row — so the
    # next check_manifest run goes red for a reason nothing in this file explains. The
    # hazard belongs to any fixture tree that gets imported, not to one guard, which is
    # why it is applied here once instead of per row. (-I ignores PYTHON* for the outer
    # interpreter, which is fine: the value only has to reach the child.)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = run([sys.executable, "-I", "-P", *args], env=env)
    combined = result.stdout + result.stderr
    assert result.returncode != 0, f"guard '{name}' PASSED its poison — weakened:\n{combined}"
    assert marker in combined, f"guard '{name}' failed poison for the wrong reason:\n{combined}"


def test_oracle_shadow_fails_its_poison() -> None:
    """RT-M1-01 (D0102): L1.16's differential oracle refuses to run against a `_fragment`
    that is not the frozen one, instead of silently comparing against the impostor.

    Deliberately NOT a row in POISON above, because every difference from that table is
    load-bearing and a shared runner would erase all three. No `-I -P`: the attack under
    test is a module reaching sys.modules through PYTHONPATH ahead of the frozen file's
    bare `import _fragment as F`, and isolated mode ignores PYTHONPATH outright — under
    `-I` the fixture's own setup could never run, so the guard would report green having
    never been challenged. `-B` because the fixture is imported from inside
    tests/poison/oracle-shadow, a sealed directory an unmanifested __pycache__ would
    break. And it is a pytest run rather than a check_*.py run, so there is no --root.
    The venv interpreter at a literal path (D0063 ruling 3) is the one thing it keeps.
    """
    env = {k: v for k, v in os.environ.items() if k != "TANNEN_CHECK_DECISIONS_NESTED"}
    env["PYTHONPATH"] = str(REPO_ROOT / "tests" / "poison" / "oracle-shadow")
    result = run(
        [str(REPO_ROOT / ".venv" / "bin" / "python"), "-B", "-m", "pytest",
         "-p", "bootstrap_shadow", "tests/laws/m1/test_l1_duckdb.py",
         "-k", "test_l1_16_the_catalogue_covers_every_operator_of_the_fragment", "-q"],
        env=env,
    )
    combined = result.stdout + result.stderr
    assert result.returncode != 0, f"oracle-shadow PASSED its poison — weakened:\n{combined}"
    assert "RT-M1-01" in combined, combined
    assert "shadowed" in combined, combined


def test_oracle_shadow_covers_every_frozen_oracle_not_just_fragment(tmp_path: Path) -> None:
    """RT-M2-01 (D0141), the M1->M2 boundary red team's one critical finding: the check
    above pinned the single name `_fragment`, so M2's `_model` — bare-imported by five
    frozen law files — was unguarded. A decoy `_model` re-exporting the real one made
    L2.9, BRIEF §6's kill criterion, answerable by an impostor while all 113 M2 law
    nodes passed and check_manifest reported the seals unbroken.

    This test CONSTRUCTS THE VIOLATING STATE ITSELF (D0092) rather than reading a
    tests/poison/ fixture: installing one there is the owner's act at a boundary sitting,
    and a regression test that waits for a sitting is not a regression test. The poison
    fixture is queued separately (docs/redteam/fixture-candidates/oracle-shadow-model/)
    and proves the same thing from the custodian's floor.

    Two runs, because "pytest exited non-zero" alone would be satisfied by a decoy that
    merely fails to import. The second run establishes that the decoy is FAITHFUL — it
    answers to the name with the real module's API — so the first run's non-zero exit is
    the guard biting and not an import error wearing its clothes.
    """
    # Walks up to MANIFEST.sha256 rather than counting parents, so the decoy is
    # position-independent: tmp_path is nowhere near the repo.
    (tmp_path / "_model.py").write_text(
        "import importlib.util as ilu\n"
        "from pathlib import Path\n"
        f"real = Path({str(REPO_ROOT)!r}) / 'tests' / 'laws' / 'm2' / '_model.py'\n"
        "spec = ilu.spec_from_file_location('_model_real_regression', real)\n"
        "mod = ilu.module_from_spec(spec)\n"
        "spec.loader.exec_module(mod)\n"
        "for name in dir(mod):\n"
        "    if not name.startswith('__'):\n"
        "        globals()[name] = getattr(mod, name)\n"
    )
    # Loaded with -p before collection, so this import wins the sys.modules cache ahead
    # of the frozen law file's own bare `import _model as M`.
    (tmp_path / "bootstrap_shadow_model_regression.py").write_text("import _model  # noqa: F401\n")

    env = {k: v for k, v in os.environ.items() if k != "TANNEN_CHECK_DECISIONS_NESTED"}
    env["PYTHONPATH"] = str(tmp_path)
    # tests/laws/ is a SEALED directory: exec_module on the frozen _model.py would drop
    # an unmanifested __pycache__ beside it and turn the next check_manifest run red for
    # a reason nothing here explains. Same hazard, same cure, as the POISON runner above.
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # No -I -P: the attack IS a module reaching sys.modules through PYTHONPATH, and
    # isolated mode ignores PYTHONPATH outright, so under -I the fixture could never run
    # and the guard would report green having never been challenged.
    shadowed = run(
        [str(REPO_ROOT / ".venv" / "bin" / "python"), "-B", "-m", "pytest",
         "-p", "bootstrap_shadow_model_regression", "tests/laws/m2/test_l2_differential.py",
         "-q"],
        env=env,
    )
    combined = shadowed.stdout + shadowed.stderr
    assert shadowed.returncode != 0, (
        "a decoy _model answered for the frozen tests/laws/m2/_model.py and L2.9 ran "
        f"against it anyway — the oracle-shadow check has narrowed again:\n{combined}"
    )
    assert "RT-M2-01" in combined, combined
    assert "shadowed" in combined, combined
    assert str(tmp_path) in combined, f"the guard named some other module:\n{combined}"

    faithful = run(
        [str(REPO_ROOT / ".venv" / "bin" / "python"), "-B", "-c",
         "import _model; assert _model.check_differential and _model.SHAPES"],
        env=env,
    )
    assert faithful.returncode == 0, (
        "the decoy does not re-export the frozen model's API, so the run above proves "
        f"nothing about shadowing:\n{faithful.stdout + faithful.stderr}"
    )


LINT_ISOLATED = [
    str(REPO_ROOT / ".venv" / "bin" / "python"), "-I", "-c",
    "import sys; from importlinter.cli import lint_imports_command; "
    "sys.exit(lint_imports_command())",
]
#: --no-cache is not optional for a poison run: the cache directory would land inside
#: tests/poison/, a sealed directory where every file must carry a manifest row.


def test_lint_imports_fails_its_poison() -> None:
    # Invoked exactly as the custodian invokes it (D0063 ruling 3): the venv interpreter
    # at a literal path, isolated, with the poison tree supplied as the working directory
    # rather than through PYTHONPATH — which -I ignores, and which was the same inherited
    # environment channel RT-08 exploited. A liveness test that used a different
    # invocation from the floor would be proving the wrong thing works.
    result = subprocess.run(
        [*LINT_ISOLATED, "--no-cache", "--config", "pyproject.toml"],
        cwd=REPO_ROOT / "tests" / "poison" / "lint-imports",
        capture_output=True, text=True,
    )
    combined = result.stdout + result.stderr
    assert result.returncode != 0, f"lint-imports PASSED its poison — weakened:\n{combined}"
    assert "BROKEN" in combined, combined


#: The kernel's import contracts, one poison run per contract. They live in
#: governance/importlinter.toml and NOT in pyproject.toml, deliberately: the contracts are
#: part of the custody floor and pyproject.toml is builder-editable dependency territory
#: (D0063 ruling 3). The config path must therefore be absolute — the run happens with the
#: poison tree as its working directory, which is how the shadowing modules get onto
#: sys.path without an environment variable.
KERNEL_CONTRACTS = [
    "tannen.kernel is not allowed to import os",
    "tannen.kernel is not allowed to import datetime",
    "tannen is not allowed to import pkm",
]


@pytest.mark.parametrize("marker", KERNEL_CONTRACTS)
def test_lint_imports_kernel_fails_its_poison(marker: str) -> None:
    result = subprocess.run(
        [*LINT_ISOLATED, "--no-cache", "--config", str(REPO_ROOT / "governance" / "importlinter.toml")],
        cwd=REPO_ROOT / "tests" / "poison" / "lint-imports-kernel",
        capture_output=True, text=True,
    )
    combined = result.stdout + result.stderr
    assert result.returncode != 0, f"lint-imports PASSED its kernel poison — weakened:\n{combined}"
    assert marker in combined, f"contract not reported broken: {marker}\n{combined}"


def test_stale_projection_detected(tmp_path: Path) -> None:
    """Hand-editing a generated projection must turn check_concepts red."""
    import shutil

    root = tmp_path / "tree"
    for rel in ("concepts", "governance", "MANIFEST.sha256", "CONCEPTS.md", "DECISIONS.md",
                "decisions", "pyproject.toml", "budget.yaml", "allowed_signers"):
        src = REPO_ROOT / rel
        if src.is_dir():
            shutil.copytree(src, root / rel)
        else:
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, root / rel)
    concepts_md = root / "CONCEPTS.md"
    concepts_md.write_text(concepts_md.read_text(encoding="utf-8") + "\nhand edit\n", encoding="utf-8")
    # The header hash still matches its inputs, so freshness alone would pass; the
    # regeneration hook restores content. What MUST fail is a header/inputs mismatch:
    (root / "concepts" / "pkm-determinism.yaml").write_text(
        (root / "concepts" / "pkm-determinism.yaml").read_text(encoding="utf-8") + "\n# drift\n",
        encoding="utf-8",
    )
    result = run([sys.executable, "scripts/check_concepts.py", "--root", str(root)])
    assert result.returncode != 0
    assert "stale" in (result.stdout + result.stderr)


def test_a_skip_hidden_inside_a_passing_file_binding_is_caught(tmp_path: Path) -> None:
    """RT-M1-05 (2026-08-26 boundary red team). Most pytest bindings in decisions/*.yaml
    name a whole FILE, not one node (D0083, D0093, D0100, D0101, ...). `pytest_violation`
    used to call a run "skipped" only when NOTHING in it passed; a file with several test
    functions where just one is skipped and the rest pass never tripped that condition,
    the run exited 0, and the binding was reported enforced.

    Constructed as a self-contained tree (D0092's rule): a decision record bound to a file
    holding one passing test and one `pytest.mark.skip`-ed test with no allow-listed
    reason. Before the fix this tree's check_decisions run was fully green; after, the
    skip must surface as a binding failure.
    """
    root = tmp_path / "tree"
    (root / "decisions").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "decisions" / "0001-poison-file-skip.yaml").write_text(
        "id: D0001\n"
        "title: Probe -- file-level pytest binding with one skipped node\n"
        "tier: A\n"
        'date: "2020-01-02"\n'
        "decision: >-\n"
        "  Bind this record to a whole test FILE. One test function in it is skipped;\n"
        "  another passes.\n"
        "rationale: RT-M1 probe 5.\n"
        "reversibility: n/a (probe)\n"
        "status: accepted\n"
        "bindings:\n"
        "  - type: pytest\n"
        "    target: tests/test_mixed.py\n",
        encoding="utf-8",
    )
    (root / "tests" / "test_mixed.py").write_text(
        "import pytest\n\n"
        "def test_this_one_passes():\n"
        "    assert True\n\n"
        '@pytest.mark.skip(reason="the enforcement this binding claims never actually runs")\n'
        "def test_this_one_is_skipped():\n"
        "    assert False\n",
        encoding="utf-8",
    )
    # This test may itself be running NESTED inside another check_decisions.py's own
    # pytest-binding resolution (e.g. D0063 binds tests/test_governance_scripts.py at
    # file granularity, and check_decisions.py resolves it by running this whole file
    # with TANNEN_CHECK_DECISIONS_NESTED=1 set). That variable is ambient-environment
    # (RT-08) and would otherwise be inherited by the subprocess below, switching off
    # the very check this test exists to exercise. Clear it, the same way
    # test_guard_fails_its_poison does, so this test's verdict never depends on how it
    # was reached.
    env = {k: v for k, v in os.environ.items() if k != "TANNEN_CHECK_DECISIONS_NESTED"}
    result = run([sys.executable, "scripts/check_decisions.py", "--root", str(root)], env=env)
    out = result.stdout + result.stderr
    assert result.returncode != 0, f"a hidden skip inside a passing file binding went undetected:\n{out}"
    assert "unexplained skip" in out, out
    assert "RT-M1-05" in out, out


def test_same_day_boundary_starts_the_receipt_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    """A boundary minted the SAME DAY as the receipt must start the seven-day clock.

    The sitting takes the receipt and mints the close tag minutes apart (docs/SITTING.md),
    so if a same-day boundary does not count then no close tag ever does, and Tier-B
    silence-as-consent never suspends (BRIEF §9.1, D0071).

    The boundary set is substituted rather than read from refs/tags, and that substitution
    IS the test. BOUNDARY_TAG_RE matches `.+-laws-freeze`, so this repo accumulates
    boundaries dated after the latest receipt as a matter of routine; against the live tag
    set the unpatched `>` reaches the same verdict by a different route, and the assertion
    goes quiet without ever failing. Exactly one boundary, on the receipt's own day, is the
    only arrangement that tells `>` and `>=` apart (D0092).
    """
    import datetime as dt
    import sys
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import _gov

    rdate = max(dt.date.fromisoformat(p.stem) for p in (REPO_ROOT / "receipts").glob("*.md"))
    long_after = rdate + dt.timedelta(days=30)

    monkeypatch.setattr(_gov, "boundary_tag_dates", lambda root: [rdate])
    fresh, detail = _gov.receipt_state(REPO_ROOT, long_after)
    assert not fresh, f"a same-day boundary did not start the clock: {detail}"

    # The half the patch must NOT change: a boundary strictly BEFORE the receipt is one
    # the receipt already answers for, so it does not start a clock against it.
    monkeypatch.setattr(_gov, "boundary_tag_dates",
                        lambda root: [rdate - dt.timedelta(days=1)])
    fresh, detail = _gov.receipt_state(REPO_ROOT, long_after)
    assert fresh, f"an earlier boundary wrongly started the clock: {detail}"
