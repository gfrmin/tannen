"""Real transports: how an oracle actually asks the world (docs/specs/m4.md §1). A transport
is any callable `transport(effective_request) -> response`; one may also carry a
`preflight(effective_request)` that the invocation context runs BEFORE admission, so what it
could never send is refused while nothing is reserved or spent.

**No law invokes one, and no test reaches a network through one**: each takes its connection,
or its client, as an argument so a test can hand it a fake. Only `tannen.oracles` may import
the network or read a clock (frozen L4.9), which is why they live here.

  * `http_fetch` / `fetch_transport(connect=…)` — `http.client`, because a WARC-shaped request
    keeps its header pairs in order with repeats, which `urllib`'s header mapping cannot.
    Redirects are not followed: a capture records what the server said. Its `observed_at` is
    this machine's receipt time.
  * `system_clock` — the Clock oracle's reading of UTC; a capture makes it a replayable answer.
  * `anthropic_messages(client)` — the Claude Messages API through the OFFICIAL SDK's client,
    handed in (`anthropic.Anthropic()`), so tannen neither depends on the SDK nor ever holds an
    API key. `params` pass through as request parameters; a caller choosing a parameter that
    changes the price (a faster mode, a tier) declares the oracle's prices for it, and both
    are in the descriptor. It records `stop_reason` beside the content blocks — a refusal must
    not read as an answer — and refuses what its prices cannot price: a server or
    Anthropic-defined tool (billed outside tokens) before the call, and any usage count beyond
    input and output tokens after it, in which case the reservation's worst case stands (D0235).
"""

from __future__ import annotations

import datetime as dt
import http.client
import urllib.parse
from collections.abc import Callable, Mapping
from typing import Any

from tannen.oracles.errors import MalformedResponse, RequestError, SpecError

__all__ = ["anthropic_messages", "fetch_transport", "http_fetch", "system_clock"]


def _utc_now() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


# ------------------------------------------------------------------ fetch


def _fetch_preflight(request: dict) -> None:
    parts = urllib.parse.urlsplit(request["uri"])
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise RequestError(f"fetch: {request['uri']!r} is not an http or https uri with a host")


def _connect(uri: str, timeout: float) -> http.client.HTTPConnection:
    parts = urllib.parse.urlsplit(uri)
    connection = http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
    return connection(parts.netloc, timeout=timeout)


def fetch_transport(*, connect: Callable[[str, float], Any] = _connect,
                    timeout: float = 30.0) -> Callable[[dict], dict]:
    """A Fetch transport over `connect(uri, timeout)`, which returns an `http.client`-shaped
    connection."""

    def http_fetch(request: dict) -> dict:
        _fetch_preflight(request)
        parts = urllib.parse.urlsplit(request["uri"])
        target = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
        connection = connect(request["uri"], timeout)
        try:
            connection.putrequest(request["method"], target, skip_accept_encoding=True)
            for name, value in request["headers"]:
                connection.putheader(name, value)
            connection.endheaders()
            response = connection.getresponse()
            return {
                "status": response.status,
                "headers": [[name, value] for name, value in response.getheaders()],
                "body": response.read(),
                "observed_at": _utc_now(),
            }
        finally:
            connection.close()

    http_fetch.preflight = _fetch_preflight
    return http_fetch


http_fetch = fetch_transport()


# ------------------------------------------------------------------ clock


def system_clock(request: dict) -> dict:
    """The system's UTC time. The Clock oracle captures it under the caller's label."""
    return {"instant": _utc_now()}


# ------------------------------------------------------------------ llm

#: Request keys the transport sets from the effective request itself; a param may not
#: overwrite what the capture records as having been asked.
_ASKED = frozenset({"model", "system", "messages", "tools"})
#: The usage an oracle's declared prices price. Anything else that counts, refuses.
_PRICED = frozenset({"input_tokens", "output_tokens"})


def _tools(tool_schema: Any) -> list:
    if tool_schema is None:
        return []
    return list(tool_schema) if isinstance(tool_schema, list) else [tool_schema]


def _llm_preflight(request: dict) -> None:
    clash = sorted(set(request["params"]) & _ASKED)
    if clash:
        raise SpecError(
            f"llm params {clash} would overwrite the request the capture records as asked"
        )
    for tool in _tools(request["tool_schema"]):
        kind = tool.get("type") if isinstance(tool, Mapping) else None
        if kind not in (None, "custom"):
            raise SpecError(
                f"llm tool {tool.get('name')!r} is an Anthropic-defined tool (type {kind!r}); "
                "server tools are billed outside token usage, which the oracle's declared "
                "prices cannot price"
            )


def _fields(usage: Any) -> dict:
    to_dict = getattr(usage, "to_dict", None)
    if callable(to_dict):
        return dict(to_dict())
    return dict(usage) if isinstance(usage, Mapping) else dict(vars(usage))


def _counts(value: Any) -> bool:
    """Whether a usage field reports anything: a nonzero number anywhere inside it."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, Mapping):
        return any(_counts(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return any(_counts(v) for v in value)
    return False


def anthropic_messages(client: Any) -> Callable[[dict], dict]:
    """An LLM transport over the official Anthropic SDK's client (`client.messages.create`)."""
    create = getattr(getattr(client, "messages", None), "create", None)
    if not callable(create):
        raise TypeError(
            "anthropic_messages takes the official SDK's client (anthropic.Anthropic()) — "
            f"something with .messages.create, not {type(client).__name__}"
        )

    def transport(request: dict) -> dict:
        _llm_preflight(request)
        kwargs: dict[str, Any] = {"model": request["model"], **request["params"],
                                  "messages": request["messages"]}
        if request["prompt"]:
            kwargs["system"] = request["prompt"]
        tools = _tools(request["tool_schema"])
        if tools:
            kwargs["tools"] = tools
        reply = create(**kwargs)
        usage = _fields(reply.usage)
        unpriced = sorted(k for k, v in usage.items() if k not in _PRICED and _counts(v))
        if unpriced:
            raise MalformedResponse(
                f"llm: the response reports usage {unpriced} beyond input and output tokens "
                "(cache reads and writes, server tools), which the oracle's declared prices "
                "do not cover — refused rather than mispriced"
            )
        return {
            "resolved_model": reply.model,
            "content": {"stop_reason": reply.stop_reason,
                        "blocks": [_plain_block(block) for block in reply.content]},
            "usage": {"input_tokens": usage.get("input_tokens"),
                      "output_tokens": usage.get("output_tokens")},
        }

    transport.preflight = _llm_preflight
    return transport


def _plain_block(block: Any) -> Any:
    to_dict = getattr(block, "to_dict", None)
    return to_dict() if callable(to_dict) else block
