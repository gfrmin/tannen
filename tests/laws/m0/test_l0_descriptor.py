"""M0 law L0.9 — descriptor identity (docs/specs/m0.md §4, §5).

FROZEN at m0-laws-freeze. Pre-implementation this module is a visible skip.
"""

from __future__ import annotations

import re

import pytest

encoding = pytest.importorskip(
    "tannen.kernel.encoding",
    reason="M0 kernel not implemented yet (law suite frozen ahead of Session B)",
)
descriptor = pytest.importorskip(
    "tannen.kernel.descriptor",
    reason="M0 kernel not implemented yet (law suite frozen ahead of Session B)",
)

REF_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

BASE = dict(
    kind="transform",
    name="clean",
    code_hash="sha256:" + "a" * 64,
    params_hash="sha256:" + "b" * 64,
)


def test_l0_9_id_is_the_address_of_the_canonical_tuple() -> None:
    did = descriptor.descriptor_id(**BASE)
    assert REF_RE.match(did)
    assert did == encoding.content_address(
        {
            "kind": BASE["kind"],
            "name": BASE["name"],
            "code_hash": BASE["code_hash"],
            "params_hash": BASE["params_hash"],
        }
    )


@pytest.mark.parametrize("field", ["kind", "name", "code_hash", "params_hash"])
def test_l0_9_any_component_change_changes_the_id(field: str) -> None:
    changed = dict(BASE)
    changed[field] = (
        "sha256:" + "c" * 64 if field.endswith("_hash") else BASE[field] + "-x"
    )
    assert descriptor.descriptor_id(**changed) != descriptor.descriptor_id(**BASE)


def test_l0_9_label_is_a_pure_function() -> None:
    # No "forgot to bump" state (BRIEF §5.2): the label derives, never gets set.
    assert descriptor.derive_label("pipelines.hk.results", "clean", 3) == "pipelines.hk.results/clean@3"
    assert descriptor.derive_label("pipelines.hk.results", "clean", 3) == descriptor.derive_label(
        "pipelines.hk.results", "clean", 3
    )
