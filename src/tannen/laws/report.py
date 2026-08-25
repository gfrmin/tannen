"""`tannen laws report` — evidence freshness for the current descriptors (BRIEF §5.11).

Green means: for every law in the milestone's set, the store holds a passing evidence
record whose descriptor is the law's descriptor *right now*. Because the descriptor
addresses both the frozen law file and the implementation tree, a record cannot
survive an edit to either — staleness is arithmetic, not a judgement call.

**Frozen-but-not-yet-implemented is a real state, and the report has to say so.** The
frozen-oracle protocol (BRIEF §8) freezes a milestone's laws *before* its implementation
exists, so from the M1 freeze onward there is always a milestone whose laws are frozen and
whose evidence cannot exist yet. Reporting those as STALE was wrong twice over: it made
`make verify` red for the whole of every Session B — halting before lint-imports and the
custodian, so the custody floor went unchecked — and it said "the law file or the
implementation moved since the last run" about laws that never had an implementation to
move.

A milestone is **PENDING** iff *no* law in it has any evidence record at all, and PENDING
laws do not fail the report. The rule is arithmetic and has no builder-editable knob:

  * one law in the milestone earns a record  ->  the milestone is LIVE, and every law in it
    that lacks fresh evidence is STALE and fails. A half-implemented milestone is red.
  * every law fresh                          ->  green, which is the definition of done.
  * nothing touched at all                   ->  pending, and visibly so in the output.

So this cannot hide a regression: the only way to be pending is to have produced no
evidence whatsoever for that milestone, and the first law that runs ends it.
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
PENDING = "pending"

_MARKS = {
    FRESH: "ok",
    STALE: "STALE",
    FAILING: "FAIL",
    CONFLICTING: "FLAKY",
    PENDING: "frozen",
}

#: Statuses that do not fail the report. PENDING is here because a frozen milestone with no
#: implementation yet is the protocol working, not a defect (see the module docstring).
_PASSING = frozenset({FRESH, PENDING})


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

    # A milestone is LIVE once any law in it has produced any record at all; until then it
    # is frozen-and-unimplemented. Read off the records, so there is nothing to configure.
    live = {label for label, _ in by_law}

    subject = implementation_subject(root)
    laws: list[dict[str, Any]] = []
    pending_milestones: list[str] = []
    for milestone in wanted:
        label = milestone_label(milestone)
        if label not in live:
            pending_milestones.append(label)
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
                "status": STALE if label in live else PENDING,
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
        "pending_milestones": pending_milestones,
        "unknown_milestones": unknown,
        "evidence_root": str(evidence.store.root),
        "laws": laws,
        "problems": problems,
        "ok": bool(laws)
        and not unknown
        and not problems
        and all(law["status"] in _PASSING for law in laws),
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
    pending = [law["law_id"] for law in report["laws"] if law["status"] == PENDING]
    lines.append("")
    if not report["laws"]:
        lines.append("no laws discovered — nothing to attest")
    if pending:
        lines.append(
            f"FROZEN, NOT YET IMPLEMENTED — {', '.join(report['pending_milestones'])}: "
            f"{len(pending)} law(s) are frozen ahead of their implementation and have no "
            "evidence yet (BRIEF §8 frozen-oracle protocol). The first law of a milestone "
            "that runs ends this state, after which every law in it must carry fresh "
            "evidence or the report fails."
        )
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
        fresh = len(report["laws"]) - len(pending)
        summary = f"OK — {fresh} law(s) carry fresh passing evidence"
        lines.append(summary + (f"; {len(pending)} frozen and awaiting implementation." if pending else "."))
    return "\n".join(lines)
