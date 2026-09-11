"""M4 law L4.10 — the export admits only `serve` (docs/specs/m4.md §7; BRIEF P8, §5.9;
docs/specs/m1.md §6, "the `serve` default for exports arrives with the export surface at
M4").

FROZEN at m4-laws-freeze.

What leaves a pipeline is a `serve`-layer node's output — project and select only, so its
provenance is trivially the provenance of what it projects — emitted as exactly that
node's bytes, the same bytes every time. A node that ran anything wider (a `decode` map, a
`derive` join or distinct) is refused by name. ClickHouse emission is out of M4
(docs/specs/m4.md scope); this is the door any later emitter goes through.
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

VALIDATED_BY = "tests/laws/m4/_boundary_model.py::check_export"


@pytest.mark.parametrize("pipeline", sorted(M.EXPORT_PIPELINES))
def test_l4_10_the_export_door_on_every_catalogue_pipeline(pipeline) -> None:
    M.check_export(TANNEN, pipeline, [{"k": 1, "x": 1}, {"k": 1, "x": -1}, {"k": 2, "x": 3}])


@given(p=st.sampled_from(sorted(M.EXPORT_PIPELINES)), rows=M.export_rows())
def test_l4_10_the_export_door_on_drawn_rows(p, rows) -> None:
    M.check_export(TANNEN, p, rows)
