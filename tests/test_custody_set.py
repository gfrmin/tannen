"""The custody set bites both ways (decision D0061).

The set is the enumeration MANIFEST.sha256 is not: a manifest row can be deleted, which
unfreezes its path in silence (RT-01), because nothing says what the manifest should
contain. These tests pin the three ways that can go wrong — a listed file changing, a
listed pattern matching nothing, and an unlisted file being (correctly) ignored — over
throwaway roots, so they depend on neither the real repo's contents nor its signatures.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def build_root(tmp_path: Path, patterns: list[str], files: dict[str, str]) -> Path:
    root = tmp_path / "root"
    (root / "governance").mkdir(parents=True)
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    listed = "\n".join(f"    - {p}" for p in patterns)
    (root / "governance" / "tier-c.yaml").write_text(
        "version: 1\n"
        "custody:\n"
        "  file: governance/custody.sha256\n"
        "  set:\n" + listed + "\n"
    )
    return root


def gen(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(REPO / "scripts" / "gen_custody.py"), "--root", str(root), *args],
        capture_output=True, text=True, check=False,
    )


def check(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(REPO / "scripts" / "check_manifest.py"), "--root", str(root)],
        capture_output=True, text=True, check=False,
    )


@pytest.fixture()
def root(tmp_path: Path) -> Path:
    root = build_root(tmp_path, ["guard.py", "governance/tier-c.yaml"],
                      {"guard.py": "print('guard')\n"})
    assert gen(root).returncode == 0
    return root


def test_a_generated_set_is_current(root: Path) -> None:
    result = gen(root, "--check")
    assert result.returncode == 0, result.stderr
    assert "2 custody path(s) current" in result.stdout


def test_editing_a_listed_file_is_drift(root: Path) -> None:
    (root / "guard.py").write_text("print('softened')\n")
    result = gen(root, "--check")
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "stale" in combined
    detail = check(root).stdout + check(root).stderr
    assert "custody drift: guard.py changed" in detail


def test_a_pattern_matching_nothing_is_a_hole_not_an_empty_set(tmp_path: Path) -> None:
    root = build_root(tmp_path, ["guard.py", "scripts/never_written.py"],
                      {"guard.py": "print('guard')\n"})
    result = gen(root)
    assert result.returncode != 0
    assert "matches nothing: scripts/never_written.py" in result.stderr


def test_deleting_a_listed_file_is_caught_even_though_the_row_could_be_dropped(root: Path) -> None:
    # The failure mode the manifest cannot see: remove the artifact AND its row, and a
    # whitelist of hashes is satisfied. The declaration in tier-c.yaml is what notices.
    (root / "guard.py").unlink()
    custody = root / "governance" / "custody.sha256"
    custody.write_text("".join(l + "\n" for l in custody.read_text().splitlines()
                               if not l.endswith("  guard.py")))
    combined = check(root).stdout + check(root).stderr
    assert "matches nothing: guard.py" in combined


def test_an_unlisted_file_is_ignored(root: Path) -> None:
    (root / "scratch.txt").write_text("not part of the custody floor\n")
    assert gen(root, "--check").returncode == 0
