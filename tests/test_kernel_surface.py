"""Kernel behaviour chosen during implementation, beyond what the frozen laws pin.

The M0 law suite is the contract; these are the decisions the contract left open, each
bound to the decision record that made it (D0038, D0039, D0046). They live outside
`tests/laws/` deliberately: they are not laws, they emit no evidence, and they may be
edited — unlike anything under the freeze.
"""

from __future__ import annotations

import hashlib
import os
from decimal import Decimal

import pytest

from tannen.kernel import descriptor, encoding, refs
from tannen.store import IntegrityError, MissingRef, Store


# --------------------------------------------------------------- encoding pins (D0039)


def test_decimals_beyond_context_precision_survive_exactly() -> None:
    """The minimal form is computed from the digit tuple, never `Decimal.normalize()`.

    `normalize()` rounds to the active context precision (28 by default), so a 35-digit
    value would come back short — silently, and only for values long enough to matter.
    """
    value = Decimal("1.2345678901234567890123456789012345E-9")
    assert len(value.as_tuple().digits) > 28
    encoded = encoding.encode_canonical(value)
    assert encoding.decode_canonical(encoded) == value
    assert encoded == b'{"$decimal":"0.0000000012345678901234567890123456789012345"}'
    assert encoding.content_address(value) == encoding.content_address(Decimal(str(value)))


@pytest.mark.parametrize(
    "spelling, expected",
    [
        (Decimal("1.50"), b'{"$decimal":"1.5"}'),
        (Decimal("0.00"), b'{"$decimal":"0"}'),
        (Decimal("-0.0"), b'{"$decimal":"0"}'),
        (Decimal("1E+2"), b'{"$decimal":"100"}'),
        (Decimal("-1.50"), b'{"$decimal":"-1.5"}'),
        (Decimal("1E-7"), b'{"$decimal":"0.0000001"}'),
    ],
)
def test_decimal_minimal_form(spelling: Decimal, expected: bytes) -> None:
    assert encoding.encode_canonical(spelling) == expected


def test_decode_does_not_normalise() -> None:
    """Decode is lenient; canonicalisation is encode's job alone (D0031, D0039).

    So decode can hand back a value that encode then *refuses* — two keys that are
    distinct in the input and collide under NFC. That asymmetry is deliberate: the
    encoder is the only gate, and it refuses rather than merging.
    """
    decoded = encoding.decode_canonical(b'{"e\\u0301":1,"\\u00e9":2}')
    assert len(decoded) == 2
    with pytest.raises(encoding.CanonicalEncodingError, match="forge identity"):
        encoding.encode_canonical(decoded)
    assert encoding.decode_canonical(b'"he\\u0301llo"') == "héllo"


def test_cycles_are_refused_by_name_not_by_stack_overflow() -> None:
    cyclic: list = [1]
    cyclic.append(cyclic)
    with pytest.raises(encoding.CanonicalEncodingError, match="cyclic"):
        encoding.encode_canonical(cyclic)


def test_encoding_error_names_the_path_and_the_door() -> None:
    with pytest.raises(encoding.CanonicalEncodingError) as excinfo:
        encoding.encode_canonical({"a": [0, {"b": 1.5}]})
    message = str(excinfo.value)
    assert "$.a[1].b" in message and "Lossy" in message


# ------------------------------------------------------------- the ref grammar (D0038)


@pytest.mark.parametrize(
    "candidate",
    ["", "sha256:", "sha256:" + "A" * 64, "sha256:" + "a" * 63, "sha1:" + "a" * 64, "a" * 64, None],
)
def test_ref_hex_refuses_everything_outside_the_grammar(candidate: object) -> None:
    assert not refs.is_ref(candidate)
    with pytest.raises(refs.RefError):
        refs.ref_hex(candidate)  # type: ignore[arg-type]


def test_one_home_for_the_grammar() -> None:
    """Every ref the system emits is minted by `refs`, so the grammar has one home."""
    data = b"source bytes"
    assert refs.ref_for_bytes(data) == f"sha256:{hashlib.sha256(data).hexdigest()}"
    assert encoding.content_address({"a": 1}) == refs.ref_for_bytes(
        encoding.encode_canonical({"a": 1})
    )
    assert refs.is_ref(descriptor.descriptor_id(
        kind="transform", name="clean",
        code_hash="sha256:" + "a" * 64, params_hash="sha256:" + "b" * 64,
    ))


# ------------------------------------------------------------- descriptors (D0038)


def test_descriptor_id_refuses_hashes_that_are_not_refs() -> None:
    with pytest.raises(refs.RefError):
        descriptor.descriptor_id(
            kind="transform", name="clean", code_hash="deadbeef", params_hash="sha256:" + "b" * 64
        )


@pytest.mark.parametrize(
    "module_path, name, seq",
    [("pipelines@x", "clean", 0), ("pipelines", "clean@2", 0), ("pipelines", "a/b", 0),
     ("", "clean", 0), ("pipelines", "clean", -1), ("pipelines", "clean", True)],
)
def test_derive_label_refuses_ambiguous_components(module_path: str, name: str, seq: int) -> None:
    with pytest.raises(descriptor.DescriptorError):
        descriptor.derive_label(module_path, name, seq)


# ------------------------------------------------------------------- the store


def test_iter_refs_enumerates_without_verifying(tmp_path) -> None:
    store = Store(tmp_path / "s")
    written = {store.put_bytes(b"a"), store.put_bytes(b"b"), store.put_value({"k": 1})}
    assert set(store.iter_refs()) == written


def test_missing_ref_is_a_key_error(tmp_path) -> None:
    store = Store(tmp_path / "s")
    with pytest.raises(MissingRef):
        store.get_bytes("sha256:" + "0" * 64)


def test_integrity_is_enforced_on_read_not_by_permissions(tmp_path) -> None:
    """D0046: object files stay writable; the store's guarantee is verify-on-read.

    Read-only files would be a second, weaker mechanism — weaker because it protects
    only against this process, and because any restore or copy silently drops it.
    """
    store = Store(tmp_path / "s")
    ref = store.put_bytes(b"pristine")
    victim = next(p for p in (tmp_path / "s").rglob("*") if p.is_file())
    assert os.access(victim, os.W_OK)
    victim.write_bytes(b"tampered")
    with pytest.raises(IntegrityError):
        store.get_bytes(ref)
    assert store.has(ref)  # presence is not integrity, and does not claim to be


def test_store_refuses_a_malformed_ref_rather_than_answering_false(tmp_path) -> None:
    store = Store(tmp_path / "s")
    with pytest.raises(refs.RefError):
        store.has("not-a-ref")
