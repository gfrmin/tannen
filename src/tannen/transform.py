"""The registering decorator — the only way to put a function in a graph
(docs/specs/m1.md §8; BRIEF §5.1, §5.2).

A shell module, deliberately outside `tannen.kernel`: it reads the decorated function's
source to compute `code_hash`, and reading a file is IO however convenient it would be to
pretend otherwise.

    @transform(kind=..., params=..., layer=None)

attaches `code_hash` (the ref of the source text — `inspect.getsource`, dedented,
LF-normalised, decorator lines included), `params_hash` (the content address of `params`),
`label` (M0's `derive_label(module, name, seq)`, `seq` counting prior registrations of that
`(module, name)`), `descriptor_id` (M0's `descriptor_id` over the four components) and the
optional declared `layer`. Hashing the source means a comment change mints a new
descriptor — deliberately (D0084). A lambda cannot be registered; registering the same
function object twice is refused; an unregistered function is refused by name.
"""

from __future__ import annotations

import inspect
import textwrap
from collections.abc import Callable
from typing import Any

from tannen.kernel.descriptor import derive_label, descriptor_id
from tannen.kernel.encoding import content_address
from tannen.kernel.layers import Layer
from tannen.kernel.refs import ref_for_bytes

__all__ = ["TransformError", "descriptor_of", "source_text", "transform"]


class TransformError(ValueError):
    """A registration the decorator refuses, or a function that was never registered."""


#: (module, name) -> number of registrations so far; the next label's `seq`.
_SEQ: dict[tuple[str, str], int] = {}


def source_text(fn: Callable[..., Any]) -> str:
    """The bytes a callable is hashed by: `inspect.getsource`, dedented, LF-normalised.

    Public since D0197 because `tannen.incremental` needs the same rule for the code a
    DeltaNode names, and BRIEF §2 wants one implementation of it rather than two."""
    try:
        source = inspect.getsource(fn)
    except (OSError, TypeError) as exc:
        raise TransformError(
            f"{getattr(fn, '__qualname__', fn)!r}: source text is unavailable, so it cannot be "
            "hashed and cannot enter a graph (BRIEF §5.1)"
        ) from exc
    return textwrap.dedent(source).replace("\r\n", "\n").replace("\r", "\n")


def transform(
    *, kind: str, params: Any, layer: Layer | None = None
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    if not isinstance(kind, str) or not kind:
        raise TransformError("kind must be a non-empty str")
    if layer is not None and not isinstance(layer, Layer):
        raise TransformError(f"layer must be a tannen.kernel.layers.Layer member or None, not {layer!r}")
    params_hash = content_address(params)  # CanonicalEncodingError: params must be a value

    def register(fn: Callable[..., Any]) -> Callable[..., Any]:
        if not inspect.isfunction(fn):
            raise TransformError(f"{fn!r} is not a plain function")
        if fn.__name__ == "<lambda>":
            raise TransformError("a lambda has no name to derive a label from (§8)")
        if getattr(fn, "is_transform", False):
            raise TransformError(
                f"{fn.__qualname__} is already registered as {fn.label}; a function has one "
                "descriptor, and silently shadowing it would leave two claiming it"
            )
        code_hash = ref_for_bytes(source_text(fn).encode("utf-8"))
        pair = (fn.__module__, fn.__name__)
        seq = _SEQ.get(pair, 0)
        _SEQ[pair] = seq + 1
        fn.kind = kind
        fn.params = params
        fn.layer = layer
        fn.code_hash = code_hash
        fn.params_hash = params_hash
        fn.label = derive_label(fn.__module__, fn.__name__, seq)
        fn.descriptor_id = descriptor_id(
            kind=kind, name=fn.__name__, code_hash=code_hash, params_hash=params_hash
        )
        fn.is_transform = True
        return fn

    return register


def descriptor_of(fn: Any) -> str:
    """The descriptor of a registered transform; an unregistered function is refused by name."""
    if not getattr(fn, "is_transform", False):
        raise TransformError(
            f"{getattr(fn, '__qualname__', fn)!r} is not a registered transform — an unhashed "
            "function cannot enter a graph (BRIEF §5.1)"
        )
    return fn.descriptor_id
