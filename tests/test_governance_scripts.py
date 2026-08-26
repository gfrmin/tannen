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
    result = run([sys.executable, "-I", "-P", *args], env=env)
    combined = result.stdout + result.stderr
    assert result.returncode != 0, f"guard '{name}' PASSED its poison — weakened:\n{combined}"
    assert marker in combined, f"guard '{name}' failed poison for the wrong reason:\n{combined}"


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
