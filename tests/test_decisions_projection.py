"""DECISIONS.md states only what its commit contains (D0215).

The projection used to carry the attention-receipt verdict and each Tier-B record's
effective status. Both are functions of the clock and of `git tag -l`, a commit contains
neither, and `check_decisions` compared them with what the day computes — so minting a close
tag reddened the very commit it attests (m1-, m2- and m3-close all point at such commits).
The verdict now lives only in the dated digest. These tests hold the three halves of that:

  T1  the rendered bytes do not move with the date or with the tag set (D0215's control);
  T2  a projection that stores a verdict is refused, so RT-M2-05's failure — a tracked file
      asserting FRESH after the receipt went stale — cannot come back by regeneration drift;
  T3  the one receipt fact the file does carry is checked against the tree it sits in.

Hermetic: throwaway trees, no real key, no network. [cites: D0215, RT-M2-05, D0141]
"""

from __future__ import annotations

import datetime as dt
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from _gov import STORED_VERDICT_RE, git_env, input_hash, receipt_line  # noqa: E402
from gen_projections import gen_decisions, header  # noqa: E402

GUARD = REPO_ROOT / "scripts" / "check_decisions.py"
TODAY = "2026-08-25"


def tree(root: Path) -> Path:
    """One accepted Tier-A record, one provisional Tier-B record PAST its veto date — the
    row whose effective status used to move with the clock — and a signed-looking receipt."""
    (root / "decisions").mkdir(parents=True)
    common = ('date: "2026-08-01"\n'
              "decision: Probe.\nrationale: Probe.\nreversibility: Probe.\n")
    (root / "decisions" / "0001-a.yaml").write_text(
        "id: D0001\ntitle: A\ntier: A\n" + common + "status: accepted\n"
        "bindings:\n  - type: file\n    target: decisions/0001-a.yaml\n")
    (root / "decisions" / "0002-b.yaml").write_text(
        "id: D0002\ntitle: B\ntier: B\n" + common + 'veto_by: "2026-08-08"\n'
        "status: provisional\n"
        "bindings:\n  - type: file\n    target: decisions/0002-b.yaml\n")
    (root / "receipts").mkdir()
    (root / "receipts" / "2026-08-02.md").write_text("# Attention receipt — 2026-08-02\n")
    (root / "receipts" / "2026-08-02.md.sig").write_text("not verified by the projection\n")
    (root / "receipts" / "REWRITE-2026-08-03.md").write_text("an attestation, not a receipt\n")
    return root


def git(*args: str) -> None:
    subprocess.run(["git", *args], check=True, capture_output=True, env=git_env())


def guard(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(GUARD), "--root", str(root), "--today", TODAY],
        capture_output=True, text=True, check=False, env=git_env(),
    )


def fresh_projection(root: Path, extra: str = "") -> None:
    paths = sorted((root / "decisions").glob("*.yaml"))
    (root / "DECISIONS.md").write_text(
        header(input_hash(paths, root)) + f"\n{receipt_line(root)}\n{extra}")


# ------------------------------------------------------------------ T1: the D0215 control
def test_the_projection_does_not_move_with_the_date_or_the_tag_set(tmp_path: Path) -> None:
    """D0215's own evidence, applied deliberately: af41fe8 passed on 2026-09-10 and failed
    byte-identical on 2026-09-11 because `m3-close` was minted in between. Render, then move
    the date past the Tier-B veto AND mint a boundary tag dated on the receipt's day, and
    assert not one byte moved."""
    root = tree(tmp_path / "t")
    before = gen_decisions(root, dt.date(2026, 8, 2))

    git("-C", str(root), "init", "-q")
    git("-C", str(root), "-c", "user.email=t@invalid", "-c", "user.name=t",
        "commit", "-q", "--allow-empty", "-m", "fixture")
    git("-C", str(root), "tag", "m9-close")
    listed = subprocess.run(["git", "-C", str(root), "tag", "-l"], capture_output=True,
                            text=True, env=git_env()).stdout
    assert "m9-close" in listed, "control is inert: the tag was never minted"

    after = gen_decisions(root, dt.date(2030, 1, 1))
    assert after == before, "DECISIONS.md moved with the clock or the tag set (D0215)"
    assert not STORED_VERDICT_RE.search(after), "the projection stores a verdict again"
    assert "| D0002 | B | B | Probe. | provisional |" in after, (
        "the Tier-B row must show the RECORDED status, not a date-dependent effective one")


# ------------------------------------------------------------------ T2: no stored verdict
def test_the_verdict_detector_fires_on_both_spellings_and_not_on_prose() -> None:
    """The detector's own positive and negative controls: a scan nobody watched catch
    anything is not evidence of a clean file (produce-the-failure)."""
    assert STORED_VERDICT_RE.search("x\nAttention receipt: **FRESH** — receipt a.md\n")
    assert STORED_VERDICT_RE.search("- Attention receipt: **STALE** — receipt a.md stale\n")
    assert not STORED_VERDICT_RE.search(
        "| D0215 | C | DECISIONS.md's attention-receipt line reads **FRESH** at the tip |\n")


def test_a_projection_that_stores_a_verdict_is_refused(tmp_path: Path) -> None:
    root = tree(tmp_path / "t")
    fresh_projection(root)
    clean = guard(root)
    assert clean.returncode == 0, clean.stdout + clean.stderr   # the positive control

    fresh_projection(root, "Attention receipt: **FRESH** — receipt 2026-08-02.md fresh\n")
    run = guard(root)
    assert run.returncode != 0, run.stdout + run.stderr
    assert "stores an attention-receipt verdict" in run.stderr, run.stderr


def test_the_guard_still_prints_the_verdict_it_no_longer_stores(tmp_path: Path) -> None:
    """Removing the claim from the file must not remove the computation: the run prints
    the verdict and the Tier-B clock (the owner's only other window onto it is the digest)."""
    root = tree(tmp_path / "t")
    fresh_projection(root)
    run = guard(root)
    assert "attention receipt: STALE" in run.stdout, run.stdout   # no key enrolled here
    assert "veto clock: D0002" in run.stdout, run.stdout


# ------------------------------------------------------------------ T3: the receipt line
def test_a_receipt_line_that_disagrees_with_the_tree_is_refused(tmp_path: Path) -> None:
    root = tree(tmp_path / "t")
    fresh_projection(root)
    (root / "receipts" / "2026-08-09.md").write_text("# Attention receipt — 2026-08-09\n")
    run = guard(root)
    assert run.returncode != 0, run.stdout + run.stderr
    assert "receipt line does not match" in run.stderr, run.stderr
    assert "receipts/2026-08-09.md" in run.stderr and "NO signature file" in run.stderr


def test_the_receipt_line_ignores_a_rewrite_attestation(tmp_path: Path) -> None:
    """Same date parse as receipt_state (D0183): REWRITE-<date>.md is not a receipt, even
    when it is the newest file in receipts/."""
    root = tree(tmp_path / "t")
    assert receipt_line(root) == (
        "Latest attention receipt: `receipts/2026-08-02.md` — signature file present.")
