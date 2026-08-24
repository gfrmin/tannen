"""`tannen laws report` — evidence freshness for the current descriptors (BRIEF §5.11).

Green means: for every law in the milestone's set, the store holds a passing evidence
record whose descriptor is the law's descriptor *right now*. Because the descriptor
addresses both the frozen law file and the implementation tree, a record cannot
survive an edit to either — staleness is arithmetic, not a judgement call.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tannen.laws.discovery import (
    discover_laws,
    implementation_subject,
    law_descriptor,
    milestone_label,
    milestones,
)
from tannen.laws.evidence import EvidenceStore

__all__ = ["FRESH", "build_report", "render"]

FRESH = "fresh"
STALE = "stale"
FAILING = "failing"
CONFLICTING = "conflicting"

_MARKS = {FRESH: "ok", STALE: "STALE", FAILING: "FAIL", CONFLICTING: "FLAKY"}


def build_report(root: Path, selected: list[str] | None = None) -> dict[str, Any]:
    available = milestones(root)
    wanted = [m for m in available if selected is None or m in {s.lower() for s in selected}]
    unknown = sorted({s.lower() for s in selected or []} - set(available))

    evidence = EvidenceStore(root)
    by_law: dict[tuple[str, str], list[tuple[str, dict]]] = {}
    problems: list[str] = []
    for ref, record, problem in evidence.scan():
        if problem == "not an evidence record":
            continue
        if problem is not None:
            problems.append(f"{ref}: {problem}")
            continue
        by_law.setdefault((record["milestone"], record["law_id"]), []).append((ref, record))

    subject = implementation_subject(root)
    laws: list[dict[str, Any]] = []
    for milestone in wanted:
        label = milestone_label(milestone)
        for law, modules in discover_laws(root, milestone).items():
            descriptor = law_descriptor(root, law, modules, subject=subject)
            matches = [
                (ref, record)
                for ref, record in by_law.get((label, law), [])
                if descriptor in record["descriptors"]
            ]
            entry: dict[str, Any] = {
                "law_id": law,
                "milestone": label,
                "descriptor": descriptor,
                "files": sorted(modules),
                "status": STALE,
                "evidence_ref": None,
                "run_at": None,
                "seed": None,
                "verdict": None,
            }
            if matches:
                verdicts = {record["verdict"] for _, record in matches}
                ref, record = max(matches, key=lambda pair: (pair[1]["run_at"], pair[0]))
                entry.update(
                    evidence_ref=ref,
                    run_at=record["run_at"],
                    seed=record["seed"],
                    verdict=record["verdict"],
                    runs=len(matches),
                    status=(
                        CONFLICTING if len(verdicts) > 1
                        else FRESH if record["verdict"] == "pass"
                        else FAILING
                    ),
                )
            laws.append(entry)

    return {
        "root": str(root),
        "milestones": wanted,
        "unknown_milestones": unknown,
        "evidence_root": str(evidence.store.root),
        "laws": laws,
        "problems": problems,
        "ok": bool(laws) and not unknown and not problems and all(l["status"] == FRESH for l in laws),
    }


def render(report: dict[str, Any]) -> str:
    lines = [
        f"tannen laws report — milestones: {', '.join(report['milestones']) or 'none'}",
        f"evidence store: {report['evidence_root']}",
        "",
        f"{'law':<8}{'state':<8}{'verdict':<9}{'seed':<26}{'run at':<34}descriptor",
    ]
    for law in report["laws"]:
        lines.append(
            f"{law['law_id']:<8}{_MARKS[law['status']]:<8}{law['verdict'] or '-':<9}"
            f"{(law['seed'] or '-'):<26}{(law['run_at'] or '-'):<34}{law['descriptor'][:23]}…"
        )
    stale = [law["law_id"] for law in report["laws"] if law["status"] == STALE]
    failing = [law["law_id"] for law in report["laws"] if law["status"] in (FAILING, CONFLICTING)]
    lines.append("")
    if not report["laws"]:
        lines.append("no laws discovered — nothing to attest")
    if stale:
        lines.append(
            f"NO FRESH EVIDENCE for {', '.join(stale)}: the law file or the implementation "
            "moved since the last run. Run `uv run pytest` and report again."
        )
    if failing:
        lines.append(f"EVIDENCE RECORDS A FAILURE for {', '.join(failing)}.")
    for problem in report["problems"]:
        lines.append(f"CORRUPT EVIDENCE — {problem}")
    for milestone in report["unknown_milestones"]:
        lines.append(f"unknown milestone: {milestone}")
    if report["ok"]:
        lines.append(f"OK — {len(report['laws'])} law(s) carry fresh passing evidence.")
    return "\n".join(lines)
