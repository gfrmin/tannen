"""M4 law L4.3 — invoke iff no capture (docs/specs/m4.md §3; BRIEF §4).

FROZEN at m4-laws-freeze.

"Policy = invoke iff no capture for (oracle_descriptor, input_key)." However many times, in
however many sessions over one store, a question is asked, the world is asked once; every
later ask is answered by the capture, byte for byte, and costs nothing. The key is the PAIR:
a different oracle asking the same request is a different question, and so is the same
oracle asking a different one. Two captures answering one key is refused by name — nothing
can say which is the record [cites: pkm-event-identity].
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

from hypothesis import given, strategies as st  # noqa: E402

M = bind.m4("_boundary_model")
TANNEN = bind.m4("_boundary_subject").make(M)

VALIDATED_BY = "tests/laws/m4/_boundary_model.py::check_invoke_once"


@pytest.mark.parametrize("kind", M.KINDS)
def test_l4_3_the_world_is_asked_once_per_descriptor_and_input_key(kind) -> None:
    M.check_invoke_once(TANNEN, kind, M.spec_for(kind, 1, 1), "bit", 3)


@given(o=M.oracle_specs(), n=st.integers(1, 5))
def test_l4_3_repeats_across_sessions_never_reach_the_transport_twice(o, n) -> None:
    kind, _name, spec, cls = o
    M.check_invoke_once(TANNEN, kind, spec, cls, n)


@pytest.mark.parametrize("kind", M.KINDS)
def test_l4_3_two_captures_for_one_key_are_refused_by_name(kind) -> None:
    """Sequential callers cannot produce this; two racing processes can. The record must
    not pick one silently."""
    spec = M.spec_for(kind, 0, 1)
    budget = {"scope": "M4", "unit": spec["unit"], "ceilings": {"total": 10**9, kind: 10**9}}
    store = TANNEN.store_local()
    oracle = TANNEN.oracle(kind, f"{kind}-conflict", spec, "bit", M.FakeTransport(kind))
    request = M.requests_for(kind, 0)
    session = TANNEN.session(store, "spend", budget)
    ref = TANNEN.invoke(session, oracle, request)
    rival = dict(TANNEN.get_value(store, ref))
    rival["scope"] = "a-racing-process"
    TANNEN.put_value(store, rival)
    silent = M.FakeTransport(kind)
    again = TANNEN.oracle(kind, f"{kind}-conflict", spec, "bit", silent)
    with pytest.raises(TANNEN.conflict):
        TANNEN.invoke(TANNEN.session(store, None, None), again, request)
    assert silent.calls == []
