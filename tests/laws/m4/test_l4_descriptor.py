"""M4 law L4.1 — an oracle's identity is its full effective spec and its declared
reproducibility class (docs/specs/m4.md §2; BRIEF §4 descriptors).

FROZEN at m4-laws-freeze.

A capture is keyed by the descriptor of the oracle that made it, so everything that can
change what the world is asked — the model id, the prompt, the tool schema, the params, the
request template, the price it was admitted at — must move the descriptor, or two different
questions share one recorded answer. The reproducibility class is data the kernel carries,
declared per oracle from pkm's vocabulary and never inferred [cites: pkm-determinism]: an
oracle that does not declare one cannot be built.
"""

from __future__ import annotations

import importlib.util as _ilu
from pathlib import Path as _Path

import pytest

pytest.importorskip("tannen.oracles", reason=(
    "M4 boundary not implemented yet (law suite frozen ahead of Session B); M4's laws go "
    "live together — docs/specs/m4.md §11"))

_spec = _ilu.spec_from_file_location("tannen_frozen_m4._frozen_bind",
                                     _Path(__file__).with_name("_frozen_bind.py"))
bind = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(bind)

from hypothesis import given  # noqa: E402

M = bind.m4("_boundary_model")
TANNEN = bind.m4("_boundary_subject").make(M)

VALIDATED_BY = "tests/laws/m4/_boundary_model.py::check_descriptors"


@given(o=M.oracle_specs())
def test_l4_1_an_oracle_descriptor_is_its_full_spec_and_its_declared_class(o) -> None:
    """Stable; moved by the name, by every field of the effective spec, and by the class."""
    M.check_descriptors(TANNEN, *o)


@pytest.mark.parametrize("kind", M.KINDS)
@pytest.mark.parametrize("declared", [None, "", "reproducible-ish"])
def test_l4_1_an_oracle_without_a_declared_class_cannot_be_built(kind, declared) -> None:
    """No default class, no inferred class: the declaration is the owner's to make and the
    kernel's to carry, never to guess (BRIEF §2's pkm row: "do not redefine, do not fix")."""
    transport = M.FakeTransport(kind)
    with pytest.raises(TANNEN.undeclared):
        TANNEN.oracle(kind, f"{kind}-undeclared", M.spec_for(kind), declared, transport)
    assert transport.calls == []
