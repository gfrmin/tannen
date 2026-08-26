"""The law descriptor's subject: everything that decides how hard a law was tested (RT-09).

M0 hashed only `src/tannen/**/*.py` into a law's `params_hash`, so the Hypothesis profile
(`conftest.py`), the dependency pins (`pyproject.toml`) and any non-`.py` file the
implementation reads sat outside the subject: changing them left every recorded verdict
"fresh" for a harness that no longer existed (`docs/redteam/2026-08-24-m0-boundary.md`,
RT-09). This widens the subject to every file under `src/tannen`, the root `conftest.py`,
`pyproject.toml`, and every `conftest.py` under `tests/` — each of which can change what a
law run means without touching a law or the implementation's `.py` files.

Pure function of the tree: same bytes, same ref. `__pycache__` is excluded because compiled
output is a function of source already in the subject (docs/specs/m1.md §8; law L1.17).
"""

from __future__ import annotations

from pathlib import Path

from tannen.kernel.encoding import content_address
from tannen.kernel.refs import ref_for_bytes

__all__ = ["HARNESS_FILES", "IMPLEMENTATION_DIR", "TESTS_DIR", "harness_subject"]

IMPLEMENTATION_DIR = Path("src") / "tannen"
TESTS_DIR = Path("tests")
#: Root-level files that shape every law run. Absent files are simply not part of the subject
#: (a miniature tree in a test may lack them), present ones always are.
HARNESS_FILES = ("conftest.py", "pyproject.toml")


def _implementation_files(root: Path) -> list[Path]:
    return [
        path
        for path in sorted((root / IMPLEMENTATION_DIR).rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    ]


def _conftests(root: Path) -> list[Path]:
    tests = root / TESTS_DIR
    if not tests.is_dir():
        return []
    return [p for p in sorted(tests.rglob("conftest.py")) if "__pycache__" not in p.parts]


def harness_subject(root: Path) -> str:
    """Ref of the whole harness a law is run against: implementation + the files that
    decide how hard it was tested."""
    root = Path(root)
    paths = _implementation_files(root)
    paths += [root / name for name in HARNESS_FILES if (root / name).is_file()]
    paths += _conftests(root)
    sources = {
        path.relative_to(root).as_posix(): ref_for_bytes(path.read_bytes()) for path in paths
    }
    return content_address(sources)
