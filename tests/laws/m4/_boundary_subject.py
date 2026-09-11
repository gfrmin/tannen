"""tannen on the stand — the IMPLEMENTATION half of M4's boundary laws
(docs/specs/m4.md §10). FROZEN at m4-laws-freeze.

`_boundary_model.py` holds the checks; this file puts the shipped package behind the same
interface, so one assertion text runs against both.

`pytest.importorskip("tannen.oracles")` is M4's SENTINEL — BRIEF §5.3's IO doorway, the
module M4 introduces. While it does not exist every boundary law is a visible skip; the
model half runs unconditionally from `tests/test_law_validation.py`. Every other module
this adapter needs that is new at M4 is importorskip'd too, so a Session B that has landed
some of them and not others sees skips, never a collection error that aborts the run.

It is loaded by `_frozen_bind.m4()` under a private name and is handed the model by
`make(M)`: no helper imports another by name (docs/specs/m4.md §8). `TannenSubject`
deliberately does NOT subclass the model's `Subject` — `make` checks `REQUIRED` against
this class's own `__dict__`, so a missing method is a hole here and never a silent
fallback to model code (the m2/m3 rule, verbatim).

The surface it pins is docs/specs/m4.md §1:

  tannen.oracles   Fetch / LLM / Clock (name, *, reproducibility=None, transport, **spec)
                   .kind .name .descriptor; input_key(request); REPLAY, SPEND;
                   load_budget(mapping | path); Oracles(store, *, mode=REPLAY, budget=None)
                   .invoke(oracle, request) -> capture ref; .read(ref) -> response value;
                   NovelInvocationRefused, SpendDenied, CaptureWriteFailed,
                   UndeclaredReproducibility, CaptureConflict
  tannen.store     Store(root) as before; Store(backend=...); R2Backend(client);
                   IntegrityError, MissingRef
  tannen.export    export(store, built) -> bytes; LayerError for anything but serve
"""

from __future__ import annotations

import atexit
import shutil
import tempfile
from typing import Any

import pytest

_SENTINEL = ("M4 boundary not implemented yet (law suite frozen ahead of Session B); M4's "
             "laws go live together — docs/specs/m4.md §11")

oracles = pytest.importorskip("tannen.oracles", reason=_SENTINEL)
export_mod = pytest.importorskip("tannen.export", reason=_SENTINEL)
store_mod = pytest.importorskip("tannen.store")
executor = pytest.importorskip("tannen.executor")
ops = pytest.importorskip("tannen.kernel.ops")
layers = pytest.importorskip("tannen.kernel.layers")
sources = pytest.importorskip("tannen.sources")
transform_mod = pytest.importorskip("tannen.transform")

if not hasattr(store_mod, "R2Backend"):
    pytest.skip(_SENTINEL + " (tannen.store has no R2Backend yet)", allow_module_level=True)

_SCRATCH = tempfile.mkdtemp(prefix="tannen-m4-laws-")
atexit.register(shutil.rmtree, _SCRATCH, True)


def _fresh_dir() -> str:
    return tempfile.mkdtemp(dir=_SCRATCH)


_KINDS = {"fetch": oracles.Fetch, "llm": oracles.LLM, "clock": oracles.Clock}
_MODES = {"replay": oracles.REPLAY, "spend": oracles.SPEND}
_SOURCE = "sha256:" + "4e" * 32
_SCHEMA = ("k", "x")


# -- the export catalogue, as registered transforms (the model's EXPORT_PIPELINES)


def _x_positive(row: Any) -> bool:
    return row["x"] > 0


def _plus_one(row: Any) -> Any:
    return {"k": row["k"], "x": row["x"] + 1}


@transform_mod.transform(kind="derive", params={"m4-export": "select"})
def _export_select(rel: Any) -> Any:
    return ops.select(rel, _x_positive)


@transform_mod.transform(kind="derive", params={"m4-export": "project"})
def _export_project(rel: Any) -> Any:
    return ops.project(rel, ("k",))


@transform_mod.transform(kind="derive", params={"m4-export": "select-project"})
def _export_select_project(rel: Any) -> Any:
    return ops.project(ops.select(rel, _x_positive), ("k",))


@transform_mod.transform(kind="derive", params={"m4-export": "map"})
def _export_map(rel: Any) -> Any:
    return ops.map_rows(rel, _plus_one, _SCHEMA)


@transform_mod.transform(kind="derive", params={"m4-export": "join"})
def _export_join(left: Any, right: Any) -> Any:
    return ops.join(left, right, _SCHEMA)


@transform_mod.transform(kind="derive", params={"m4-export": "distinct"})
def _export_distinct(rel: Any) -> Any:
    return ops.distinct(rel)


_PIPELINES = {
    "select": (_export_select, 1),
    "project": (_export_project, 1),
    "select-project": (_export_select_project, 1),
    "map": (_export_map, 1),
    "join": (_export_join, 2),
    "distinct": (_export_distinct, 1),
}


class _Session:
    """An `Oracles` context and the store it was opened over."""

    __slots__ = ("context", "store")

    def __init__(self, context: Any, store: Any) -> None:
        self.context = context
        self.store = store


def _never_called(request: Any) -> Any:
    raise AssertionError("constructing an oracle must not touch its transport")


class TannenSubject:
    """The shipped package behind the model's `Subject` interface."""

    name = "tannen"
    novel_refused = oracles.NovelInvocationRefused
    spend_denied = oracles.SpendDenied
    write_failed = oracles.CaptureWriteFailed
    undeclared = oracles.UndeclaredReproducibility
    integrity_error = store_mod.IntegrityError
    missing_ref = store_mod.MissingRef
    layer_error = layers.LayerError
    conflict = oracles.CaptureConflict

    # -- identity (§2)
    def descriptor(self, kind: str, name: str, spec: dict, reproducibility: Any) -> str:
        return self.oracle(kind, name, spec, reproducibility, _never_called).descriptor

    def oracle(self, kind: str, name: str, spec: dict, reproducibility: Any,
               transport: Any) -> Any:
        return _KINDS[kind](name, reproducibility=reproducibility, transport=transport, **spec)

    def input_key(self, request: dict) -> str:
        return oracles.input_key(request)

    # -- the store (§5)
    def store_local(self) -> Any:
        return store_mod.Store(_fresh_dir())

    def store_remote(self, client: Any) -> Any:
        return store_mod.Store(backend=store_mod.R2Backend(client))

    def put_bytes(self, store: Any, data: bytes) -> str:
        return store.put_bytes(data)

    def put_value(self, store: Any, value: Any) -> str:
        return store.put_value(value)

    def get_bytes(self, store: Any, ref: str) -> bytes:
        return store.get_bytes(ref)

    def get_value(self, store: Any, ref: str) -> Any:
        return store.get_value(ref)

    def has(self, store: Any, ref: str) -> bool:
        return store.has(ref)

    def iter_refs(self, store: Any) -> list:
        return sorted(store.iter_refs())

    def gc(self, store: Any) -> str:
        return store.gc()

    # -- sessions and invocation (§3, §4)
    def session(self, store: Any, mode: Any = None, budget: Any = None) -> _Session:
        kwargs: dict = {}
        if mode is not None:
            kwargs["mode"] = _MODES[mode]
        if budget is not None:
            kwargs["budget"] = oracles.load_budget(budget)
        return _Session(oracles.Oracles(store, **kwargs), store)

    def invoke(self, session: _Session, oracle: Any, request: dict) -> str:
        return session.context.invoke(oracle, request)

    def read(self, session: _Session, ref: str) -> dict:
        return session.context.read(ref)

    def capture_value(self, session: _Session, ref: str) -> Any:
        return session.store.get_value(ref)

    # -- the export door (§7)
    def _build(self, pipeline: str, rows: list) -> tuple:
        root = _fresh_dir()
        store = store_mod.Store(root + "/store")
        traces = executor.TraceStore(root + "/traces")
        rel = sources.ingest(store, _SOURCE, _SCHEMA, rows)
        ref = store.put_value(rel.to_value())
        fn, arity = _PIPELINES[pipeline]
        built = executor.AlwaysRebuild().build(executor.Node(fn, (ref,) * arity), store, traces)
        return store, built

    def output_bytes(self, pipeline: str, rows: list) -> bytes:
        store, built = self._build(pipeline, rows)
        return store.get_bytes(built.output_ref)

    def export(self, pipeline: str, rows: list) -> bytes:
        store, built = self._build(pipeline, rows)
        return export_mod.export(store, built)


def make(model: Any) -> TannenSubject:
    """The tannen subject, checked against the model's `REQUIRED` list."""
    missing = [name for name in model.REQUIRED if name not in vars(TannenSubject)]
    assert not missing, (
        f"TannenSubject does not define {missing} — it does not inherit from the model's "
        "Subject on purpose, so a missing method is a hole here and never a silent fallback "
        "to the model")
    return TannenSubject()
