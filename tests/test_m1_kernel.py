"""Pre-ops checks on Rel: the golden vectors that need no operator, and the merge rules.

Not a law (the laws are frozen under tests/laws/m1). This exists so the rel/1 canonical form
is checked against golden-rels.json BEFORE ops lands — M1's kill criterion is a golden
mismatch, and the response is to fix the encoding before anything else (docs/specs/m1.md §10).
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from tannen.kernel.encoding import encode_canonical
from tannen.kernel.rel import DEFAULT_ANNOTATIONS, Rel, RelError
from tannen.kernel.semiring import B, Why, Z, ZxWhy

GOLDEN = {
    v["name"]: v
    for v in json.loads(
        (Path(__file__).resolve().parents[1] / "tests/laws/m1/golden-rels.json").read_text(encoding="utf-8")
    )
}
R1 = "sha256:" + "11" * 32
R2 = "sha256:" + "22" * 32
WHY = "unit fixture"

OPERATOR_FREE = {
    "empty-z": lambda: Rel(("a", "b"), (), annotations=Z, annotations_reason=WHY),
    "one-row-z": lambda: Rel(("a",), [({"a": 1}, 3)], annotations=Z, annotations_reason=WHY),
    "zero-dropped": lambda: Rel(("a",), [({"a": 1}, 3), ({"a": 2}, 0)], annotations=Z, annotations_reason=WHY),
    "decimal-merge": lambda: Rel(
        ("p",), [({"p": Decimal("1.50")}, 1), ({"p": Decimal("1.5")}, 2)], annotations=Z, annotations_reason=WHY
    ),
    "nfc-merge": lambda: Rel(
        ("a",), [({"a": "héllo"}, 1), ({"a": "héllo"}, 1)], annotations=Z, annotations_reason=WHY
    ),
    "bool-rel": lambda: Rel(("a",), [({"a": 1}, True), ({"a": 2}, True)], annotations=B, annotations_reason=WHY),
    "why-antichain": lambda: Rel(("a",), [({"a": 1}, Why.of({R1}, {R1, R2}))], annotations=Why, annotations_reason=WHY),
    "zxwhy-one-row": lambda: Rel(("a",), [({"a": 1}, (2, Why.of({R1})))]),
    "zxwhy-zero-count": lambda: Rel(("a",), [({"a": 1}, (0, Why.of({R1})))]),
}


@pytest.mark.parametrize("name", sorted(OPERATOR_FREE))
def test_operator_free_golden_vectors(name: str) -> None:
    rel = OPERATOR_FREE[name]()
    assert encode_canonical(rel.to_value()) == GOLDEN[name]["canonical"].encode("utf-8"), GOLDEN[name]["note"]
    assert rel.content_address() == GOLDEN[name]["address"]
    assert Rel.from_value(rel.to_value()) == rel


def test_default_is_zxwhy_and_explicit_default_needs_no_reason() -> None:
    assert Rel(("a",)).annotations is DEFAULT_ANNOTATIONS
    assert Rel(("a",), annotations=ZxWhy).annotations_reason is None
    with pytest.raises(RelError):
        Rel(("a",), annotations=Z)


def test_iteration_is_canonical_order_and_rows_are_copies() -> None:
    rel = Rel(("k",), [({"k": 3}, 1), ({"k": 1}, 1), ({"k": 2}, 1)], annotations=Z, annotations_reason=WHY)
    keys = [row["k"] for row, _ in rel]
    assert keys == sorted(keys, key=lambda k: encode_canonical({"k": k}))
    first = next(iter(rel))[0]
    first["k"] = 99
    assert next(iter(rel))[0] == {"k": keys[0]}


def test_schema_errors_precede_encoding_errors() -> None:
    with pytest.raises(RelError):
        Rel((1,), [({1: 1.5}, 1)], annotations=Z, annotations_reason=WHY)
