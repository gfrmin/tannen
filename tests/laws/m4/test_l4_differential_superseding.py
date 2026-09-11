"""M4 law L4.22 — SUCCESSOR of L3.16, the M3 differential (docs/specs/m4.md §8;
docs/specs/m3.md §9).

FROZEN at m4-laws-freeze. Superseded forward under D0106 ruling 2; the M3 file
`tests/laws/m3/test_l3_differential.py` is retained unedited and keeps running — the poison
fixtures `oracle-shadow-model` and `oracle-shadow-spoofed` name that file, and it must stay
there for them to keep their teeth.

The claim is L3.16's unchanged: the shipped package and the frozen model agree annotation
for annotation over every catalogue shape and perturbation stream. What changes is the one
thing RT-M3-04 showed a decoy could reach: this file binds `check_differential` from the
frozen bytes by file location, borrowing the bare names only for the load and putting them
back, so a module claiming `_delta_model` first cannot answer for it — and, because nothing
is left under the bare name, the oracle-shadow guard still sees the M3 siblings' binding and
still aborts a run a decoy has reached (docs/proposals/2026-09-04-m3-boundary-sitting/
SUPERSESSIONS.md, measured both ways).
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

M, TANNEN = bind.m3()

VALIDATION_REASON = (
    "L4.22 IS the M3 differential: its oracle is tests/laws/m3/_delta_model.py, so naming a "
    "model family would be circular (the L2.9/L3.16 precedent). The model is exercised "
    "against its mutants by tests/test_law_validation.py."
)


@pytest.mark.parametrize("shape", M.SHAPES, ids=[s.name for s in M.SHAPES])
@given(data=st.data())
def test_l4_22_the_package_agrees_with_the_model_over_the_stream(shape, data) -> None:
    schemas, ticks, net = data.draw(M.stream_tables(names="".join(shape.tables)))
    M.check_differential(TANNEN, shape, schemas, ticks, net)
