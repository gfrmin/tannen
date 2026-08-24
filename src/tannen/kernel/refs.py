"""Content-address refs — the one home for the pinned ref grammar.

`sha256:<64 lowercase hex>` [cites: provenance-ref-grammar]: pkm SPEC-PRINCIPLES §1's
hash-prefix discipline, Renavon ADR-002's typed opaque refs. Every ref this system
emits is minted here, so the grammar cannot drift between the encoder, the store and
the descriptor module (BRIEF §2: restatement is duplication; duplication is drift).

Pure: hashing is not IO (BRIEF §5.3, contract `kernel-no-io`).
"""

from __future__ import annotations

import hashlib
import re

__all__ = ["REF_RE", "RefError", "ref_for_bytes", "ref_hex", "is_ref"]

ALGORITHM = "sha256"
REF_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class RefError(ValueError):
    """A string was used as a ref but does not match the pinned grammar."""


def ref_for_bytes(data: bytes) -> str:
    """The ref of raw bytes — source identity, computable outside the system."""
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError(f"refs address bytes, not {type(data).__name__}")
    return f"{ALGORITHM}:{hashlib.sha256(data).hexdigest()}"


def ref_hex(ref: str) -> str:
    """The hex digest of a ref, refusing anything outside the grammar by name."""
    if not isinstance(ref, str) or not REF_RE.match(ref):
        raise RefError(f"not a ref in the pinned grammar 'sha256:<64 lowercase hex>': {ref!r}")
    return ref.split(":", 1)[1]


def is_ref(candidate: object) -> bool:
    return isinstance(candidate, str) and REF_RE.match(candidate) is not None
