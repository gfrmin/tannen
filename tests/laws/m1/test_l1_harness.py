"""M1 law L1.17 — the law descriptor addresses its own harness (RT-09).

FROZEN at m1-laws-freeze. The M0 boundary red team found that `implementation_subject`
hashes only `src/tannen/**/*.py`, so what decides *how hard a law was tested* was outside
the subject entirely: cutting the Hypothesis profile to one example, adding a data file the
implementation reads, or changing a dependency pin all left every descriptor byte-identical
and every verdict "fresh" (`docs/redteam/2026-08-24-m0-boundary.md`, RT-09).

Its closure was scheduled for the START of M1 rather than the M0 boundary, because landing
it moves every descriptor by design — all existing evidence is invalidated on the commit
that lands it and re-earned by the next run. Session B does this FIRST, before any M1
evidence exists, so nothing is invalidated twice.

It names a NEW module deliberately. A law naming the existing `implementation_subject`
would run and fail today rather than skip, and a red law is not a frozen law.
"""

from __future__ import annotations

from pathlib import Path

import pytest

harness = pytest.importorskip(
    "tannen.laws.harness",
    reason="RT-09's widened law-descriptor subject not implemented yet "
    "(law suite frozen ahead of Session B)",
)

from tannen.kernel.refs import is_ref  # noqa: E402
from tannen.laws import discovery  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture()
def tree(tmp_path: Path) -> Path:
    """A miniature repo root carrying everything the subject must cover."""
    (tmp_path / "src" / "tannen" / "kernel").mkdir(parents=True)
    (tmp_path / "src" / "tannen" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "src" / "tannen" / "kernel" / "encoding.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "src" / "tannen" / "kernel" / "table.json").write_text('{"a": 1}\n', encoding="utf-8")
    (tmp_path / "conftest.py").write_text("PROFILE = 'tannen-laws'\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "tannen"\n', encoding="utf-8")
    return tmp_path


def test_l1_17_the_subject_is_a_ref(tree: Path) -> None:
    assert is_ref(harness.harness_subject(tree))
    assert is_ref(harness.harness_subject(REPO_ROOT))


def test_l1_17_the_subject_is_a_pure_function_of_the_tree(tree: Path) -> None:
    assert harness.harness_subject(tree) == harness.harness_subject(tree)


@pytest.mark.parametrize(
    "relative",
    [
        "src/tannen/kernel/encoding.py",   # the CONTROL: already covered before RT-09
        "conftest.py",                     # the Hypothesis profile — how hard a law was tested
        "pyproject.toml",                  # dependency pins, including the L6 oracle's
        "src/tannen/kernel/table.json",    # a non-.py file the implementation reads
    ],
    ids=["source", "conftest", "pyproject", "data-file"],
)
def test_l1_17_changing_any_harness_input_moves_the_subject(tree: Path, relative: str) -> None:
    # Each of these left all ten M0 descriptors byte-identical before the fix.
    before = harness.harness_subject(tree)
    target = tree / relative
    target.write_bytes(target.read_bytes() + b"\n# moved\n")
    assert harness.harness_subject(tree) != before, (
        f"{relative} is outside the law descriptor's subject: a change to it would leave "
        "every recorded verdict reading 'fresh' for a harness that no longer exists (RT-09)"
    )


def test_l1_17_adding_a_file_to_the_implementation_moves_the_subject(tree: Path) -> None:
    before = harness.harness_subject(tree)
    (tree / "src" / "tannen" / "kernel" / "added.py").write_text("y = 2\n", encoding="utf-8")
    assert harness.harness_subject(tree) != before


def test_l1_17_pycache_is_not_part_of_the_subject(tree: Path) -> None:
    # Compiled output is a function of the source already in the subject; including it
    # would make the descriptor depend on whether anyone happened to import the module.
    before = harness.harness_subject(tree)
    cache = tree / "src" / "tannen" / "kernel" / "__pycache__"
    cache.mkdir()
    (cache / "encoding.cpython-313.pyc").write_bytes(b"\x00\x01\x02")
    assert harness.harness_subject(tree) == before


def test_l1_17_the_law_descriptor_actually_uses_it(tree: Path) -> None:
    # The binding that makes this law load-bearing rather than decorative: the widened
    # subject must be what `implementation_subject` — and therefore `law_descriptor`, and
    # therefore `tannen laws report` — computes.
    assert discovery.implementation_subject(tree) == harness.harness_subject(tree)
    assert discovery.implementation_subject(REPO_ROOT) == harness.harness_subject(REPO_ROOT)


def test_l1_17_a_descriptor_moves_when_the_harness_moves(tree: Path) -> None:
    law_files = ["src/tannen/kernel/encoding.py"]  # any tracked file serves as the code_hash input
    before = discovery.law_descriptor(tree, "L1.17", law_files)
    (tree / "conftest.py").write_text("PROFILE = 'weakened'\n", encoding="utf-8")
    assert discovery.law_descriptor(tree, "L1.17", law_files) != before
