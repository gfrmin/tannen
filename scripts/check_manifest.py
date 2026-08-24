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

from _gov import (Failures, custody_declaration, custody_rows, load_yaml, parse_manifest,
                  sha256_bytes, sha256_file, REPO_ROOT)


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


def check_sealed_paths(root: Path, fail: Failures) -> None:
    """A sealed directory is sealed, not a whitelist (RT-01, RT-03; decision D0056).

    MANIFEST.sha256 does not list itself and nothing enumerates what it *should*
    contain, so a row can be deleted — unfreezing the path — and a file can be added
    inside a frozen directory, changing what the frozen tests mean, both with no trace
    and with every guard green. Under a seal the two are one rule: every file under a
    sealed directory carries a manifest row.
    """
    tier_c_path = root / "governance" / "tier-c.yaml"
    if not tier_c_path.exists():
        return  # check_tier_c_consistency reports the absence; do not crash here
    tier_c = load_yaml(tier_c_path) or {}
    sealed = (tier_c.get("frozen_paths") or {}).get("sealed_dirs") or []
    manifest = root / "MANIFEST.sha256"
    entries = parse_manifest(manifest) if manifest.exists() else {}
    for rel in sealed:
        base = root / rel
        if not base.is_dir():
            fail.add(f"sealed directory does not exist: {rel}")
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            key = path.relative_to(root).as_posix()
            if key not in entries:
                fail.add(
                    f"unmanifested file in sealed path: {key} — a sealed directory is "
                    "sealed, not a whitelist: rows may not be removed from it and files "
                    "may not be added to it (BRIEF §9.1 custody floor)"
                )


def check_required_signatures(root: Path, fail: Failures) -> None:
    """An optional signature is not a signature (RT-04, decision D0056).

    The custodian verifies governance/policy.yaml.sig *if it exists* and otherwise
    reports "unsigned (expected before the opening sitting)" and passes — correct before
    the sitting, and a silent floor-lowering after it. Deleting the file is enough to
    make the owner-signed policy the guards consume freely editable.
    """
    tier_c_path = root / "governance" / "tier-c.yaml"
    if not tier_c_path.exists():
        return
    required = (load_yaml(tier_c_path) or {}).get("required_signatures") or []
    signers = root / "allowed_signers"
    for entry in required:
        target = root / entry["path"]
        sig = target.with_name(target.name + ".sig")
        if not target.exists():
            fail.add(f"required-signature target does not exist: {entry['path']}")
            continue
        if not sig.exists():
            fail.add(
                f"missing owner signature: {entry['path']}.sig — this file is declared "
                "owner-signed in tier-c.yaml, so its signature is required, not "
                "optional. Deleting it would otherwise lower the custody floor in "
                "silence (RT-04)."
            )
            continue
        if not signers.exists():
            fail.add(f"allowed_signers is missing, so {entry['path']}.sig cannot verify")
            continue
        verify = subprocess.run(
            ["ssh-keygen", "-Y", "verify", "-f", str(signers), "-I", entry["signer"],
             "-n", entry["namespace"], "-s", str(sig)],
            input=target.read_bytes(), capture_output=True,
        )
        if verify.returncode != 0:
            fail.add(f"signature does not verify for {entry['path']} against {entry['signer']}")


def check_custody(root: Path, fail: Failures) -> None:
    """The custody set is current, and its holes are named (decision D0061).

    MANIFEST.sha256 is a whitelist of hashes with nothing enumerating what it should
    contain, so a row can be deleted and the path silently unfreezes (RT-01). The custody
    set is that missing enumeration for the subset the owner signs. It is deliberately
    NOT the manifest: the manifest grows at every law freeze under the builder's standing
    delegation, so signing it would put the owner's key in the path of every milestone.
    """
    declaration = custody_declaration(root)
    if not declaration:
        return
    rows, problems = custody_rows(root)
    for problem in problems:
        fail.add(problem)
    target = root / declaration["file"]
    if not target.exists():
        fail.add(f"custody file missing: {declaration['file']} — run scripts/gen_custody.py")
        return
    want = {row.split("  ", 1)[1]: row.split("  ", 1)[0] for row in rows}
    have = parse_manifest(target)
    for rel in sorted(set(have) - set(want)):
        fail.add(f"custody drift: {rel} is signed for but no longer declared in "
                 "tier-c.yaml custody.set")
    for rel in sorted(set(want) - set(have)):
        fail.add(f"custody drift: {rel} is declared in the custody set but absent from "
                 f"{declaration['file']} — run scripts/gen_custody.py")
    for rel in sorted(set(want) & set(have)):
        if want[rel] != have[rel]:
            fail.add(
                f"custody drift: {rel} changed since the custody file was written. Any "
                "owner signature over it no longer covers these bytes — regenerate with "
                "scripts/gen_custody.py and have the owner re-sign at the next boundary "
                "sitting (this is the alarm, not a bug)."
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
    # Every list, not an enumerated few: a new forbidden_imports list added here must
    # be covered by a contract too, or the human-readable source would quietly outrun
    # the machine-enforced one (D0016).
    for kind, modules in forbidden.items():
        for mod in modules or []:
            if mod not in covered:
                fail.add(
                    f"tier-c.yaml forbidden_imports.{kind} lists {mod!r} but no "
                    "pyproject.toml import-linter contract forbids it (one source, D0016)"
                )

    # A contract's teeth are its SHAPE, not just its forbidden list (RT-02, D0056).
    # Coverage of tier-c.yaml's modules says nothing about who is checked or what is
    # excused: narrowing source_modules to one module excuses the rest of the package,
    # and an ignore_imports line excuses everything, both while every other guard stays
    # green and `Contracts: 3 kept` is printed.
    expected_sources = {
        "kernel-no-io": ["tannen.kernel"],
        "kernel-no-clock": ["tannen.kernel"],
        "no-cross-repo": ["tannen"],
    }
    seen_ids = {c.get("id") for c in contracts}
    for cid, expected in expected_sources.items():
        if cid not in seen_ids:
            fail.add(f"import contract {cid!r} is missing from pyproject.toml entirely")
    for contract in contracts:
        cid = contract.get("id")
        if cid not in expected_sources:
            continue
        if contract.get("type") != "forbidden":
            fail.add(f"import contract {cid} is not a 'forbidden' contract")
        if contract.get("source_modules") != expected_sources[cid]:
            fail.add(
                f"import contract {cid} source_modules is "
                f"{contract.get('source_modules')!r}, expected {expected_sources[cid]!r} "
                "— narrowing the source silently excuses the rest of the package"
            )
        for key in ("ignore_imports", "unmatched_ignore_imports_alerting"):
            if contract.get(key):
                fail.add(
                    f"import contract {cid} carries {key} — a contract with exceptions "
                    "is not the contract tier-c.yaml declares"
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
    check_sealed_paths(root, fail)
    check_required_signatures(root, fail)
    check_custody(root, fail)
    if args.staged:
        check_staged(root, fail)
    check_tier_c_consistency(root, fail)
    return fail.finish("frozen paths intact; seals unbroken; custody set current; "
                       "required signatures present; tier-c.yaml consistent with the guards")


if __name__ == "__main__":
    sys.exit(main())
