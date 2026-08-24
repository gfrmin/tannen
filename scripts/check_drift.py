#!/usr/bin/env python3
"""check_drift.py — upstream drift report (BRIEF §2).

For every concept source pinned to an owner repo, compare the pinned commit against
the owner's current HEAD (via the read-only clone in .reference/, fetched first unless
--no-fetch) and report when the CITED DOCUMENT changed between pin and HEAD. Drift is
reported, not policed by prose: with --file-records each drifted concept gets a
drafted Tier-B re-pin decision record (next free sequence, veto_by +7 days), which
the digest then queues; without it, the report alone makes the drift visible.

Exit codes: 0 = no drift; 3 = drift detected; 1 = operational error (missing clone,
git failure). Scheduling note (decision D0028): this runs via `make drift` at session
starts; a cron/CI schedule would need the repo hosted, and hosting is Tier-C door
external-bytes, so none is configured yet.
"""

from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path

# Run under `python -I -P` (conferral ruling 3, D0063): isolated mode ignores
# PYTHONPATH, PYTHONHOME and user site-packages, and -P stops any directory being
# prepended to sys.path implicitly — including this script's own. The floor may depend
# only on tools the OS provides and paths named literally, so the one path this guard
# needs is named literally here, derived from __file__ rather than inherited.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _gov import load_yaml, REPO_ROOT  # noqa: E402


def git(clone: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(clone), *args], capture_output=True, text=True)


def draft_repin_record(root: Path, concept: dict, source: dict, head: str, today: dt.date) -> Path | None:
    decisions = root / "decisions"
    existing = sorted(decisions.glob("*.yaml"))
    for path in existing:
        rec = load_yaml(path)
        if head[:12] in rec.get("decision", "") and concept["id"] in rec.get("decision", ""):
            return None  # already filed for this drift
    seq = max((int(p.stem[:4]) for p in existing), default=0) + 1
    slug = f"repin-{concept['id']}"
    path = decisions / f"{seq:04d}-{slug}.yaml"
    veto_by = today + dt.timedelta(days=7)
    flags = "\nrisk_flags: [ref-grammar]" if concept["id"] == "provenance-ref-grammar" else ""
    path.write_text(
        f"""# Decision record — drafted by scripts/check_drift.py (BRIEF §2 drift job).
id: D{seq:04d}
title: Re-pin {concept['id']} — owner moved {source['document']}
tier: B
date: "{today.isoformat()}"
decision: >-
  Owner repo {source['repo']} moved from pinned commit {source['commit']} to
  {head}; the cited document {source['document']} changed in between. Re-pin the
  source, re-vendor the cited section, and update the record's snapshot hash.
rationale: >-
  BRIEF §2: upstream drift is reported, not policed by prose; a drift files a Tier-B
  record prompting a re-pin. Adopting the owner's new text is the default posture;
  vetoing means recording why tannen stays on the old pin.
reversibility: >-
  A re-pin is one record edit plus re-vendored bytes; the old pin remains in git
  history.
status: provisional
veto_by: "{veto_by.isoformat()}"
veto_procedure: >-
  Say so in the next digest review; the concept then stays pinned and this record is
  marked rejected.
bindings:
  - type: file
    target: concepts/{concept['id']}.yaml
    detail: the record whose pin this drift invalidates{flags}
""",
        encoding="utf-8",
    )
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--no-fetch", action="store_true", help="compare against the clone as-is")
    parser.add_argument("--file-records", action="store_true",
                        help="draft a Tier-B re-pin record per drifted concept")
    parser.add_argument("--today", type=dt.date.fromisoformat, default=dt.date.today())
    args = parser.parse_args()
    root = args.root.resolve()

    drift = errors = 0
    fetched: set[Path] = set()
    for record_path in sorted((root / "concepts").glob("*.yaml")):
        concept = load_yaml(record_path)
        for source in concept["sources"]:
            if source["commit"] is None or source["repo"].startswith("this repo"):
                continue
            clone = root / ".reference" / source["repo"].rstrip("/").rsplit("/", 1)[-1]
            if not clone.is_dir():
                print(f"check_drift: ERROR — clone missing: {clone} (re-clone at pinned SHA)", file=sys.stderr)
                errors += 1
                continue
            if not args.no_fetch and clone not in fetched:
                if git(clone, "fetch", "--quiet", "origin").returncode != 0:
                    print(f"check_drift: ERROR — fetch failed for {clone.name}", file=sys.stderr)
                    errors += 1
                fetched.add(clone)
            head_proc = git(clone, "rev-parse", "origin/HEAD")
            if head_proc.returncode != 0:
                head_proc = git(clone, "rev-parse", "origin/master")
            if head_proc.returncode != 0:
                print(f"check_drift: ERROR — cannot resolve owner HEAD for {clone.name}", file=sys.stderr)
                errors += 1
                continue
            head = head_proc.stdout.strip()
            if head == source["commit"]:
                print(f"check_drift: {concept['id']} · {source['document']}: pin is at owner HEAD")
                continue
            changed = git(clone, "diff", "--quiet", source["commit"], head, "--", source["document"])
            if changed.returncode == 0:
                print(f"check_drift: {concept['id']} · {source['document']}: owner moved "
                      f"({head[:12]}) but the cited document is unchanged — pin still exact")
            else:
                drift += 1
                print(f"check_drift: DRIFT — {concept['id']} · {source['document']} changed "
                      f"between {source['commit'][:12]} and {head[:12]}")
                if args.file_records:
                    filed = draft_repin_record(root, concept, source, head, args.today)
                    if filed:
                        print(f"check_drift: drafted {filed.relative_to(root)} — regenerate projections")

    if errors:
        return 1
    if drift:
        print(f"check_drift: {drift} drifted source(s) — Tier-B re-pin due")
        return 3
    print("check_drift: OK — no cited document has drifted from its pin")
    return 0


if __name__ == "__main__":
    sys.exit(main())
