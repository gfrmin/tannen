"""The real R2 client: an `ObjectClient` over Cloudflare R2's S3 API (docs/specs/m4.md §1, §5;
decision D0234). Standard library only — `urllib`, `hmac`, `hashlib`, `xml.etree` — and AWS
Signature Version 4, pinned in `tests/test_r2.py` against AWS's own SigV4 test suite.

**No law and no test instantiates it against a network.** The first write to a real bucket is
a network write outside a captured oracle; `governance/policy.yaml` says
`network_writes: captured-oracles-only`, so it is Tier-C door 2 and is queued for the owner
(D0228). `R2Backend(R2Client(...))` is how a store would speak to R2 once that door opens.

**Two things are injected rather than reached for, each for a reason.**
  * The CLOCK. SigV4 signs a timestamp, and frozen L4.9 lets only `tannen.oracles` and
    `tannen.laws` import a clock module — this module is a network door, not a clock door. So
    `clock()` is the caller's, returning SigV4 time `YYYYMMDDTHHMMSSZ`.
  * The CREDENTIALS. Nothing here reads the environment: an ambient credential is exactly the
    hidden input BRIEF §5.3 exists to rule out. They are constructor arguments, never printed.

Write-once is the conditional PUT (`If-None-Match: *`): a 412 means the object is already
there and was left untouched. Every other failure — an unexpected status, a connection that
breaks mid-response, a clock that does not speak SigV4 time, a listing that is not one — is
`R2Error`, an `OSError`, which is what lets `tannen.oracles` report a failed remote write as
`CaptureWriteFailed`. Redirects are not followed: a signed request answered by another host
is a failure, not an answer. Integrity is not this module's job: `tannen.store.Store`
verifies every read, so nothing R2 returns is believed.
"""

from __future__ import annotations

import hashlib
import hmac
import http.client
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ElementTree
from collections.abc import Callable, Iterable, Mapping
from typing import Any

__all__ = ["ALGORITHM", "R2Client", "R2Error", "canonical_request", "sign"]

ALGORITHM = "AWS4-HMAC-SHA256"
_AMZ_DATE = re.compile(r"^[0-9]{8}T[0-9]{6}Z$")
#: RFC 3986 unreserved characters besides alphanumerics — what SigV4 leaves unencoded.
_UNRESERVED = "-_.~"


class R2Error(OSError):
    """R2 answered with something other than the call's success or its one expected refusal."""


def _encode(text: str, safe: str = "") -> str:
    return urllib.parse.quote(text, safe=_UNRESERVED + safe)


def _query_string(query: Iterable[tuple[str, str]]) -> str:
    return "&".join(f"{_encode(k)}={_encode(v)}" for k, v in sorted(query))


def canonical_request(
    method: str,
    path: str,
    query: Iterable[tuple[str, str]],
    headers: Mapping[str, str],
    payload_hash: str,
) -> str:
    """SigV4's canonical request: method, encoded path, sorted query, lower-cased sorted
    headers with collapsed whitespace, the signed-header list, and the payload's hash."""
    values = {name.lower(): " ".join(str(value).split()) for name, value in headers.items()}
    names = sorted(values)
    return "\n".join([
        method,
        _encode(path, safe="/"),
        _query_string(query),
        "".join(f"{name}:{values[name]}\n" for name in names),
        ";".join(names),
        payload_hash,
    ])


def _scope(amz_date: str, region: str, service: str) -> str:
    return f"{amz_date[:8]}/{region}/{service}/aws4_request"


def sign(canonical: str, *, secret: str, amz_date: str, region: str, service: str) -> str:
    """The hex SigV4 signature of `canonical` — the HMAC chain AWS publishes, over the
    string to sign it defines."""
    string_to_sign = "\n".join([
        ALGORITHM, amz_date, _scope(amz_date, region, service),
        hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    ])
    key = ("AWS4" + secret).encode("utf-8")
    for part in (amz_date[:8], region, service, "aws4_request"):
        key = hmac.new(key, part.encode("utf-8"), hashlib.sha256).digest()
    return hmac.new(key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _listing(body: bytes) -> tuple[list[str], str | None]:
    """(keys on this ListObjectsV2 page, the continuation token if the listing continues).

    Strict, because a listing that is read wrong reads as an EMPTY store — every capture
    lookup a miss, every spend fold zero."""
    try:
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError as exc:
        raise R2Error(f"R2 listing is not XML: {exc}") from exc
    if _local(root.tag) != "ListBucketResult":
        raise R2Error(f"R2 answered a listing with <{_local(root.tag)}>, not <ListBucketResult>")
    flags = [(e.text or "").strip() for e in root if _local(e.tag) == "IsTruncated"]
    if flags not in (["true"], ["false"]):
        raise R2Error(f"R2 listing carries IsTruncated {flags!r}, not exactly one true/false")
    keys = [element.text or "" for element in root.iter() if _local(element.tag) == "Key"]
    token = next((e.text for e in root if _local(e.tag) == "NextContinuationToken"), None)
    if flags == ["true"] and not token:
        raise R2Error("R2 says the listing continues but gives no continuation token")
    return keys, token if flags == ["true"] else None


class _NoRedirects(urllib.request.HTTPRedirectHandler):
    """A redirect answer surfaces as its own status (and so as `R2Error`), never followed."""

    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


_OPENER = urllib.request.build_opener(_NoRedirects)


class R2Client:
    """An `ObjectClient` over one R2 bucket (path-style addressing, SigV4, service `s3`,
    region `auto`). See the module docstring for why `clock` and the credentials are
    constructor arguments."""

    __slots__ = ("_host", "_bucket", "_access_key_id", "_secret", "_clock", "_region",
                 "_service", "_opener", "_timeout")

    def __init__(
        self,
        *,
        account_id: str,
        bucket: str,
        access_key_id: str,
        secret_access_key: str,
        clock: Callable[[], str],
        region: str = "auto",
        service: str = "s3",
        opener: Callable[..., Any] = _OPENER.open,
        timeout: float = 60,
    ) -> None:
        for label, value in (("account_id", account_id), ("bucket", bucket),
                             ("access_key_id", access_key_id),
                             ("secret_access_key", secret_access_key),
                             ("region", region), ("service", service)):
            if not isinstance(value, str) or not value:
                raise ValueError(f"R2Client: {label} is a non-empty str")
        if not callable(clock) or not callable(opener):
            raise TypeError("R2Client: clock and opener are callables")
        self._host = f"{account_id}.r2.cloudflarestorage.com"
        self._bucket = bucket
        self._access_key_id = access_key_id
        self._secret = secret_access_key
        self._clock = clock
        self._region = region
        self._service = service
        self._opener = opener
        self._timeout = timeout

    def __repr__(self) -> str:  # never the secret
        return f"R2Client(bucket={self._bucket!r}, host={self._host!r})"

    # ------------------------------------------------------------------ ObjectClient

    def put_if_absent(self, key: str, data: bytes) -> bool:
        status, body = self._send("PUT", key, data=bytes(data), condition={"if-none-match": "*"})
        if status in (200, 201):
            return True
        if status == 412:
            return False  # already there: S3's conditional write left it untouched
        raise R2Error(f"R2 PUT {key}: HTTP {status}: {body[:200]!r}")

    def get(self, key: str) -> bytes | None:
        status, body = self._send("GET", key)
        if status == 200:
            return body
        if status == 404:
            return None
        raise R2Error(f"R2 GET {key}: HTTP {status}: {body[:200]!r}")

    def list(self, prefix: str) -> list[str]:
        keys: list[str] = []
        token: str | None = None
        while True:
            query = [("list-type", "2"), ("prefix", prefix)]
            if token is not None:
                query.append(("continuation-token", token))
            status, body = self._send("GET", None, query=query)
            if status != 200:
                raise R2Error(f"R2 LIST {prefix}: HTTP {status}: {body[:200]!r}")
            page, token = _listing(body)
            keys.extend(page)
            if token is None:
                return sorted(keys)

    # ------------------------------------------------------------------ the wire

    def _send(
        self,
        method: str,
        key: str | None,
        *,
        query: list[tuple[str, str]] | None = None,
        data: bytes = b"",
        condition: Mapping[str, str] | None = None,
    ) -> tuple[int, bytes]:
        amz_date = self._clock()
        if not isinstance(amz_date, str) or not _AMZ_DATE.match(amz_date):
            raise R2Error(
                f"R2Client: clock() must return SigV4 time YYYYMMDDTHHMMSSZ, not {amz_date!r}; "
                "nothing was sent"
            )
        query = query or []
        path = f"/{self._bucket}" + (f"/{key}" if key is not None else "")
        payload_hash = hashlib.sha256(data).hexdigest()
        headers = {"host": self._host, "x-amz-content-sha256": payload_hash,
                   "x-amz-date": amz_date, **(condition or {})}
        signature = sign(canonical_request(method, path, query, headers, payload_hash),
                         secret=self._secret, amz_date=amz_date,
                         region=self._region, service=self._service)
        headers["authorization"] = (
            f"{ALGORITHM} Credential={self._access_key_id}/"
            f"{_scope(amz_date, self._region, self._service)}, "
            f"SignedHeaders={';'.join(sorted(headers))}, Signature={signature}"
        )
        url = f"https://{self._host}{_encode(path, safe='/')}"
        if query:
            url += "?" + _query_string(query)
        request = urllib.request.Request(
            url, data=data if method == "PUT" else None, method=method, headers=headers
        )
        try:
            with self._opener(request, timeout=self._timeout) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read()
        except http.client.HTTPException as exc:
            # Not an OSError: a connection that breaks mid-response. Whether a PUT landed is
            # unknown, which the caller must treat as a write that may not have happened.
            raise R2Error(
                f"R2 {method}: the connection failed mid-response ({type(exc).__name__}); "
                "the outcome is unknown"
            ) from exc
