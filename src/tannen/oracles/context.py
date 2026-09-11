"""The invocation context: invoke iff no capture, capture before read, replay-only by default,
and SpendGuard as a reserve-then-settle fold over the store (docs/specs/m4.md §3, §4;
L4.2–L4.5, L4.7, L4.8, L4.13).

**One call, in this order, and the order is the law's** — frozen L4.13 compares every
step's outcome with the frozen model's:

  1. the request is exactly its kind's variable part, or `RequestError`;
  2. its input key, and one scan of the store (§10 excludes performance — every lookup and
     every fold is a full scan, deliberately);
  3. more than one capture for (descriptor, input key): `CaptureConflict`; one: its ref is
     the answer, in any mode, at any budget, for free [cites: pkm-event-identity];
  4. not `SPEND`: `NovelInvocationRefused` — before the transport, having written nothing;
  5. the worst case, the transport's own preflight (what it could never send is refused
     while nothing is spent), then admission: the budget names a scope, a unit and a ceiling
     for the kind and the total, the units match, and for both `ceiling > 0 and spent + worst
     <= ceiling` — so a zero ceiling refuses even a free call;
  6. a `reservation/1` is written EXCLUSIVELY — a racing session that already holds it means
     this one calls nothing — and only then is the transport called;
  7. the answer is normalised (or refused as `MalformedResponse`, its reservation standing),
     a Fetch body is written by ref and read back, then the `capture/1`, exclusively; its ref
     is returned.

A write that does not happen, may not have happened, or finds its key already taken is
`CaptureWriteFailed`: before the call nothing is called, after it the value is withheld.
`read` returns what the capture, read back and verified, says — never a copy held in memory.

**Spend is a fold, never a counter.** For a scope, `spent` sums over its reservations the
settled price of the captures that name each, or, if none does, its worst case — so a second
session cannot start again from zero and a paid call whose capture failed still counts. A
capture must agree with the reservation it names; two naming one both count. Anything the fold
cannot read honestly — a malformed value, a capture contradicting its reservation, a scope
holding another unit — makes spend unknowable, and admission denies: an unknowable spend is
not zero.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from typing import Any

from tannen.kernel.encoding import decode_canonical, encode_canonical
from tannen.kernel.refs import is_ref
from tannen.oracles.budget import Budget
from tannen.oracles.errors import (
    CaptureConflict,
    CaptureWriteFailed,
    NotACapture,
    NovelInvocationRefused,
    SpendDenied,
)
from tannen.oracles.identity import Oracle, input_key, tagged_value
from tannen.store import AlreadyStored, IntegrityError

__all__ = ["CAPTURE_TAG", "Mode", "Oracles", "REPLAY", "RESERVATION_TAG", "SPEND", "spent"]

CAPTURE_TAG = "capture/1"
RESERVATION_TAG = "reservation/1"
#: The fields a capture must share with the reservation it settles.
_SETTLES = ("kind", "oracle", "input_key", "scope", "unit")


class Mode(Enum):
    REPLAY = "replay"
    SPEND = "spend"


#: Replay-only is the default (BRIEF §5.10); `SPEND` is the one spelling that can call.
REPLAY = Mode.REPLAY
SPEND = Mode.SPEND

Values = tuple[tuple[str, dict], ...]


def _tagged(store: Any) -> Values:
    """Every verified object that decodes as a tagged value, with its ref. `IntegrityError`
    propagates: a store whose bytes do not verify cannot be folded."""
    out = []
    for ref in sorted(store.iter_refs()):
        value = tagged_value(store.get_bytes(ref))
        if value is not None:
            out.append((ref, value))
    return tuple(out)


def _captures(values: Values, descriptor: str, key: str) -> list[str]:
    return [ref for ref, v in values if v["tannen"] == CAPTURE_TAG
            and v.get("oracle") == descriptor and v.get("input_key") == key]


def _unknowable(value: dict, why: str) -> SpendDenied:
    return SpendDenied(
        f"spend is unknowable: the store holds a {value['tannen']} value that {why} — an "
        "unknowable spend is not zero (docs/specs/m4.md §4)"
    )


def spent(values: Values, scope: str, unit: str, kind: str | None = None) -> int:
    """The fold: over the scope's reservations, the settled price of the captures that name
    each (summed: a duplicate can only raise spend), or the reservation's worst case."""
    reservations: dict[str, dict] = {}
    for ref, value in values:
        if value["tannen"] != RESERVATION_TAG:
            continue
        worst = value.get("worst_case")
        if not all(isinstance(value.get(f), str) for f in _SETTLES) or type(worst) is not int \
                or worst < 0:
            raise _unknowable(value, f"lacks what the fold reads ({sorted(value)})")
        reservations[ref] = value
    settled: dict[str, int] = {}
    for _, value in values:
        if value["tannen"] != CAPTURE_TAG:
            continue
        named, price = value.get("reservation"), value.get("price")
        reservation = reservations.get(named) if is_ref(named) else None
        if reservation is None or type(price) is not int or price < 0:
            raise _unknowable(value, "names no reservation in the store, or no integer price")
        if any(value.get(f) != reservation[f] for f in _SETTLES):
            raise _unknowable(value, f"contradicts the reservation it names on {list(_SETTLES)}")
        settled[named] = settled.get(named, 0) + price
    total = 0
    for ref, reservation in reservations.items():
        if reservation["scope"] != scope:
            continue
        if reservation["unit"] != unit:
            raise _unknowable(reservation, f"counts {reservation['unit']!r} in scope {scope!r}, "
                                           f"where the budget counts {unit!r} — never converted")
        if kind is None or reservation["kind"] == kind:
            total += settled.get(ref, reservation["worst_case"])
    return total


def _admit(budget: Budget | None, oracle: Oracle, worst: int, values: Values) -> None:
    who = f"{oracle.kind} {oracle.name!r}"
    if budget is None:
        raise SpendDenied(
            f"{who}: default-deny — no budget was given (tannen run --budget PATH; "
            "Oracles(..., budget=load_budget(...)))"
        )
    if not budget.scope or not budget.unit:
        raise SpendDenied(
            f"{who}: default-deny — the budget names no scope and no unit, so it authorises "
            "nothing (docs/specs/m4.md §4)"
        )
    if oracle.unit != budget.unit:
        raise SpendDenied(
            f"{who}: priced in {oracle.unit!r}, and the budget counts {budget.unit!r} — refused, "
            "never converted"
        )
    for kind in (oracle.kind, "total"):
        ceiling = budget.ceilings.get(kind)
        if ceiling is None:
            raise SpendDenied(f"the budget names no {kind!r} ceiling: default-deny")
        already = spent(values, budget.scope, budget.unit, None if kind == "total" else kind)
        if not (ceiling > 0 and already + worst <= ceiling):
            raise SpendDenied(
                f"{kind}: spent {already} + worst case {worst} against ceiling {ceiling} "
                f"{budget.unit} in scope {budget.scope!r}"
                + (" — a zero ceiling authorises nothing, not even a free call" if ceiling == 0
                   else "")
            )


def _attempt(values: Values, descriptor: str, key: str, scope: str) -> int:
    """1 + the reservations already made for this question in this scope, so a retry after a
    failed capture write is a second reservation rather than the first one's bytes again."""
    return 1 + sum(1 for _, v in values if v["tannen"] == RESERVATION_TAG
                   and v.get("oracle") == descriptor and v.get("input_key") == key
                   and v.get("scope") == scope)


def _write(what: str, thunk: Callable[[], str]) -> str:
    after = ("; nothing was called" if what == "the reservation"
             else "; the value is withheld (BRIEF P1)")
    try:
        return thunk()
    except AlreadyStored as exc:
        raise CaptureWriteFailed(
            f"{what} was already in the store ({exc}) — something else holds its key, so this "
            f"session did not write it{after}"
        ) from exc
    except IntegrityError as exc:
        raise CaptureWriteFailed(f"{what}'s key holds other bytes ({exc}){after}") from exc
    except OSError as exc:
        raise CaptureWriteFailed(
            f"{what} may not have been written ({type(exc).__name__}: {exc}){after}"
        ) from exc


def _copy(value: Any) -> Any:
    """A detached copy of a plain value, through the canonical encoding."""
    return decode_canonical(encode_canonical(value))


class Oracles:
    """An invocation context over one store: a mode and, to spend, a loaded budget."""

    __slots__ = ("_store", "_mode", "_budget")

    def __init__(self, store: Any, *, mode: Mode = REPLAY, budget: Budget | None = None) -> None:
        if not isinstance(mode, Mode):
            raise TypeError(
                f"mode is tannen.oracles.REPLAY or tannen.oracles.SPEND (a Mode), not {mode!r} — "
                "spending is spelled explicitly (BRIEF §5.10)"
            )
        if budget is not None and not isinstance(budget, Budget):
            raise TypeError(
                f"a budget is what tannen.oracles.load_budget returns, not {type(budget).__name__} "
                "— loading is where a budget's ceilings are checked"
            )
        self._store = store
        self._mode = mode
        self._budget = budget

    @property
    def store(self) -> Any:
        return self._store

    @property
    def mode(self) -> Mode:
        return self._mode

    @property
    def budget(self) -> Budget | None:
        return self._budget

    def invoke(self, oracle: Oracle, request: Any) -> str:
        """The ref of the capture that answers `request` — found, or made under SpendGuard."""
        if not isinstance(oracle, Oracle):
            raise TypeError(f"invoke takes a Fetch, LLM or Clock, not {type(oracle).__name__}")
        request = oracle.checked(request)
        key = input_key(request)
        values = _tagged(self._store)
        hits = _captures(values, oracle.descriptor, key)
        if len(hits) > 1:
            raise CaptureConflict(
                f"{len(hits)} captures answer {oracle.descriptor} at {key} — nothing can say "
                "which is the record, and choosing one would be a guess"
            )
        if hits:
            return hits[0]
        if self._mode is not SPEND:
            raise NovelInvocationRefused(
                f"{oracle.kind} {oracle.name!r}: no capture answers {key}, and replay-only is "
                "the default (BRIEF §5.10) — only mode=SPEND (tannen run --spend) can call"
            )
        sent = oracle.effective(request)
        worst = oracle.worst_case(sent)
        preflight = getattr(oracle.transport, "preflight", None)
        if callable(preflight):
            preflight(_copy(sent))  # what the transport could never send, refused unspent
        _admit(self._budget, oracle, worst, values)
        scope = self._budget.scope
        reservation = _write("the reservation", lambda: self._store.put_value({
            "tannen": RESERVATION_TAG, "kind": oracle.kind, "oracle": oracle.descriptor,
            "input_key": key, "scope": scope, "unit": oracle.unit, "worst_case": worst,
            "attempt": _attempt(values, oracle.descriptor, key, scope),
        }, exclusive=True))
        # The transport gets its own copy: what the capture records is what was decided
        # here, whatever the transport does with its argument.
        response = oracle.normalise(oracle.transport(_copy(sent)))
        stored = dict(response)
        if oracle.kind == "fetch":
            stored["body"] = _write("the fetched body", lambda: self._stored(response["body"]))
        return _write("the capture", lambda: self._store.put_value({
            "tannen": CAPTURE_TAG, "kind": oracle.kind, "oracle": oracle.descriptor,
            "input_key": key, "request": sent, "response": stored, "scope": scope,
            "unit": oracle.unit, "price": oracle.price(response), "reservation": reservation,
        }, exclusive=True))

    def _stored(self, body: bytes) -> str:
        """Write a payload and read it back: a body is content-addressed and may already sit
        in the store, so the check is that the bytes under its key are its bytes."""
        ref = self._store.put_bytes(body)
        self._store.get_bytes(ref)  # IntegrityError if a squatter holds the key
        return ref

    def read(self, ref: str) -> dict:
        """What the capture at `ref` says, read back and verified; a Fetch body as bytes."""
        value = tagged_value(self._store.get_bytes(ref))  # verified: tampered bytes raise here
        if value is None or value["tannen"] != CAPTURE_TAG or not isinstance(value.get("response"), dict):
            raise NotACapture(f"{ref} is not a {CAPTURE_TAG} value")
        response = dict(value["response"])
        if value.get("kind") == "fetch":
            if not is_ref(response.get("body")):
                raise NotACapture(f"{ref}: a fetch capture holds its body by ref")
            response["body"] = self._store.get_bytes(response["body"])
        return response
