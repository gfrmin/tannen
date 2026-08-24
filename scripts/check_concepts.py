#!/usr/bin/env python3
"""check_concepts.py — concept records ↔ vendored artifacts complete; projection fresh.

Per BRIEF §2: the registry is data the build consumes. This check enforces:
  - every concepts/*.yaml validates against governance/schemas/concept-record.schema.json;
  - every snapshot a record cites exists and hashes to the recorded sha256;
  - every file under concepts/snapshots/ is cited by some record (no orphan artifacts);
  - grade S records name an existing, non-empty vector corpus; every corpus directory
    under conformance/vectors/ belongs to some grade-S record;
  - the generated CONCEPTS.md is fresh (its input-hash header matches the records).

Exits non-zero on any violation.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Run under `python -I -P` (conferral ruling 3, D0063): isolated mode ignores
# PYTHONPATH, PYTHONHOME and user site-packages, and -P stops any directory being
# prepended to sys.path implicitly — including this script's own. The floor may depend
# only on tools the OS provides and paths named literally, so the one path this guard
# needs is named literally here, derived from __file__ rather than inherited.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _gov import (  # noqa: E402
    Failures,
    input_hash,
    load_schema,
    load_yaml,
    read_header_hash,
    schema_errors,
    sha256_file,
    REPO_ROOT,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    fail = Failures("check_concepts")

    schema = load_schema(root, "concept-record.schema.json")
    record_paths = sorted((root / "concepts").glob("*.yaml"))
    if not record_paths:
        fail.add("no concept records found under concepts/")

    cited_snapshots: set[Path] = set()
    cited_vector_dirs: set[Path] = set()
    seen_ids: set[str] = set()

    for path in record_paths:
        rel = path.relative_to(root)
        record = load_yaml(path)
        errors = schema_errors(record, schema)
        if errors:
            for err in errors:
                fail.add(f"{rel}: schema violation at {err}")
            continue
        if record["id"] in seen_ids:
            fail.add(f"{rel}: duplicate concept id {record['id']}")
        seen_ids.add(record["id"])
        if path.stem != record["id"]:
            fail.add(f"{rel}: filename stem {path.stem!r} != id {record['id']!r}")

        for source in record["sources"]:
            snap_rel = source["snapshot"]["path"]
            snap = root / snap_rel
            cited_snapshots.add(snap)
            if not snap.exists():
                fail.add(f"{rel}: vendored snapshot missing: {snap_rel}")
            elif sha256_file(snap) != source["snapshot"]["sha256"]:
                fail.add(f"{rel}: vendored snapshot content drifted: {snap_rel}")

        vectors = record["conformance"].get("vectors")
        if record["grade"] == "S":
            vec_dir = root / vectors
            cited_vector_dirs.add(vec_dir)
            if not vec_dir.is_dir() or not any(vec_dir.iterdir()):
                fail.add(f"{rel}: grade-S record names missing/empty vector corpus: {vectors}")
        elif vectors is not None:
            fail.add(f"{rel}: only grade-S records may name a vector corpus (grade {record['grade']})")

        for test_path in record["conformance"]["tests"]:
            if not (root / test_path.split("::", 1)[0]).exists():
                fail.add(f"{rel}: conformance test path missing: {test_path}")

    snapshots_root = root / "concepts" / "snapshots"
    if snapshots_root.exists():
        for artifact in sorted(p for p in snapshots_root.rglob("*") if p.is_file()):
            if artifact not in cited_snapshots:
                fail.add(f"orphan vendored artifact (no record cites it): {artifact.relative_to(root)}")

    vectors_root = root / "conformance" / "vectors"
    if vectors_root.exists():
        for entry in sorted(p for p in vectors_root.iterdir() if p.is_dir()):
            if entry not in cited_vector_dirs:
                fail.add(f"orphan vector corpus (no grade-S record cites it): {entry.relative_to(root)}")

    # Normative-prose markers (BRIEF §2): spec documents must declare what they own
    # or cite ([owns] / [cites: <concept-id>]), and every citation must resolve to a
    # registered concept. Scope: docs/specs/ (the normative prose this repo writes);
    # constitution and generated files are out of scope (decision D0029).
    marker_re = re.compile(r"\[cites:\s*([a-z0-9-]+)\]")
    for doc in sorted((root / "docs" / "specs").glob("*.md")):
        text = doc.read_text(encoding="utf-8")
        rel_doc = doc.relative_to(root)
        if "[owns]" not in text and not marker_re.search(text):
            fail.add(f"{rel_doc}: normative prose without [owns] or [cites: <concept-id>] markers")
        for cited in marker_re.findall(text):
            if cited not in seen_ids:
                fail.add(f"{rel_doc}: [cites: {cited}] does not resolve to a registered concept")

    projection = root / "CONCEPTS.md"
    if record_paths:
        expected = input_hash(record_paths, root)
        actual = read_header_hash(projection)
        if actual is None:
            fail.add("CONCEPTS.md missing or lacks the generated input-hash header — run make projections")
        elif actual != expected:
            fail.add("CONCEPTS.md is stale (input-hash mismatch) — run make projections; never hand-edit")

    return fail.finish(f"{len(record_paths)} records, artifacts complete, CONCEPTS.md fresh")


if __name__ == "__main__":
    sys.exit(main())
