"""Oracle identity, `oracle/1` [owns] (docs/specs/m4.md §2; L4.1).

An oracle's descriptor is the content address of its kind, its name, its full effective spec
— every field that decides what the world is asked or what it costs, prices and unit included
— and its declared reproducibility class. The class vocabulary is pkm's, in the spellings m0 §4
fixed; it is data the kernel carries and never interprets or defaults
[cites: pkm-determinism]. So an oracle with no class from `CLASSES` cannot be built, and
constructing one touches nothing: the transport is held, never called.

An oracle is immutable once built — its descriptor is the address of what it was built with,
and anything that could change afterwards would make that address a lie. So the spec is kept
as its canonical BYTES and every read of `spec` decodes a fresh copy: mutating what you were
handed changes nothing the oracle computes. The encoding also refuses a float or a tuple by
name (P7).

Each kind owns the facts about one call that the invocation context must not guess: the exact
request its transport is handed (recorded verbatim in the capture), the worst case that call
can cost (known before it is made), the shape an answer must have to be recorded, and what the
call actually cost (the world's own report, never clamped) — docs/specs/m4.md §3, §4.
"""

from __future__ import annotations

import re
import urllib.parse
from collections.abc import Callable, Mapping
from typing import Any, ClassVar

from tannen.kernel.encoding import (
    CanonicalEncodingError,
    content_address,
    decode_canonical,
    encode_canonical,
)
from tannen.oracles.errors import (
    MalformedResponse,
    RequestError,
    SpecError,
    UndeclaredReproducibility,
)

__all__ = [
    "CLASSES", "Clock", "Fetch", "INSTANT", "LLM", "ORACLE_TAG", "Oracle", "input_key",
    "tagged_value",
]

#: The declared reproducibility classes [cites: pkm-determinism].
CLASSES: tuple[str, ...] = ("bit", "in-distribution", "non-reproducible")
ORACLE_TAG = "oracle/1"
#: RFC 3339 UTC with a `Z` — the `capture/1` schema's own instant pattern.
INSTANT = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]+)?Z$")
#: Header names that carry credentials. A Fetch's fixed headers are recorded verbatim in every
#: capture, in a store that can never delete — so a credential belongs to the transport.
_CREDENTIAL_HEADER = re.compile(
    r"^(authorization|proxy-authorization|cookie)$|api[-_]?key|token|secret|password", re.I
)


def input_key(request: Any) -> str:
    """The content address of an invocation's variable part (docs/specs/m4.md §1)."""
    try:
        return content_address(request)
    except CanonicalEncodingError as exc:
        raise RequestError(f"a request is a canonical value: {exc}") from exc


def tagged_value(data: bytes) -> dict | None:
    """The tagged value these bytes decode to — a dict whose `tannen` key is a str — or None.
    Any bytes that do not decode (a payload, a source, an integer past Python's digit limit)
    are simply not a tagged value."""
    try:
        value = decode_canonical(data)
    except (ValueError, RecursionError):  # CanonicalEncodingError is a ValueError
        return None
    return value if isinstance(value, dict) and isinstance(value.get("tannen"), str) else None


def _plain(value: Any, what: str, error: type[Exception]) -> Any:
    """A detached plain copy through the canonical encoding."""
    try:
        return decode_canonical(encode_canonical(value))
    except CanonicalEncodingError as exc:
        raise error(f"{what}: {exc}") from exc


def _money(label: str, value: Any) -> int:
    if type(value) is not int or value < 0:
        raise SpecError(
            f"{label} is a non-negative integer count of the unit, not {value!r} — money is "
            "exact [cites: exactness-and-the-door]"
        )
    return value


def _text(label: str, value: Any, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not value and not empty):
        raise SpecError(f"{label} is a {'' if empty else 'non-empty '}str, not {value!r}")
    return value


def _pairs(label: str, value: Any, error: type[Exception]) -> list[list[str]]:
    """Ordered `[name, value]` pairs, repeats kept, as a WARC record keeps them. A refusal
    names the pair's position and header name, never its value: a header value may be a
    credential, and an error message ends up in logs."""
    if not isinstance(value, (list, tuple)):
        raise error(f"{label} are ordered [name, value] pairs, not a {type(value).__name__}")
    out = []
    for position, pair in enumerate(value):
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise error(f"{label}[{position}] is not a [name, value] pair")
        name, text = pair
        if not isinstance(name, str) or not name:
            raise error(f"{label}[{position}]: a header name is a non-empty str")
        if not isinstance(text, str):
            raise error(f"{label}[{position}] ({name!r}): a header value is a str, "
                        f"not {type(text).__name__}")
        out.append([name, text])
    return out


class Oracle:
    """A constructed oracle. Build one with `Fetch`, `LLM` or `Clock`."""

    kind: ClassVar[str]
    #: The one request field that is the invocation's variable part.
    variable: ClassVar[str]

    __slots__ = ("name", "reproducibility", "transport", "_spec", "descriptor")

    def __init__(self, name: Any, reproducibility: Any, transport: Any, spec: dict) -> None:
        if not isinstance(reproducibility, str) or reproducibility not in CLASSES:
            raise UndeclaredReproducibility(
                f"{self.kind} {name!r}: reproducibility {reproducibility!r} is not declared from "
                f"{CLASSES} — the class is the owner's to declare and the kernel's to carry, "
                "never to default [cites: pkm-determinism]"
            )
        if not callable(transport):
            raise SpecError(f"{self.kind} {name!r}: the transport is a callable, not {transport!r}")
        spec = _plain(spec, f"{self.kind} {name!r} spec", SpecError)
        object.__setattr__(self, "name", _text("name", name))
        object.__setattr__(self, "reproducibility", reproducibility)
        object.__setattr__(self, "transport", transport)
        object.__setattr__(self, "_spec", encode_canonical(spec))
        object.__setattr__(self, "descriptor", content_address({
            "tannen": ORACLE_TAG, "kind": self.kind, "name": self.name, "spec": spec,
            "reproducibility": reproducibility,
        }))

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError(
            f"{type(self).__name__} is immutable: its descriptor is the address of what it was "
            "built with"
        )

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.name!r}, {self.reproducibility}, {self.descriptor})"

    @property
    def spec(self) -> dict:
        """A fresh copy of the effective spec — the descriptor's own content."""
        return decode_canonical(self._spec)

    @property
    def unit(self) -> str:
        return self.spec["unit"]

    # ------------------------------------------------------------ one call's facts

    def checked(self, request: Any) -> dict:
        """The request, refused by name unless it is exactly this kind's variable part."""
        if not isinstance(request, Mapping) or set(request) != {self.variable}:
            raise RequestError(
                f"{self.kind} {self.name!r}: a request is exactly {{{self.variable!r}}}, "
                f"not {request!r}"
            )
        request = _plain(dict(request), f"{self.kind} request", RequestError)
        self._check(request[self.variable])
        return request

    def _check(self, value: Any) -> None:
        raise NotImplementedError

    def effective(self, request: dict) -> dict:
        """What the transport is handed and the capture records verbatim."""
        raise NotImplementedError

    def worst_case(self, sent: dict) -> int:
        """The most this call can cost, known before it is made. Fetch and the Clock: the
        declared price."""
        return self.spec["price"]

    def normalise(self, response: Any) -> dict:
        """The world's answer as plain values a capture can hold, or `MalformedResponse`."""
        raise NotImplementedError

    def price(self, response: dict) -> int:
        """What the call cost. Fetch and the Clock: the declared price."""
        return self.spec["price"]


def _mapping(kind: str, response: Any) -> Mapping:
    if not isinstance(response, Mapping):
        raise MalformedResponse(f"{kind}: a transport answers with a mapping, not "
                                f"{type(response).__name__}")
    return response


def _instant(kind: str, label: str, value: Any) -> str:
    if not isinstance(value, str) or not INSTANT.match(value):
        raise MalformedResponse(f"{kind}: {label} is an RFC 3339 UTC instant with a Z, not {value!r}")
    return value


class Fetch(Oracle):
    """A WARC-shaped fetch: request `{method, uri, headers}`, response `{status, headers,
    body, observed_at}` with the body kept by ref (docs/specs/m4.md §3). Its headers are
    recorded in every capture, so a credential-carrying header is refused: credentials belong
    to the transport, as the LLM transport's client already holds its key."""

    kind = "fetch"
    variable = "uri"
    __slots__ = ()

    def __init__(self, name: str, *, reproducibility: Any = None, transport: Callable[..., Any],
                 method: str, headers: Any, unit: str, price: int) -> None:
        pairs = _pairs("headers", headers, SpecError)
        secret = [header for header, _ in pairs if _CREDENTIAL_HEADER.search(header)]
        if secret:
            raise SpecError(
                f"fetch {name!r}: header(s) {secret} carry credentials, and a Fetch's headers are "
                "recorded verbatim in every capture of a store that can never delete — give "
                "credentials to the transport instead"
            )
        super().__init__(name, reproducibility, transport, {
            "method": _text("method", method), "headers": pairs,
            "unit": _text("unit", unit), "price": _money("price", price),
        })

    def _check(self, value: Any) -> None:
        if not isinstance(value, str) or not value:
            raise RequestError(f"fetch {self.name!r}: uri is a non-empty str, not {value!r}")
        parts = urllib.parse.urlsplit(value)
        if parts.username or parts.password:
            raise RequestError(
                f"fetch {self.name!r}: the uri carries credentials, and a uri is recorded "
                "verbatim in every capture — give credentials to the transport instead"
            )

    def effective(self, request: dict) -> dict:
        spec = self.spec
        return {"method": spec["method"], "uri": request["uri"], "headers": spec["headers"]}

    def normalise(self, response: Any) -> dict:
        response = _mapping(self.kind, response)
        status = response.get("status")
        if type(status) is not int or not 100 <= status <= 599:
            raise MalformedResponse(f"fetch: status is an integer 100-599, not {status!r}")
        body = response.get("body")
        if not isinstance(body, (bytes, bytearray, memoryview)):
            raise MalformedResponse(f"fetch: body is bytes, not {type(body).__name__}")
        body = bytes(body)
        if tagged_value(body) is not None:
            # A body is stored beside captures and reservations, in one address space. Bytes
            # the world chose that decode as a tannen value would be read back as one — a
            # planted capture served to a question nobody asked, or a planted price in the
            # spend fold. The world never authors a tannen value.
            raise MalformedResponse(
                "fetch: the body decodes as a tannen value, and a fetched body may never be "
                "stored where it could be read back as a capture or a reservation"
            )
        return {"status": status,
                "headers": _pairs("fetch response headers", response.get("headers"),
                                  MalformedResponse),
                "body": body,
                "observed_at": _instant(self.kind, "observed_at", response.get("observed_at"))}


class LLM(Oracle):
    """A model call: request `{model, prompt, tool_schema, params, messages}`, response
    `{resolved_model, content, usage}` — the resolved model recorded as reported, never
    normalised to the one asked for (docs/specs/m4.md §3)."""

    kind = "llm"
    variable = "messages"
    __slots__ = ()

    def __init__(self, name: str, *, reproducibility: Any = None, transport: Callable[..., Any],
                 model: str, prompt: str, tool_schema: Any, params: Any, unit: str,
                 input_price: int, output_price: int) -> None:
        # `params` is not checked for `max_tokens` here: that is a fact about pricing a call,
        # checked when one is priced (`worst_case`). Frozen L4.1 builds LLM oracles whose
        # params carry no `max_tokens`, and each must still have a descriptor.
        if not isinstance(params, Mapping):
            raise SpecError(f"llm {name!r}: params is a mapping, not {params!r}")
        super().__init__(name, reproducibility, transport, {
            "model": _text("model", model), "prompt": _text("prompt", prompt, empty=True),
            "tool_schema": tool_schema, "params": dict(params), "unit": _text("unit", unit),
            "input_price": _money("input_price", input_price),
            "output_price": _money("output_price", output_price),
        })

    def _check(self, value: Any) -> None:
        if not isinstance(value, list) or not all(
            isinstance(m, dict) and isinstance(m.get("role"), str) and m["role"] and "content" in m
            for m in value
        ):
            raise RequestError(
                f"llm {self.name!r}: messages is a list of {{role, content}} mappings"
            )

    def effective(self, request: dict) -> dict:
        spec = self.spec
        return {"model": spec["model"], "prompt": spec["prompt"],
                "tool_schema": spec["tool_schema"], "params": spec["params"],
                "messages": request["messages"]}

    def worst_case(self, sent: dict) -> int:
        """`input_price` × the UTF-8 bytes of the canonical request (a token is at least a
        byte) + `output_price` × `max_tokens` (docs/specs/m4.md §4). A provider can still bill
        more — tokens it adds to the prompt itself — and such an overrun is recorded as
        reported and seen by the next admission, never clamped."""
        spec = self.spec
        max_tokens = spec["params"].get("max_tokens")
        if type(max_tokens) is not int or max_tokens < 1:
            raise SpecError(
                f"llm {self.name!r}: params.max_tokens is a positive integer, not {max_tokens!r} — "
                "without it the call has no worst case, and an unbounded call cannot be admitted"
            )
        return spec["input_price"] * len(encode_canonical(sent)) + spec["output_price"] * max_tokens

    def normalise(self, response: Any) -> dict:
        response = _mapping(self.kind, response)
        resolved = response.get("resolved_model")
        if not isinstance(resolved, str) or not resolved:
            raise MalformedResponse(f"llm: resolved_model is a non-empty str, not {resolved!r}")
        if "content" not in response:
            raise MalformedResponse("llm: the response carries no content")
        usage = response.get("usage")
        tokens = {}
        for field in ("input_tokens", "output_tokens"):
            count = usage.get(field) if isinstance(usage, Mapping) else None
            if type(count) is not int or count < 0:
                raise MalformedResponse(f"llm: usage.{field} is a non-negative integer, not {count!r}")
            tokens[field] = count
        return {"resolved_model": resolved,
                "content": _plain(response["content"], "llm content", MalformedResponse),
                "usage": tokens}

    def price(self, response: dict) -> int:
        """The provider's reported usage at the declared prices — recorded as reported, never
        clamped to the worst case (docs/specs/m4.md §4)."""
        spec, usage = self.spec, response["usage"]
        return (spec["input_price"] * usage["input_tokens"]
                + spec["output_price"] * usage["output_tokens"])


class Clock(Oracle):
    """Time, as a captured value (BRIEF P7, §5.7): request `{label}`, response `{instant}`.
    A label is a question with one recorded answer; a new label is a new reading."""

    kind = "clock"
    variable = "label"
    __slots__ = ()

    def __init__(self, name: str, *, reproducibility: Any = None, transport: Callable[..., Any],
                 unit: str, price: int) -> None:
        super().__init__(name, reproducibility, transport,
                         {"unit": _text("unit", unit), "price": _money("price", price)})

    def _check(self, value: Any) -> None:
        if not isinstance(value, str) or not value:
            raise RequestError(f"clock {self.name!r}: label is a non-empty str, not {value!r}")

    def effective(self, request: dict) -> dict:
        return {"label": request["label"]}

    def normalise(self, response: Any) -> dict:
        response = _mapping(self.kind, response)
        return {"instant": _instant(self.kind, "instant", response.get("instant"))}
