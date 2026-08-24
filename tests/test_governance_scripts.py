"""The guards guard, and the poison proves it (BRIEF §9, §9.1).

Success path: every check script exits 0 against the real tree. Liveness: every guard
exits non-zero against its tests/poison/ fixture AND emits the fixture's intended
marker — the same matrix scripts/custodian.sh enforces, exercised here from pytest so
plain `uv run pytest` catches a weakened guard too.
"""

from __future__ import annotations

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


POISON = [
    (
        [sys.executable, "scripts/check_manifest.py", "--root", "tests/poison/check-manifest"],
        "frozen path modified",
    ),
    (
        [sys.executable, "scripts/check_concepts.py", "--root", "tests/poison/check-concepts"],
        "snapshot content drifted",
    ),
    (
        [sys.executable, "scripts/check_decisions.py", "--root", "tests/poison/check-decisions"],
        "binding does not resolve",
    ),
]


@pytest.mark.parametrize("args, marker", POISON, ids=[p[0][1].split("/")[-1] for p in POISON])
def test_guard_fails_its_poison(args: list[str], marker: str) -> None:
    result = run(args)
    combined = result.stdout + result.stderr
    assert result.returncode != 0, f"guard PASSED its poison — weakened:\n{combined}"
    assert marker in combined, f"guard failed poison for the wrong reason:\n{combined}"


def test_lint_imports_fails_its_poison() -> None:
    result = run(
        ["uv", "run", "lint-imports", "--config", "tests/poison/lint-imports/pyproject.toml"],
        env={"PATH": __import__("os").environ["PATH"], "PYTHONPATH": "tests/poison/lint-imports"},
    )
    combined = result.stdout + result.stderr
    assert result.returncode != 0, f"lint-imports PASSED its poison — weakened:\n{combined}"
    assert "BROKEN" in combined, combined


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
