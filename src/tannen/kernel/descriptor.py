"""Descriptor identity — `docs/specs/m0.md` §4, frozen at `m0-laws-freeze`.

`H(kind, name, code_hash, params_hash)` with a human label derived automatically, so
there is no "forgot to bump" state (BRIEF §5.2). Aligned with the pkm event tuple:
what would make this a different event belongs in the hash [cites: pkm-event-identity]
[cites: pkm-determinism]. Law L0.9 is the normative statement.

Pure (contract `kernel-no-io`).
"""

from __future__ import annotations

from tannen.kernel.encoding import content_address
from tannen.kernel.refs import RefError, is_ref

__all__ = ["DescriptorError", "descriptor_id", "derive_label"]

#: Characters that would make a derived label ambiguous about its own parse.
_LABEL_SEPARATORS = ("/", "@")


class DescriptorError(ValueError):
    """A descriptor component is outside its domain."""


def descriptor_id(kind: str, name: str, code_hash: str, params_hash: str) -> str:
    """The content address of the canonical 4-tuple (L0.9).

    The two hashes are themselves refs in the pinned grammar, checked here: a
    descriptor built over a non-ref would mint an identity that no store can resolve.
    """
    for label, component in (("kind", kind), ("name", name)):
        if not isinstance(component, str) or not component:
            raise DescriptorError(f"{label} must be a non-empty str, got {component!r}")
    for label, component in (("code_hash", code_hash), ("params_hash", params_hash)):
        if not is_ref(component):
            raise RefError(
                f"{label} must be a ref in the pinned grammar 'sha256:<64 lowercase hex>', "
                f"got {component!r}"
            )
    return content_address(
        {"kind": kind, "name": name, "code_hash": code_hash, "params_hash": params_hash}
    )


def derive_label(module_path: str, name: str, seq: int) -> str:
    """`<module_path>/<name>@<seq>` — a pure function of its inputs (L0.9, BRIEF §5.2).

    `seq` is the count of distinct prior descriptors for `(module_path, name)`; the
    registering decorator supplies it at M1. Separators are refused inside the
    components so distinct inputs can never derive one label.
    """
    for label, component in (("module_path", module_path), ("name", name)):
        if not isinstance(component, str) or not component:
            raise DescriptorError(f"{label} must be a non-empty str, got {component!r}")
        for separator in _LABEL_SEPARATORS:
            if separator in component:
                raise DescriptorError(
                    f"{label} may not contain {separator!r}: it separates label components, "
                    f"so allowing it would let two distinct descriptors derive one label"
                )
    if isinstance(seq, bool) or not isinstance(seq, int) or seq < 0:
        raise DescriptorError(f"seq must be a non-negative int, got {seq!r}")
    return f"{module_path}/{name}@{seq}"
