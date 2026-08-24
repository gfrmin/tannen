"""M0 laws L0.1–L0.4, L0.8 — canonical encoding (docs/specs/m0.md §2, §5).

FROZEN at m0-laws-freeze. Pre-implementation this module is a visible skip
(importorskip); M0 completion requires it green with zero skips. Wrong laws are
never edited: record the defect, freeze a superseding file (CLAUDE.md).
"""

from __future__ import annotations

import json
import subprocess
import sys
import unicodedata
from decimal import Decimal
from pathlib import Path

import pytest
from hypothesis import given, strategies as st

encoding = pytest.importorskip(
    "tannen.kernel.encoding",
    reason="M0 kernel not implemented yet (law suite frozen ahead of Session B)",
)

REPO_ROOT = Path(__file__).resolve().parents[3]
GOLDEN_VECTORS = json.loads(
    (Path(__file__).parent / "golden-vectors.json").read_text(encoding="utf-8")
)

# The encodable value domain (m0.md §2), generated already NFC-normalised: the
# encoder normalises to NFC, so NFC values are the fixed points on which decode is
# an exact inverse; convergence FROM non-NFC input is law-tested by example below.
nfc_text = st.text().map(lambda s: unicodedata.normalize("NFC", s))
scalars = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    nfc_text,
    st.decimals(allow_nan=False, allow_infinity=False),
)
values = st.recursive(
    scalars,
    lambda children: st.one_of(
        st.lists(children, max_size=8),
        st.dictionaries(nfc_text.filter(lambda k: k != "$decimal"), children, max_size=8),
    ),
    max_leaves=25,
)


# L0.1 — determinism: equal values ⇒ identical canonical bytes.
@given(values)
def test_l0_1_encoding_is_deterministic(value) -> None:
    assert encoding.encode_canonical(value) == encoding.encode_canonical(value)


# L0.2 — golden conformance: authored vectors decode, re-encode byte-identically,
# and carry exactly the recorded content address.
@pytest.mark.parametrize("vector", GOLDEN_VECTORS, ids=[v["name"] for v in GOLDEN_VECTORS])
def test_l0_2_golden_conformance(vector: dict) -> None:
    data = vector["canonical"].encode("utf-8")
    value = encoding.decode_canonical(data)
    assert encoding.encode_canonical(value) == data
    assert encoding.content_address(value) == vector["address"]


# L0.3 — the door: everything outside the value domain is refused by name.
@pytest.mark.parametrize(
    "bad",
    [
        1.5,                                   # bare float
        [1.5],                                 # float nested in a list
        {"a": 1.5},                            # float nested in a map
        float("nan"),
        float("inf"),
        b"bytes",                              # bytes are sources, not values
        (1, 2),                                # tuples are not values
        {1: "a"},                              # non-str key
        {"$decimal": "1.5"},                   # reserved tag key in a user map
        {"$decimal": "1.5", "x": 1},           # reserved tag key, mixed
        {"e\u0301": 1, "\u00e9": 2},   # NFD vs NFC spellings of e-acute collide after NFC
        Decimal("NaN"),
        Decimal("Infinity"),
    ],
    ids=[
        "float", "float-in-list", "float-in-map", "nan", "inf", "bytes", "tuple",
        "int-key", "reserved-key", "reserved-key-mixed", "nfc-key-collision",
        "decimal-nan", "decimal-inf",
    ],
)
def test_l0_3_door_refuses_by_name(bad) -> None:
    with pytest.raises(encoding.CanonicalEncodingError):
        encoding.encode_canonical(bad)


@pytest.mark.parametrize(
    "data",
    [
        b"1.5",                                # float literal
        b"[1e3]",                              # exponent float literal
        b'{"$decimal":5}',                     # malformed tag payload
        b'{"$decimal":"1.5","x":1}',           # tag key mixed into a map
        b'{"a":1,"a":2}',                      # duplicate keys
        b"not json",
    ],
    ids=["float-literal", "exponent-literal", "bad-tag-payload", "tag-mixed", "dup-keys", "garbage"],
)
def test_l0_3_decode_door(data: bytes) -> None:
    with pytest.raises(encoding.CanonicalEncodingError):
        encoding.decode_canonical(data)


# L0.4 — round-trip: decode inverts encode, at identity level.
@given(values)
def test_l0_4_round_trip(value) -> None:
    encoded = encoding.encode_canonical(value)
    decoded = encoding.decode_canonical(encoded)
    assert decoded == value
    assert encoding.encode_canonical(decoded) == encoded


def test_l0_4_nfc_convergence() -> None:
    nfd, nfc = "he\u0301llo", "h\u00e9llo"
    assert nfd != nfc
    assert encoding.encode_canonical(nfd) == encoding.encode_canonical(nfc)
    assert encoding.decode_canonical(encoding.encode_canonical(nfd)) == nfc


def test_l0_4_decimal_spellings_converge() -> None:
    assert encoding.content_address(Decimal("1.50")) == encoding.content_address(Decimal("1.5"))
    assert encoding.encode_canonical(Decimal("1E+2")) == b'{"$decimal":"100"}'
    assert encoding.encode_canonical(Decimal("-0")) == b'{"$decimal":"0"}'


def test_l0_4_decode_is_lenient_outside_the_canonical_image() -> None:
    # Canonicalisation is encode's job alone: decode accepts strict float-free JSON
    # in any layout (m0.md §2, pinned per BRIEF §4's ambiguity rule).
    assert encoding.decode_canonical(b'{ "b" : 1 , "a" : 2 }') == {"a": 2, "b": 1}


def test_l0_4_bool_int_identities_distinct() -> None:
    assert encoding.encode_canonical(True) == b"true"
    assert encoding.encode_canonical(1) == b"1"


# L0.8 — fresh-interpreter replay: a new process with a randomised hash seed
# reproduces every golden byte-identically (L1's mechanism at M0 scope).
_REPLAY = """
import json
from tannen.kernel.encoding import content_address, decode_canonical, encode_canonical
for v in json.load(open("tests/laws/m0/golden-vectors.json", encoding="utf-8")):
    data = v["canonical"].encode("utf-8")
    value = decode_canonical(data)
    assert encode_canonical(value) == data, v["name"]
    assert content_address(value) == v["address"], v["name"]
print("L0.8-OK")
"""


def test_l0_8_fresh_interpreter_replay() -> None:
    result = subprocess.run(
        [sys.executable, "-c", _REPLAY],
        cwd=REPO_ROOT,
        env={"PYTHONHASHSEED": "random", "PATH": ""},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "L0.8-OK" in result.stdout
