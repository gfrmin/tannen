"""`tannen.oracles` — the one IO doorway (BRIEF §5.3, §5.7; docs/specs/m4.md §1–§4).

All nondeterminism enters here, and is captured immutably before anything reads it (BRIEF
P1). An oracle is declared (`Fetch`, `LLM`, `Clock`) with its full effective spec and its
reproducibility class; an invocation context (`Oracles`) answers each question from its
capture if one exists, refuses a novel one unless it was opened with `mode=SPEND`, and then
admits it only under SpendGuard against a loaded budget.

The real transports are in `tannen.oracles.transports` and are not re-exported: a caller
names the one it means.
"""

from __future__ import annotations

from tannen.oracles.budget import Budget, load_budget
from tannen.oracles.context import (
    CAPTURE_TAG,
    REPLAY,
    RESERVATION_TAG,
    SPEND,
    Mode,
    Oracles,
)
from tannen.oracles.errors import (
    BudgetError,
    CaptureConflict,
    CaptureWriteFailed,
    MalformedResponse,
    NotACapture,
    NovelInvocationRefused,
    RequestError,
    SpecError,
    SpendDenied,
    UndeclaredReproducibility,
)
from tannen.oracles.identity import CLASSES, LLM, ORACLE_TAG, Clock, Fetch, Oracle, input_key

__all__ = [
    "Budget",
    "BudgetError",
    "CAPTURE_TAG",
    "CLASSES",
    "CaptureConflict",
    "CaptureWriteFailed",
    "Clock",
    "Fetch",
    "LLM",
    "MalformedResponse",
    "Mode",
    "NotACapture",
    "NovelInvocationRefused",
    "ORACLE_TAG",
    "Oracle",
    "Oracles",
    "REPLAY",
    "RESERVATION_TAG",
    "RequestError",
    "SPEND",
    "SpecError",
    "SpendDenied",
    "UndeclaredReproducibility",
    "input_key",
    "load_budget",
]
