"""The content-addressed store — `docs/specs/m0.md` §3, frozen at `m0-laws-freeze`; over a
backend since M4 (`docs/specs/m4.md` §1, §5).

Write-once, append-only. The effectful shell, deliberately outside `tannen.kernel`: this
module is where `pathlib` is allowed to appear. The cache is a view over what happened, and
recording makes no truth claims [cites: pkm-event-identity]. Laws L0.5–L0.7 and L4.11 are
the normative statement.

There is no delete and no overwrite — not as a policy, as an absence. `gc()` prints a
refusal (BRIEF §10 "No store mutation, ever"; `governance/tier-c.yaml` guard_enforced
`store-mutation`).

**One store, two places for its bytes.** `Store(root)` keeps its M0 meaning — every frozen
M0–M3 law builds a store that way — and is `Store(backend=LocalBackend(root))`.
`R2Backend(client)` puts the same store over an `ObjectClient`: three calls, a conditional
put that never replaces an object (S3's `If-None-Match: *`, which R2 honours), a get, a
sorted listing. Every RULE stays here in `Store` — the key layout, write-once, verification
on every read, the refusals — so a backend is only somewhere to keep bytes, and a remote is
never trusted to hand back what it was given (BRIEF §10; the M0 rule that integrity is
verification). The real R2 client is `tannen.r2`; a write to a real bucket is Tier-C door 2
and is queued for the owner (D0228), so no law and no test points it at one.

**Exclusive puts.** `put_bytes(..., exclusive=True)` raises `AlreadyStored` when the object
was already there. The local backend's create is exclusive at the filesystem (a hard link
from a synced temporary file, which fails if the name exists), so two processes racing to
write one object see one creation between them — which is what lets `tannen.oracles` hold a
spend reservation against a racing session (D0235).
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Protocol

from tannen.kernel.encoding import decode_canonical, encode_canonical
from tannen.kernel.refs import is_ref, ref_for_bytes, ref_hex

__all__ = [
    "AlreadyStored",
    "GC_REFUSAL",
    "IntegrityError",
    "LocalBackend",
    "MissingRef",
    "ObjectClient",
    "R2Backend",
    "Store",
]

#: Two-character fanout, so a store stays navigable with ordinary tools.
_FANOUT = 2
#: Where a ref's bytes live under a backend: `objects/<hex[:2]>/<hex[2:]>`.
_OBJECTS = "objects/"
#: A local write in progress (or interrupted) is a file with this prefix; never an object.
_TMP_PREFIX = ".tmp-"

GC_REFUSAL = (
    "gc: refused. A tannen store is append-only and write-once: nothing in it may be "
    "deleted or overwritten, ever (BRIEF §10; governance/tier-c.yaml guard_enforced: "
    "store-mutation). Nothing was changed. Reclaiming space is not a build-system "
    "decision — changing this rule is a Tier-C act belonging to the owner."
)


class IntegrityError(Exception):
    """Stored bytes no longer hash to the ref they are filed under."""


class MissingRef(KeyError):
    """No content is stored at this ref."""


class AlreadyStored(Exception):
    """An exclusive put found an object already under the ref's key (it was left as it was)."""


class ObjectClient(Protocol):
    """What a remote object store must answer (docs/specs/m4.md §1). `put_if_absent` creates
    the object and returns True, or leaves an existing one untouched and returns False; a
    write that did not happen raises `OSError`."""

    def put_if_absent(self, key: str, data: bytes) -> bool: ...

    def get(self, key: str) -> bytes | None: ...

    def list(self, prefix: str) -> list[str]: ...


def _key(ref: str) -> str:
    digest = ref_hex(ref)  # refuses anything outside the pinned grammar, by name
    return f"{_OBJECTS}{digest[:_FANOUT]}/{digest[_FANOUT:]}"


# ---------------------------------------------------------------------- backends


class LocalBackend:
    """An `ObjectClient` over a directory: the M0 store's filesystem layout, unchanged, so
    `sha256sum` on a file still reproduces its address. It writes the object and nothing
    else — no marker, no metadata — because L0.5 and L0.6 compare the whole tree."""

    __slots__ = ("_root",)

    def __init__(self, root: str | os.PathLike[str]) -> None:
        self._root = Path(root)
        (self._root / _OBJECTS).mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        return self._root

    def __repr__(self) -> str:
        return f"LocalBackend({str(self._root)!r})"

    def put_if_absent(self, key: str, data: bytes) -> bool:
        path = self._path(key)
        if path.exists():
            return False  # write-once: an existing object is never touched again
        new_fanout = not path.parent.exists()
        path.parent.mkdir(parents=True, exist_ok=True)
        if new_fanout:
            _fsync_directory(path.parent.parent)
        return _create_exclusively(path, bytes(data))

    def get(self, key: str) -> bytes | None:
        try:
            return self._path(key).read_bytes()
        except FileNotFoundError:
            return None

    def has(self, key: str) -> bool:
        return self._path(key).exists()

    def list(self, prefix: str) -> list[str]:
        keys = (
            path.relative_to(self._root).as_posix()
            for path in self._root.rglob("*")
            if path.is_file() and not path.name.startswith(_TMP_PREFIX)
        )
        return sorted(key for key in keys if key.startswith(prefix))

    def _path(self, key: str) -> Path:
        parts = key.split("/")
        if not key or key.startswith("/") or any(part in ("", ".", "..") for part in parts):
            raise ValueError(f"not an object key: {key!r}")
        return self._root.joinpath(*parts)


class R2Backend:
    """A store over an `ObjectClient` — R2's S3 API through `tannen.r2`, or the frozen
    in-memory client L4.11 drives. It adds no rule of its own: `Store` verifies every read,
    so what the remote hands back is checked, never believed."""

    __slots__ = ("_client",)

    def __init__(self, client: ObjectClient) -> None:
        missing = [n for n in ("put_if_absent", "get", "list") if not callable(getattr(client, n, None))]
        if missing:
            raise TypeError(f"{client!r} is not an ObjectClient: it lacks {missing}")
        self._client = client

    def __repr__(self) -> str:
        return f"R2Backend({self._client!r})"

    def put_if_absent(self, key: str, data: bytes) -> bool:
        return bool(self._client.put_if_absent(key, bytes(data)))

    def get(self, key: str) -> bytes | None:
        data = self._client.get(key)
        return None if data is None else bytes(data)

    def has(self, key: str) -> bool:
        return self._client.get(key) is not None

    def list(self, prefix: str) -> list[str]:
        return sorted(self._client.list(prefix))


# ---------------------------------------------------------------------- the store


class Store:
    """A content-addressed store over exactly one backend.

    One address space: a *value* is stored as its canonical encoding, a *source* as its
    raw bytes, and in both cases the address is the ref of the bytes at rest — so the store
    is debuggable from first principles on either backend.
    """

    __slots__ = ("_backend",)

    def __init__(self, root: str | os.PathLike[str] | None = None, *, backend: Any = None) -> None:
        if (root is None) == (backend is None):
            raise TypeError(
                "a store is built from exactly one of a root or a backend "
                "(Store(root) or Store(backend=...); docs/specs/m4.md §1)"
            )
        if backend is not None:
            missing = [
                n for n in ("put_if_absent", "get", "has", "list")
                if not callable(getattr(backend, n, None))
            ]
            if missing:
                raise TypeError(
                    f"{backend!r} is not a store backend (it lacks {missing}); a bare "
                    "ObjectClient goes in as Store(backend=R2Backend(client))"
                )
        self._backend = LocalBackend(root) if backend is None else backend

    @property
    def root(self) -> Path:
        if isinstance(self._backend, LocalBackend):
            return self._backend.root
        raise AttributeError(
            f"{self!r} has no local root: its bytes live behind {type(self._backend).__name__}"
        )

    def __repr__(self) -> str:
        if isinstance(self._backend, LocalBackend):
            return f"Store({str(self._backend.root)!r})"
        return f"Store(backend={self._backend!r})"

    # ------------------------------------------------------------------ writing

    def put_bytes(self, data: bytes, *, exclusive: bool = False) -> str:
        """Store raw bytes; return their ref. Idempotent: a re-put writes nothing (L0.5).

        A key that already holds an object is left exactly as it is — even when its bytes
        are not these (a squatter): write-once is kept at the key, and verify-on-read is what
        refuses the squatter (L4.11). With `exclusive=True` an existing object is refused as
        `AlreadyStored` instead of silently accepted."""
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError(f"put_bytes stores bytes, not {type(data).__name__}")
        data = bytes(data)
        ref = ref_for_bytes(data)
        created = self._backend.put_if_absent(_key(ref), data)
        if exclusive and not created:
            raise AlreadyStored(ref)
        return ref

    def put_value(self, value: Any, *, exclusive: bool = False) -> str:
        """Store a value as its canonical encoding; return its content address (L0.5)."""
        return self.put_bytes(encode_canonical(value), exclusive=exclusive)

    # ------------------------------------------------------------------ reading

    def get_bytes(self, ref: str) -> bytes:
        """The bytes at `ref`, verified on read (L0.5, L4.11)."""
        key = _key(ref)
        data = self._backend.get(key)
        if data is None:
            raise MissingRef(ref)
        actual = ref_for_bytes(data)
        if actual != ref:
            raise IntegrityError(
                f"content at {ref} hashes to {actual}: the bytes at rest were modified "
                f"outside the store ({self!r}, {key})"
            )
        return data

    def get_value(self, ref: str) -> Any:
        """The value at `ref`, decoded from its verified canonical bytes."""
        return decode_canonical(self.get_bytes(ref))

    def has(self, ref: str) -> bool:
        return self._backend.has(_key(ref))

    def iter_refs(self) -> Iterator[str]:
        """Every ref in the store, in key order.

        Read-only enumeration — the laws runner reads its evidence back this way. It is not
        a mutation surface and does not verify: `get_bytes` does that. A key outside the
        pinned layout is not an object and is not reported.
        """
        for key in self._backend.list(_OBJECTS):
            parts = key.split("/")
            candidate = f"sha256:{parts[1]}{parts[2]}" if len(parts) == 3 else ""
            if is_ref(candidate) and _key(candidate) == key:
                yield candidate

    # ------------------------------------------------------------------ refusals

    def gc(self) -> str:
        """Print and return the refusal; change nothing (L0.6) — on every backend."""
        print(GC_REFUSAL)
        return GC_REFUSAL


def _create_exclusively(path: Path, data: bytes) -> bool:
    """Write `data` at `path` only if nothing is there: synced to a temporary file, then
    hard-linked into place, which fails if the name exists. True if this call created it."""
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=_TMP_PREFIX)
    try:
        with os.fdopen(handle, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            return False  # another writer got there first; its object stands
        _fsync_directory(path.parent)
        return True
    finally:
        Path(temporary).unlink(missing_ok=True)


def _fsync_directory(directory: Path) -> None:
    """Make a directory entry durable: without it a crash can lose a file whose own bytes
    were synced — and a reservation a paid call depends on is such a file."""
    handle = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(handle)
    finally:
        os.close(handle)
