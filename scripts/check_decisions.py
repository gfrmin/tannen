#!/usr/bin/env python3
"""check_decisions.py — decision records valid, bindings load-bearing, clocks computed.

Per BRIEF §9: decisions are append-only event records; bindings make them
load-bearing; CI fails if a binding's target is missing or skipped. This check:
  - validates every decisions/*.yaml against the decision-record schema;
  - enforces filename ↔ id agreement and id uniqueness;
  - resolves every binding (file exists / config key resolves / pytest node
    collects and is not skipped / path listed in MANIFEST.sha256);
  - flags unbound records as `unenforced` (acceptable only with a stated reason —
    the schema requires one, so a bare unbound record fails);
  - computes Tier-B veto clocks (expiry transitions effective status mechanically;
    the record file is never edited);
  - verifies the generated DECISIONS.md is fresh (input-hash header).

Exits non-zero on any violation.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import yaml

from _gov import (
    Failures,
    input_hash,
    load_schema,
    load_yaml,
    parse_manifest,
    read_header_hash,
    receipt_state,
    resolve_dotted,
    schema_errors,
    REPO_ROOT,
)

FILENAME_RE = re.compile(r"^(\d{4})-[a-z0-9]+(-[a-z0-9]+)*$")


def binding_violation(root: Path, kind: str, target: str) -> str | None:
    if kind == "file":
        return None if (root / target).exists() else f"target does not exist: {target}"
    if kind == "manifest":
        manifest = root / "MANIFEST.sha256"
        if not manifest.exists():
            return "MANIFEST.sha256 does not exist"
        return None if target in parse_manifest(manifest) else f"not listed in MANIFEST.sha256: {target}"
    if kind == "config":
        if "#" not in target:
            return f"config target needs 'path#dotted.key': {target}"
        rel, dotted = target.split("#", 1)
        path = root / rel
        if not path.exists():
            return f"config file does not exist: {rel}"
        if path.suffix == ".toml":
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        else:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        try:
            resolve_dotted(data, dotted)
        except KeyError:
            return f"config key {dotted!r} does not resolve in {rel}"
        return None
    if kind == "pytest":
        run = subprocess.run(
            ["uv", "run", "pytest", target, "-q", "--no-header", "-p", "no:cacheprovider"],
            cwd=root, capture_output=True, text=True, check=False,
        )
        out = run.stdout + run.stderr
        if "no tests ran" in out or run.returncode == 4:
            return f"pytest node does not collect: {target}"
        if re.search(r"\b[1-9]\d* skipped\b", out) and " passed" not in out:
            return f"pytest node is skipped (a skipped binding is not enforcement): {target}"
        if run.returncode != 0:
            return f"pytest node fails: {target}"
        return None
    return f"unknown binding type: {kind}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--today", type=dt.date.fromisoformat, default=dt.date.today(),
                        help="override 'today' for veto-clock computation (tests)")
    args = parser.parse_args()
    root = args.root.resolve()
    fail = Failures("check_decisions")

    schema = load_schema(root, "decision-record.schema.json")
    record_paths = sorted((root / "decisions").glob("*.yaml"))
    if not record_paths:
        fail.add("no decision records found under decisions/")

    receipts_fresh, receipt_detail = receipt_state(root, args.today)
    print(f"  attention receipt: {'FRESH' if receipts_fresh else 'STALE'} — {receipt_detail}")

    seen_ids: set[str] = set()
    unenforced: list[str] = []
    clocks: list[str] = []

    for path in record_paths:
        rel = path.relative_to(root)
        m = FILENAME_RE.match(path.stem)
        if not m:
            fail.add(f"{rel}: filename must be <seq>-<slug>.yaml")
            continue
        record = load_yaml(path)
        errors = schema_errors(record, schema)
        if errors:
            for err in errors:
                fail.add(f"{rel}: schema violation at {err}")
            continue
        rid = record["id"]
        if rid in seen_ids:
            fail.add(f"{rel}: duplicate decision id {rid}")
        seen_ids.add(rid)
        if rid != f"D{m.group(1)}":
            fail.add(f"{rel}: id {rid} does not match filename sequence {m.group(1)}")

        for binding in record["bindings"]:
            problem = binding_violation(root, binding["type"], binding["target"])
            if problem:
                fail.add(f"{rel}: binding does not resolve — {problem}")
        if not record["bindings"]:
            unenforced.append(f"{rid} ({record['title']}): {record['unenforced_reason']}")

        if record["tier"] == "B" and record["status"] == "provisional":
            veto_by = dt.date.fromisoformat(record["veto_by"])
            days = (veto_by - args.today).days
            if days >= 0:
                clocks.append(f"{rid}: veto open, {days} day(s) remaining (until {veto_by})")
            elif receipts_fresh:
                clocks.append(f"{rid}: veto lapsed {-days} day(s) ago — effective status accepted (silence = consent under fresh receipt)")
            else:
                clocks.append(
                    f"{rid}: veto window passed {-days} day(s) ago but the attention receipt "
                    "is stale — BLOCKED, not consented (BRIEF §9.1; blocks accumulate)"
                )

    projection = root / "DECISIONS.md"
    if record_paths:
        expected = input_hash(record_paths, root)
        actual = read_header_hash(projection)
        if actual is None:
            fail.add("DECISIONS.md missing or lacks the generated input-hash header — run make projections")
        elif actual != expected:
            fail.add("DECISIONS.md is stale (input-hash mismatch) — run make projections; never hand-edit")

    for line in clocks:
        print(f"  veto clock: {line}")
    for line in unenforced:
        print(f"  unenforced (visible debt): {line}")
    return fail.finish(
        f"{len(record_paths)} records valid; {len(unenforced)} unenforced (with reasons); "
        f"{len(clocks)} Tier-B clock(s) computed; DECISIONS.md fresh"
    )


if __name__ == "__main__":
    sys.exit(main())
