"""The store over a backend (docs/specs/m4.md §1, §5; decision D0233) — what frozen L4.11
does not pin.

L4.11 drives both backends through the frozen model's `MemoryClient` and asserts they
answer alike. What is left is the seam's own shape: that a store is built from exactly one
of a root or a backend, that the local backend is write-once at the key level, that
enumeration reads only keys in the pinned layout, and that putting a backend underneath did
not grow the store a mutation surface (L0.6's discipline, one layer down).

The fake client here is written out rather than borrowed from `tests/laws/m4/`: a frozen
law helper is reached by file location or not at all (docs/specs/m4.md §8).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tannen.kernel.refs import ref_for_bytes
from tannen.store import (
    GC_REFUSAL,
    AlreadyStored,
    IntegrityError,
    LocalBackend,
    MissingRef,
    R2Backend,
    Store,
)


class _Client:
    """An `ObjectClient` with S3's conditional-write semantics, in a dict."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_if_absent(self, key: str, data: bytes) -> bool:
        if key in self.objects:
            return False
        self.objects[key] = bytes(data)
        return True

    def get(self, key: str) -> bytes | None:
        return self.objects.get(key)

    def list(self, prefix: str) -> list[str]:
        return sorted(k for k in self.objects if k.startswith(prefix))


def _key(ref: str) -> str:
    digest = ref.split(":", 1)[1]
    return f"objects/{digest[:2]}/{digest[2:]}"


def _remote() -> tuple[Store, _Client]:
    client = _Client()
    return Store(backend=R2Backend(client)), client


def test_a_store_is_built_from_exactly_one_of_a_root_or_a_backend(tmp_path) -> None:
    with pytest.raises(TypeError, match="exactly one"):
        Store()
    with pytest.raises(TypeError, match="exactly one"):
        Store(tmp_path, backend=LocalBackend(tmp_path))


def test_the_local_backend_creates_once_and_never_rewrites(tmp_path) -> None:
    backend = LocalBackend(tmp_path)
    assert backend.put_if_absent("objects/ab/cd", b"first") is True
    assert backend.put_if_absent("objects/ab/cd", b"second") is False
    assert backend.get("objects/ab/cd") == b"first"
    assert backend.has("objects/ab/cd") and not backend.has("objects/ab/ce")
    assert backend.get("objects/ab/ce") is None


def test_enumeration_reads_only_keys_in_the_pinned_layout(tmp_path) -> None:
    local = Store(tmp_path / "s")
    ref = local.put_bytes(b"real")
    fan = tmp_path / "s" / "objects" / ref.split(":")[1][:2]
    (fan / ".tmp-interrupted").write_bytes(b"half a write")
    (tmp_path / "s" / "objects" / "zz").mkdir()
    (tmp_path / "s" / "objects" / "zz" / "not-a-digest").write_bytes(b"")
    assert list(local.iter_refs()) == [ref]
    assert all(not key.rsplit("/", 1)[1].startswith(".tmp-")
               for key in LocalBackend(tmp_path / "s").list("objects/"))

    remote, client = _remote()
    ref = remote.put_bytes(b"real")
    client.objects["objects/zz/not-a-digest"] = b""
    client.objects["elsewhere/" + ref.split(":")[1]] = b"real"
    assert list(remote.iter_refs()) == [ref]


def test_a_remote_store_answers_and_refuses_as_the_local_one_does(tmp_path, capsys) -> None:
    local = Store(tmp_path / "s")
    remote, client = _remote()
    blobs = [b"", b"one", "ünïcode".encode("utf-8")]
    assert [local.put_bytes(b) for b in blobs] == [remote.put_bytes(b) for b in blobs]
    for blob in blobs:
        ref = ref_for_bytes(blob)
        assert remote.get_bytes(ref) == local.get_bytes(ref) == blob
        assert remote.has(ref)
    assert sorted(remote.iter_refs()) == sorted(local.iter_refs())

    absent = ref_for_bytes(b"never written")
    for store in (local, remote):
        with pytest.raises(MissingRef):
            store.get_bytes(absent)
        assert not store.has(absent)
    assert remote.gc() == local.gc() == GC_REFUSAL

    swapped = ref_for_bytes(b"one")
    client.objects[_key(swapped)] = b"swapped behind the store's back"
    with pytest.raises(IntegrityError):
        remote.get_bytes(swapped)


def test_a_put_leaves_a_squatter_where_it_is_and_the_read_refuses_it() -> None:
    """Write-once at the key: a conditional put never replaces an object, so bytes already
    sitting under a ref's key stay there — and verify-on-read refuses them. Raising at the
    put instead would fail frozen L4.11, which puts over a squatter outside any `try`."""
    remote, client = _remote()
    ref = ref_for_bytes(b"victim")
    client.objects[_key(ref)] = b"squatter"
    assert remote.put_bytes(b"victim") == ref
    assert client.objects[_key(ref)] == b"squatter"
    with pytest.raises(IntegrityError):
        remote.get_bytes(ref)


def test_root_is_the_local_directory_and_a_remote_store_has_none(tmp_path) -> None:
    assert Store(tmp_path / "s").root == Path(tmp_path / "s")
    remote, _ = _remote()
    with pytest.raises(AttributeError, match="no local root"):
        remote.root


@pytest.mark.parametrize("which", ["local", "remote"])
def test_an_exclusive_put_refuses_an_object_already_there(tmp_path, which) -> None:
    """What lets a spend reservation be HELD: the first writer creates it, any other writer of
    the same bytes is told so rather than silently accepted (D0233, D0235)."""
    store = Store(tmp_path / "s") if which == "local" else _remote()[0]
    ref = store.put_bytes(b"held", exclusive=True)
    with pytest.raises(AlreadyStored):
        store.put_bytes(b"held", exclusive=True)
    assert store.put_bytes(b"held") == ref  # the ordinary put stays idempotent (L0.5)


def test_the_local_create_is_exclusive_at_the_filesystem(tmp_path) -> None:
    """Checked by name existence alone, two processes could both see "absent" and both
    report creating one object. The create itself must be exclusive: a name that appeared
    after the existence check makes it answer False, the object that got there first stands,
    and the temporary file is gone either way."""
    from tannen.store import _create_exclusively

    target = tmp_path / "cd"
    target.write_bytes(b"the other writer")  # landed between the check and the create
    assert _create_exclusively(target, b"mine") is False
    assert target.read_bytes() == b"the other writer"
    fresh = tmp_path / "ef"
    assert _create_exclusively(fresh, b"mine") is True and fresh.read_bytes() == b"mine"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["cd", "ef"]


@pytest.mark.parametrize("which", ["local", "remote"])
def test_a_backend_underneath_grows_no_mutation_surface(tmp_path, which) -> None:
    store = Store(tmp_path / "s") if which == "local" else _remote()[0]
    for name in ("delete", "remove", "unlink", "overwrite", "clear", "prune", "compact"):
        assert not hasattr(store, name), f"Store exposes {name!r} (BRIEF §10)"
