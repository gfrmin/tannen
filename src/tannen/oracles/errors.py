"""The refusals `tannen.oracles` raises, each by name (docs/specs/m4.md §1).

The first five are the spec's. The rest name the ways a caller, a spec or the world can be
wrong in a shape no capture could hold; each is refused before anything reaches a caller,
because a value that entered by a side door would be a value no capture holds (BRIEF P1).
"""

from __future__ import annotations

__all__ = [
    "BudgetError",
    "CaptureConflict",
    "CaptureWriteFailed",
    "MalformedResponse",
    "NotACapture",
    "NovelInvocationRefused",
    "RequestError",
    "SpecError",
    "SpendDenied",
    "UndeclaredReproducibility",
]


class NovelInvocationRefused(Exception):
    """No capture answers this question, and the context is replay-only (BRIEF §5.10)."""


class SpendDenied(Exception):
    """SpendGuard said no: default-deny, a unit mismatch, a zero or exhausted ceiling, or a
    store whose spend cannot be folded (docs/specs/m4.md §4)."""


class CaptureWriteFailed(Exception):
    """A reservation or a capture was not written, so nothing may be read (BRIEF P1)."""


class UndeclaredReproducibility(ValueError):
    """An oracle whose class is not one of `CLASSES` cannot be built [cites: pkm-determinism]."""


class CaptureConflict(Exception):
    """Two captures answer one (descriptor, input key): nothing can say which is the record."""


class BudgetError(ValueError):
    """A budget that is not an exact envelope: a non-integer, negative or boolean ceiling, or
    a file that is not a mapping. (A budget that merely names no scope or unit loads, and
    authorises nothing.)"""


class RequestError(ValueError):
    """A request that is not exactly its kind's variable part (Fetch `uri`, LLM `messages`,
    Clock `label`)."""


class SpecError(ValueError):
    """An oracle spec that cannot be built, or cannot price the call it is asked to make."""


class MalformedResponse(ValueError):
    """The world answered in a shape no `capture/1` can hold. The call happened, so its
    reservation stands at its worst case; no capture is written and no value escapes."""


class NotACapture(ValueError):
    """`read` was handed a ref whose value is not a `capture/1`."""
