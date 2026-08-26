"""`derivation_id` — the identity of one derivation (docs/specs/m1.md §8; BRIEF §4).

    derivation_id(transform_descriptor, input_ids) = H({"inputs": sorted(input_ids),
                                                        "transform": transform_descriptor})

Order-insensitive in the inputs (which order the caller held them in is not part of what
was derived); duplicates are kept (deriving from an input twice is a different derivation);
every component is a ref in the pinned grammar or the call is refused.
"""

from __future__ import annotations

from collections.abc import Iterable

from tannen.kernel.encoding import content_address
from tannen.kernel.refs import is_ref

__all__ = ["DerivationError", "derivation_id"]


class DerivationError(ValueError):
    """A descriptor or input outside the pinned ref grammar."""


def derivation_id(transform_descriptor: str, input_ids: Iterable[str]) -> str:
    if not is_ref(transform_descriptor):
        raise DerivationError(f"transform descriptor is not a ref: {transform_descriptor!r}")
    inputs = list(input_ids)
    bad = [ref for ref in inputs if not is_ref(ref)]
    if bad:
        raise DerivationError(f"input ids are refs in the pinned grammar; not: {bad!r}")
    return content_address({"inputs": sorted(inputs), "transform": transform_descriptor})
