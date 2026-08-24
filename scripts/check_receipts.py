#!/usr/bin/env python3
"""check_receipts.py — the attention receipts are an append-only witness (D0063 ruling 4).

No arrangement inside a repo constrains what happens in the working tree before a commit
exists: every guard runs on a tree the builder controls, on a machine with no second
observer. The cheap partial answer is an external witness, and this repo already owns one
— the owner-signed receipts. Each records the HEAD it was taken at; requiring each
receipt's HEAD to be an ancestor of the next makes history rewriting BETWEEN sittings
detectable from artifacts the builder cannot forge, because it cannot sign them.

What this does not claim: it says nothing about what happened between two commits inside
one interval, and a builder who never takes a receipt is not caught by it — a stale
receipt is caught instead, by receipt_state suspending Tier-B consent.

Exits non-zero on any violation.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Run under `python -I -P` (conferral ruling 3, D0063): see scripts/check_manifest.py.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _gov import Failures, REPO_ROOT, git_env, owner_key_enrolled  # noqa: E402

HEAD_RE = re.compile(r"^- HEAD: ([0-9a-f]{7,40}|\(unborn\))\s*$", re.M)


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *args],
                          capture_output=True, text=True, check=False, env=git_env())


def receipt_head(path: Path) -> str | None:
    match = HEAD_RE.search(path.read_text(encoding="utf-8"))
    if match is None or match.group(1) == "(unborn)":
        return None
    return match.group(1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    fail = Failures("check_receipts")

    receipts = sorted((root / "receipts").glob("*.md")) if (root / "receipts").is_dir() else []
    if not receipts:
        print("  no receipts yet (the first lands at the opening sitting)")
        return fail.finish("no receipts to check")

    enrolled = owner_key_enrolled(root)
    signers = root / "allowed_signers"
    previous: tuple[Path, str] | None = None

    for receipt in receipts:
        sig = receipt.with_name(receipt.name + ".sig")
        if not sig.exists():
            if enrolled:
                fail.add(
                    f"{receipt.relative_to(root)} has no signature. A receipt is an "
                    "attestation of presence; an unsigned one attests to nothing and "
                    "would let the chain below be extended by the party it measures."
                )
        elif not signers.exists():
            fail.add("allowed_signers is missing, so no receipt signature can verify")
        else:
            verify = subprocess.run(
                ["ssh-keygen", "-Y", "verify", "-f", str(signers), "-I", "owner@tannen",
                 "-n", "tannen-receipt", "-s", str(sig)],
                input=receipt.read_bytes(), capture_output=True,
            )
            if verify.returncode != 0:
                fail.add(f"{receipt.relative_to(root)}: signature does not verify against "
                         "owner@tannen (namespace tannen-receipt)")

        head = receipt_head(receipt)
        if head is None:
            print(f"  {receipt.stem}: no HEAD recorded (pre-chain receipt)")
            continue
        if git(root, "cat-file", "-e", f"{head}^{{commit}}").returncode != 0:
            fail.add(
                f"{receipt.relative_to(root)} records HEAD {head}, which is not a commit "
                "in this repository — the history the owner attested to is gone"
            )
            continue
        if previous is not None:
            prev_receipt, prev_head = previous
            if git(root, "merge-base", "--is-ancestor", prev_head, head).returncode != 0:
                fail.add(
                    f"receipt chain broken: {prev_receipt.stem} recorded HEAD {prev_head}, "
                    f"which is NOT an ancestor of {receipt.stem}'s {head}. History was "
                    "rewritten between two owner-signed attestations (D0063 ruling 4)."
                )
        previous = (receipt, head)

    if previous is not None:
        last_receipt, last_head = previous
        current = git(root, "rev-parse", "HEAD")
        if current.returncode == 0:
            current_head = current.stdout.strip()
            if git(root, "merge-base", "--is-ancestor", last_head, current_head).returncode != 0:
                fail.add(
                    f"receipt chain broken at the tip: the latest receipt "
                    f"({last_receipt.stem}) recorded HEAD {last_head}, which is not an "
                    "ancestor of the current HEAD. Work since the last attestation is not "
                    "an extension of what was attested."
                )

    return fail.finish(f"{len(receipts)} receipt(s); chain unbroken to HEAD")


if __name__ == "__main__":
    sys.exit(main())
