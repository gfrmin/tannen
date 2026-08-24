"""The content-addressed store — `docs/specs/m0.md` §3, frozen at `m0-laws-freeze`.

Write-once, append-only, local filesystem. The effectful shell, deliberately outside
`tannen.kernel`: this module is where `pathlib` is allowed to appear. The cache is a
view over what happened, and recording makes no truth claims
[cites: pkm-event-identity]. Laws L0.5–L0.7 are the normative statement.

There is no delete and no overwrite — not as a policy, as an absence. `gc()` prints a
refusal (BRIEF §10 "No store mutation, ever"; `governance/tier-c.yaml` guard_enforced
`store-mutation`).
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from tannen.kernel.encoding import decode_canonical, encode_canonical
from tannen.kernel.refs import ref_for_bytes, ref_hex

__all__ = ["IntegrityError", "MissingRef", "Store"]

#: Two-character fanout, so a store stays navigable with ordinary tools.
_FANOUT = 2

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


class Store:
    """A content-addressed store rooted at a directory.

    One address space: a *value* is stored as its canonical encoding, a *source* as its
    raw bytes, and in both cases the address is the ref of the bytes at rest — so
    `sha256sum` on the file reproduces the address, and the store is debuggable from
    first principles.
    """

    def __init__(self, root: str | os.PathLike[str]) -> None:
        self._root = Path(root)
        self._objects = self._root / "objects"
        self._objects.mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        return self._root

    def __repr__(self) -> str:
        return f"Store({str(self._root)!r})"

    # ------------------------------------------------------------------ writing

    def put_bytes(self, data: bytes) -> str:
        """Store raw bytes; return their ref. Idempotent: a re-put writes nothing (L0.5)."""
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError(f"put_bytes stores bytes, not {type(data).__name__}")
        data = bytes(data)
        ref = ref_for_bytes(data)
        path = self._path_for(ref)
        if path.exists():
            return ref  # already written; write-once means we do not touch it again
        path.parent.mkdir(parents=True, exist_ok=True)
        self._write_atomically(path, data)
        return ref

    def put_value(self, value: Any) -> str:
        """Store a value as its canonical encoding; return its content address (L0.5)."""
        return self.put_bytes(encode_canonical(value))

    # ------------------------------------------------------------------ reading

    def get_bytes(self, ref: str) -> bytes:
        """The bytes at `ref`, verified on read (L0.5)."""
        path = self._path_for(ref)
        try:
            data = path.read_bytes()
        except FileNotFoundError as exc:
            raise MissingRef(ref) from exc
        actual = ref_for_bytes(data)
        if actual != ref:
            raise IntegrityError(
                f"content at {ref} hashes to {actual}: the bytes at rest were modified "
                f"outside the store ({path})"
            )
        return data

    def get_value(self, ref: str) -> Any:
        """The value at `ref`, decoded from its verified canonical bytes."""
        return decode_canonical(self.get_bytes(ref))

    def has(self, ref: str) -> bool:
        return self._path_for(ref).exists()

    def iter_refs(self) -> Iterator[str]:
        """Every ref in the store, in no particular order.

        Read-only enumeration — the laws runner reads its evidence back this way. It
        is not a mutation surface and does not verify: `get_bytes` does that.
        """
        for path in sorted(self._objects.rglob("*")):
            if not path.is_file():
                continue
            candidate = f"sha256:{path.parent.name}{path.name}"
            if self._path_for_unchecked(candidate) == path:
                yield candidate

    # ------------------------------------------------------------------ refusals

    def gc(self) -> str:
        """Print and return the refusal; change nothing (L0.6)."""
        print(GC_REFUSAL)
        return GC_REFUSAL

    # ------------------------------------------------------------------ internals

    def _path_for(self, ref: str) -> Path:
        digest = ref_hex(ref)  # refuses anything outside the pinned grammar, by name
        return self._objects / digest[:_FANOUT] / digest[_FANOUT:]

    def _path_for_unchecked(self, ref: str) -> Path | None:
        try:
            return self._path_for(ref)
        except ValueError:
            return None

    def _write_atomically(self, path: Path, data: bytes) -> None:
        handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
        try:
            with os.fdopen(handle, "wb") as fh:
                fh.write(data)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(temporary, path)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise
