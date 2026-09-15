# Poison fixture candidate (D0229 item 3(a); docs/proposals/2026-09-04-m3-boundary-sitting/
# SUPERSESSIONS.md, "What is genuinely owner-only", item (a)): a CODE decoy for the frozen M3
# oracle, aimed at the property no single-file invocation can see.
#
# The decoy itself is oracle-shadow-spoofed's — it answers to the frozen oracle's name,
# re-exports every callable, reports the frozen file's path as its own `__file__`, and
# substitutes the one function that decides whether tannen agrees with the model at all.
# What is new is WHERE it is aimed. The custodian's oracle-shadow-spoofed line collects
# tests/laws/m3/test_l3_differential.py ALONE. This fixture's invocation collects that file
# TOGETHER WITH its forward successor, tests/laws/m4/test_l4_differential_superseding.py —
# because the successor binds the same oracle from the frozen bytes, and a successor whose
# loader KEPT the frozen module under the bare name `_delta_model` would overwrite this decoy
# in sys.modules before the oracle-shadow guard reads it at the end of collection. The guard
# would then see the honest module and stay silent, while the superseded file had already
# bound this stub. Measured at M4 Session A: 52 passed, exit 0.
#
# So the property pinned here is the successor's: it BORROWS the bare name and puts back
# what it found. The code is identical to the sibling fixture's on purpose — one fixture,
# one reason, and the reason is the invocation, not the decoy.
import importlib.util as _ilu
from pathlib import Path as _Path


def _find_repo_root(start: _Path) -> _Path:
    # Same walk as tannen.laws.discovery.find_root, and deliberately not a hardcoded
    # parent count: installing this fixture is a `git mv` into tests/poison/, which
    # changes its depth under the repo root.
    for candidate in (start, *start.parents):
        if (candidate / "MANIFEST.sha256").exists():
            return candidate
    raise RuntimeError("oracle-shadow-cross-file poison fixture: no MANIFEST.sha256 above it")


_FROZEN = _find_repo_root(_Path(__file__).resolve().parent) / "tests" / "laws" / "m3" / "_delta_model.py"
_spec = _ilu.spec_from_file_location("_delta_model_real_cross_file", _FROZEN)
_real = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_real)

# Re-export everything, so the run looks identical to a run against the frozen module...
for _name in dir(_real):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_real, _name)
__all__ = list(getattr(_real, "__all__", ()))


# ...except the differential itself. `*args` on purpose: the payload is that NOTHING is
# checked, and a stub tracking the oracle's arity would be one more thing to keep in step.
def check_differential(*args, **kwargs):  # noqa: ANN002, ANN003, ANN201, D103
    return None


# The lie that makes the name-based identity test useless, so only the code comparison
# (plugin.py `_substituted_callables`) can see this decoy — and only if the decoy is still
# the module under the bare name when collection ends.
__file__ = str(_FROZEN)

REDTEAM_SHADOW_MARKER = (
    "oracle-shadow-cross-file: this is the fixture's _delta_model.py, collected alongside "
    "the M4 successor that must not overwrite it"
)
