#!/usr/bin/env python3
"""check_manifest.py — frozen paths intact (CLAUDE.md hard rules; BRIEF §8/§9).

Default mode: every path listed in MANIFEST.sha256 exists and its sha256 matches.
--staged mode (pre-commit): no staged change may alter or delete a manifest-listed
path — the staged blob must hash to the manifest's value.

Also enforces the tier-c.yaml single-source rule (decision D0016): the manifest
named by governance/tier-c.yaml exists, the budget file it names exists, and every
module in its forbidden_imports lists is covered by a pyproject.toml import-linter
contract, so the human-readable list and the machine-enforced list cannot drift.

Exits non-zero on any violation.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tomllib
from pathlib import Path

from _gov import Failures, load_yaml, parse_manifest, sha256_bytes, sha256_file, REPO_ROOT


def check_frozen_files(root: Path, fail: Failures) -> None:
    manifest_path = root / "MANIFEST.sha256"
    if not manifest_path.exists():
        fail.add("MANIFEST.sha256 is missing")
        return
    try:
        entries = parse_manifest(manifest_path)
    except ValueError as exc:
        fail.add(str(exc))
        return
    if not entries:
        fail.add("MANIFEST.sha256 lists no frozen paths")
    for rel, expected in entries.items():
        target = root / rel
        if not target.exists():
            fail.add(f"frozen path missing: {rel}")
        elif sha256_file(target) != expected:
            fail.add(f"frozen path modified: {rel} (sha256 differs from MANIFEST.sha256)")
    # A manifest row must reference a committed artifact — an untracked file
    # (bytecode cache, local scratch) verifies on the machine that wrote the row
    # and fails on every clean clone (defect D0034).
    ls = subprocess.run(
        ["git", "-C", str(root), "ls-files"], capture_output=True, text=True, check=False
    )
    if ls.returncode == 0:
        tracked = set(ls.stdout.splitlines())
        for rel in entries:
            if rel not in tracked:
                fail.add(f"frozen path not git-tracked: {rel} (manifest rows must be committed artifacts, D0034)")


def check_staged(root: Path, fail: Failures) -> None:
    manifest_path = root / "MANIFEST.sha256"
    if not manifest_path.exists():
        return  # nothing frozen yet
    entries = parse_manifest(manifest_path)
    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=root, capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    for rel in staged:
        if rel not in entries:
            continue
        show = subprocess.run(
            ["git", "show", f":{rel}"], cwd=root, capture_output=True, check=False
        )
        if show.returncode != 0:
            fail.add(f"frozen path staged for deletion: {rel}")
        elif sha256_bytes(show.stdout) != entries[rel]:
            fail.add(
                f"frozen path staged with modified content: {rel} — frozen paths are "
                "read-only; record a defect decision and supersede instead (CLAUDE.md)"
            )


def check_tier_c_consistency(root: Path, fail: Failures) -> None:
    tier_c_path = root / "governance" / "tier-c.yaml"
    if not tier_c_path.exists():
        fail.add("governance/tier-c.yaml is missing")
        return
    tier_c = load_yaml(tier_c_path)

    manifest_rel = tier_c.get("frozen_paths", {}).get("manifest")
    if manifest_rel != "MANIFEST.sha256":
        fail.add(f"tier-c.yaml frozen_paths.manifest is {manifest_rel!r}, expected 'MANIFEST.sha256'")

    budget_rel = tier_c.get("budget", {}).get("file")
    if not budget_rel or not (root / budget_rel).exists():
        fail.add(f"tier-c.yaml budget.file {budget_rel!r} does not exist")

    policy_rel = tier_c.get("policy", {}).get("file")
    if not policy_rel or not (root / policy_rel).exists():
        fail.add(f"tier-c.yaml policy.file {policy_rel!r} does not exist")
    elif budget_rel and (root / budget_rel).exists():
        # BRIEF §9.2: operational SpendGuard ceilings may never exceed what the
        # owner-signed policy envelopes authorise (Tier-C door: spend-envelopes).
        envelopes = (load_yaml(root / policy_rel) or {}).get("budget_envelopes", {})
        max_envelope = max(envelopes.values(), default=0)
        ceilings = (load_yaml(root / budget_rel) or {}).get("ceilings", {})
        for name, value in ceilings.items():
            if value > max_envelope:
                fail.add(
                    f"budget.yaml ceiling {name}={value} exceeds every policy.yaml "
                    f"budget envelope (max {max_envelope}) — Tier-C door spend-envelopes"
                )

    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        fail.add("pyproject.toml is missing")
        return
    contracts = tomllib.loads(pyproject.read_text(encoding="utf-8")) \
        .get("tool", {}).get("importlinter", {}).get("contracts", [])
    covered = {m for c in contracts for m in c.get("forbidden_modules", [])}
    forbidden = tier_c.get("forbidden_imports", {})
    for kind in ("io_modules", "cross_repo"):
        for mod in forbidden.get(kind, []):
            if mod not in covered:
                fail.add(
                    f"tier-c.yaml forbidden_imports.{kind} lists {mod!r} but no "
                    "pyproject.toml import-linter contract forbids it (one source, D0016)"
                )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--staged", action="store_true",
                        help="pre-commit mode: reject staged edits to frozen paths")
    args = parser.parse_args()
    root = args.root.resolve()

    fail = Failures("check_manifest")
    check_frozen_files(root, fail)
    if args.staged:
        check_staged(root, fail)
    check_tier_c_consistency(root, fail)
    return fail.finish("frozen paths intact; tier-c.yaml consistent with the guards")


if __name__ == "__main__":
    sys.exit(main())
