"""M4 laws L4.6 and L4.7 — the `capture/1` envelope (docs/specs/m4.md §3; BRIEF §2.1, §4).

FROZEN at m4-laws-freeze.

L4.6. `capture/1` is Grade-S data [owns]: a frozen JSON Schema beside a frozen corpus of
positive and negative vectors, and conformance is parse-all-positives, reject-all-negatives
— the evidence-record shape (L0.10), one milestone on. The schema lives under this sealed
directory rather than `governance/schemas/`, which is custody-set (docs/specs/m4.md §3).

L4.7. Every capture the package writes is a valid `capture/1` carrying what BRIEF §4 names
for its kind: Fetch a WARC-shaped request and response, headers as ordered and possibly
repeated pairs, the body by content address; the LLM its full request, the resolved model
and the provider's usage, priced from that usage; the Clock its instant.
"""

from __future__ import annotations

import importlib.util as _ilu
import json
from pathlib import Path as _Path

import pytest

pytest.importorskip("tannen.oracles", reason=(
    "M4 boundary not implemented yet (law suite frozen ahead of Session B); M4's laws go "
    "live together — docs/specs/m4.md §11"))

_spec = _ilu.spec_from_file_location("tannen_frozen_m4._frozen_bind",
                                     _Path(__file__).with_name("_frozen_bind.py"))
bind = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(bind)

import jsonschema  # noqa: E402

M = bind.m4("_boundary_model")
TANNEN = bind.m4("_boundary_subject").make(M)

VALIDATED_BY = "tests/laws/m4/_boundary_model.py::check_envelopes"

POSITIVE = M.vector_paths("positive")
NEGATIVE = M.vector_paths("negative")

if not POSITIVE or not NEGATIVE:
    raise RuntimeError("the capture/1 corpus is missing a side (a Grade-S corpus has both)")


def test_l4_6_the_schema_is_a_valid_2020_12_schema() -> None:
    jsonschema.Draft202012Validator.check_schema(M.capture_schema())


@pytest.mark.parametrize("path", POSITIVE, ids=[p.stem for p in POSITIVE])
def test_l4_6_parses_all_positives(path) -> None:
    jsonschema.Draft202012Validator(M.capture_schema()).validate(
        json.loads(path.read_text(encoding="utf-8")))


@pytest.mark.parametrize("path", NEGATIVE, ids=[p.stem for p in NEGATIVE])
def test_l4_6_rejects_all_negatives(path) -> None:
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(M.capture_schema()).validate(
            json.loads(path.read_text(encoding="utf-8")))


@pytest.mark.parametrize("kind", M.KINDS)
def test_l4_7_every_capture_the_package_writes_is_a_valid_capture(kind) -> None:
    M.check_envelopes(TANNEN, kind, M.spec_for(kind, 1, 2))
