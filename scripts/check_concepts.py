#!/usr/bin/env python3
"""check_concepts.py — concept records ↔ vendored artifacts complete; projection fresh.

Per BRIEF §2: the registry is data the build consumes. This check enforces:
  - every concepts/*.yaml validates against governance/schemas/concept-record.schema.json;
  - every snapshot a record cites either exists and hashes to the recorded sha256, or is
    absent and verified by PIN alone (D0115 mechanism (a) — the published tree carries
    the citation, the authorised clone carries the bytes);
  - the number of citation pins accounted for matches governance/policy.yaml's
    `concept_registry.expected_citation_pins`, which is NOT derived from concepts/;
  - every file under concepts/snapshots/ is cited by some record (no orphan artifacts);
  - grade S records name an existing, non-empty vector corpus; every corpus directory
    under conformance/vectors/ belongs to some grade-S record;
  - the generated CONCEPTS.md is fresh (its input-hash header matches the records);
  - brief_row quotes a BRIEF §2 row verbatim, and the owners that row names match the
    record's sources[].repo unless the record declares otherwise under
    brief_row_divergence (D0180 — until then no guard read the field at all).

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


#: The constellation vocabulary BRIEF §2's Owner column is read against — the same five
#: tokens the probe that measured this used (docs/proposals/2026-09-06-publication/probes/).
#: A hand-written enumeration, which CLAUDE.md's standing rule says a guard should not
#: depend on; kept because BRIEF §1's first column is prose ("Renavon monorepo", not a
#: slug), so deriving it needs a normalisation that is itself a judgement — named as a
#: known weakness in patch 05 rather than left for the next red team. The fourth token
#: stays after D0180 for the reason importlinter.toml's forbidden names do: it is what
#: lets the guard SEE a citation to that repository, declared or not.
OWNER_TOKENS = ("pkm", "life-agent", "proplang", "renavon", "tannen")


def norm(text: str) -> str:
    """Markdown emphasis is not content: strip backticks and asterisks, collapse whitespace.
    Measured 2026-09-06: without this, 2 of 8 faithful records fail on markup alone
    (similarity 0.990 and 0.991, prose identical) — the first spelling of this check died
    of that false positive."""
    return re.sub(r"\s+", " ", re.sub(r"[`*]", "", text)).strip()


def load_brief(root: Path) -> tuple[str, dict[str, str]] | None:
    """(normalised BRIEF.md text, {normalised Concept cell: normalised Owner cell}) over
    every table row, or None when this root has no BRIEF.md.

    NO fallback to the real repo's BRIEF: a poison tree that needs this tooth carries its
    own one-row constitution excerpt, the way check-concepts/ carries its own policy.yaml —
    a fixture violates a guard, it does not duplicate the governance corpus, and a fixture
    record forced to quote the real §2 would be exactly that duplication. In the real tree
    BRIEF.md is frozen and custody-set, so its absence is check_manifest's failure before
    it is this one's; the skip is printed, never silent.
    """
    brief_md = root / "BRIEF.md"
    if not brief_md.exists():
        return None
    text = brief_md.read_text(encoding="utf-8")
    rows: dict[str, str] = {}
    for line in text.splitlines():
        if line.startswith("|") and line.count("|") >= 4 and not line.startswith("|---"):
            cells = line.split("|")
            rows[norm(cells[1])] = norm(cells[2])
    return norm(text), rows


def owners_in(text: str) -> set[str]:
    lowered = text.lower()
    return {token for token in OWNER_TOKENS if token in lowered}


def brief_row_problems(record: dict, brief: tuple[str, dict[str, str]]) -> list[str]:
    """D0180's finding, in two teeth: `brief_row` is a required field whose stated job is
    to carry the BRIEF §2 row a record answers to, and until this nothing read it, so a
    record could misreport who owns a concept with the whole gate green.

    Tooth 1 — the double-quoted span in brief_row is verbatim in BRIEF.md (markup-
    normalised). Catches a record that rewrites the concept title.

    Tooth 2 — the owners BRIEF §2 names for that row equal the record's sources[].repo
    set, unless the record declares the difference under `brief_row_divergence`. The
    declaration is the point: it turns "a human wrote a paragraph explaining this" into
    data the guard reads, so the NEXT divergence — the undeclared one — is the one that
    fails. A declaration naming an owner BRIEF does not name for the row, or one the
    record cites anyway, is itself a failure: a dormant declaration would silently cover
    a future omission (D0116 species I).

    The quoted span is only BRIEF §2's Concept column; the Owner column is free prose
    after the closing quote. That is why a check on the span alone measured GREEN on the
    exact case it existed for, and why there are two teeth.
    """
    brief_text, rows = brief
    problems: list[str] = []
    quoted = re.search(r'"([^"]+)"', record["brief_row"])
    if quoted is None:
        return ["brief_row quotes nothing — the BRIEF §2 concept cell must appear in double quotes"]
    span = norm(quoted.group(1))
    if span not in brief_text:
        problems.append(f"brief_row quotes {span!r}, which is not verbatim in BRIEF.md")
    owner_cell = rows.get(span)
    if owner_cell is None:
        problems.append(
            f"brief_row quotes {span!r}, which is not a BRIEF §2 table row, so its owners "
            "cannot be checked"
        )
        return problems
    want = owners_in(owner_cell)
    got = owners_in(" ".join(source["repo"] for source in record["sources"]))
    declared = set((record.get("brief_row_divergence") or {}).get("omits") or ())
    stale = declared - (want - got)
    if stale:
        problems.append(
            f"brief_row_divergence declares omits {sorted(stale)}, but BRIEF §2 names no "
            "such owner that this record fails to cite — a stale declaration would cover a "
            "future omission (D0116 species I)"
        )
    missing = want - got - declared
    if missing:
        problems.append(
            f"brief_row owners per BRIEF §2 are {sorted(want)} but sources[].repo names "
            f"{sorted(got)} — undeclared divergence: {sorted(missing)} (cite the owner, or "
            "declare the omission under brief_row_divergence)"
        )
    extra = got - want
    if extra:
        problems.append(
            f"brief_row: sources[].repo names {sorted(extra)}, which BRIEF §2 does not name "
            "as an owner of this row"
        )
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    fail = Failures("check_concepts")

    schema = load_schema(root, "concept-record.schema.json")
    brief = load_brief(root)
    if brief is None:
        print(f"  brief_row fidelity: no BRIEF.md under {root.name}/ — both teeth skipped "
              "(a poison tree that needs them carries its own excerpt)")
    record_paths = sorted((root / "concepts").glob("*.yaml"))
    if not record_paths:
        fail.add("no concept records found under concepts/")

    cited_snapshots: set[Path] = set()
    cited_vector_dirs: set[Path] = set()
    seen_ids: set[str] = set()

    # D0115 mechanism (a). A published clone carries the citation PINS; the bytes stay in
    # the authorised clone. Both are legal, and the difference is counted rather than
    # assumed: `by_bytes` is a full verification, `by_pin` is a promise nothing here can
    # check. The totals are printed so a reader can see which mode a tree is in.
    pins_by_bytes = 0
    pins_by_pin = 0

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
        if brief is not None:
            for problem in brief_row_problems(record, brief):
                fail.add(f"{rel}: {problem}")

        for source in record["sources"]:
            snap_rel = source["snapshot"]["path"]
            snap = root / snap_rel
            cited_snapshots.add(snap)
            if not snap.exists():
                # NOT a failure since D0115: absence is the published configuration. The
                # pin still has to be ACCOUNTED FOR below, which is the whole reason this
                # branch cannot simply `continue` in silence.
                pins_by_pin += 1
            elif sha256_file(snap) != source["snapshot"]["sha256"]:
                fail.add(f"{rel}: vendored snapshot content drifted: {snap_rel}")
                pins_by_bytes += 1
            else:
                pins_by_bytes += 1

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

    # THE CONDITION D0115 MAKES NON-OPTIONAL, and the reason the branch above counts
    # instead of skipping. A degraded check whose input set is empty reports success
    # having verified nothing — species I of D0116's taxonomy, installed by the fix for
    # a publication, in the configuration nobody runs locally. So the pins are counted
    # and the total is compared against an expectation that does NOT come from
    # concepts/: deriving 13 from concepts/*.yaml lets a truncated registry agree with
    # itself. It comes from governance/policy.yaml, which the degraded path does not
    # also skip and which the custody floor already covers (required_signatures, so it
    # cannot be edited without an owner re-signature).
    pins_seen = pins_by_bytes + pins_by_pin
    policy_path = root / "governance" / "policy.yaml"
    if not policy_path.exists():
        fail.add(
            "governance/policy.yaml is missing, so the citation-pin expectation cannot be "
            "read — a registry check with no expectation to meet is the vacuous pass this "
            "count exists to prevent (D0115)"
        )
    else:
        expected_pins = (load_yaml(policy_path).get("concept_registry") or {}).get(
            "expected_citation_pins"
        )
        if not isinstance(expected_pins, int):
            fail.add(
                "governance/policy.yaml names no integer "
                "concept_registry.expected_citation_pins — see D0115: the expectation is "
                "owner-signed policy precisely so a truncated concepts/ cannot supply it"
            )
        elif pins_seen != expected_pins:
            fail.add(
                f"citation pins accounted for = {pins_seen} "
                f"({pins_by_bytes} by bytes, {pins_by_pin} by pin), but "
                f"governance/policy.yaml expects {expected_pins}. Either a concept record "
                "is missing from this tree, or the registry changed and the owner-signed "
                "expectation was not updated with it"
            )

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

    return fail.finish(
        f"{len(record_paths)} records, {pins_by_bytes} pin(s) verified by bytes + "
        f"{pins_by_pin} by pin, artifacts complete, CONCEPTS.md fresh"
    )


if __name__ == "__main__":
    sys.exit(main())
