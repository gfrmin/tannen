"""`tannen.r2` — the real R2 client, driven through a fake opener (docs/specs/m4.md §1, §5;
decision D0234). Nothing here reaches a network, and nothing can: every request goes to the
injected `opener`.

What is pinned. (1) The signer, against AWS's own Signature Version 4 test suite — case
`get-vanilla` in `awslabs/aws-c-auth`, `tests/aws-signing-test-suite/v4/get-vanilla/`
(`context.json`, `header-canonical-request.txt`, `header-signature.txt`) — so the algorithm
is checked against a vector this repo did not write. (2) The wire shape of the three
`ObjectClient` calls: a conditional PUT that answers False on 412, a GET that answers None on
404, a paginated ListObjectsV2. (3) That any other status is an `OSError`, which is what makes
a failed remote write a `CaptureWriteFailed` in `tannen.oracles`.

What is NOT claimed: that R2 accepts these requests. The first write to a real bucket is
Tier-C door 2, queued for the owner (D0228).
"""

from __future__ import annotations

import hashlib
import io
import re
import urllib.error
from urllib.parse import parse_qs, urlsplit

import pytest

from tannen.r2 import R2Client, R2Error, canonical_request, sign

#: The suite's own credentials (`context.json`). The access-key id is not AWS-key-shaped, so
#: the PII guard's credential patterns do not fire on it.
SUITE_ACCESS_KEY = "AKIDEXAMPLE"
SUITE_SECRET = "wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY"
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()


def test_the_canonical_request_is_the_suites_get_vanilla() -> None:
    assert canonical_request(
        "GET", "/", [], {"host": "example.amazonaws.com", "x-amz-date": "20150830T123600Z"},
        EMPTY_SHA256,
    ) == (
        "GET\n/\n\nhost:example.amazonaws.com\nx-amz-date:20150830T123600Z\n\n"
        "host;x-amz-date\n" + EMPTY_SHA256
    )


def test_the_signature_is_the_suites_get_vanilla() -> None:
    canonical = canonical_request(
        "GET", "/", [], {"host": "example.amazonaws.com", "x-amz-date": "20150830T123600Z"},
        EMPTY_SHA256,
    )
    assert sign(canonical, secret=SUITE_SECRET, amz_date="20150830T123600Z",
                region="us-east-1", service="service") == (
        "5fa00fa31553b73ebf1942676e86291e8372ff2a2260956d9b8aae1d763fbf31"
    )


# ------------------------------------------------------------------ the wire, faked


class _Response:
    def __init__(self, status: int, body: bytes = b"") -> None:
        self.status = status
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False


def _http_error(request, code: int, body: bytes = b"") -> urllib.error.HTTPError:
    return urllib.error.HTTPError(request.full_url, code, "fake", {}, io.BytesIO(body))


class _Opener:
    """Answers each request with the next scripted (status, body); records what it was sent."""

    def __init__(self, *script: tuple[int, bytes]) -> None:
        self.script = list(script)
        self.sent: list = []

    def __call__(self, request, timeout=None):
        self.sent.append(request)
        status, body = self.script.pop(0)
        if status >= 400:
            raise _http_error(request, status, body)
        return _Response(status, body)


def _headers(request) -> dict[str, str]:
    return {name.lower(): value for name, value in request.header_items()}


def _client(opener, clock=lambda: "20260912T000000Z") -> R2Client:
    return R2Client(account_id="0123456789abcdef", bucket="tannen-test",
                    access_key_id=SUITE_ACCESS_KEY, secret_access_key=SUITE_SECRET,
                    clock=clock, opener=opener)


def test_put_if_absent_is_a_conditional_put_and_412_means_already_there() -> None:
    opener = _Opener((200, b""), (412, b"<Error><Code>PreconditionFailed</Code></Error>"))
    client = _client(opener)
    assert client.put_if_absent("objects/ab/cd", b"payload") is True
    assert client.put_if_absent("objects/ab/cd", b"payload") is False
    request = opener.sent[0]
    headers = _headers(request)
    assert request.get_method() == "PUT"
    assert urlsplit(request.full_url).path == "/tannen-test/objects/ab/cd"
    assert request.data == b"payload"
    assert headers["if-none-match"] == "*"
    assert headers["x-amz-content-sha256"] == hashlib.sha256(b"payload").hexdigest()
    assert headers["x-amz-date"] == "20260912T000000Z"
    assert re.fullmatch(
        r"AWS4-HMAC-SHA256 Credential=AKIDEXAMPLE/20260912/auto/s3/aws4_request, "
        r"SignedHeaders=[a-z0-9;-]+, Signature=[0-9a-f]{64}",
        headers["authorization"],
    ), headers["authorization"]
    assert "if-none-match" in headers["authorization"], "the condition must be signed"


def test_get_returns_the_bytes_or_none_on_404() -> None:
    opener = _Opener((200, b"stored"), (404, b"<Error><Code>NoSuchKey</Code></Error>"))
    client = _client(opener)
    assert client.get("objects/ab/cd") == b"stored"
    assert client.get("objects/ab/ce") is None
    assert all(request.get_method() == "GET" for request in opener.sent)


_PAGE = """<?xml version="1.0" encoding="UTF-8"?>
<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
  <IsTruncated>{truncated}</IsTruncated>
  {contents}
  {token}
</ListBucketResult>"""


def _page(keys, token=None) -> bytes:
    return _PAGE.format(
        truncated="true" if token else "false",
        contents="".join(f"<Contents><Key>{k}</Key><Size>1</Size></Contents>" for k in keys),
        token=f"<NextContinuationToken>{token}</NextContinuationToken>" if token else "",
    ).encode("utf-8")


def test_list_follows_continuation_tokens_and_returns_sorted_keys() -> None:
    opener = _Opener((200, _page(["objects/cd/2", "objects/ab/1"], token="page-2")),
                     (200, _page(["objects/ab/0"])))
    assert _client(opener).list("objects/") == ["objects/ab/0", "objects/ab/1", "objects/cd/2"]
    first, second = (parse_qs(urlsplit(r.full_url).query) for r in opener.sent)
    assert first["list-type"] == ["2"] and first["prefix"] == ["objects/"]
    assert "continuation-token" not in first
    assert second["continuation-token"] == ["page-2"]


@pytest.mark.parametrize("call", ["put", "get", "list"])
def test_any_other_status_is_an_oserror(call) -> None:
    client = _client(_Opener((500, b"<Error><Code>InternalError</Code></Error>")))
    with pytest.raises(R2Error) as caught:
        if call == "put":
            client.put_if_absent("objects/ab/cd", b"x")
        elif call == "get":
            client.get("objects/ab/cd")
        else:
            client.list("objects/")
    assert isinstance(caught.value, OSError), "a failed remote write must read as OSError"
    assert SUITE_SECRET not in str(caught.value)


def test_a_clock_that_does_not_speak_sigv4_time_is_refused_before_any_request() -> None:
    """An OSError like every other failed call, so a write it prevented reads upstream as a
    write that did not happen."""
    opener = _Opener((200, b""))
    with pytest.raises(R2Error, match="YYYYMMDDTHHMMSSZ"):
        _client(opener, clock=lambda: "2026-09-12T00:00:00Z").get("objects/ab/cd")
    assert opener.sent == []


@pytest.mark.parametrize("body", [
    b"<Error><Code>AccessDenied</Code></Error>",
    b'<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/"></ListBucketResult>',
    b"<ListBucketResult><IsTruncated>maybe</IsTruncated></ListBucketResult>",
])
def test_a_listing_that_is_not_one_is_refused_never_read_as_empty(body) -> None:
    """A listing read wrong reads as an EMPTY store — every capture lookup a miss, every spend
    fold zero — so anything but a well-formed ListBucketResult is `R2Error`."""
    with pytest.raises(R2Error):
        _client(_Opener((200, body))).list("objects/")


def test_a_connection_that_breaks_mid_response_is_an_oserror() -> None:
    import http.client

    def opener(request, timeout=None):
        raise http.client.IncompleteRead(b"partial")

    with pytest.raises(R2Error, match="outcome is unknown"):
        _client(opener).put_if_absent("objects/ab/cd", b"x")


def test_the_default_opener_follows_no_redirect() -> None:
    from tannen import r2

    assert r2._NoRedirects().redirect_request(None, None, 301, "moved", {}, "https://elsewhere/") is None
