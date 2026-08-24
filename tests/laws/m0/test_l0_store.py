"""M0 laws L0.5–L0.7 — the write-once store (docs/specs/m0.md §3, §5).

FROZEN at m0-laws-freeze. Pre-implementation this module is a visible skip.
"""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

import pytest
from hypothesis import given, strategies as st

encoding = pytest.importorskip(
    "tannen.kernel.encoding",
    reason="M0 kernel not implemented yet (law suite frozen ahead of Session B)",
)
store_mod = pytest.importorskip(
    "tannen.store",
    reason="M0 store not implemented yet (law suite frozen ahead of Session B)",
)

REF_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@pytest.fixture()
def store(tmp_path: Path):
    return store_mod.Store(tmp_path / "store")


def tree_state(root: Path) -> list[tuple[str, bytes]]:
    return sorted(
        (str(p.relative_to(root)), p.read_bytes()) for p in root.rglob("*") if p.is_file()
    )


# L0.5 — write-once: put is idempotent; reads verify; no mutation surface exists.
def test_l0_5_put_bytes_idempotent(store, tmp_path: Path) -> None:
    ref1 = store.put_bytes(b"some source bytes")
    state = tree_state(tmp_path)
    ref2 = store.put_bytes(b"some source bytes")
    assert ref1 == ref2
    assert tree_state(tmp_path) == state  # the second put wrote nothing


def test_l0_5_round_trip_bytes_and_values(store) -> None:
    data = b"raw source"
    assert store.get_bytes(store.put_bytes(data)) == data
    value = {"rows": [1, 2], "price": Decimal("1.50"), "note": None}
    ref = store.put_value(value)
    assert store.get_value(ref) == value
    assert ref == encoding.content_address(value)  # one address space
    assert store.has(ref) and not store.has("sha256:" + "0" * 64)


def test_l0_5_bytes_at_rest_are_the_bytes_put(store, tmp_path: Path) -> None:
    # Debuggable from first principles: sha256sum of the file reproduces the address.
    import hashlib

    ref = store.put_bytes(b"inspect me")
    matches = [
        p for p in tmp_path.rglob("*")
        if p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == ref.split(":", 1)[1]
    ]
    assert matches, "stored bytes are wrapped or transformed at rest"


def test_l0_5_verify_on_read(store, tmp_path: Path) -> None:
    ref = store.put_bytes(b"pristine")
    victim = next(
        p for p in tmp_path.rglob("*") if p.is_file() and p.read_bytes() == b"pristine"
    )
    victim.write_bytes(b"tampered!")
    with pytest.raises(store_mod.IntegrityError):
        store.get_bytes(ref)


def test_l0_5_no_mutation_surface(store) -> None:
    exposed = {name for name in dir(store) if not name.startswith("_")}
    forbidden = {"delete", "remove", "unlink", "overwrite", "clear", "prune", "compact"}
    assert not (exposed & forbidden), f"mutation surface exposed: {exposed & forbidden}"


# L0.6 — gc refusal: nothing changes, and the refusal says so.
def test_l0_6_gc_refuses(store, tmp_path: Path, capsys) -> None:
    store.put_bytes(b"keep me forever")
    state = tree_state(tmp_path)
    message = store.gc()
    printed = capsys.readouterr().out
    assert "refus" in message.lower()
    assert "refus" in printed.lower()
    assert tree_state(tmp_path) == state


# L0.7 — ref grammar: everything the store emits is a pinned-grammar ref.
@given(st.binary(max_size=256))
def test_l0_7_bytes_refs_match_grammar(tmp_path_factory, data: bytes) -> None:
    store = store_mod.Store(tmp_path_factory.mktemp("s") / "store")
    assert REF_RE.match(store.put_bytes(data))


@given(st.one_of(st.none(), st.booleans(), st.integers(), st.text()))
def test_l0_7_value_refs_match_grammar(tmp_path_factory, value) -> None:
    store = store_mod.Store(tmp_path_factory.mktemp("s") / "store")
    assert REF_RE.match(store.put_value(value))


def test_l0_7_distinct_content_distinct_refs(store) -> None:
    assert store.put_bytes(b"a") != store.put_bytes(b"b")
