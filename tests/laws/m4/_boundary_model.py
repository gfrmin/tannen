"""The MODEL half of M4's boundary laws — the frozen oracle (docs/specs/m4.md §10).

FROZEN at m4-laws-freeze, for D0094's reason, restated at every freeze because it is the
point: under the frozen-oracle protocol every law is a skip at exactly the moment it becomes
unrewritable, so `pytest tests/laws/m4` prints the same "N skipped" whether the laws are
correct, contradictory or nonsense. A model beside them turns Session A's gate from "the laws
do not run" into "the laws pass against a model and fail against a stated mutant".

It imports NOTHING from tannen (D0089), and it uses NO dataclasses: it is loaded by file
location under names that are not in `sys.modules` (`tests/test_law_validation.py`, the
oracle-shadow fingerprint load), and a `from __future__ import annotations` dataclass
cannot be built there (measured on 3.13 while planning this freeze).

Nobody imports it by its bare name. Every M4 law file reaches it through
`_frozen_bind.m4()`, which executes these bytes from their file location under a private
dotted name — the forward fix for the naming hazard RT-M1-01, RT-M2-01 and RT-M3-04 found,
so this file is not a twentieth bare-import oracle.

Four things live here.

1.  A naive transcription of docs/specs/m4.md §2–§7: oracle identity, the invocation
    policy (invoke iff no capture, capture before read, replay-only by default), SpendGuard
    as a reserve-then-settle fold over the store, the `capture/1` envelope, the store over
    an `ObjectClient`, and the serve-only export door.
2.  The `Subject` interface every check is written against, and `MODEL`.
    `_boundary_subject.py` puts the shipped package behind the same interface.
3.  The fakes the laws drive instead of the world: `MemoryClient` (an in-memory object
    store with S3's conditional-write semantics and injectable faults) and `FakeTransport`
    (a counting transport per oracle kind). No law touches a network.
4.  `MUTANTS` — deliberately broken subjects, each aimed at by exactly one family
    (`CAUGHT_BY`). Several are the tempting wrong behaviours this boundary invites, written
    down before they could be written in: a per-session spend counter, a budget checked
    after the call, a zero ceiling read as "free calls allowed", a paid call with no
    reservation, a store that trusts the bytes the remote hands back.

Generators follow D0118's rule: every case that matters is drawn as a NAMED case, each
declares what it exercises, and every draw reports its shape through hypothesis `event()`.
No thresholds anywhere.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from hypothesis import event, strategies as st

__all__ = [
    "CAUGHT_BY", "CLASSES", "EXPORT_PIPELINES", "FAMILIES", "KINDS", "MODEL", "MUTANTS",
    "MemoryClient", "FakeTransport", "REQUIRED", "SPEND_CASES", "Subject",
    "capture_schema", "check_backend", "check_capture_before_read", "check_descriptors",
    "check_differential", "check_envelopes", "check_export", "check_invoke_once",
    "check_modes", "check_spend", "differential_scenarios", "oracle_specs", "requests_for",
    "run_family", "spend_scenarios", "vector_paths", "worst_case", "actual_price",
]

# ------------------------------------------------------------------------ vocabulary

#: The reproducibility classes. The VOCABULARY is pkm's (BRIEF §2, [cites: pkm-determinism]);
#: these are the spellings docs/specs/m0.md §4 already fixed for tannen's descriptors.
CLASSES = ("bit", "in-distribution", "non-reproducible")

#: The built-in oracle kinds at M4 (BRIEF §4).
KINDS = ("fetch", "llm", "clock")

REPLAY = "replay"
SPEND = "spend"

#: The refusal text of `gc` — the model's own; only its equality across two stores of one
#: subject is a law (§5), never its wording.
GC_TEXT = "gc: refused. A store is append-only and write-once."

REF_PREFIX = "sha256:"


class ModelRefusal(Exception):
    """Base of every refusal the model raises by name."""


class NovelRefused(ModelRefusal):
    """A novel invocation outside spend mode (BRIEF §5.10)."""


class SpendRefused(ModelRefusal):
    """SpendGuard said no (BRIEF §4)."""


class WriteFailed(ModelRefusal):
    """A capture or reservation could not be written, so nothing may be read (P1)."""


class Undeclared(ModelRefusal):
    """An oracle with no reproducibility class from the vocabulary."""


class Integrity(ModelRefusal):
    """Bytes read back do not hash to the ref they were asked for."""


class Missing(ModelRefusal):
    """No object at that ref."""


class LayerRefusal(ModelRefusal):
    """An export of something wider than `serve`."""


class Conflict(ModelRefusal):
    """Two captures answer one (descriptor, input key): nothing can say which is the record."""


# ------------------------------------------------------------------------ encoding


def encode(value: Any) -> bytes:
    """The model's canonical form: sorted keys, no whitespace, UTF-8, no floats. It need not
    be tannen's byte for byte — addresses never cross between subjects in any check."""
    def refuse_float(v: Any) -> Any:
        if isinstance(v, float):
            raise TypeError("the model encodes no floats (P7)")
        if isinstance(v, dict):
            return {k: refuse_float(x) for k, x in v.items()}
        if isinstance(v, (list, tuple)):
            return [refuse_float(x) for x in v]
        return v
    return json.dumps(refuse_float(value), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def address_bytes(data: bytes) -> str:
    return REF_PREFIX + hashlib.sha256(data).hexdigest()


def address(value: Any) -> str:
    return address_bytes(encode(value))


def key_for(ref: str) -> str:
    """ref -> object key: `objects/<hex[:2]>/<hex[2:]>`, the local store's fan-out (§5)."""
    hexpart = ref[len(REF_PREFIX):]
    return f"objects/{hexpart[:2]}/{hexpart[2:]}"


def _decode(data: bytes) -> Any:
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None


# ------------------------------------------------------------------------ the fakes


class MemoryClient:
    """An in-memory `ObjectClient` with S3 conditional-write semantics (§5).

    `put_if_absent(key, data) -> bool` creates the object and returns True, or leaves an
    existing object untouched and returns False. `get(key)` returns the bytes or None.
    `list(prefix)` returns the keys under a prefix, sorted. Two faults are injectable:
    `fail_when(data) -> bool` makes a put raise `OSError` (a write that did not happen), and
    `tamper(key, data)` replaces an object's bytes behind the store's back. `put` — an
    UNCONDITIONAL write — exists only so a mutant can overwrite; every call to it that lands
    on an existing key is counted in `overwrites`, which a lawful store keeps at zero."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.fail_when: Any = None
        self.overwrites = 0
        self.puts = 0

    def put_if_absent(self, key: str, data: bytes) -> bool:
        self.puts += 1
        if self.fail_when is not None and self.fail_when(data):
            raise OSError("MemoryClient: injected write failure")
        if key in self.objects:
            return False
        self.objects[key] = bytes(data)
        return True

    def put(self, key: str, data: bytes) -> None:
        self.puts += 1
        if self.fail_when is not None and self.fail_when(data):
            raise OSError("MemoryClient: injected write failure")
        if key in self.objects:
            self.overwrites += 1
        self.objects[key] = bytes(data)

    def get(self, key: str) -> bytes | None:
        return self.objects.get(key)

    def list(self, prefix: str) -> list[str]:
        return sorted(k for k in self.objects if k.startswith(prefix))

    def tamper(self, key: str, data: bytes) -> None:
        self.objects[key] = bytes(data)


class FakeTransport:
    """A counting transport for one oracle kind. `calls` holds every effective request it
    was handed, so "the transport was not touched" is `calls == []`, observed rather than
    inferred. Responses are deterministic functions of the request, so a replay that
    reached the transport would still return the same value — which is exactly why the
    laws count calls instead of comparing values (P1: the call is the cost)."""

    def __init__(self, kind: str, *, overrun: int = 0) -> None:
        if kind not in KINDS:
            raise ValueError(kind)
        self.kind = kind
        self.overrun = overrun
        self.calls: list[Any] = []

    def __call__(self, request: Any) -> dict:
        self.calls.append(request)
        digest = hashlib.sha256(encode(request)).hexdigest()
        if self.kind == "fetch":
            return {
                "status": 200,
                "headers": [["content-type", "text/plain"], ["x-seen", digest[:8]],
                            ["x-seen", digest[8:16]]],
                "body": ("body " + digest[:16]).encode("utf-8"),
                "observed_at": "2026-09-11T00:00:00Z",
            }
        if self.kind == "llm":
            params = request["params"]
            return {
                "resolved_model": request["model"] + "-resolved",
                "content": "answer " + digest[:12],
                "usage": {"input_tokens": len(encode(request)) // 4 + 1,
                          "output_tokens": params["max_tokens"] + self.overrun},
            }
        return {"instant": "2026-09-11T00:00:%02dZ" % (int(digest[:2], 16) % 60)}


# ------------------------------------------------------------------------ pricing


def effective_request(kind: str, spec: dict, request: dict) -> dict:
    """What the transport is handed, and what the capture records verbatim (§3): the
    oracle's fixed spec completed by the invocation's variable part."""
    if kind == "fetch":
        return {"method": spec["method"], "uri": request["uri"], "headers": spec["headers"]}
    if kind == "llm":
        return {"model": spec["model"], "prompt": spec["prompt"],
                "tool_schema": spec["tool_schema"], "params": spec["params"],
                "messages": request["messages"]}
    return {"label": request["label"]}


def worst_case(kind: str, spec: dict, request: dict) -> int:
    """Declared before the call and exact (§4). An LLM's input is bounded by the UTF-8
    bytes of the canonical effective request (a token is at least a byte); its output by
    `max_tokens`."""
    if kind == "llm":
        sent = effective_request(kind, spec, request)
        return (spec["input_price"] * len(encode(sent))
                + spec["output_price"] * spec["params"]["max_tokens"])
    return spec["price"]


def actual_price(kind: str, spec: dict, response: dict) -> int:
    """What the capture records as spent: the world's own report for an LLM, the declared
    price otherwise. It may exceed the worst case — a world overrun — and is recorded as
    is, never clamped (§4)."""
    if kind == "llm":
        usage = response["usage"]
        return (spec["input_price"] * usage["input_tokens"]
                + spec["output_price"] * usage["output_tokens"])
    return spec["price"]


# ------------------------------------------------------------------------ the store


class MStore:
    """The model store: content-addressed, write-once, verify-on-read, over any client."""

    def __init__(self, client: Any, subject: "Subject") -> None:
        self.client = client
        self.subject = subject

    def put(self, data: bytes) -> str:
        return self.subject.store_put(self, data)

    def get(self, ref: str) -> bytes:
        return self.subject.store_get(self, ref)

    def refs(self) -> list[str]:
        out = []
        for key in self.client.list("objects/"):
            _, fan, rest = key.split("/", 2)
            out.append(REF_PREFIX + fan + rest)
        return sorted(out)

    def values(self) -> list[tuple[str, Any]]:
        """Every object that decodes as a tagged value, with its ref. A tampered object
        raises here: a store whose bytes do not verify cannot be folded (§4)."""
        out = []
        for ref in self.refs():
            value = _decode(self.get(ref))
            if isinstance(value, dict) and "tannen" in value:
                out.append((ref, value))
        return out


class MOracle:
    """A constructed oracle: kind, name, effective spec, class, transport, descriptor."""

    def __init__(self, kind: str, name: str, spec: dict, reproducibility: str,
                 transport: Any, descriptor: str) -> None:
        self.kind = kind
        self.name = name
        self.spec = spec
        self.reproducibility = reproducibility
        self.transport = transport
        self.descriptor = descriptor


class MSession:
    """An invocation context: a store, a mode, a budget. It holds NO spend state — spend is
    a fold over the store (§4), which is the whole of what `counter-not-fold` breaks."""

    def __init__(self, store: MStore, mode: str, budget: Any) -> None:
        self.store = store
        self.mode = mode
        self.budget = budget
        self.memo: dict[str, Any] = {}


# ------------------------------------------------------------------------ the subject


class Subject:
    """What a law needs of an implementation. Every check is written against this and
    nothing else, so one assertion text runs against the model, each mutant, and tannen.
    Hooks are fine-grained so a mutant can break one mechanism without forging the rest."""

    name = "model"
    novel_refused = NovelRefused
    spend_denied = SpendRefused
    write_failed = WriteFailed
    undeclared = Undeclared
    integrity_error = Integrity
    missing_ref = Missing
    layer_error = LayerRefusal
    conflict = Conflict

    # -- identity (§2)
    def descriptor_value(self, kind: str, name: str, spec: dict, reproducibility: str) -> dict:
        return {"tannen": "oracle/1", "kind": kind, "name": name, "spec": spec,
                "reproducibility": reproducibility}

    def descriptor(self, kind: str, name: str, spec: dict, reproducibility: Any) -> str:
        if reproducibility not in CLASSES:
            raise Undeclared(f"{kind} {name!r}: reproducibility {reproducibility!r} is not "
                             f"declared from {CLASSES}")
        return address(self.descriptor_value(kind, name, spec, reproducibility))

    def oracle(self, kind: str, name: str, spec: dict, reproducibility: Any,
               transport: Any) -> MOracle:
        return MOracle(kind, name, spec, reproducibility, transport,
                       self.descriptor(kind, name, spec, reproducibility))

    def input_key(self, request: dict) -> str:
        return address(request)

    # -- the store (§5)
    def store_local(self) -> MStore:
        return MStore(MemoryClient(), self)

    def store_remote(self, client: Any) -> MStore:
        return MStore(client, self)

    def store_put(self, store: MStore, data: bytes) -> str:
        ref = address_bytes(data)
        store.client.put_if_absent(key_for(ref), data)
        return ref

    def store_get(self, store: MStore, ref: str) -> bytes:
        data = store.client.get(key_for(ref))
        if data is None:
            raise Missing(ref)
        if address_bytes(data) != ref:
            raise Integrity(f"{ref}: the bytes read back hash elsewhere")
        return data

    def put_bytes(self, store: MStore, data: bytes) -> str:
        return store.put(data)

    def put_value(self, store: MStore, value: Any) -> str:
        return store.put(encode(value))

    def get_bytes(self, store: MStore, ref: str) -> bytes:
        return store.get(ref)

    def get_value(self, store: MStore, ref: str) -> Any:
        return _decode(store.get(ref))

    def has(self, store: MStore, ref: str) -> bool:
        return store.client.get(key_for(ref)) is not None

    def iter_refs(self, store: MStore) -> list[str]:
        return store.refs()

    def gc(self, store: MStore) -> str:
        return GC_TEXT

    # -- sessions and invocation (§3, §4)
    def session(self, store: MStore, mode: Any = None, budget: Any = None) -> MSession:
        return MSession(store, REPLAY if mode is None else mode, budget)

    def find_captures(self, store: MStore, descriptor: str, key: str) -> list[str]:
        return [ref for ref, v in store.values()
                if v.get("tannen") == "capture/1" and v.get("oracle") == descriptor
                and v.get("input_key") == key]

    def spent(self, session: MSession, scope: str, kind: str | None) -> int:
        captures = {v["reservation"]: v["price"] for _, v in session.store.values()
                    if v.get("tannen") == "capture/1"}
        total = 0
        for ref, v in session.store.values():
            if v.get("tannen") != "reservation/1" or v.get("scope") != scope:
                continue
            if kind is not None and v.get("kind") != kind:
                continue
            total += captures.get(ref, v["worst_case"])
        return total

    def admissible(self, ceiling: int, spent: int, worst: int) -> bool:
        return ceiling > 0 and spent + worst <= ceiling

    def admit(self, session: MSession, oracle: MOracle, worst: int) -> None:
        budget = session.budget
        if not isinstance(budget, dict) or not budget.get("scope") or not budget.get("unit"):
            raise SpendRefused("no budget names a scope and a unit: default-deny")
        if budget["unit"] != oracle.spec["unit"]:
            raise SpendRefused(f"unit {oracle.spec['unit']!r} is not the budget's "
                               f"{budget['unit']!r}")
        ceilings = budget.get("ceilings", {})
        for kind in (oracle.kind, "total"):
            ceiling = ceilings.get(kind)
            if ceiling is None:
                raise SpendRefused(f"the budget names no {kind!r} ceiling: default-deny")
            spent = self.spent(session, budget["scope"], None if kind == "total" else kind)
            if not self.admissible(ceiling, spent, worst):
                raise SpendRefused(f"{kind}: spent {spent} + worst case {worst} against "
                                   f"ceiling {ceiling}")

    def reserve(self, session: MSession, oracle: MOracle, key: str, worst: int) -> str:
        scope = session.budget["scope"]
        attempt = 1 + sum(1 for _, v in session.store.values()
                          if v.get("tannen") == "reservation/1" and v.get("oracle")
                          == oracle.descriptor and v.get("input_key") == key
                          and v.get("scope") == scope)
        value = {"tannen": "reservation/1", "kind": oracle.kind, "oracle": oracle.descriptor,
                 "input_key": key, "scope": scope, "unit": oracle.spec["unit"],
                 "worst_case": worst, "attempt": attempt}
        try:
            return self.put_value(session.store, value)
        except OSError as exc:
            raise WriteFailed(f"reservation not written ({exc}); nothing was called") from exc

    def call(self, oracle: MOracle, sent: dict) -> dict:
        return oracle.transport(sent)

    def response_value(self, session: MSession, kind: str, response: dict) -> dict:
        if kind == "fetch":
            body = self.put_bytes(session.store, response["body"])
            return {"status": response["status"], "headers": response["headers"],
                    "body": body, "observed_at": response["observed_at"]}
        if kind == "llm":
            return {"resolved_model": response["resolved_model"],
                    "content": response["content"], "usage": response["usage"]}
        return {"instant": response["instant"]}

    def envelope(self, session: MSession, oracle: MOracle, key: str, sent: dict,
                 stored: dict, response: dict, reservation: str) -> dict:
        return {"tannen": "capture/1", "kind": oracle.kind, "oracle": oracle.descriptor,
                "input_key": key, "request": sent, "response": stored,
                "scope": session.budget["scope"], "unit": oracle.spec["unit"],
                "price": actual_price(oracle.kind, oracle.spec, response),
                "reservation": reservation}

    def record(self, session: MSession, oracle: MOracle, key: str, sent: dict,
               response: dict, reservation: str) -> str:
        try:
            stored = self.response_value(session, oracle.kind, response)
            return self.put_value(session.store, self.envelope(
                session, oracle, key, sent, stored, response, reservation))
        except OSError as exc:
            raise WriteFailed(f"capture not written ({exc}); the value is withheld") from exc

    def invoke(self, session: MSession, oracle: MOracle, request: dict) -> str:
        key = self.input_key(request)
        hits = self.find_captures(session.store, oracle.descriptor, key)
        if len(hits) > 1:
            raise Conflict(f"{len(hits)} captures answer {oracle.descriptor} at {key}")
        if hits:
            return hits[0]
        if session.mode != SPEND:
            raise NovelRefused(f"{oracle.kind} {oracle.name!r}: no capture at {key}, and "
                               "replay-only is the default")
        sent = effective_request(oracle.kind, oracle.spec, request)
        worst = worst_case(oracle.kind, oracle.spec, request)
        self.admit(session, oracle, worst)
        reservation = self.reserve(session, oracle, key, worst)
        response = self.call(oracle, sent)
        return self.record(session, oracle, key, sent, response, reservation)

    def read(self, session: MSession, ref: str) -> dict:
        value = _decode(self.get_bytes(session.store, ref))
        if not isinstance(value, dict) or value.get("tannen") != "capture/1":
            raise Missing(f"{ref} is not a capture")
        response = dict(value["response"])
        if value["kind"] == "fetch":
            response["body"] = self.get_bytes(session.store, response["body"])
        return response

    def capture_value(self, session: MSession, ref: str) -> Any:
        return self.get_value(session.store, ref)

    # -- the export door (§7)
    def output_bytes(self, pipeline: str, rows: list) -> bytes:
        return encode({"pipeline": pipeline, "rows": _pipeline_rows(pipeline, rows)})

    def export(self, pipeline: str, rows: list) -> bytes:
        if _layer_of(EXPORT_PIPELINES[pipeline]) != "serve":
            raise LayerRefusal(f"{pipeline}: layer {_layer_of(EXPORT_PIPELINES[pipeline])}, "
                               "and an export admits only serve")
        return self.output_bytes(pipeline, rows)


#: Exactly what a check calls on a subject. `_boundary_subject.py` asserts the tannen
#: adapter defines EVERY name here in its own `__dict__` — no subclassing, no silent
#: fallback to model code (the m2/m3 rule, unchanged).
REQUIRED = (
    "name", "novel_refused", "spend_denied", "write_failed", "undeclared",
    "integrity_error", "missing_ref", "layer_error", "conflict",
    "descriptor", "oracle", "input_key",
    "store_local", "store_remote", "put_bytes", "put_value", "get_bytes", "get_value",
    "has", "iter_refs", "gc",
    "session", "invoke", "read", "capture_value",
    "output_bytes", "export",
)

MODEL = Subject()


# ------------------------------------------------------------------------ layers & export

_LAYERS = (
    ("capture", frozenset()),
    ("serve", frozenset({"project", "select"})),
    ("decode", frozenset({"project", "select", "map_rows"})),
    ("derive", frozenset({"project", "select", "map_rows", "union", "join", "distinct",
                          "aggregate", "anti_join"})),
)

#: The export catalogue: each pipeline by the operators it runs. Three are `serve`, three
#: are wider — one per wider layer, so the door is tried at each step of the chain.
EXPORT_PIPELINES = {
    "select": frozenset({"select"}),
    "project": frozenset({"project"}),
    "select-project": frozenset({"select", "project"}),
    "map": frozenset({"map_rows"}),
    "join": frozenset({"join"}),
    "distinct": frozenset({"distinct"}),
}


def _layer_of(operators: frozenset) -> str:
    for name, admitted in _LAYERS:
        if operators <= admitted:
            return name
    raise AssertionError("unreachable: derive admits every operator")


def _pipeline_rows(pipeline: str, rows: list) -> list:
    """The model's reading of each catalogue pipeline over rows {k, x} — a bag, sorted."""
    if pipeline == "select":
        out = [r for r in rows if r["x"] > 0]
    elif pipeline == "project":
        out = [{"k": r["k"]} for r in rows]
    elif pipeline == "select-project":
        out = [{"k": r["k"]} for r in rows if r["x"] > 0]
    elif pipeline == "map":
        out = [{"k": r["k"], "x": r["x"] + 1} for r in rows]
    elif pipeline == "join":
        out = [{**a, **b} for a in rows for b in rows if a["k"] == b["k"]]
    else:
        out = sorted({encode(r): r for r in rows}.values(), key=encode)
    return sorted(out, key=encode)


# ------------------------------------------------------------------------ the schema

_HERE = Path(__file__).resolve().parent


def capture_schema() -> dict:
    return json.loads((_HERE / "capture" / "schema.json").read_text(encoding="utf-8"))


def vector_paths(side: str) -> list[Path]:
    return sorted((_HERE / "capture" / side).glob("*.json"))


def _validate(value: Any) -> None:
    """Raise AssertionError unless `value` is a valid `capture/1` (§3)."""
    import jsonschema

    try:
        jsonschema.Draft202012Validator(capture_schema()).validate(value)
    except jsonschema.ValidationError as exc:
        raise AssertionError(f"not a valid capture/1: {exc.message}") from None


# ------------------------------------------------------------------------ generators


def _spec(kind: str, variant: int, price: int = 0, *, input_price: int = 1,
          output_price: int = 1, max_tokens: int = 2, unit: str = "nano-usd") -> dict:
    if kind == "fetch":
        headers = [["accept", "text/plain"]] + ([["x-variant", str(variant)]] if variant else [])
        return {"method": "GET", "headers": headers, "unit": unit, "price": price}
    if kind == "llm":
        return {"model": f"model-{variant}", "prompt": f"summarise v{variant}",
                "tool_schema": None if variant % 2 == 0 else {"name": "lookup"},
                "params": {"max_tokens": max_tokens, "temperature_milli": 500},
                "unit": unit, "input_price": input_price, "output_price": output_price}
    return {"unit": unit, "price": price}


def spec_for(kind: str, variant: int = 0, price: int = 0) -> dict:
    """A catalogue effective spec for `kind` — what a law file hands an oracle constructor."""
    return _spec(kind, variant, price)


def requests_for(kind: str, index: int) -> dict:
    if kind == "fetch":
        return {"uri": f"https://example.com/page/{index}"}
    if kind == "llm":
        return {"messages": [{"role": "user", "content": f"question {index}"}]}
    return {"label": f"reading-{index}"}


@st.composite
def oracle_specs(draw: Any) -> tuple:
    """(kind, name, spec, class) — one oracle's full identity, every kind drawn."""
    kind = draw(st.sampled_from(KINDS))
    variant = draw(st.integers(0, 3))
    price = draw(st.integers(0, 5))
    cls = draw(st.sampled_from(CLASSES))
    event(f"oracle kind: {kind}")
    return kind, f"{kind}-oracle", _spec(kind, variant, price), cls


#: Spend scenarios drawn BY NAME (D0118): each exists to make one wrong rule visible.
#: A scenario is (budget, oracles, steps, faults): `oracles` maps an id to (kind, spec);
#: `steps` is a sequence of (session, oracle id, request index); `faults` maps a step index
#: to the write it fails ("reservation" or "capture").
SPEND_CASES = {
    # a zero ceiling refuses even a free call — the plain inequality would admit it
    "zero-refuses-free": (
        {"scope": "M4", "unit": "nano-usd", "ceilings": {"total": 0, "clock": 0}},
        {"c": ("clock", _spec("clock", 0, 0))}, [(0, "c", 0)], {}),
    # a class the budget does not name is denied, however large the total
    "absent-class": (
        {"scope": "M4", "unit": "nano-usd", "ceilings": {"total": 100, "llm": 100}},
        {"f": ("fetch", _spec("fetch", 0, 1))}, [(0, "f", 0)], {}),
    # a unit that is not the budget's is denied, not converted
    "unit-mismatch": (
        {"scope": "M4", "unit": "nano-usd", "ceilings": {"total": 100, "fetch": 100}},
        {"f": ("fetch", _spec("fetch", 0, 1, unit="cents"))}, [(0, "f", 0)], {}),
    # exactly fits: the last admitted call lands on the ceiling, the next is refused
    "exact-fit": (
        {"scope": "M4", "unit": "nano-usd", "ceilings": {"total": 6, "fetch": 6}},
        {"f": ("fetch", _spec("fetch", 0, 3))}, [(0, "f", 0), (0, "f", 1), (0, "f", 2)], {}),
    # two sessions over one store: spend is the store's, not a session's
    "two-sessions-exhaust": (
        {"scope": "M4", "unit": "nano-usd", "ceilings": {"total": 5, "fetch": 5}},
        {"f": ("fetch", _spec("fetch", 0, 3))}, [(0, "f", 0), (1, "f", 1)], {}),
    # a paid call whose capture failed to write still counts, at its worst case
    "capture-write-fails-after-call": (
        {"scope": "M4", "unit": "nano-usd", "ceilings": {"total": 5, "fetch": 5}},
        {"f": ("fetch", _spec("fetch", 0, 3))}, [(0, "f", 0), (0, "f", 1)],
        {0: "capture"}),
    # a reservation that could not be written means no call at all
    "reservation-write-fails": (
        {"scope": "M4", "unit": "nano-usd", "ceilings": {"total": 5, "fetch": 5}},
        {"f": ("fetch", _spec("fetch", 0, 3))}, [(0, "f", 0), (0, "f", 0)],
        {0: "reservation"}),
    # a hit costs nothing and needs no budget headroom
    "hit-is-free": (
        {"scope": "M4", "unit": "nano-usd", "ceilings": {"total": 3, "fetch": 3}},
        {"f": ("fetch", _spec("fetch", 0, 3))}, [(0, "f", 0), (1, "f", 0), (0, "f", 0)], {}),
    # the world overruns an LLM's worst case: recorded, and seen by the next admission
    "llm-overrun-is-recorded": (
        {"scope": "M4", "unit": "nano-usd", "ceilings": {"total": 10000, "llm": 10000}},
        {"l": ("llm", _spec("llm", 0, input_price=0, output_price=1000, max_tokens=4))},
        [(0, "l", 0), (0, "l", 1), (0, "l", 2)], {"overrun": 3}),
    # the total ceiling binds across kinds
    "total-binds-across-kinds": (
        {"scope": "M4", "unit": "nano-usd",
         "ceilings": {"total": 4, "fetch": 4, "clock": 4}},
        {"f": ("fetch", _spec("fetch", 0, 3)), "c": ("clock", _spec("clock", 0, 2))},
        [(0, "f", 0), (0, "c", 0)], {}),
}


@st.composite
def spend_scenarios(draw: Any) -> tuple:
    """A random spend scenario: named budget shape, two or three oracles, up to six steps
    over two sessions, at most one injected fault."""
    shape = draw(st.sampled_from(("tight", "ample", "zero", "absent-class")))
    ceiling = {"tight": 5, "ample": 10_000, "zero": 0, "absent-class": 50}[shape]
    ceilings = {"total": ceiling, "fetch": ceiling, "llm": ceiling}
    if shape != "absent-class":
        ceilings["clock"] = ceiling
    oracles = {
        "f": ("fetch", _spec("fetch", 0, draw(st.integers(0, 3)))),
        "l": ("llm", _spec("llm", draw(st.integers(0, 1)), input_price=0,
                           output_price=draw(st.integers(1, 2)),
                           max_tokens=draw(st.integers(1, 3)))),
        "c": ("clock", _spec("clock", 0, 0)),
    }
    steps = draw(st.lists(st.tuples(st.integers(0, 1), st.sampled_from(sorted(oracles)),
                                    st.integers(0, 2)), min_size=1, max_size=6))
    faults: dict = {}
    fault = draw(st.sampled_from(("none", "reservation", "capture")))
    if fault != "none":
        faults[draw(st.integers(0, len(steps) - 1))] = fault
    event(f"spend budget shape: {shape}")
    event(f"spend fault: {fault}")
    return ({"scope": "M4", "unit": "nano-usd", "ceilings": ceilings}, oracles, steps, faults)


@st.composite
def differential_scenarios(draw: Any) -> tuple:
    """A scenario for the package/model differential: a mode per session, then the spend
    scenario's shape. Replay sessions see whatever the spend sessions captured."""
    budget, oracles, steps, faults = draw(spend_scenarios())
    modes = (draw(st.sampled_from((SPEND, REPLAY, None))), SPEND)
    event(f"first session mode: {modes[0]}")
    return budget, oracles, steps, faults, modes


# ------------------------------------------------------------------------ helpers


def _fresh_oracles(subject: Subject, oracles: dict, overrun: int = 0) -> dict:
    built = {}
    for oid, (kind, spec) in oracles.items():
        transport = FakeTransport(kind, overrun=overrun if kind == "llm" else 0)
        built[oid] = subject.oracle(kind, f"{kind}-{oid}", spec, "non-reproducible", transport)
    return built


def _arm(client: MemoryClient, fault: str | None) -> None:
    marker = {"reservation": b"reservation/1", "capture": b"capture/1"}.get(fault or "")
    client.fail_when = (lambda data, m=marker: m in data) if marker else None


def _outcome(subject: Subject, thunk: Any) -> tuple:
    """Run one invocation; classify it by the refusal it raised, if any."""
    try:
        return ("ok", thunk())
    except subject.novel_refused:
        return ("novel", None)
    except subject.spend_denied:
        return ("spend", None)
    except subject.write_failed:
        return ("write", None)
    except subject.conflict:
        return ("conflict", None)


# ------------------------------------------------------------------------ the checks


def check_descriptors(subject: Subject, kind: str, name: str, spec: dict, cls: str) -> None:
    """L4.1: the descriptor is the address of the full effective spec AND the declared
    class. Stable; moved by the name, by every spec field, by the class; unconstructible
    without a class from the vocabulary."""
    base = subject.descriptor(kind, name, spec, cls)
    assert base == subject.descriptor(kind, name, dict(spec), cls), "descriptor is not stable"
    assert base != subject.descriptor(kind, name + "-other", spec, cls), \
        "the name does not move the descriptor"
    for field in sorted(spec):
        moved = dict(spec)
        value = spec[field]
        moved[field] = ([["x", "y"]] if isinstance(value, list) else
                        value + 1 if isinstance(value, int) else
                        {"other": value} if isinstance(value, dict) or value is None else
                        str(value) + "-moved")
        assert subject.descriptor(kind, name, moved, cls) != base, (
            f"{kind}: changing spec field {field!r} left the descriptor where it was — "
            "the descriptor must carry the FULL effective spec (BRIEF §4)")
    for other in CLASSES:
        if other != cls:
            assert subject.descriptor(kind, name, spec, other) != base, (
                f"{kind}: class {other!r} and {cls!r} share one descriptor — the declared "
                "class is part of the identity [cites: pkm-determinism]")
    for bad in (None, "", "reproducible-ish"):
        try:
            subject.descriptor(kind, name, spec, bad)
        except subject.undeclared:
            continue
        raise AssertionError(f"{kind}: an oracle with class {bad!r} was constructed")
    transport = FakeTransport(kind)
    built = subject.oracle(kind, name, spec, cls, transport)
    assert subject.descriptor(kind, name, spec, cls) == _descriptor_of(subject, built), \
        "the constructed oracle's descriptor is not the declared one"
    assert transport.calls == [], "constructing an oracle touched its transport"


def _descriptor_of(subject: Subject, oracle: Any) -> str:
    return oracle.descriptor


def check_capture_before_read(subject: Subject, kind: str, spec: dict, fault: str) -> None:
    """L4.2: a caller receives only what a capture already in the store says. A failed
    write is a refusal and never a value; a returned ref resolves in a FRESH session; a
    tampered capture is refused on read, never served from memory."""
    client = MemoryClient()
    store = subject.store_remote(client)
    budget = {"scope": "M4", "unit": spec["unit"], "ceilings": {"total": 10**9, kind: 10**9}}
    oracle = subject.oracle(kind, f"{kind}-cbr", spec, "bit", FakeTransport(kind))
    request = requests_for(kind, 0)
    _arm(client, fault if fault != "none" else None)
    session = subject.session(store, SPEND, budget)
    outcome, ref = _outcome(subject, lambda: subject.invoke(session, oracle, request))
    client.fail_when = None
    if fault != "none":
        assert outcome == "write", (
            f"{kind}: the {fault} write failed and the invocation answered {outcome!r} — a "
            "value no capture holds reached the caller (P1)")
        return
    assert outcome == "ok", f"{kind}: a clean invocation answered {outcome!r}"
    fresh = subject.session(store, None, None)
    first = subject.read(session, ref)
    assert subject.read(fresh, ref) == first, (
        f"{kind}: a fresh session over the same store reads something else — the value came "
        "from somewhere other than the capture")
    assert subject.capture_value(fresh, ref)["tannen"] == "capture/1"
    key = key_for(ref)
    original = client.objects[key]
    client.tamper(key, original.replace(b"capture/1", b"capture/9"))
    try:
        subject.read(session, ref)
    except subject.integrity_error:
        pass
    else:
        raise AssertionError(f"{kind}: a tampered capture was read without complaint — the "
                             "value was not read back from the store")


def check_invoke_once(subject: Subject, kind: str, spec: dict, cls: str, repeats: int) -> None:
    """L4.3: the transport is reached at most once per (descriptor, input key) across any
    number of calls and sessions over one store; a different descriptor or request is a
    new question; a hit returns the identical capture."""
    store = subject.store_local()
    budget = {"scope": "M4", "unit": spec["unit"], "ceilings": {"total": 10**9, kind: 10**9}}
    transport = FakeTransport(kind)
    oracle = subject.oracle(kind, f"{kind}-once", spec, cls, transport)
    request = requests_for(kind, 1)
    sessions = [subject.session(store, SPEND, budget) for _ in range(2)]
    refs = {subject.invoke(sessions[i % 2], oracle, request) for i in range(repeats)}
    assert len(transport.calls) == 1, (
        f"{kind}: {repeats} invocations of one question reached the transport "
        f"{len(transport.calls)} times — a capture hit must never call (§3)")
    assert len(refs) == 1, f"{kind}: one question returned {len(refs)} different captures"
    ref = refs.pop()
    replay = subject.session(store, None, None)
    assert subject.invoke(replay, oracle, request) == ref
    assert subject.read(replay, ref) == subject.read(sessions[0], ref)

    other_transport = FakeTransport(kind)
    renamed = subject.oracle(kind, f"{kind}-once-other", spec, cls, other_transport)
    subject.invoke(sessions[0], renamed, request)
    assert len(other_transport.calls) == 1, (
        f"{kind}: a different oracle asking the same request was answered from the first "
        "oracle's capture — the capture key must include the descriptor")
    subject.invoke(sessions[1], oracle, requests_for(kind, 2))
    assert len(transport.calls) == 2, f"{kind}: a new request was served from an old capture"


def check_modes(subject: Subject, kind: str, spec: dict) -> None:
    """L4.4: replay-only is the default and the refusal comes BEFORE the transport, with
    nothing written; a capture made under spend replays with no transport at all."""
    store = subject.store_local()
    transport = FakeTransport(kind)
    oracle = subject.oracle(kind, f"{kind}-mode", spec, "in-distribution", transport)
    request = requests_for(kind, 0)
    for mode in (None, REPLAY):
        before = subject.iter_refs(store)
        session = subject.session(store, mode, None)
        try:
            subject.invoke(session, oracle, request)
        except subject.novel_refused:
            pass
        else:
            raise AssertionError(f"{kind}: mode {mode!r} answered a novel invocation")
        assert transport.calls == [], (
            f"{kind}: the replay-only refusal came after the transport was touched — "
            "refusing late still spends (BRIEF §5.10)")
        assert subject.iter_refs(store) == before, f"{kind}: a refused invocation wrote"
    budget = {"scope": "M4", "unit": spec["unit"], "ceilings": {"total": 10**9, kind: 10**9}}
    ref = subject.invoke(subject.session(store, SPEND, budget), oracle, request)
    silent = FakeTransport(kind)
    replay_oracle = subject.oracle(kind, f"{kind}-mode", spec, "in-distribution", silent)
    assert subject.invoke(subject.session(store, None, None), replay_oracle, request) == ref
    assert silent.calls == [], f"{kind}: a replay reached the transport"


def check_spend(subject: Subject, scenario: tuple) -> None:
    """L4.5: SpendGuard as a reserve-then-settle fold over the store. The expected outcome
    of every step is PREDICTED from the rule — admission iff ceiling > 0 and spent + worst
    case <= ceiling for the oracle's kind and for the total, with spent the sum over the
    scope's reservations of the settled price or, unsettled, the worst case — and the
    subject must agree step for step, including how many times each transport was called."""
    budget, oracles, steps, faults = scenario
    overrun = faults.get("overrun", 0)
    client = MemoryClient()
    store = subject.store_remote(client)
    built = _fresh_oracles(subject, oracles, overrun)
    sessions = [subject.session(store, SPEND, budget) for _ in range(2)]
    reservations: list[tuple[str, int, int | None]] = []   # (kind, worst, settled)
    captured: dict[tuple, Any] = {}
    first_reads: dict[tuple, Any] = {}

    def spent(kind: str | None) -> int:
        return sum(settled if settled is not None else worst
                   for k, worst, settled in reservations if kind is None or k == kind)

    for index, (s, oid, r) in enumerate(steps):
        kind, spec = oracles[oid]
        request = requests_for(kind, r)
        identity = (oid, r)
        calls_before = len(built[oid].transport.calls)
        fault = faults.get(index)
        _arm(client, fault if isinstance(fault, str) else None)
        outcome, ref = _outcome(subject, lambda: subject.invoke(sessions[s], built[oid], request))
        client.fail_when = None
        calls = len(built[oid].transport.calls) - calls_before

        if identity in captured:
            want, want_calls = "ok", 0
        else:
            worst = worst_case(kind, spec, request)
            ceilings = budget.get("ceilings", {})
            ok = (spec["unit"] == budget.get("unit") and kind in ceilings
                  and "total" in ceilings
                  and ceilings[kind] > 0 and ceilings["total"] > 0
                  and spent(kind) + worst <= ceilings[kind]
                  and spent(None) + worst <= ceilings["total"])
            if not ok:
                want, want_calls = "spend", 0
            elif fault == "reservation":
                want, want_calls = "write", 0
            elif fault == "capture":
                want, want_calls = "write", 1
                reservations.append((kind, worst, None))
            else:
                want, want_calls = "ok", 1
                response = FakeTransport(kind, overrun=overrun if kind == "llm" else 0)(
                    effective_request(kind, spec, request))
                reservations.append((kind, worst, actual_price(kind, spec, response)))
                captured[identity] = True
        assert (outcome, calls) == (want, want_calls), (
            f"step {index} ({oid}, request {r}, session {s}): got {outcome!r} with {calls} "
            f"transport call(s), the rule says {want!r} with {want_calls} — spent so far "
            f"{spent(None)} against {budget.get('ceilings')}")
        if outcome == "ok":
            value = subject.read(sessions[s], ref)
            first_reads.setdefault(identity, value)
            assert value == first_reads[identity], "a hit read differently from its capture"


def check_envelopes(subject: Subject, kind: str, spec: dict) -> None:
    """L4.6–L4.8: the frozen `capture/1` schema parses every positive vector and refuses
    every negative one; every capture the subject writes validates; the per-kind payload
    carries what BRIEF §4 names (Fetch's WARC-shaped request and response with the body by
    ref; the LLM's resolved model and usage; the Clock's instant, replayed exactly)."""
    import jsonschema

    jsonschema.Draft202012Validator.check_schema(capture_schema())
    for path in vector_paths("positive"):
        _validate(json.loads(path.read_text(encoding="utf-8")))
    for path in vector_paths("negative"):
        try:
            _validate(json.loads(path.read_text(encoding="utf-8")))
        except AssertionError:
            continue
        raise AssertionError(f"negative vector {path.name} was accepted")

    store = subject.store_local()
    budget = {"scope": "M4", "unit": spec["unit"], "ceilings": {"total": 10**9, kind: 10**9}}
    transport = FakeTransport(kind)
    oracle = subject.oracle(kind, f"{kind}-env", spec, "non-reproducible", transport)
    request = requests_for(kind, 3)
    session = subject.session(store, SPEND, budget)
    ref = subject.invoke(session, oracle, request)
    value = subject.capture_value(session, ref)
    _validate(value)
    assert value["kind"] == kind and value["request"] == effective_request(kind, spec, request)
    sent = transport.calls[0]
    world = FakeTransport(kind)(sent)
    read = subject.read(subject.session(store, None, None), ref)
    if kind == "fetch":
        assert read["body"] == world["body"], "the fetched body did not round-trip by ref"
        assert read["headers"] == world["headers"], "header order or repeats were lost"
        assert subject.get_bytes(store, value["response"]["body"]) == world["body"]
    elif kind == "llm":
        assert value["response"]["resolved_model"] == world["resolved_model"]
        assert value["response"]["usage"] == world["usage"]
        assert value["price"] == actual_price(kind, spec, world)
    else:
        assert read["instant"] == world["instant"], "the clock did not replay its instant"


def check_export(subject: Subject, pipeline: str, rows: list) -> None:
    """L4.10: an export admits only a `serve`-layer node, emits exactly that node's output
    bytes, deterministically; anything wider is refused by name (m1 §6's promise)."""
    serve = _layer_of(EXPORT_PIPELINES[pipeline]) == "serve"
    try:
        out = subject.export(pipeline, rows)
    except subject.layer_error:
        assert not serve, f"{pipeline} is serve-layer and its export was refused"
        return
    assert serve, (f"{pipeline} runs {sorted(EXPORT_PIPELINES[pipeline])} — wider than serve "
                   "— and was exported")
    assert out == subject.export(pipeline, rows), "an export is not deterministic"
    assert out == subject.output_bytes(pipeline, rows), \
        "an export emitted something other than its node's output"


def check_backend(subject: Subject, blobs: list) -> None:
    """L4.11: a store over an ObjectClient answers exactly as the local store does — refs,
    bytes, enumeration, the missing-ref refusal, the gc refusal — and holds write-once and
    verify-on-read against a remote that already holds, or later swaps, the bytes."""
    local = subject.store_local()
    client = MemoryClient()
    remote = subject.store_remote(client)
    local_refs = [subject.put_bytes(local, b) for b in blobs]
    remote_refs = [subject.put_bytes(remote, b) for b in blobs]
    assert local_refs == remote_refs, "the two backends address the same bytes differently"
    for ref, blob in zip(remote_refs, blobs):
        assert subject.get_bytes(remote, ref) == blob == subject.get_bytes(local, ref)
        assert subject.has(remote, ref) and subject.has(local, ref)
    assert subject.iter_refs(remote) == subject.iter_refs(local) == sorted(set(remote_refs))
    absent = address_bytes(b"never written " + encode(len(blobs)))
    for store in (local, remote):
        try:
            subject.get_bytes(store, absent)
        except subject.missing_ref:
            continue
        raise AssertionError("a missing ref was answered")
    assert subject.gc(remote) == subject.gc(local), "the two backends refuse gc differently"
    assert subject.iter_refs(remote) == sorted(set(remote_refs)), "gc changed the store"

    # write-once: a key that already holds (wrong) bytes is never overwritten ...
    victim = b"victim " + encode(len(blobs))
    ref = address_bytes(victim)
    client.objects[key_for(ref)] = b"squatter"
    subject.put_bytes(remote, victim)
    assert client.overwrites == 0 and client.objects[key_for(ref)] == b"squatter", \
        "a put overwrote an existing object — the store is write-once (BRIEF §4, §10)"
    # ... and verify-on-read refuses what the squatter left there
    for target in (ref, remote_refs[0] if remote_refs else ref):
        if target != ref:
            client.tamper(key_for(target), b"swapped behind the store's back")
        try:
            subject.get_bytes(remote, target)
        except subject.integrity_error:
            continue
        raise AssertionError("bytes that do not hash to their ref were returned — the "
                             "remote was trusted instead of verified")


def check_differential(subject: Subject, scenario: tuple) -> None:
    """L4.13's oracle: the subject and the model, driven through one scenario, agree on
    every step's outcome, every value read, and every transport's call count. Addresses
    are subject-relative and never compared; values are ref-free by construction (a fetch
    body is read back as bytes)."""
    got = _trace(subject, scenario)
    want = _trace(MODEL, scenario)
    assert got == want, f"the subject diverged from the model:\n  got  {got}\n  want {want}"


def _trace(subject: Subject, scenario: tuple) -> list:
    budget, oracles, steps, faults, modes = scenario
    client = MemoryClient()
    store = subject.store_remote(client)
    built = _fresh_oracles(subject, oracles, faults.get("overrun", 0))
    sessions = [subject.session(store, mode, budget if mode == SPEND else None)
                for mode in modes]
    out = []
    for index, (s, oid, r) in enumerate(steps):
        fault = faults.get(index)
        _arm(client, fault if isinstance(fault, str) else None)
        outcome, ref = _outcome(subject, lambda: subject.invoke(
            sessions[s], built[oid], requests_for(oracles[oid][0], r)))
        client.fail_when = None
        value = subject.read(sessions[s], ref) if outcome == "ok" else None
        out.append((index, outcome, value))
    out.append(("calls", {oid: len(o.transport.calls) for oid, o in sorted(built.items())}))
    return out


# ------------------------------------------------------------------------ mutants


class _ClassOutsideDescriptor(Subject):
    """The class is checked but not hashed: two classes, one identity."""
    name = "class-outside-descriptor"

    def descriptor_value(self, kind, name, spec, reproducibility):
        return {"tannen": "oracle/1", "kind": kind, "name": name, "spec": spec}


class _ReadBeforeCapture(Subject):
    """Swallows a failed capture write and serves the value from session memory."""
    name = "read-before-capture"

    def record(self, session, oracle, key, sent, response, reservation):
        try:
            return super().record(session, oracle, key, sent, response, reservation)
        except WriteFailed:
            ref = address({"unwritten": oracle.descriptor, "input_key": key})
            session.memo[ref] = response
            return ref

    def read(self, session, ref):
        if ref in session.memo:
            return session.memo[ref]
        return super().read(session, ref)


class _InvokeOnHit(Subject):
    """Calls the transport even when a capture exists, then returns the capture."""
    name = "invoke-on-hit"

    def invoke(self, session, oracle, request):
        key = self.input_key(request)
        if self.find_captures(session.store, oracle.descriptor, key) and session.mode == SPEND:
            self.call(oracle, effective_request(oracle.kind, oracle.spec, request))
        return super().invoke(session, oracle, request)


class _KeyIgnoresDescriptor(Subject):
    """Finds captures by input key alone: every oracle asking one request shares a record."""
    name = "key-ignores-descriptor"

    def find_captures(self, store, descriptor, key):
        return [ref for ref, v in store.values()
                if v.get("tannen") == "capture/1" and v.get("input_key") == key][:1]


class _TransportThenRefuse(Subject):
    """Refuses a novel replay-only invocation — after touching the transport."""
    name = "transport-then-refuse"

    def invoke(self, session, oracle, request):
        key = self.input_key(request)
        if session.mode != SPEND and not self.find_captures(session.store, oracle.descriptor, key):
            self.call(oracle, effective_request(oracle.kind, oracle.spec, request))
        return super().invoke(session, oracle, request)


class _ZeroMeansFree(Subject):
    """The plain inequality: a zero ceiling admits a zero-priced call."""
    name = "zero-means-free"

    def admissible(self, ceiling, spent, worst):
        return spent + worst <= ceiling


class _CheckAfterCall(Subject):
    """Calls, then asks SpendGuard — so a denial has already spent."""
    name = "check-after-call"

    def invoke(self, session, oracle, request):
        key = self.input_key(request)
        if session.mode == SPEND and not self.find_captures(session.store, oracle.descriptor, key):
            self.call(oracle, effective_request(oracle.kind, oracle.spec, request))
        return super().invoke(session, oracle, request)


class _CounterNotFold(Subject):
    """Keeps spend in a per-session counter: a second session starts from zero."""
    name = "counter-not-fold"

    def spent(self, session, scope, kind):
        return session.memo.get(("spent", kind), 0)

    def reserve(self, session, oracle, key, worst):
        ref = super().reserve(session, oracle, key, worst)
        for k in (oracle.kind, None):
            session.memo[("spent", k)] = session.memo.get(("spent", k), 0) + worst
        return ref


class _UnreservedCall(Subject):
    """Folds captures only — no reservation — so a paid call whose capture failed to write
    is spend nobody can see."""
    name = "unreserved-call"

    def spent(self, session, scope, kind):
        return sum(v["price"] for _, v in session.store.values()
                   if v.get("tannen") == "capture/1" and v.get("scope") == scope
                   and (kind is None or v.get("kind") == kind))


class _EnvelopeDropsUsage(Subject):
    """Writes an LLM capture without the provider's usage report."""
    name = "envelope-drops-usage"

    def response_value(self, session, kind, response):
        value = super().response_value(session, kind, response)
        value.pop("usage", None)
        return value


class _ExportAcceptsDerive(Subject):
    """Exports whatever it is handed."""
    name = "export-accepts-derive"

    def export(self, pipeline, rows):
        return self.output_bytes(pipeline, rows)


class _OverwriteOnPut(Subject):
    """Writes unconditionally: an existing object is replaced."""
    name = "overwrite-on-put"

    def store_put(self, store, data):
        ref = address_bytes(data)
        store.client.put(key_for(ref), data)
        return ref


class _TrustRemoteBytes(Subject):
    """Returns whatever the remote hands back, unverified."""
    name = "trust-remote-bytes"

    def store_get(self, store, ref):
        data = store.client.get(key_for(ref))
        if data is None:
            raise Missing(ref)
        return data


MUTANTS = {
    m.name: m for m in (
        _ClassOutsideDescriptor(), _ReadBeforeCapture(), _InvokeOnHit(),
        _KeyIgnoresDescriptor(), _TransportThenRefuse(), _ZeroMeansFree(),
        _CheckAfterCall(), _CounterNotFold(), _UnreservedCall(), _EnvelopeDropsUsage(),
        _ExportAcceptsDerive(), _OverwriteOnPut(), _TrustRemoteBytes(),
    )
}

CAUGHT_BY = {
    "class-outside-descriptor": "check_descriptors",
    "read-before-capture": "check_capture_before_read",
    "invoke-on-hit": "check_invoke_once",
    "key-ignores-descriptor": "check_invoke_once",
    "transport-then-refuse": "check_modes",
    "zero-means-free": "check_spend",
    "check-after-call": "check_spend",
    "counter-not-fold": "check_spend",
    "unreserved-call": "check_spend",
    "envelope-drops-usage": "check_envelopes",
    "export-accepts-derive": "check_export",
    "overwrite-on-put": "check_backend",
    "trust-remote-bytes": "check_backend",
}


# ------------------------------------------------------------------------ the harness


def _profile(max_examples: int) -> Any:
    from hypothesis import HealthCheck, settings

    return settings(
        max_examples=max_examples, deadline=None, derandomize=True,
        report_multiple_bugs=False,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )


def blob_lists() -> Any:
    return st.lists(st.binary(min_size=0, max_size=24), min_size=1, max_size=6, unique=True)


def export_rows() -> Any:
    return st.lists(st.fixed_dictionaries({"k": st.integers(-2, 2), "x": st.integers(-2, 2)}),
                    min_size=0, max_size=5)


def run_family(subject: Subject, family: str, max_examples: int = 25) -> None:
    """Run one model-checked family against `subject`; raise on the first counterexample.
    Named cases run unconditionally before any draw (D0118): a mutant must not survive
    because the search did not happen to reach the case that kills it."""
    from hypothesis import given

    profile = _profile(max_examples)

    def drive(strategies: dict, prop: Any) -> None:
        profile(given(**strategies)(prop))()

    if family == "check_descriptors":
        drive(dict(o=oracle_specs()), lambda o: check_descriptors(subject, *o))
    elif family == "check_capture_before_read":
        for kind in KINDS:
            for fault in ("none", "reservation", "capture"):
                check_capture_before_read(subject, kind, _spec(kind, 0, 1), fault)
    elif family == "check_invoke_once":
        for kind in KINDS:
            check_invoke_once(subject, kind, _spec(kind, 1, 1), "bit", 3)
        drive(dict(o=oracle_specs(), n=st.integers(1, 5)),
              lambda o, n: check_invoke_once(subject, o[0], o[2], o[3], n))
    elif family == "check_modes":
        for kind in KINDS:
            check_modes(subject, kind, _spec(kind, 0, 1))
    elif family == "check_spend":
        for case in sorted(SPEND_CASES):
            check_spend(subject, SPEND_CASES[case])
        drive(dict(s=spend_scenarios()), lambda s: check_spend(subject, s))
    elif family == "check_envelopes":
        for kind in KINDS:
            check_envelopes(subject, kind, _spec(kind, 1, 2))
    elif family == "check_export":
        for pipeline in sorted(EXPORT_PIPELINES):
            check_export(subject, pipeline, [{"k": 1, "x": 1}, {"k": 1, "x": -1}])
        drive(dict(p=st.sampled_from(sorted(EXPORT_PIPELINES)), rows=export_rows()),
              lambda p, rows: check_export(subject, p, rows))
    elif family == "check_backend":
        check_backend(subject, [b"", b"one", b"two"])
        drive(dict(blobs=blob_lists()), lambda blobs: check_backend(subject, blobs))
    elif family == "check_differential":
        for case in sorted(SPEND_CASES):
            budget, oracles, steps, faults = SPEND_CASES[case]
            for first in (SPEND, REPLAY, None):
                check_differential(subject, (budget, oracles, steps, faults, (first, SPEND)))
        drive(dict(s=differential_scenarios()), lambda s: check_differential(subject, s))
    else:
        raise AssertionError(f"unknown family {family!r}")


#: Every model-checked family. `check_differential` is deliberately outside — it is
#: L4.13's own oracle, not a family a mutant aims at (the m2/m3 rule).
FAMILIES = (
    "check_descriptors",
    "check_capture_before_read",
    "check_invoke_once",
    "check_modes",
    "check_spend",
    "check_envelopes",
    "check_export",
    "check_backend",
)
