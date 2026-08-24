"""The law runner and the evidence stream (BRIEF P6, §6; `docs/specs/m0.md` §5–§6).

Effectful shell, outside `tannen.kernel` by design: it reads law files, writes evidence
records, and reads the runner's wall clock — none of which the kernel may do.
"""

from __future__ import annotations

from tannen.laws.discovery import (
    discover_laws,
    find_root,
    implementation_subject,
    law_descriptor,
    milestone_label,
    milestones,
)
from tannen.laws.evidence import EvidenceStore, build_record, validate_record
from tannen.laws.report import build_report, render

__all__ = [
    "EvidenceStore",
    "build_record",
    "build_report",
    "discover_laws",
    "find_root",
    "implementation_subject",
    "law_descriptor",
    "milestone_label",
    "milestones",
    "render",
    "validate_record",
]
