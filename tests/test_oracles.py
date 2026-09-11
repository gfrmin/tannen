"""`tannen.oracles` — what the frozen M4 laws leave open (docs/specs/m4.md §1–§4; decisions
D0235, D0236).

L4.1–L4.13 pin identity, capture-before-read, invoke-iff-no-capture, the modes, SpendGuard's
rule and fold, the envelope and the replay, against the frozen model. What is decided here is
everything a caller can get WRONG that the model never tries: a mode spelled as a bare string,
a budget handed in unloaded, a request or a spec of the wrong shape, a world that answers in
a shape no capture can hold, a store whose spend cannot be folded, and the three real
transports — each driven through an injected fake, so nothing here reaches a network and
nothing spends.

Run with `TANNEN_NO_EVIDENCE=1` like everything else before M4's evidence refresh; this file
defines no law, but `tests/laws/m4` goes live the moment `tannen.oracles` imports (D0227).
"""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from tannen.kernel.encoding import encode_canonical
from tannen.oracles import (
    LLM,
    REPLAY,
    SPEND,
    BudgetError,
    CaptureWriteFailed,
    Clock,
    Fetch,
    MalformedResponse,
    NotACapture,
    NovelInvocationRefused,
    Oracles,
    RequestError,
    SpecError,
    SpendDenied,
    input_key,
    load_budget,
)
from tannen.oracles.transports import anthropic_messages, fetch_transport, system_clock
from tannen.store import R2Backend, Store

REPO_ROOT = Path(__file__).resolve().parent.parent
INSTANT = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]+)?Z$")
AMPLE = {"scope": "M4", "unit": "nano-usd",
         "ceilings": {"total": 10**6, "fetch": 10**6, "llm": 10**6, "clock": 10**6}}


class _Transport:
    """Answers every call with `answer(request)`; records what it was handed."""

    def __init__(self, answer) -> None:
        self.answer = answer
        self.calls: list = []

    def __call__(self, request):
        self.calls.append(request)
        return self.answer(request)


def _page(request):
    return {"status": 200, "headers": [["content-type", "text/plain"]], "body": b"page",
            "observed_at": "2026-09-12T00:00:00Z"}


def _fetch(transport, price=3) -> Fetch:
    return Fetch("f", reproducibility="bit", transport=transport, method="GET",
                 headers=[["accept", "text/plain"]], unit="nano-usd", price=price)


def _llm(transport, params) -> LLM:
    return LLM("l", reproducibility="non-reproducible", transport=transport, model="m",
               prompt="p", tool_schema=None, params=params, unit="nano-usd",
               input_price=1, output_price=1)


def _tagged(store) -> list[dict]:
    """Every tagged value in the store; raw payload bytes (a fetched body) are skipped."""
    out = []
    for ref in store.iter_refs():
        try:
            value = store.get_value(ref)
        except ValueError:
            continue
        if isinstance(value, dict) and isinstance(value.get("tannen"), str):
            out.append(value)
    return out


def _tags(store) -> list[str]:
    return sorted(value["tannen"] for value in _tagged(store))


# ------------------------------------------------------------------ the context's inputs


def test_a_mode_is_a_member_never_a_string_and_a_budget_is_loaded(tmp_path) -> None:
    """The ugly opt-out is `mode=SPEND`, imported by name (BRIEF §5.10). A bare "spend" is
    refused rather than read, and a budget goes through `load_budget`, whose checks a raw
    mapping would skip."""
    store = Store(tmp_path / "s")
    with pytest.raises(TypeError, match="Mode"):
        Oracles(store, mode="spend")
    with pytest.raises(TypeError, match="load_budget"):
        Oracles(store, mode=SPEND, budget=AMPLE)
    assert Oracles(store).mode is REPLAY


@pytest.mark.parametrize("request_", [{}, {"uri": "https://example.com/", "extra": 1},
                                      {"uri": 3}, {"url": "https://example.com/"}, "a string"])
def test_a_request_of_the_wrong_shape_is_refused_before_anything_is_written(tmp_path, request_):
    """A request is exactly its kind's variable part. Extra keys would be two input keys for
    one question; a missing one is no question at all."""
    store = Store(tmp_path / "s")
    transport = _Transport(_page)
    before = sorted(store.iter_refs())
    with pytest.raises(RequestError):
        Oracles(store, mode=SPEND, budget=load_budget(AMPLE)).invoke(_fetch(transport), request_)
    assert sorted(store.iter_refs()) == before and transport.calls == []


@pytest.mark.parametrize("params", [{"other": 1}, {"max_tokens": True}, {"max_tokens": 0}])
def test_an_llm_that_cannot_be_priced_is_refused_before_the_transport(tmp_path, params) -> None:
    """`max_tokens` bounds the worst case, so it is checked when a call is priced — at
    invocation, not construction: frozen L4.1 builds oracles whose params carry no
    `max_tokens` at all, and each must still have a descriptor."""
    store = Store(tmp_path / "s")
    transport = _Transport(lambda r: pytest.fail("reached the transport"))
    oracle = _llm(transport, params)
    assert oracle.descriptor.startswith("sha256:")
    before = sorted(store.iter_refs())
    with pytest.raises(SpecError, match="max_tokens"):
        Oracles(store, mode=SPEND, budget=load_budget(AMPLE)).invoke(
            oracle, {"messages": [{"role": "user", "content": "q"}]})
    assert sorted(store.iter_refs()) == before


# ------------------------------------------------------------------ what the world says


def _bad(**changes):
    def answer(request):
        return {**_page(request), **changes}
    return answer


@pytest.mark.parametrize("kind, answer", [
    ("fetch", _bad(status=700)),
    ("fetch", _bad(body="not bytes")),
    ("fetch", _bad(headers=[["only-a-name"]])),
    ("fetch", _bad(observed_at="2026-09-12T00:00:00+00:00")),
    ("llm", lambda r: {"resolved_model": "m", "content": "a",
                       "usage": {"input_tokens": 1.5, "output_tokens": 1}}),
    ("llm", lambda r: {"resolved_model": "m", "content": "a"}),
    ("clock", lambda r: {"instant": "noon"}),
])
def test_a_response_no_capture_can_hold_is_refused_and_writes_no_capture(tmp_path, kind, answer):
    store = Store(tmp_path / "s")
    transport = _Transport(answer)
    oracle = {"fetch": lambda: _fetch(transport),
              "llm": lambda: _llm(transport, {"max_tokens": 2}),
              "clock": lambda: Clock("c", reproducibility="bit", transport=transport,
                                     unit="nano-usd", price=1)}[kind]()
    request = {"fetch": {"uri": "https://example.com/"},
               "llm": {"messages": [{"role": "user", "content": "q"}]},
               "clock": {"label": "noon"}}[kind]
    with pytest.raises(MalformedResponse):
        Oracles(store, mode=SPEND, budget=load_budget(AMPLE)).invoke(oracle, request)
    assert len(transport.calls) == 1
    assert "capture/1" not in _tags(store) and "reservation/1" in _tags(store)


def test_a_refused_response_still_counts_its_worst_case(tmp_path) -> None:
    """The call happened, so the spend did: an unsettled reservation is its worst case in
    the fold, exactly as when a capture fails to write (docs/specs/m4.md §4)."""
    store = Store(tmp_path / "s")
    budget = load_budget({"scope": "M4", "unit": "nano-usd", "ceilings": {"total": 5, "fetch": 5}})
    with pytest.raises(MalformedResponse):
        Oracles(store, mode=SPEND, budget=budget).invoke(
            _fetch(_Transport(_bad(status=700))), {"uri": "https://example.com/a"})
    healthy = _Transport(_page)
    with pytest.raises(SpendDenied):
        Oracles(store, mode=SPEND, budget=budget).invoke(
            _fetch(healthy), {"uri": "https://example.com/b"})
    assert healthy.calls == []


@pytest.mark.parametrize("stray", [
    {"tannen": "reservation/1", "kind": "fetch", "scope": "M4"},
    {"tannen": "reservation/1", "kind": "fetch", "scope": "M4", "worst_case": "3"},
    {"tannen": "capture/1", "kind": "fetch", "scope": "M4", "reservation": 5, "price": 1},
])
def test_a_store_whose_spend_cannot_be_folded_denies(tmp_path, stray) -> None:
    """A tagged value that does not carry what the fold reads makes spend unknowable, and an
    unknowable spend is not zero: admission says no rather than skip it."""
    store = Store(tmp_path / "s")
    store.put_value(stray)
    transport = _Transport(_page)
    with pytest.raises(SpendDenied, match="unknowable"):
        Oracles(store, mode=SPEND, budget=load_budget(AMPLE)).invoke(
            _fetch(transport), {"uri": "https://example.com/"})
    assert transport.calls == []


class _FailOnce:
    """An ObjectClient whose first write carrying `marker` fails; everything else lands."""

    def __init__(self, marker: bytes) -> None:
        self.objects: dict[str, bytes] = {}
        self.marker: bytes | None = marker

    def put_if_absent(self, key, data):
        if self.marker is not None and self.marker in data:
            self.marker = None
            raise OSError("injected")
        if key in self.objects:
            return False
        self.objects[key] = bytes(data)
        return True

    def get(self, key):
        return self.objects.get(key)

    def list(self, prefix):
        return sorted(k for k in self.objects if k.startswith(prefix))


def test_a_retry_after_a_failed_capture_write_is_a_second_reservation() -> None:
    """Without `attempt`, the retry's reservation would be byte-identical to the first, the
    write-once store would keep one, and the fold would count one paid call where two were
    made (docs/specs/m4.md §4)."""
    store = Store(backend=R2Backend(_FailOnce(b"capture/1")))
    transport = _Transport(_page)
    context = Oracles(store, mode=SPEND, budget=load_budget(AMPLE))
    request = {"uri": "https://example.com/"}
    with pytest.raises(CaptureWriteFailed):
        context.invoke(_fetch(transport), request)
    ref = context.invoke(_fetch(transport), request)
    assert len(transport.calls) == 2
    reservations = [v for v in _tagged(store) if v["tannen"] == "reservation/1"]
    assert sorted(r["attempt"] for r in reservations) == [1, 2]
    assert store.get_value(store.get_value(ref)["reservation"])["attempt"] == 2


def test_read_refuses_a_ref_that_is_not_a_capture(tmp_path) -> None:
    store = Store(tmp_path / "s")
    ref = store.put_value({"tannen": "reservation/1"})
    with pytest.raises(NotACapture):
        Oracles(store).read(ref)


# ------------------------------------------------------------------ the budget file


def test_the_budget_file_as_frozen_at_m0_authorises_nothing(tmp_path) -> None:
    """`budget.yaml` names no scope and no unit, so `--spend` against it can authorise
    nothing — not even a free clock read — until an owner sitting says otherwise
    (docs/specs/m4.md §4; Tier-C door 1)."""
    budget = load_budget(REPO_ROOT / "budget.yaml")
    assert budget.scope is None and budget.unit is None
    assert all(ceiling == 0 for ceiling in budget.ceilings.values())
    transport = _Transport(lambda r: {"instant": "2026-09-12T00:00:00Z"})
    clock = Clock("c", reproducibility="non-reproducible", transport=transport,
                  unit="nano-usd", price=0)
    with pytest.raises(SpendDenied, match="scope"):
        Oracles(Store(tmp_path / "s"), mode=SPEND, budget=budget).invoke(clock, {"label": "x"})
    assert transport.calls == []


@pytest.mark.parametrize("source", [
    {"ceilings": {"total": 1.5}},
    {"ceilings": {"total": True}},
    {"ceilings": {"total": -1}},
    {"ceilings": {"total": "5"}},
    {"ceilings": [5]},
    {"scope": 3},
    42,
])
def test_load_budget_refuses_what_is_not_an_exact_envelope(source) -> None:
    with pytest.raises(BudgetError):
        load_budget(source)


def test_load_budget_refuses_a_file_that_is_not_a_mapping(tmp_path) -> None:
    path = tmp_path / "budget.yaml"
    path.write_text("- total\n- 5\n", encoding="utf-8")
    with pytest.raises(BudgetError):
        load_budget(path)


def test_load_budget_accepts_extra_keys_missing_kinds_and_zero_ceilings() -> None:
    budget = load_budget({"version": 0, "currency": "USD", "scope": "M4", "unit": "nano-usd",
                          "ceilings": {"total": 0}})
    assert (budget.scope, budget.unit, dict(budget.ceilings)) == ("M4", "nano-usd", {"total": 0})


# ------------------------------------------------------------------ the real transports


class _Connection:
    def __init__(self, status, headers, body) -> None:
        self.response = SimpleNamespace(status=status, getheaders=lambda: list(headers),
                                        read=lambda: body)
        self.sent: list = []

    def putrequest(self, method, target, **kwargs):
        self.sent.append(("request", method, target))

    def putheader(self, name, value):
        self.sent.append(("header", name, value))

    def endheaders(self, *args, **kwargs):
        self.sent.append(("end",))

    def getresponse(self):
        return self.response

    def close(self):
        self.sent.append(("close",))


def test_the_fetch_transport_keeps_header_order_and_repeats_and_records_a_404() -> None:
    connection = _Connection(404, [("set-cookie", "a=1"), ("set-cookie", "b=2")], b"gone")
    opened = []
    transport = fetch_transport(connect=lambda uri, timeout: opened.append(uri) or connection)
    response = transport({"method": "GET", "uri": "https://example.com/a?b=1",
                          "headers": [["accept", "x"], ["accept", "y"]]})
    assert opened == ["https://example.com/a?b=1"]
    assert connection.sent[0] == ("request", "GET", "/a?b=1")
    assert [s for s in connection.sent if s[0] == "header"] == [
        ("header", "accept", "x"), ("header", "accept", "y")]
    assert response["status"] == 404 and response["body"] == b"gone"
    assert response["headers"] == [["set-cookie", "a=1"], ["set-cookie", "b=2"]]
    assert INSTANT.match(response["observed_at"])
    assert ("close",) in connection.sent


def test_the_system_clock_reads_utc() -> None:
    assert INSTANT.match(system_clock({"label": "now"})["instant"])


class _Block:
    def __init__(self, value: dict) -> None:
        self.value = value

    def to_dict(self) -> dict:
        return dict(self.value)


class _Client:
    """The shape of the official SDK's client that the transport uses: `.messages.create`."""

    def __init__(self, response) -> None:
        self.sent: dict = {}
        self.messages = SimpleNamespace(create=self._create)
        self._response = response

    def _create(self, **kwargs):
        self.sent = kwargs
        return self._response


def _reply(**usage):
    return SimpleNamespace(
        model="claude-opus-5", stop_reason="end_turn",
        content=[_Block({"type": "text", "text": "hi"})],
        usage=SimpleNamespace(input_tokens=10, output_tokens=3, **usage))


def _asked(**changes):
    return {"model": "claude-opus-5", "prompt": "be brief", "tool_schema": None,
            "params": {"max_tokens": 64, "output_config": {"effort": "low"}},
            "messages": [{"role": "user", "content": "q"}], **changes}


def test_the_llm_transport_asks_through_the_official_client_and_records_what_it_says() -> None:
    client = _Client(_reply(cache_creation_input_tokens=0, cache_read_input_tokens=None))
    answer = anthropic_messages(client)(_asked())
    assert client.sent == {"model": "claude-opus-5", "max_tokens": 64, "system": "be brief",
                           "messages": [{"role": "user", "content": "q"}],
                           "output_config": {"effort": "low"}}
    assert answer == {
        "resolved_model": "claude-opus-5",
        "content": {"stop_reason": "end_turn", "blocks": [{"type": "text", "text": "hi"}]},
        "usage": {"input_tokens": 10, "output_tokens": 3},
    }


def test_the_llm_transport_sends_tools_and_omits_an_empty_prompt() -> None:
    client = _Client(_reply())
    anthropic_messages(client)(_asked(prompt="", tool_schema={"name": "lookup"}))
    assert "system" not in client.sent and client.sent["tools"] == [{"name": "lookup"}]


def test_the_llm_transport_will_not_price_what_its_prices_do_not_cover() -> None:
    """Cache reads and writes are priced differently from input, and the oracle declares
    one input price — so a response reporting either is refused rather than mispriced. The
    reservation's worst case stands in the fold instead."""
    with pytest.raises(MalformedResponse, match="cache"):
        anthropic_messages(_Client(_reply(cache_read_input_tokens=5)))(_asked())


def test_the_llm_transport_refuses_params_that_would_overwrite_the_request() -> None:
    with pytest.raises(SpecError, match="messages"):
        anthropic_messages(_Client(_reply()))(_asked(params={"max_tokens": 1, "messages": []}))


def test_the_llm_transport_needs_a_client_with_messages_create() -> None:
    with pytest.raises(TypeError):
        anthropic_messages(object())


# ------------------------------------------------------------------ found in review
#
# Each test below pins a defect the two review passes of this session found in the first
# draft (D0235). The first two were reproduced red before their fixes.


class _Dict:
    """A plain ObjectClient over a dict, with an optional hook run inside each put."""

    def __init__(self, before_put=None) -> None:
        self.objects: dict[str, bytes] = {}
        self.before_put = before_put

    def put_if_absent(self, key, data):
        if self.before_put is not None:
            self.before_put(self, key, bytes(data))
        if key in self.objects:
            return False
        self.objects[key] = bytes(data)
        return True

    def get(self, key):
        return self.objects.get(key)

    def list(self, prefix):
        return sorted(k for k in self.objects if k.startswith(prefix))


def _key_of(ref: str) -> str:
    return f"objects/{ref[7:9]}/{ref[9:]}"


def test_a_fetched_body_can_never_be_read_back_as_a_capture() -> None:
    """The world chose these bytes; decoded, they are a well-formed `capture/1` for a question
    nobody asked. Stored as a body, the scan would have served them to that question —
    reproduced, before the fix, as a replay returning planted content."""
    store = Store(backend=R2Backend(_Dict()))
    probe = _fetch(_Transport(_page), price=1)
    victim = {"uri": "https://example.com/victim"}
    forged = {"tannen": "capture/1", "kind": "fetch", "oracle": probe.descriptor,
              "input_key": input_key(victim), "request": {}, "scope": "M4", "unit": "nano-usd",
              "response": {"status": 200, "headers": [], "body": store.put_bytes(b"planted"),
                           "observed_at": "2026-09-12T00:00:00Z"},
              "price": 0, "reservation": "sha256:" + "0" * 64}
    evil = _Transport(lambda r: {**_page(r), "body": encode_canonical(forged)})
    with pytest.raises(MalformedResponse, match="tannen value"):
        Oracles(store, mode=SPEND, budget=load_budget(AMPLE)).invoke(
            _fetch(evil, price=1), {"uri": "https://example.com/attacker"})
    with pytest.raises(NovelInvocationRefused):
        Oracles(store).invoke(_fetch(_Transport(_page), price=1), victim)


def test_a_racing_session_that_finds_its_reservation_held_calls_nothing() -> None:
    """Two sessions that scanned the same store compute the same `attempt` and so the same
    reservation bytes. The exclusive write is what makes one of them lose: without it, both
    paid, one reservation was kept, and the fold counted one call (reproduced in review)."""
    def rival(client, key, data):
        if b"reservation/1" in data and key not in client.objects:
            client.objects[key] = data  # the other session wrote these bytes a moment earlier

    store = Store(backend=R2Backend(_Dict(before_put=rival)))
    transport = _Transport(_page)
    with pytest.raises(CaptureWriteFailed, match="nothing was called"):
        Oracles(store, mode=SPEND, budget=load_budget(AMPLE)).invoke(
            _fetch(transport), {"uri": "https://example.com/"})
    assert transport.calls == []


def test_every_capture_naming_a_reservation_counts() -> None:
    """Two captures settling one reservation — a race, or a forgery — both count: a
    duplicate can only RAISE spend, never pick the cheaper answer."""
    store = Store(backend=R2Backend(_Dict()))
    budget = load_budget({"scope": "M4", "unit": "nano-usd",
                          "ceilings": {"total": 10, "fetch": 10}})
    ref = Oracles(store, mode=SPEND, budget=budget).invoke(
        _fetch(_Transport(_page)), {"uri": "https://example.com/a"})
    twin = dict(store.get_value(ref))
    twin["price"] = 5
    twin["response"] = {**twin["response"], "status": 201}
    store.put_value(twin)                                     # spend is now 3 + 5 = 8
    with pytest.raises(SpendDenied, match="spent 8"):
        Oracles(store, mode=SPEND, budget=budget).invoke(
            _fetch(_Transport(_page)), {"uri": "https://example.com/b"})


def test_a_capture_that_contradicts_its_reservation_makes_spend_unknowable() -> None:
    store = Store(backend=R2Backend(_Dict()))
    ref = Oracles(store, mode=SPEND, budget=load_budget(AMPLE)).invoke(
        _fetch(_Transport(_page)), {"uri": "https://example.com/a"})
    forged = dict(store.get_value(ref))
    forged["kind"], forged["price"] = "clock", 0
    store.put_value(forged)
    with pytest.raises(SpendDenied, match="contradicts"):
        Oracles(store, mode=SPEND, budget=load_budget(AMPLE)).invoke(
            _fetch(_Transport(_page)), {"uri": "https://example.com/b"})


def test_a_scope_holding_another_unit_makes_spend_unknowable() -> None:
    """Changing a budget's unit mid-scope would otherwise add cents to nano-dollars 1:1."""
    store = Store(backend=R2Backend(_Dict()))
    cents = load_budget({"scope": "M4", "unit": "cents", "ceilings": {"total": 99, "fetch": 99}})
    in_cents = Fetch("f", reproducibility="bit", transport=_Transport(_page), method="GET",
                     headers=[], unit="cents", price=1)
    Oracles(store, mode=SPEND, budget=cents).invoke(in_cents, {"uri": "https://example.com/a"})
    with pytest.raises(SpendDenied, match="never converted"):
        Oracles(store, mode=SPEND, budget=load_budget(AMPLE)).invoke(
            _fetch(_Transport(_page)), {"uri": "https://example.com/b"})


@pytest.mark.parametrize("oracle, request_", [
    (lambda t: _fetch(fetch_transport(connect=lambda uri, timeout: pytest.fail("connected"))),
     {"uri": "ftp://example.com/file"}),
    (lambda t: _llm(anthropic_messages(_Client(_reply())), {"max_tokens": 1, "messages": []}),
     {"messages": [{"role": "user", "content": "q"}]}),
])
def test_what_a_transport_could_never_send_is_refused_before_anything_is_reserved(
        tmp_path, oracle, request_) -> None:
    """A local refusal after the reservation would charge a worst case for a call that never
    left the machine, again on every retry (found in review). The transport's preflight runs
    before admission instead."""
    store = Store(tmp_path / "s")
    with pytest.raises((RequestError, SpecError)):
        Oracles(store, mode=SPEND, budget=load_budget(AMPLE)).invoke(oracle(None), request_)
    assert list(store.iter_refs()) == []


def test_a_server_tool_is_refused_before_the_call(tmp_path) -> None:
    store = Store(tmp_path / "s")
    oracle = LLM("l", reproducibility="non-reproducible",
                 transport=anthropic_messages(_Client(_reply())), model="m", prompt="p",
                 tool_schema={"type": "web_search_20260209", "name": "web_search"},
                 params={"max_tokens": 2}, unit="nano-usd", input_price=1, output_price=1)
    with pytest.raises(SpecError, match="billed outside token usage"):
        Oracles(store, mode=SPEND, budget=load_budget(AMPLE)).invoke(
            oracle, {"messages": [{"role": "user", "content": "q"}]})
    assert list(store.iter_refs()) == []


def test_usage_beyond_input_and_output_tokens_is_refused_whatever_it_is_called() -> None:
    """Refused by structure — any other field reporting a nonzero count — not by a list of
    names someone has to keep up with. A string such as the service tier reports no count."""
    bill = _reply(server_tool_use={"web_search_requests": 40}, service_tier="standard")
    with pytest.raises(MalformedResponse, match="server_tool_use"):
        anthropic_messages(_Client(bill))(_asked())
    assert anthropic_messages(_Client(_reply(service_tier="standard")))(_asked())["usage"] == {
        "input_tokens": 10, "output_tokens": 3}


@pytest.mark.parametrize("headers", [[["Authorization", "Bearer do-not-print"]],
                                     [["X-Api-Key", "do-not-print"]], [["Cookie", "a=do-not-print"]]])
def test_a_credential_header_is_refused_and_never_echoed(headers) -> None:
    """A Fetch's headers are recorded verbatim in every capture, in a store that can never
    delete; and an error message ends up in logs."""
    with pytest.raises(SpecError) as refused:
        Fetch("f", reproducibility="bit", transport=_page, method="GET", headers=headers,
              unit="nano-usd", price=1)
    assert "do-not-print" not in str(refused.value)


def test_a_uri_carrying_credentials_is_refused(tmp_path) -> None:
    with pytest.raises(RequestError, match="credentials"):
        Oracles(Store(tmp_path / "s"), mode=SPEND, budget=load_budget(AMPLE)).invoke(
            _fetch(_Transport(_page)), {"uri": "https://someone:hunter2@example.com/"})


def test_an_oracles_spec_cannot_change_behind_its_descriptor() -> None:
    oracle = _fetch(_Transport(_page), price=3)
    oracle.spec["price"] = 0
    oracle.spec["headers"].append(["x", "y"])
    assert oracle.spec["price"] == 3 and oracle.worst_case({}) == 3
    assert oracle.effective({"uri": "u"})["headers"] == [["accept", "text/plain"]]
    with pytest.raises(AttributeError):
        oracle.descriptor = "sha256:" + "0" * 64


@pytest.mark.parametrize("marker", [b"capture/1", b"page"])
def test_a_key_already_holding_other_bytes_withholds_the_value(marker) -> None:
    """The capture is written exclusively and the body is read back, so a squatter at
    either key is a failed write — never a ref returned as if the value were stored."""
    def squat(client, key, data):
        if marker in data and key not in client.objects:
            client.objects[key] = b"squatter"

    store = Store(backend=R2Backend(_Dict(before_put=squat)))
    with pytest.raises(CaptureWriteFailed, match="withheld"):
        Oracles(store, mode=SPEND, budget=load_budget(AMPLE)).invoke(
            _fetch(_Transport(_page)), {"uri": "https://example.com/"})


def test_bytes_no_decoder_accepts_never_break_the_scan(tmp_path) -> None:
    """A JSON integer past Python's digit limit raises a plain ValueError in the decoder; a
    stored payload like that used to break every later invocation over the store."""
    store = Store(tmp_path / "s")
    clock = Clock("c", reproducibility="bit", transport=_Transport(
        lambda r: {"instant": "2026-09-12T00:00:00Z"}), unit="nano-usd", price=1)
    ref = Oracles(store, mode=SPEND, budget=load_budget(AMPLE)).invoke(clock, {"label": "x"})
    blob = store.put_bytes(b"7" * 5000)
    assert Oracles(store).invoke(clock, {"label": "x"}) == ref
    with pytest.raises(NotACapture):
        Oracles(store).read(blob)


def test_spend_with_no_budget_says_no_budget_was_given(tmp_path) -> None:
    with pytest.raises(SpendDenied, match="no budget was given"):
        Oracles(Store(tmp_path / "s"), mode=SPEND).invoke(
            _fetch(_Transport(_page)), {"uri": "https://example.com/"})
