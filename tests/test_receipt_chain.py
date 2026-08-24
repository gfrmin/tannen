"""The receipt chain detects history rewritten between attestations (D0063 ruling 4).

Hermetic: ephemeral owner key, throwaway repo. The point of the guard is that the one
artifact a builder cannot forge — an owner signature — becomes a witness to the shape of
history, so a test that depended on the real owner key would be testing the wrong thing.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from _gov import git_env  # noqa: E402

GUARD = REPO_ROOT / "scripts" / "check_receipts.py"


def sh(*args: str) -> subprocess.CompletedProcess:
    run = subprocess.run(args, capture_output=True, text=True, check=False, env=git_env())
    assert run.returncode == 0, f"{args}\n{run.stdout}\n{run.stderr}"
    return run


@pytest.fixture
def world(tmp_path: Path):
    key = tmp_path / "owner"
    sh("ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "owner@tannen", "-f", str(key))
    root = tmp_path / "repo"
    (root / "receipts").mkdir(parents=True)
    (root / "allowed_signers").write_text(
        f"owner@tannen {key.with_suffix('.pub').read_text().strip()}\n")
    sh("git", "init", "-q", "-b", "master", str(root))
    for k, v in (("user.name", "t"), ("user.email", "b@t"), ("commit.gpgsign", "false")):
        sh("git", "-C", str(root), "config", k, v)

    def commit(message: str) -> str:
        (root / "f.txt").write_text(message)
        sh("git", "-C", str(root), "add", "-A")
        sh("git", "-C", str(root), "commit", "-q", "-m", message)
        return sh("git", "-C", str(root), "rev-parse", "HEAD").stdout.strip()

    def receipt(date: str, head: str) -> None:
        path = root / "receipts" / f"{date}.md"
        path.write_text(f"# Attention receipt — {date}\n\n- HEAD: {head}\n"
                        "- custodian: all checks green\n")
        sh("ssh-keygen", "-Y", "sign", "-f", str(key), "-n", "tannen-receipt", str(path))

    def run() -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(GUARD), "--root", str(root)],
                              capture_output=True, text=True, check=False, env=git_env())

    return type("World", (), dict(root=root, key=key, commit=staticmethod(commit),
                                  receipt=staticmethod(receipt), run=staticmethod(run)))


def test_a_linear_history_verifies(world):
    first = world.commit("one")
    world.receipt("2026-01-01", first)
    second = world.commit("two")
    world.receipt("2026-01-08", second)
    world.commit("three")
    run = world.run()
    assert run.returncode == 0, run.stdout + run.stderr
    assert "chain unbroken to HEAD" in run.stdout


def test_history_rewritten_between_receipts_is_caught(world):
    base = world.commit("base")
    first = world.commit("one")
    world.receipt("2026-01-01", first)
    # The rewrite: drop the attested commit and build a different history from the base.
    sh("git", "-C", str(world.root), "reset", "-q", "--hard", base)
    world.commit("different one")
    second = world.commit("different two")
    world.receipt("2026-01-08", second)
    run = world.run()
    assert run.returncode != 0
    assert "receipt chain broken" in run.stderr


def test_a_rewrite_after_the_last_receipt_is_caught_at_the_tip(world):
    first = world.commit("one")
    world.commit("two")
    head = world.commit("three")
    world.receipt("2026-01-01", head)
    sh("git", "-C", str(world.root), "reset", "-q", "--hard", first)
    world.commit("rewritten")
    run = world.run()
    assert run.returncode != 0
    assert "broken at the tip" in run.stderr


def test_an_unsigned_receipt_is_refused_once_an_owner_is_enrolled(world):
    head = world.commit("one")
    world.receipt("2026-01-01", head)
    (world.root / "receipts" / "2026-01-01.md.sig").unlink()
    run = world.run()
    assert run.returncode != 0
    assert "has no signature" in run.stderr


def test_an_edited_receipt_no_longer_verifies(world):
    head = world.commit("one")
    world.receipt("2026-01-01", head)
    path = world.root / "receipts" / "2026-01-01.md"
    path.write_text(path.read_text().replace("all checks green", "all checks green (edited)"))
    run = world.run()
    assert run.returncode != 0
    assert "signature does not verify" in run.stderr


def test_a_receipt_naming_a_vanished_commit_is_caught(world):
    world.commit("one")
    world.receipt("2026-01-01", "0" * 40)
    run = world.run()
    assert run.returncode != 0
    assert "not a commit in this repository" in run.stderr
