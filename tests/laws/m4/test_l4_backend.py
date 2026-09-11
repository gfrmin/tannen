"""M4 law L4.11 — the R2 backend answers as the local store does (docs/specs/m4.md §5;
BRIEF §4 "Store: local fs (M0), R2 (M4)", §10 "No store mutation, ever").

FROZEN at m4-laws-freeze.

A store over an `ObjectClient` — the protocol R2's S3 API is spoken through — addresses the
same bytes by the same refs, returns them, enumerates them and refuses a missing ref and a
`gc` exactly as the local store does. Write-once is kept by a conditional put that never
replaces an existing object; integrity is kept by verifying every read, because the remote
is not trusted to return what it was given.

What this does NOT establish, stated rather than implied: that any real client conforms to
R2. The laws drive a frozen in-memory client with S3's conditional-write semantics; the
first write to a real bucket is a network write outside a captured oracle — Tier-C door 2,
refused today by `governance/policy.yaml` (`network_writes: captured-oracles-only`) — and is
queued for the owner (docs/specs/m4.md §5).
"""

from __future__ import annotations

import importlib.util as _ilu
from pathlib import Path as _Path

import pytest

pytest.importorskip("tannen.oracles", reason=(
    "M4 boundary not implemented yet (law suite frozen ahead of Session B); M4's laws go "
    "live together — docs/specs/m4.md §11"))

_spec = _ilu.spec_from_file_location("tannen_frozen_m4._frozen_bind",
                                     _Path(__file__).with_name("_frozen_bind.py"))
bind = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(bind)

from hypothesis import given  # noqa: E402

M = bind.m4("_boundary_model")
TANNEN = bind.m4("_boundary_subject").make(M)

from tannen import store as store_mod  # noqa: E402

VALIDATED_BY = "tests/laws/m4/_boundary_model.py::check_backend"


def test_l4_11_the_backends_agree_on_a_fixed_corpus() -> None:
    M.check_backend(TANNEN, [b"", b"one", b"two", "ünïcode".encode("utf-8")])


@given(blobs=M.blob_lists())
def test_l4_11_the_backends_agree_on_drawn_corpora(blobs) -> None:
    M.check_backend(TANNEN, blobs)


def test_l4_11_store_root_is_the_local_backend(tmp_path) -> None:
    """`Store(root)` keeps its meaning — every frozen M0–M3 law constructs a store that way
    — and is the same store as `Store(backend=LocalBackend(root))` over the same root."""
    plain = store_mod.Store(tmp_path / "s")
    ref = plain.put_bytes(b"written through Store(root)")
    explicit = store_mod.Store(backend=store_mod.LocalBackend(tmp_path / "s"))
    assert explicit.get_bytes(ref) == b"written through Store(root)"
    other = explicit.put_bytes(b"written through LocalBackend")
    assert plain.get_bytes(other) == b"written through LocalBackend"
    assert sorted(plain.iter_refs()) == sorted(explicit.iter_refs()) == sorted({ref, other})
