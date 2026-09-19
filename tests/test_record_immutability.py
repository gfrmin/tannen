"""A decision record's decision is history (D0045, RT-12).

RT-12: editing a past record's decision, tier or bindings passed every guard once
DECISIONS.md was regenerated. check_decisions now compares each record with the blob that
first added its sequence number. Content fields must be equal. Bindings, links and
unenforced_reason may only move the way D0045 allows (added, hardened, dropped for the
binding they predicted). status and bindings_count are free. A legitimate past edit is
declared in governance/record-edits.yaml, which re-baselines one field at one commit.

Every refusal below is watched on a real git fixture, next to its positive control.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from _gov import Failures, input_hash, receipt_line  # noqa: E402
from check_decisions import check_immutability, field_violation  # noqa: E402
from gen_projections import header  # noqa: E402

GUARD = REPO_ROOT / "scripts" / "check_decisions.py"
RECORD = "decisions/0001-a.yaml"


def env() -> dict[str, str]:
    """pre-commit exports GIT_INDEX_FILE, which beats `git -C`: scrub every GIT_* var."""
    return {k: v for k, v in os.environ.items()
            if not k.startswith("GIT_") and k != "TANNEN_CHECK_DECISIONS_NESTED"}


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), "-c", "user.email=t@invalid", "-c", "user.name=t",
         "-c", "commit.gpgsign=false", *args],
        check=True, capture_output=True, text=True, env=env()).stdout.strip()


def record(*, decision: str = "Probe.", status: str = "accepted",
           bindings: str = "  - type: manifest\n    target: BRIEF.md\n",
           extra: str = "") -> str:
    return ("id: D0001\ntitle: A\ntier: A\ndate: \"2026-08-01\"\n"
            f"decision: {decision}\nrationale: Probe.\nreversibility: Probe.\n"
            f"status: {status}\n{extra}bindings:\n{bindings}")


def repo(tmp_path: Path) -> Path:
    root = tmp_path / "t"
    (root / "decisions").mkdir(parents=True)
    (root / RECORD).write_text(record())
    git(root, "init", "-q")
    commit(root, "add D0001")
    return root


def commit(root: Path, message: str) -> str:
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)
    return git(root, "rev-parse", "HEAD")


def edit(root: Path, text: str, message: str = "edit D0001") -> str:
    (root / RECORD).write_text(text)
    return commit(root, message)


def declare(root: Path, entries: str) -> None:
    (root / "governance").mkdir(exist_ok=True)
    (root / "governance" / "record-edits.yaml").write_text(f"edits:\n{entries}")


def check(root: Path) -> tuple[list[str], str]:
    fail = Failures("check_decisions")
    summary = check_immutability(root, fail)
    return fail.messages, summary


# ------------------------------------------------------------------ the rule, field by field
BINDING = {"type": "manifest", "target": "BRIEF.md"}


@pytest.mark.parametrize("field", ["decision", "rationale", "tier", "title", "date",
                                   "reversibility", "risk_flags", "retires_bindings"])
def test_a_content_field_may_not_change(field: str) -> None:
    assert field_violation(field, "Probe.", "Probe, amended.")
    assert field_violation(field, None, "added later")
    assert field_violation(field, "Probe.", "Probe.") is None


@pytest.mark.parametrize("field", ["status", "bindings_count"])
def test_status_and_bindings_count_are_free(field: str) -> None:
    assert field_violation(field, "proposed", "accepted") is None


def test_a_binding_may_be_added_or_hardened_in_place() -> None:
    documentary = {"type": "file", "target": "x.py", "strength": "documentary"}
    assert field_violation("bindings", [BINDING], [BINDING, documentary]) is None
    assert field_violation("bindings", [documentary], [{"type": "file", "target": "x.py"}]) is None
    assert field_violation("bindings", [{"type": "file", "target": "x.py"}],
                           [{"type": "manifest", "target": "x.py", "detail": "frozen"}]) is None
    assert field_violation("bindings", [{"type": "manifest", "target": "t.py"}],
                           [{"type": "pytest", "target": "t.py"}]) is None


def test_a_binding_may_not_be_dropped_weakened_or_downgraded() -> None:
    assert field_violation("bindings", [BINDING], [])
    assert field_violation("bindings", [BINDING], [{**BINDING, "strength": "documentary"}])
    # RT-12's composition with RT-01: unfreeze BRIEF.md by relabelling D0022's binding.
    assert field_violation("bindings", [BINDING], [{"type": "file", "target": "BRIEF.md"}])
    assert field_violation("bindings", [BINDING], [{**BINDING, "target": "BRIEF2.md"}])


def test_links_are_append_only_and_unenforced_reason_may_only_be_dropped() -> None:
    assert field_violation("links", ["D0001"], ["D0001", "D0002"]) is None
    assert field_violation("links", ["D0001", "D0002"], ["D0002"])
    assert field_violation("unenforced_reason", "no guard yet", None) is None
    assert field_violation("unenforced_reason", "no guard yet", "a different excuse")
    assert field_violation("unenforced_reason", None, "an excuse added later")


# ------------------------------------------------------------------ against real history
def test_an_edited_decision_is_refused(tmp_path: Path) -> None:
    root = repo(tmp_path)
    edit(root, record(decision="Probe, quietly amended."))
    messages, _ = check(root)
    assert any("D0001" in m and "decision" in m and "RT-12" in m for m in messages), messages


def test_an_uncommitted_edit_is_refused_too(tmp_path: Path) -> None:
    """The working tree is what check_decisions reads, and what pre-commit is about to commit."""
    root = repo(tmp_path)
    (root / RECORD).write_text(record(decision="Probe, amended before commit."))
    messages, _ = check(root)
    assert any("decision" in m for m in messages), messages


def test_a_status_only_change_passes(tmp_path: Path) -> None:
    root = repo(tmp_path)
    edit(root, record(status="superseded"))
    messages, summary = check(root)
    assert messages == []
    assert "1 record(s) compared" in summary, summary


def test_a_declared_edit_passes_and_rebaselines_only_that_field(tmp_path: Path) -> None:
    root = repo(tmp_path)
    at = edit(root, record(decision="Probe. UPDATE, amended in place."))
    declare(root, f"  - record: D0001\n    field: decision\n    at: {at}\n"
                  "    reason: the fixture's legitimate past edit\n")
    commit(root, "declare")
    messages, summary = check(root)
    assert messages == [], messages
    assert "1 declared edit(s)" in summary, summary

    # The declaration pins the value at `at`; a second edit of the same field is refused.
    edit(root, record(decision="Probe. UPDATE, amended in place, and again."))
    messages, _ = check(root)
    assert any("decision" in m for m in messages), messages


def test_a_declaration_nothing_needs_is_refused(tmp_path: Path) -> None:
    """A declaration no edit uses is a permission waiting for an edit (the D0181 rule)."""
    root = repo(tmp_path)
    at = git(root, "rev-parse", "HEAD")
    declare(root, f"  - record: D0001\n    field: decision\n    at: {at}\n    reason: pre-emptive\n")
    messages, _ = check(root)
    assert any("stale edit declaration" in m for m in messages), messages


def test_a_declaration_at_a_commit_outside_head_is_refused(tmp_path: Path) -> None:
    """The side commit carries the very value HEAD has, so only its ancestry can refuse it."""
    root = repo(tmp_path)
    git(root, "checkout", "-q", "-b", "side")
    side = edit(root, record(decision="Probe, as the side branch would have it."), "side")
    git(root, "checkout", "-q", "-")
    git(root, "branch", "-q", "-D", "side")
    head = edit(root, record(decision="Probe, as the side branch would have it."), "on HEAD")
    assert side != head   # identical tree, parent, message and second give identical ids
    declare(root, f"  - record: D0001\n    field: decision\n    at: {side}\n    reason: forged\n")
    messages, _ = check(root)
    assert any("not in HEAD's history" in m for m in messages), messages


def test_a_malformed_declaration_is_refused(tmp_path: Path) -> None:
    root = repo(tmp_path)
    declare(root, "  - record: D0001\n    field: status\n    at: HEAD\n    reason: x\n")
    messages, _ = check(root)
    assert any("record-edits.yaml" in m for m in messages), messages


def test_a_dropped_binding_is_refused(tmp_path: Path) -> None:
    root = repo(tmp_path)
    edit(root, record(bindings="  - type: file\n    target: BRIEF.md\n"))
    messages, _ = check(root)
    assert any("bindings" in m and "BRIEF.md" in m for m in messages), messages


def test_a_deleted_record_is_refused(tmp_path: Path) -> None:
    root = repo(tmp_path)
    (root / "decisions" / "0002-b.yaml").write_text(record().replace("D0001", "D0002"))
    commit(root, "add D0002")
    (root / RECORD).unlink()
    commit(root, "delete D0001")
    messages, _ = check(root)
    assert any("D0001" in m and "deleted" in m for m in messages), messages


def test_a_renamed_record_is_compared_with_its_original_blob(tmp_path: Path) -> None:
    """Keyed by sequence number, so `git mv` cannot reset the baseline."""
    root = repo(tmp_path)
    (root / RECORD).unlink()
    (root / "decisions" / "0001-renamed.yaml").write_text(record(decision="Probe, renamed."))
    commit(root, "rename D0001 and edit it")
    messages, _ = check(root)
    assert any("decision" in m for m in messages), messages


def test_a_new_uncommitted_record_has_no_baseline_yet(tmp_path: Path) -> None:
    root = repo(tmp_path)
    (root / "decisions" / "0002-b.yaml").write_text(record().replace("D0001", "D0002"))
    messages, summary = check(root)
    assert messages == []
    assert "1 new" in summary, summary


def test_a_shallow_clone_fails_closed(tmp_path: Path) -> None:
    """In a shallow clone every record looks added at the graft, so every edit looks clean."""
    root = repo(tmp_path)
    edit(root, record(decision="Probe, amended."))
    shallow = tmp_path / "shallow"
    subprocess.run(["git", "clone", "-q", "--depth", "1", f"file://{root}", str(shallow)],
                   check=True, capture_output=True, env=env())
    messages, _ = check(shallow)
    assert any("shallow" in m for m in messages), messages


def test_no_git_history_is_reported_not_passed_silently(tmp_path: Path) -> None:
    root = tmp_path / "plain"
    (root / "decisions").mkdir(parents=True)
    (root / RECORD).write_text(record())
    messages, summary = check(root)
    assert messages == []
    assert "NOT CHECKED" in summary, summary


# ------------------------------------------------------------------ wired into the guard
def full_tree(tmp_path: Path) -> Path:
    root = repo(tmp_path)
    (root / "MANIFEST.sha256").write_text("0" * 64 + "  BRIEF.md\n")
    (root / "receipts").mkdir()
    (root / "receipts" / "2026-08-02.md").write_text("# Attention receipt — 2026-08-02\n")
    project(root)
    commit(root, "tree")
    return root


def project(root: Path) -> None:
    paths = sorted((root / "decisions").glob("*.yaml"))
    (root / "DECISIONS.md").write_text(header(input_hash(paths, root)) + f"\n{receipt_line(root)}\n")


def guard(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(GUARD), "--root", str(root), "--today", "2026-08-25"],
                          capture_output=True, text=True, check=False, env=env())


def test_rt12_reproduction_is_refused_by_the_guard(tmp_path: Path) -> None:
    """RT-12's own reproduction: edit a record, regenerate DECISIONS.md, run the guard."""
    root = full_tree(tmp_path)
    clean = guard(root)
    assert clean.returncode == 0, clean.stdout + clean.stderr
    assert "1 record(s) compared" in clean.stdout, clean.stdout

    (root / RECORD).write_text(record(decision="Probe, quietly amended."))
    project(root)
    run = guard(root)
    assert run.returncode != 0, run.stdout + run.stderr
    assert "RT-12" in run.stderr, run.stderr


def test_the_real_history_passes_with_every_record_compared() -> None:
    """The positive control on the real repo, and proof the comparison's input is not empty."""
    messages, summary = check(REPO_ROOT)
    assert messages == [], "\n".join(messages)
    m = re.match(r"(\d+) record\(s\) compared .*, (\d+) new, (\d+) declared", summary)
    assert m, summary
    compared, new, _ = map(int, m.groups())
    assert compared + new == len(list((REPO_ROOT / "decisions").glob("*.yaml")))
    assert compared >= 273, "m5-close had 273 records, and none may be deleted"
