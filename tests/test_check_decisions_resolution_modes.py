"""check_decisions.py's three pytest-binding resolution modes (D0266 item 2; D0267 ruling
3): the default spawns pytest itself; `--collect-only` checks collection only, for the
pre-commit hook; `--pytest-report FILE` replays a prior `pytest --junitxml=FILE` run, for
the gate (Makefile order: pytest, then this guard).

Hermetic: a throwaway tree with one bound node that PASSES and one PLANTED FAILING bound
node that still collects cleanly — the shape D0266 item 2 names: `--collect-only` must let
the planted failure through (it only checks collection), and `--pytest-report` must catch
it (D0267 ruling 3's split: commit hooks structural, CI the gate).
"""

from __future__ import annotations

import datetime as dt
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from _gov import git_env, input_hash, receipt_line  # noqa: E402
from gen_projections import gen_decisions, header  # noqa: E402

GUARD = REPO_ROOT / "scripts" / "check_decisions.py"
TODAY = dt.date(2026, 9, 17)


def tree(root: Path) -> Path:
    (root / "decisions").mkdir(parents=True)
    common = ('date: "2026-09-17"\ndecision: Probe.\nrationale: Probe.\n'
              "reversibility: Probe.\nstatus: accepted\n")
    (root / "decisions" / "0001-ok.yaml").write_text(
        "id: D0001\ntitle: OK\ntier: A\n" + common +
        "bindings:\n  - type: pytest\n    target: tests/sample.py::test_ok\n")
    (root / "decisions" / "0002-bad.yaml").write_text(
        "id: D0002\ntitle: Bad\ntier: A\n" + common +
        "bindings:\n  - type: pytest\n    target: tests/sample.py::test_bad\n")
    (root / "tests").mkdir()
    (root / "tests" / "sample.py").write_text(
        "def test_ok():\n    assert True\n\n\ndef test_bad():\n    assert False\n")
    (root / "receipts").mkdir()
    (root / "receipts" / "2026-09-10.md").write_text("# Attention receipt — 2026-09-10\n")
    paths = sorted((root / "decisions").glob("*.yaml"))
    (root / "DECISIONS.md").write_text(
        header(input_hash(paths, root)) + f"\n{receipt_line(root)}\n")
    return root


def guard(root: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(GUARD), "--root", str(root), "--today", TODAY.isoformat(), *extra],
        capture_output=True, text=True, check=False, env=git_env(),
    )


def test_default_resolution_catches_the_planted_failure(tmp_path: Path) -> None:
    root = tree(tmp_path / "t")
    result = guard(root)
    assert result.returncode != 0
    assert "tests/sample.py::test_bad" in result.stdout + result.stderr


def test_collect_only_lets_the_planted_failure_through(tmp_path: Path) -> None:
    """`--collect-only` checks that a bound node still COLLECTS, nothing more — a red node
    may sit on a branch until CI (D0267 ruling 3)."""
    root = tree(tmp_path / "t")
    result = guard(root, "--collect-only")
    assert result.returncode == 0, result.stdout + result.stderr


def test_collect_only_is_not_fooled_by_the_word_error_in_a_passing_test_name(
    tmp_path: Path,
) -> None:
    """A test's own NAME may contain "error" (test_a_usage_error, test_an_oserror — both
    real, currently-bound names in this repo) while collecting and passing cleanly.
    `collect_violation` used to scan pytest's combined output for the substring "error"
    rather than checking its returncode, so both tripped a FAIL against a tree with
    nothing wrong — caught running --collect-only against the real tree right after the
    collect/report split landed."""
    root = tree(tmp_path / "t")
    (root / "decisions" / "0002-bad.yaml").write_text(
        (root / "decisions" / "0002-bad.yaml").read_text()
        .replace("test_bad", "test_named_after_an_error_but_passing"))
    (root / "tests" / "sample.py").write_text(
        "def test_ok():\n    assert True\n\n\n"
        "def test_named_after_an_error_but_passing():\n    assert True\n")
    paths = sorted((root / "decisions").glob("*.yaml"))
    (root / "DECISIONS.md").write_text(
        header(input_hash(paths, root)) + f"\n{receipt_line(root)}\n")
    result = guard(root, "--collect-only")
    assert result.returncode == 0, result.stdout + result.stderr


def test_collect_only_still_catches_a_node_that_does_not_collect(tmp_path: Path) -> None:
    root = tree(tmp_path / "t")
    (root / "decisions" / "0002-bad.yaml").write_text(
        (root / "decisions" / "0002-bad.yaml").read_text().replace("test_bad", "test_missing"))
    paths = sorted((root / "decisions").glob("*.yaml"))
    (root / "DECISIONS.md").write_text(
        header(input_hash(paths, root)) + f"\n{receipt_line(root)}\n")
    result = guard(root, "--collect-only")
    assert result.returncode != 0
    assert "does not collect" in result.stdout + result.stderr


def test_pytest_report_catches_the_planted_failure(tmp_path: Path) -> None:
    root = tree(tmp_path / "t")
    report = root / "pytest-report.xml"
    run = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/sample.py", "-q",
         f"--junitxml={report}", "--no-header", "-p", "no:cacheprovider"],
        cwd=root, capture_output=True, text=True, check=False,
    )
    assert report.is_file(), run.stdout + run.stderr
    result = guard(root, "--pytest-report", str(report))
    assert result.returncode != 0
    assert "tests/sample.py::test_bad" in result.stdout + result.stderr


def test_pytest_report_passes_when_the_report_is_clean(tmp_path: Path) -> None:
    root = tree(tmp_path / "t")
    (root / "tests" / "sample.py").write_text(
        "def test_ok():\n    assert True\n\n\ndef test_bad():\n    assert True\n")
    report = root / "pytest-report.xml"
    subprocess.run(
        [sys.executable, "-m", "pytest", "tests/sample.py", "-q",
         f"--junitxml={report}", "--no-header", "-p", "no:cacheprovider"],
        cwd=root, capture_output=True, text=True, check=False,
    )
    result = guard(root, "--pytest-report", str(report))
    assert result.returncode == 0, result.stdout + result.stderr


def test_pytest_report_does_not_read_a_strict_xfail_retirement_as_a_skip(tmp_path: Path) -> None:
    """`conftest.py`'s law-retirement machinery marks a superseded node `xfail(strict=True)`
    rather than skip it, specifically so the DEFAULT resolution mode's text scan (no
    "SKIPPED" line for an xfail) never sees it as a skip (D0124). pytest's junitxml
    plugin reports that same xfail as `<skipped type="pytest.xfail">` — caught live
    against this repo's own tests/laws/m1/test_l1_rel.py right after the collect/report
    split landed, where a genuinely retired, strict-xfail node was read as an
    "unexplained skip" and failed a green tree."""
    root = tree(tmp_path / "t")
    (root / "tests" / "sample.py").write_text(
        "import pytest\n\n\n"
        "def test_ok():\n    assert True\n\n\n"
        "@pytest.mark.xfail(strict=True, reason='retired forward, D0124 shape')\n"
        "def test_bad():\n    assert False\n")
    report = root / "pytest-report.xml"
    subprocess.run(
        [sys.executable, "-m", "pytest", "tests/sample.py", "-q",
         f"--junitxml={report}", "--no-header", "-p", "no:cacheprovider"],
        cwd=root, capture_output=True, text=True, check=False,
    )
    result = guard(root, "--pytest-report", str(report))
    assert result.returncode == 0, result.stdout + result.stderr


def test_pytest_report_lets_a_documented_skip_through_but_flags_an_undocumented_one(
    tmp_path: Path,
) -> None:
    """A single-node binding on a skipped node is always "not enforcement" (RT-M1-05
    does not apply — there is nothing else in the match set to be "otherwise-passing").
    The reason-check only has something to disagree with when the binding covers a
    MIX of outcomes — a whole-file binding here, matching D0087's real shape — so
    0002-bad.yaml is retargeted to the file, not the single node."""
    root = tree(tmp_path / "t")
    (root / "decisions" / "0002-bad.yaml").write_text(
        (root / "decisions" / "0002-bad.yaml").read_text()
        .replace("tests/sample.py::test_bad", "tests/sample.py"))
    paths = sorted((root / "decisions").glob("*.yaml"))
    (root / "DECISIONS.md").write_text(
        header(input_hash(paths, root)) + f"\n{receipt_line(root)}\n")
    (root / "tests" / "sample.py").write_text(
        "import pytest\n\n\n"
        "def test_ok():\n    assert True\n\n\n"
        "def test_bad():\n    pytest.skip('no reason given')\n")
    report = root / "pytest-report.xml"
    subprocess.run(
        [sys.executable, "-m", "pytest", "tests/sample.py", "-q",
         f"--junitxml={report}", "--no-header", "-p", "no:cacheprovider"],
        cwd=root, capture_output=True, text=True, check=False,
    )
    result = guard(root, "--pytest-report", str(report))
    assert result.returncode != 0
    assert "unexplained skip" in result.stdout + result.stderr

    (root / "tests" / "sample.py").write_text(
        "import pytest\n\n\n"
        "def test_ok():\n    assert True\n\n\n"
        "def test_bad():\n    pytest.skip('S-pending: owner has not published vectors')\n")
    subprocess.run(
        [sys.executable, "-m", "pytest", "tests/sample.py", "-q",
         f"--junitxml={report}", "--no-header", "-p", "no:cacheprovider"],
        cwd=root, capture_output=True, text=True, check=False,
    )
    result = guard(root, "--pytest-report", str(report))
    assert result.returncode == 0, result.stdout + result.stderr


def test_pytest_report_refuses_a_node_absent_from_the_report(tmp_path: Path) -> None:
    """A node the report never mentions was not run at all — refused exactly as a node
    that does not collect, never read as silent success."""
    root = tree(tmp_path / "t")
    report = root / "pytest-report.xml"
    subprocess.run(
        [sys.executable, "-m", "pytest", "tests/sample.py::test_ok", "-q",
         f"--junitxml={report}", "--no-header", "-p", "no:cacheprovider"],
        cwd=root, capture_output=True, text=True, check=False,
    )
    result = guard(root, "--pytest-report", str(report))
    assert result.returncode != 0
    assert "not run" in result.stdout + result.stderr


def test_collect_only_and_pytest_report_are_mutually_exclusive() -> None:
    result = subprocess.run(
        [sys.executable, str(GUARD), "--collect-only", "--pytest-report", "x.xml"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0
