"""The incremental (delta) executor — docs/specs/m3.md §7. A shell module: it reads and
writes the store and the trace store, which is why it is not in `tannen.kernel`.

**Per-node, caller-composed — there is no graph object.** M1's executor is deliberately
caller-side (`Node`, one derivation at a time) and nothing in BRIEF §8 mandates a circuit
runtime; L4's "random composite graphs" live where M2 already put composite plans, in the
frozen model's plan catalogue. A graph representation would be API surface with no law of
its own, and it can arrive later with one if demand appears.

- **`DeltaNode`** is a *declared* operator application — operator name plus parameters,
  as data. Incrementality is derived from declared structure (BRIEF P5) and a registered
  transform's body is opaque, so the incremental executor runs declared nodes and
  arbitrary transforms stay the reference executor's domain. Code a node needs (a
  predicate, a row map, a monoid, a group) is referenced BY NAME out of the registries
  below, because a lambda has no content address and a descriptor over one would be a
  lie [cites: pkm-event-identity].
- **State** is a content-addressed `incstate/1` value holding the node's integral refs.
  "The executor's state" is therefore a value in the store like any other — nothing
  hidden, nothing mutable, and a state ref is as inspectable as any relation.
- **`advance`** is one step: a pure function of `(descriptor, state, ledger, deltas)`,
  with the store and the trace as its only effects. A **tick** is the caller advancing
  sources first, then derived nodes in its own topological order, threading the ledger
  through and passing each node the deltas `advance` returned.
- **The contagion rule (§4, D0163)**: a node is delta-maintained iff no `anti_join` lies
  at or below it. At and above one, the caller passes child *integral* refs and declares
  the node `replay=True`; `advance` recomputes over those integrals and still emits Δout
  as the `diff`, so a parent never has to know which discipline its child used.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from tannen.executor import TraceIntegrityError, TraceStore
from tannen.kernel import delta as delta_calculus
from tannen.kernel import ops
from tannen.kernel.algebra import AbelianGroup, Monoid
from tannen.kernel.derivation import derivation_id
from tannen.kernel.encoding import content_address
from tannen.kernel.outcome import OperatorError, Quarantine
from tannen.kernel.refs import RefError, is_ref
from tannen.kernel.rel import Rel
from tannen.kernel.semiring import why_slots
from tannen.store import IntegrityError, MissingRef, Store

__all__ = [
    "Advanced",
    "DELTA_OPERATORS",
    "DELTA_OP_TAG",
    "DeltaNode",
    "GROUPS",
    "INCSTATE_TAG",
    "INCSTEP_TAG",
    "LEDGER_TAG",
    "Ledger",
    "MAPS",
    "MONOIDS",
    "PREDICATES",
    "advance",
    "register_group",
    "register_map",
    "register_monoid",
    "register_predicate",
]

#: The value tags this module mints. Versioned like every other tannen tag: a change of
#: shape is a new tag, never a reinterpretation of this one.
DELTA_OP_TAG = "deltaop/1"
INCSTATE_TAG = "incstate/1"
INCSTEP_TAG = "incstep/1"
LEDGER_TAG = "ledger/1"

#: The operators a `DeltaNode` may declare: M1's eight, plus `source` for the node that
#: consumes an `ingest_delta` result and maintains the ledger.
DELTA_OPERATORS: tuple[str, ...] = ("source",) + ops.OPERATORS


# --------------------------------------------------------------------- declared code
#
# A `DeltaNode`'s descriptor is the content address of its declared form, so the code it
# runs has to be nameable: these registries are how a predicate, a row map or an algebra
# gets a name that a descriptor can carry. They ship seeded with the M3 catalogue — the
# names the frozen law files declare — and `register_*` is how a caller adds its own.
# Re-registering the same name with a different object is refused: a descriptor that
# meant one thing yesterday and another today is worse than no descriptor at all.

PREDICATES: dict[str, Callable[[Mapping[str, Any]], bool]] = {}
MAPS: dict[str, tuple[Callable[[Mapping[str, Any]], Mapping[str, Any]], tuple[str, ...]]] = {}
MONOIDS: dict[str, Monoid] = {}
GROUPS: dict[str, AbelianGroup] = {}


def _register(registry: dict, kind: str, name: str, value: Any) -> None:
    if not isinstance(name, str) or not name:
        raise OperatorError(f"a {kind} id is a non-empty str, not {name!r}")
    existing = registry.get(name)
    if existing is not None and existing is not value:
        raise OperatorError(
            f"{kind} {name!r} is already registered as {existing!r} — a name a descriptor "
            "carries may not change meaning (docs/specs/m3.md §7)"
        )
    registry[name] = value


def register_predicate(name: str, predicate: Callable[[Mapping[str, Any]], bool]) -> str:
    """Name a `select` predicate so a `DeltaNode` can declare it. Returns the name."""
    if not callable(predicate):
        raise OperatorError(f"predicate {name!r}: {predicate!r} is not callable")
    _register(PREDICATES, "predicate", name, predicate)
    return name


def register_map(
    name: str, f: Callable[[Mapping[str, Any]], Mapping[str, Any]], schema: Iterable[str]
) -> str:
    """Name a `map_rows` function together with the schema it declares."""
    if not callable(f):
        raise OperatorError(f"map {name!r}: {f!r} is not callable")
    _register(MAPS, "map", name, (f, tuple(sorted(schema))))
    return name


def register_monoid(name: str, monoid: Monoid) -> str:
    """Name a law-checked `Monoid` for `aggregate`'s replacement form."""
    if not isinstance(monoid, Monoid) or isinstance(monoid, AbelianGroup):
        raise OperatorError(
            f"monoid {name!r}: {monoid!r} is not a Monoid — register an AbelianGroup with "
            "register_group, so the subtractive form is chosen by declaration (§4)"
        )
    _register(MONOIDS, "monoid", name, monoid)
    return name


def register_group(name: str, group: AbelianGroup) -> str:
    """Name a law-checked `AbelianGroup` for `aggregate`'s subtractive form (L3.8)."""
    if not isinstance(group, AbelianGroup):
        raise OperatorError(f"group {name!r}: {group!r} is not an AbelianGroup")
    _register(GROUPS, "group", name, group)
    return name


#: The M3 catalogue. These are the names the frozen law files declare, so the shipped
#: package must resolve them; they are ordinary registrations with no privilege.
register_predicate("x-positive", lambda row: row.get("x", 0) > 0)
register_map("k-only", lambda row: {"k": row["k"]}, ("k",))
register_monoid("sum", Monoid("sum", lambda a, b: a + b, 0, witnesses=tuple(range(-12, 13))))
register_group(
    "sum", AbelianGroup("sum", lambda a, b: a + b, 0, lambda a: -a, witnesses=tuple(range(-12, 13)))
)


# ------------------------------------------------------------------------ the ledger


class Ledger:
    """The dead-set carrier (docs/specs/m3.md §6): srcrow refs whose net count in their
    source is now zero, as a content-addressed `ledger/1` value.

        {"tannen": "ledger/1", "dead": ["sha256:…", …]}

    sorted, deduplicated, and every entry a ref in the pinned grammar
    [cites: provenance-ref-grammar].

    It is **data on the run, not a mutable global**: every `Ledger` is frozen, every
    change returns a new one, and `advance` takes a ledger ref and returns one — so the
    kernel stays pure and the executor's state is inspectable like any other value.

    `dead` is its whole content. An earlier draft carried a second list — retired
    `anti_join` citation addresses — and the model refuted the mechanism it served: under
    the contagion rule a superseded address never reaches an integral in the first place,
    because everything that could cite it replays (D0163).
    """

    __slots__ = ("_dead",)

    #: The ledger a stream starts from. Set below the class body, where `Ledger` exists.
    EMPTY: Ledger

    def __init__(self, dead: Iterable[str] = ()) -> None:
        refs = tuple(sorted(set(dead)))
        for ref in refs:
            if not is_ref(ref):
                raise RefError(f"a ledger holds refs in the pinned grammar, not {ref!r}")
        self._dead = refs

    @property
    def dead(self) -> frozenset[str]:
        return frozenset(self._dead)

    def with_dead(self, refs: Iterable[str]) -> Ledger:
        """This ledger plus `refs` — a retraction that emptied a row's count."""
        return Ledger(self._dead + tuple(refs))

    def without(self, refs: Iterable[str]) -> Ledger:
        """This ledger minus `refs` — an arrival RESURRECTS its ref (§6). The ref is the
        same because the bytes are: a source row's atom depends on `(source, row)` only."""
        drop = frozenset(refs)
        return Ledger(ref for ref in self._dead if ref not in drop)

    def to_value(self) -> dict[str, Any]:
        return {"tannen": LEDGER_TAG, "dead": list(self._dead)}

    def ref(self) -> str:
        return content_address(self.to_value())

    @classmethod
    def from_value(cls, value: Any) -> Ledger:
        if not isinstance(value, Mapping) or value.get("tannen") != LEDGER_TAG:
            raise OperatorError(f"not a {LEDGER_TAG} value: {value!r}")
        dead = value.get("dead")
        if not isinstance(dead, list):
            raise OperatorError(f"{LEDGER_TAG}: dead is a list of refs, not {dead!r}")
        return cls(dead)

    def __contains__(self, ref: object) -> bool:
        return ref in self._dead

    def __len__(self) -> int:
        return len(self._dead)

    def __iter__(self):
        return iter(self._dead)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Ledger) and other._dead == self._dead

    def __hash__(self) -> int:
        return hash(self._dead)

    def __repr__(self) -> str:
        return f"Ledger({len(self._dead)} dead)"


Ledger.EMPTY = Ledger()


# -------------------------------------------------------------------- the declared node

#: Per operator: the parameters it requires, and how many input refs a step takes.
_REQUIRED: dict[str, tuple[str, ...]] = {
    "source": (),
    "select": ("predicate_id",),
    "project": ("columns",),
    "map_rows": ("map_id",),
    "union": (),
    "join": ("on",),
    "distinct": (),
    "anti_join": ("on",),
    "aggregate": ("by", "column", "into"),
}
_ARITY: dict[str, int] = {
    "source": 1, "select": 1, "project": 1, "map_rows": 1, "union": 2,
    "join": 2, "distinct": 1, "anti_join": 2, "aggregate": 1,
}
#: Column-set parameters: order is not part of the declared node, so they are sorted.
_COLUMN_PARAMS = frozenset({"columns", "on", "by"})
#: The operators whose delta rule is replacement whatever the caller declares (§4).
_ALWAYS_REPLAYS = frozenset({"distinct", "aggregate", "anti_join"})


class DeltaNode:
    """A declared operator application. Two spellings of the same node are the same
    descriptor, and a different operand order or parameter is a different one.

    Parameters are validated and the code they name is resolved **here**, when the node
    is declared — not at the tick. An unknown `predicate_id` is a mistake about the plan,
    and a plan's mistakes should not wait for data to arrive to be found.
    """

    __slots__ = ("operator", "params", "replay", "descriptor")

    def __init__(self, operator: str, *, replay: bool = False, **params: Any) -> None:
        if operator not in DELTA_OPERATORS:
            raise OperatorError(
                f"{operator!r} is not a delta operator; declared nodes are "
                f"{list(DELTA_OPERATORS)} (docs/specs/m3.md §7)"
            )
        if type(replay) is not bool:
            raise OperatorError(f"replay is a bool, not {replay!r}")
        if replay and operator == "source":
            raise OperatorError(
                "source: a source has no children to replay over — it consumes an "
                "ingest_delta result and maintains the ledger (docs/specs/m3.md §6, §7). "
                "Accepting the flag and ignoring it would put a word in the descriptor "
                "that means nothing"
            )
        declared = _declared_params(operator, params)
        self.operator = operator
        self.params = declared
        self.replay = replay or operator in _ALWAYS_REPLAYS
        self.descriptor = content_address(
            {
                "tannen": DELTA_OP_TAG,
                "operator": operator,
                "params": declared,
                "replay": self.replay,
            }
        )

    @property
    def arity(self) -> int:
        """How many input refs one step of this node takes."""
        return _ARITY[self.operator]

    def __eq__(self, other: object) -> bool:
        return isinstance(other, DeltaNode) and other.descriptor == self.descriptor

    def __hash__(self) -> int:
        return hash(self.descriptor)

    def __repr__(self) -> str:
        return f"DeltaNode({self.operator!r}, {self.params!r}, replay={self.replay})"


def _declared_params(operator: str, params: Mapping[str, Any]) -> dict[str, Any]:
    """The canonical declared form of `params`, refusing by name."""
    required = _REQUIRED[operator]
    allowed = set(required)
    if operator == "aggregate":
        allowed |= {"monoid_id", "group_id"}
    unknown = sorted(set(params) - allowed)
    if unknown:
        raise OperatorError(
            f"{operator}: unknown parameter(s) {unknown}; it declares {sorted(allowed)}"
        )
    missing = [name for name in required if name not in params]
    if missing:
        raise OperatorError(f"{operator}: missing parameter(s) {missing}")
    if operator == "aggregate":
        folds = [name for name in ("monoid_id", "group_id") if name in params]
        if len(folds) != 1:
            raise OperatorError(
                "aggregate: declare exactly one of monoid_id (replacement) or group_id "
                "(the subtractive form) — the choice of rule is declared, never inferred "
                "(docs/specs/m3.md §4, L3.8)"
            )
    declared: dict[str, Any] = {}
    for name in sorted(params):
        value = params[name]
        if name in _COLUMN_PARAMS:
            columns = tuple(value)
            if not columns or any(not isinstance(c, str) for c in columns):
                raise OperatorError(f"{operator}: {name} is a non-empty tuple of column names")
            if len(set(columns)) != len(columns):
                raise OperatorError(f"{operator}: duplicate column in {name} {columns!r}")
            declared[name] = sorted(columns)  # a list: the M0 encoder refuses tuples
            continue
        if not isinstance(value, str) or not value:
            raise OperatorError(f"{operator}: {name} is a non-empty str, got {value!r}")
        declared[name] = value
    for name, registry, kind in (
        ("predicate_id", PREDICATES, "predicate"),
        ("map_id", MAPS, "map"),
        ("monoid_id", MONOIDS, "monoid"),
        ("group_id", GROUPS, "group"),
    ):
        if name in declared and declared[name] not in registry:
            raise OperatorError(
                f"{operator}: {kind} {declared[name]!r} is not registered — register it "
                f"with tannen.incremental.register_{kind}; known: {sorted(registry)}"
            )
    return declared


# ------------------------------------------------------------------------ one step


@dataclass(frozen=True)
class Advanced:
    """What one `advance` did. Every field is a store ref, so a tick is inspectable."""

    step_id: str
    state_ref: str | None
    delta_ref: str | None
    ledger_ref: str
    rebuilt: bool  #: False when this step's output was already in the store or the trace
    quarantined_ref: str | None = None  #: rows that failed in user code, if any
    quarantine: Quarantine | None = None  #: set when the node failed as a whole (P3)


def advance(
    store: Store,
    traces: TraceStore,
    node: DeltaNode,
    state_ref: str | None,
    delta_refs: Iterable[str],
    ledger_ref: Any,
    *,
    record: bool = False,
) -> Advanced:
    """One tick of one declared node (docs/specs/m3.md §7).

    `state_ref` is `None` on the first tick. `delta_refs` are refs of `rel/1` values: the
    child *deltas* for a delta-maintained node, the child *integrals* for a replaying one
    (§4's contagion rule), and an `ingest_delta` result for a `source`. `ledger_ref` is a
    `Ledger` or the ref of one; the ledger value is written on every call, so the ref this
    returns always resolves.

    **Every step is its own derivation.** `step_id` is the existing `derivation_id` over
    the node's descriptor and the step's content-addressed inputs — the state ref, the
    ledger ref and the delta refs — and it holds as an identity because a step is a pure
    function of exactly those. It inherits `derivation_id`'s frozen order-insensitivity
    (m1 §8, L1.13): for a binary node the operand order is therefore NOT part of the step
    id, which is the M1 property M1's own `Node(transform, inputs)` already has, carried
    forward unchanged rather than quietly diverged from (D0167).

    **The trace is consulted, and by default not written.** A recorded output that no
    longer resolves is not a cache miss — it raises `TraceIntegrityError`, the M1 rule
    (L1.14) one step on — and a recorded output that does resolve is served without
    recomputing. Recording is the caller's act (`record=True`), exactly as M1 makes it a
    policy choice between `AlwaysRebuild` and `VerifyingTrace`; the default is off
    because frozen L3.15 pins that a plain `advance` leaves `step_id` free for the caller
    to record. Either way a replay writes nothing new, because everything a step produces
    is content-addressed: `rebuilt` reports whether this step's output was new to the
    store, which is the honest measurement of "did anything get built".

    A step whose operator quarantines as a whole writes no trace, leaves state unmoved,
    and reports the `Quarantine` (BRIEF P3, matching the reference executor). Quarantined
    ROWS are stored and named by `quarantined_ref`, and are deliberately NOT part of the
    `incstep/1` value: they are reports about a tick, never state (§7), so a step served
    from the trace carries none — nothing ran, so there is nothing to report on.
    """
    if not isinstance(node, DeltaNode):
        raise OperatorError(f"advance: {node!r} is not a DeltaNode")
    refs = tuple(delta_refs)
    for ref in refs:
        if not is_ref(ref):
            raise RefError(f"advance: a delta ref is a store ref, not {ref!r}")
    if len(refs) != node.arity:
        raise OperatorError(
            f"advance: {node.operator} takes {node.arity} input ref(s), got {len(refs)}"
        )
    if state_ref is not None and not is_ref(state_ref):
        raise RefError(f"advance: a state ref is a store ref or None, not {state_ref!r}")
    ledger = ledger_ref if isinstance(ledger_ref, Ledger) else _load_ledger(store, ledger_ref)
    ledger_in = store.put_value(ledger.to_value())  # idempotent; makes the ref resolvable

    inputs = list(refs) + [ledger_in] + ([state_ref] if state_ref is not None else [])
    step_id = derivation_id(node.descriptor, inputs)

    recorded = traces.lookup(step_id)
    if recorded is not None:
        try:
            step = store.get_value(recorded)
        except (MissingRef, IntegrityError, RefError) as exc:
            raise TraceIntegrityError(
                f"{step_id}: the trace names {recorded}, which does not resolve in the "
                f"store ({type(exc).__name__}: {exc}) — not a cache miss (docs/specs/"
                "m1.md §8, m3 §7)"
            ) from exc
        if not isinstance(step, Mapping) or step.get("tannen") != INCSTEP_TAG:
            raise TraceIntegrityError(
                f"{step_id}: the trace names {recorded}, which is not a {INCSTEP_TAG} value"
            )
        return Advanced(
            step_id=step_id,
            state_ref=step["state"],
            delta_ref=step["delta"],
            ledger_ref=step["ledger"],
            rebuilt=False,
        )

    state = _load_state(store, state_ref)
    try:
        computed = _compute(store, node, state, refs, ledger)
    except _Quarantined as stopped:
        return Advanced(
            step_id=step_id,
            state_ref=state_ref,
            delta_ref=None,
            ledger_ref=ledger_in,
            rebuilt=True,
            quarantine=stopped.quarantine,
        )

    out_state, out_delta_ref, out_ledger, quarantined = computed
    new_state_ref = store.put_value(out_state)
    out_ledger_ref = store.put_value(out_ledger.to_value())
    quarantined_ref = (
        store.put_value(quarantined.to_value()) if quarantined is not None and len(quarantined) else None
    )
    step_value = {
        "tannen": INCSTEP_TAG,
        "delta": out_delta_ref,
        "ledger": out_ledger_ref,
        "state": new_state_ref,
    }
    step_ref = content_address(step_value)
    rebuilt = not store.has(step_ref)  # content addressing is the memo: a replay is not a build
    store.put_value(step_value)
    if record:
        traces.record(step_id, step_ref)
    return Advanced(
        step_id=step_id,
        state_ref=new_state_ref,
        delta_ref=out_delta_ref,
        ledger_ref=out_ledger_ref,
        rebuilt=rebuilt,
        quarantined_ref=quarantined_ref,
    )


# ------------------------------------------------------------------------ the step body


class _Quarantined(Exception):
    """A node-level quarantine, carried out of `_compute` so the step moves nothing."""

    def __init__(self, quarantine: Quarantine) -> None:
        super().__init__(quarantine.detail)
        self.quarantine = quarantine


def _compute(
    store: Store,
    node: DeltaNode,
    state: Mapping[str, Any] | None,
    refs: tuple[str, ...],
    ledger: Ledger,
) -> tuple[dict[str, Any], str, Ledger, Rel | None]:
    """The step body: `(new incstate/1 value, Δout ref, new ledger, quarantined rows)`.

    The three disciplines of §4 meet here and nowhere else — a source advance (the only
    place the ledger moves), delta maintenance (linear operators are their own rule;
    `join` is bilinear), and replacement over integrals (the non-monotone operators, and
    anything the caller declared `replay=True` because an `anti_join` lies below it).
    Whatever the discipline, the node emits a Δout, so a parent never has to know which
    one its child used.
    """
    inputs = [_load_rel(store, ref) for ref in refs]
    held_output = _load_rel(store, state["output"]) if state is not None else None
    held: list[str] = []
    quarantined: Rel | None = None

    if node.operator == "source":
        source_delta = inputs[0]
        out_old = held_output if held_output is not None else _empty_like(source_delta)
        ledger, out_new = _advance_source(out_old, source_delta, ledger)
        # A source delta IS its own Δout, so there is nothing new to write for it.
        return _state_value(store, out_new), refs[0], ledger, None

    dead = ledger.dead

    if node.operator == "aggregate" and "group_id" in node.params:
        # The SUBTRACTIVE form (L3.8): the input integral is held so each touched group's
        # fold can be maintained through the declared group's inverse rather than redone.
        in_new = inputs[0]
        in_old = _held(store, state, 0, in_new)
        by, into = tuple(node.params["by"]), node.params["into"]
        out_old = held_output if held_output is not None else Rel._build(
            tuple(sorted(by + (into,))), in_new.annotations, in_new.annotations_reason, {}
        )
        out_new = delta_calculus.group_aggregate_delta(
            in_old, in_new, by, GROUPS[node.params["group_id"]],
            _value_of(node.params["column"]), into, out_old,
        )
        delta_out = delta_calculus.replace_delta(out_new, out_old)
        held = [store.put_value(in_new.to_value())]
    elif node.replay:
        # Replacement (§4): the inputs ARE the children's new integrals, and recomputing
        # over them IS the new output integral — DBSP's `op^Δ = D ∘ op ∘ I`, unoptimised.
        out_new, quarantined = _operate(node, inputs)
        out_old = held_output if held_output is not None else _empty_like(out_new)
        delta_out = delta_calculus.replace_delta(out_new, out_old)
    elif node.operator == "join":
        d_a, d_b = inputs
        a_old = _held(store, state, 0, d_a)
        b_old = _held(store, state, 1, d_b)
        a_new = delta_calculus.apply(a_old, d_a, dead)
        b_new = delta_calculus.apply(b_old, d_b, dead)
        delta_out = delta_calculus.join_delta(
            a_old, a_new, d_a, b_old, b_new, d_b, tuple(node.params["on"])
        )
        out_old = held_output if held_output is not None else _empty_like(delta_out)
        out_new = delta_calculus.apply(out_old, delta_out, dead)
        held = [store.put_value(a_new.to_value()), store.put_value(b_new.to_value())]
    else:
        # Linear (§4): the operator is its own delta rule, because the M1 semiring rules
        # are sign-blind — nothing new to derive, and nothing new to get wrong.
        delta_out, quarantined = _operate(node, inputs)
        out_old = held_output if held_output is not None else _empty_like(delta_out)
        out_new = delta_calculus.apply(out_old, delta_out, dead)

    return (
        _state_value(store, out_new, held),
        store.put_value(delta_out.to_value()),
        ledger,
        quarantined,
    )


def _advance_source(out_old: Rel, source_delta: Rel, ledger: Ledger) -> tuple[Ledger, Rel]:
    """A source advance, and the only place `dead` moves (§6).

    An arrival's ref is discarded **before** the `apply`, not after: applying first would
    let the valuation kill the very witness the arrival carries, and the witnessed-row
    alarm would fire on a perfectly lawful stream. The model's `retract-rearrive` stream
    found that ordering wrong during pre-freeze validation, and the order is the rule.
    The ref is the same one the row had before it died because a `srcrow/1` ref depends
    on `(source, row)` and on nothing else — resurrection is content addressing working,
    not a special case.

    A retraction adds its ref **after**, and only when the row it retracts is gone from
    the resulting integral — which is exactly the ledger's definition, "srcrow refs whose
    net count in their source is now zero".
    """
    S = source_delta.annotations
    counts = delta_calculus.group_slots(S)
    if len(counts) != 1:
        raise OperatorError(
            f"source: {S.name} carries {len(counts)} group components, and how many copies "
            "an entry moves is read from exactly one (docs/specs/m3.md §6)"
        )
    moves = [
        (key, delta_calculus.at_slot(annotation, counts[0]), _atoms(S, annotation))
        for key, _, annotation in source_delta._items()
    ]
    ledger = ledger.without(
        atom for _, moved, atoms in moves if moved > 0 for atom in atoms
    )
    out_new = delta_calculus.apply(out_old, source_delta, ledger.dead)
    present = {key for key, _, _ in out_new._items()}
    ledger = ledger.with_dead(
        atom
        for key, moved, atoms in moves
        if moved <= 0 and key not in present
        for atom in atoms
    )
    return ledger, out_new


def _operate(node: DeltaNode, inputs: list[Rel]) -> tuple[Rel, Rel | None]:
    """Apply the node's declared operator to `inputs`; a node-level `Quarantine` leaves
    through `_Quarantined`, so the step moves nothing (BRIEF P3)."""
    params = node.params
    operator = node.operator
    if operator == "select":
        outcome = ops.select(inputs[0], PREDICATES[params["predicate_id"]])
    elif operator == "project":
        outcome = ops.project(inputs[0], tuple(params["columns"]))
    elif operator == "map_rows":
        f, schema = MAPS[params["map_id"]]
        outcome = ops.map_rows(inputs[0], f, schema)
    elif operator == "union":
        outcome = ops.union(inputs[0], inputs[1])
    elif operator == "join":
        outcome = ops.join(inputs[0], inputs[1], tuple(params["on"]))
    elif operator == "distinct":
        outcome = ops.distinct(inputs[0])
    elif operator == "anti_join":
        outcome = ops.anti_join(inputs[0], inputs[1], tuple(params["on"]))
    elif operator == "aggregate":
        outcome = ops.aggregate(
            inputs[0], tuple(params["by"]), MONOIDS[params["monoid_id"]],
            _value_of(params["column"]), params["into"],
        )
    else:  # pragma: no cover — DELTA_OPERATORS and this dispatch move together
        raise OperatorError(f"advance: no delta rule for {operator!r}")
    if isinstance(outcome, Quarantine):
        raise _Quarantined(outcome)
    return outcome.rel, outcome.quarantined


def _value_of(column: str) -> Callable[[Mapping[str, Any]], Any]:
    return lambda row: row[column]


# ------------------------------------------------------------------------ state and loads


def _state_value(store: Store, output: Rel, inputs: Iterable[str] = ()) -> dict[str, Any]:
    """The `incstate/1` value: the node's integral refs — the output always, the inputs
    where the rule needs them (a `join` keeps both children's; a subtractive `aggregate`
    keeps its input's). Nothing else is state: a delta is an evaluation artifact (§5.1),
    and the ledger is threaded by the caller."""
    return {
        "tannen": INCSTATE_TAG,
        "inputs": list(inputs),
        "output": store.put_value(output.to_value()),
    }


def _load_state(store: Store, state_ref: str | None) -> Mapping[str, Any] | None:
    if state_ref is None:
        return None
    value = store.get_value(state_ref)
    if not isinstance(value, Mapping) or value.get("tannen") != INCSTATE_TAG:
        raise OperatorError(f"advance: {state_ref} is not an {INCSTATE_TAG} value")
    return value


def _load_ledger(store: Store, ledger_ref: Any) -> Ledger:
    if not is_ref(ledger_ref):
        raise RefError(f"advance: a ledger ref is a store ref or a Ledger, not {ledger_ref!r}")
    return Ledger.from_value(store.get_value(ledger_ref))


def _load_rel(store: Store, ref: str) -> Rel:
    return Rel.from_value(store.get_value(ref))


def _held(store: Store, state: Mapping[str, Any] | None, index: int, like: Rel) -> Rel:
    """A held input integral out of the state, or an empty relation shaped like `like` on
    the node's first tick — built from `like`'s own semiring and schema, so a first tick
    never silently re-defaults the annotation choice."""
    if state is not None:
        refs = state.get("inputs") or ()
        if index < len(refs):
            return _load_rel(store, refs[index])
    return _empty_like(like)


def _empty_like(rel: Rel) -> Rel:
    return Rel._build(rel.schema, rel.annotations, rel.annotations_reason, {})


def _atoms(semiring: Any, annotation: Any) -> frozenset[str]:
    """Every ref mentioned by every `Why` the annotation carries."""
    out: set[str] = set()
    for path in why_slots(semiring):
        for support in delta_calculus.at_slot(annotation, path):
            out |= set(support)
    return frozenset(out)
