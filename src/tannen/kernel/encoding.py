"""Canonical encoding — `docs/specs/m0.md` §2, frozen at `m0-laws-freeze`.

Canonical JSON (UTF-8, NFC, sorted keys, exact integers, tagged decimals, no floats),
following the production `canonical_json` precedent pinned in decision D0031. Laws
L0.1–L0.4 and L0.8 are the normative statement of this module's behaviour; the prose
here does not restate them.

Pure (BRIEF §5.3, contract `kernel-no-io`): no filesystem, no clock, no network.
"""

from __future__ import annotations

import json
import unicodedata
from decimal import Decimal
from typing import Any

from tannen.kernel.refs import ref_for_bytes

__all__ = [
    "CanonicalEncodingError",
    "DECIMAL_TAG",
    "content_address",
    "decode_canonical",
    "encode_canonical",
]

DECIMAL_TAG = "$decimal"

#: Tag namespace refused by name in user maps (the door discipline, m0.md §2).
#: Future tags extend this set only with a descriptor bump.
RESERVED_KEYS = frozenset({DECIMAL_TAG})


class CanonicalEncodingError(ValueError):
    """A value is outside the encodable domain, or bytes are outside the decodable one.

    Raised by name rather than coerced: no silent defaults, no silent lossiness
    [cites: exactness-and-the-door].
    """


# --------------------------------------------------------------------------- encode


def encode_canonical(value: Any) -> bytes:
    """The canonical bytes of a value. Equal values encode identically (L0.1)."""
    return json.dumps(
        _canonicalise(value, "$", ()),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
        check_circular=False,  # _canonicalise already refuses cycles, with a path
    ).encode("utf-8")


def content_address(value: Any) -> str:
    """The ref of a value: `sha256:<hex>` over its canonical bytes (L0.7)."""
    return ref_for_bytes(encode_canonical(value))


def _canonicalise(value: Any, path: str, stack: tuple[int, ...]) -> Any:
    """Map a value onto the JSON-ready image the encoder dumps, or refuse it by name."""
    # bool before int: True is not 1 in the identity sense (L0.4).
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise CanonicalEncodingError(
                f"{path}: {value} is not a finite decimal; NaN and Infinity have no canonical form"
            )
        return {DECIMAL_TAG: _decimal_text(value)}
    if isinstance(value, (list, dict)):
        if id(value) in stack:
            raise CanonicalEncodingError(f"{path}: cyclic structure; values are finite trees")
        stack = stack + (id(value),)
        if isinstance(value, list):
            return [_canonicalise(item, f"{path}[{i}]", stack) for i, item in enumerate(value)]
        return _canonicalise_map(value, path, stack)
    raise CanonicalEncodingError(
        f"{path}: {type(value).__name__} is not an encodable value "
        f"(the domain is None/bool/int/str/Decimal/list/dict[str]; "
        f"floats enter only through the declared Lossy door, which arrives at M1)"
    )


def _canonicalise_map(value: dict, path: str, stack: tuple[int, ...]) -> dict:
    out: dict[str, Any] = {}
    for key, item in value.items():
        if not isinstance(key, str) or isinstance(key, bool):
            raise CanonicalEncodingError(
                f"{path}: map keys must be str, not {type(key).__name__} ({key!r})"
            )
        normalised = unicodedata.normalize("NFC", key)
        if normalised in RESERVED_KEYS:
            raise CanonicalEncodingError(
                f"{path}: {normalised!r} is a reserved tag key and is refused by name, "
                "never silently escaped"
            )
        if normalised in out:
            raise CanonicalEncodingError(
                f"{path}: keys {key!r} and its NFC twin normalise to the same key "
                f"{normalised!r}; merging them would forge identity"
            )
        out[normalised] = _canonicalise(item, f"{path}.{normalised}", stack)
    return out


def _decimal_text(value: Decimal) -> str:
    """The exponent-free minimal form of a finite decimal (m0.md §2).

    Computed from the digit tuple, never through `Decimal.normalize()`: normalize
    rounds to the active context precision (28 by default), which would silently
    lose digits for values Hypothesis routinely generates — exactness is the point
    [cites: exactness-and-the-door].
    """
    sign, digits, exponent = value.as_tuple()
    if not any(digits):
        return "0"  # every spelling of zero, sign included, has one encoding
    coefficient = list(digits)
    while len(coefficient) > 1 and coefficient[-1] == 0:
        coefficient.pop()
        exponent += 1
    text = "".join(str(d) for d in coefficient)
    if exponent >= 0:
        text += "0" * exponent
    elif -exponent >= len(text):
        text = "0." + "0" * (-exponent - len(text)) + text
    else:
        text = text[:exponent] + "." + text[exponent:]
    return ("-" if sign else "") + text


# --------------------------------------------------------------------------- decode


def decode_canonical(data: bytes) -> Any:
    """Invert the encoding (L0.4).

    Lenient outside the canonical image — layout and key order are encode's job alone
    — but strict about anything that would change identity: float literals, duplicate
    keys, malformed tags (D0031).
    """
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise CanonicalEncodingError(
            f"canonical bytes are bytes, not {type(data).__name__}"
        )
    try:
        text = bytes(data).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CanonicalEncodingError(f"canonical bytes are UTF-8: {exc}") from exc
    try:
        return json.loads(
            text,
            parse_float=_refuse_float,
            parse_constant=_refuse_constant,
            object_pairs_hook=_decode_object,
        )
    except json.JSONDecodeError as exc:
        raise CanonicalEncodingError(f"not canonical JSON: {exc}") from exc


def _refuse_float(literal: str) -> Any:
    raise CanonicalEncodingError(
        f"float literal {literal!r}: no float is decodable; exact values are integers "
        f'or tagged decimals ({{"{DECIMAL_TAG}": "..."}})'
    )


def _refuse_constant(name: str) -> Any:
    raise CanonicalEncodingError(f"{name} is not a canonical JSON value")


def _decode_object(pairs: list[tuple[str, Any]]) -> Any:
    keys = [key for key, _ in pairs]
    if len(set(keys)) != len(keys):
        duplicates = sorted({key for key in keys if keys.count(key) > 1})
        raise CanonicalEncodingError(
            f"duplicate object keys {duplicates}: which one wins is not a decision "
            "the decoder gets to make"
        )
    if DECIMAL_TAG in keys:
        if len(pairs) != 1:
            raise CanonicalEncodingError(
                f"{DECIMAL_TAG!r} is a reserved tag key: a tagged decimal is a "
                f"single-key object, got keys {sorted(keys)}"
            )
        payload = pairs[0][1]
        if not isinstance(payload, str):
            raise CanonicalEncodingError(
                f"{DECIMAL_TAG!r} payload must be a string, got {type(payload).__name__}"
            )
        try:
            decimal = Decimal(payload)
        except ArithmeticError as exc:
            raise CanonicalEncodingError(f"{DECIMAL_TAG!r} payload {payload!r} is not a decimal") from exc
        if not decimal.is_finite():
            raise CanonicalEncodingError(
                f"{DECIMAL_TAG!r} payload {payload!r} is not finite; NaN and Infinity are not values"
            )
        return decimal
    return dict(pairs)
