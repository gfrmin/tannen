# Poison fixture candidate (RT-M1-01): a decoy module named exactly like the frozen L1.16
# oracle (tests/laws/m1/_fragment.py). It faithfully re-exports the real module so a run
# looks identical unless something is specifically checking WHICH module answered to the
# name -- which is exactly what src/tannen/laws/plugin.py's oracle-shadow check now does.
import importlib.util as _ilu
from pathlib import Path as _Path


def _find_repo_root(start: _Path) -> _Path:
    # Walk up looking for MANIFEST.sha256, same as tannen.laws.discovery.find_root --
    # deliberately not a hardcoded parent count, since installing this fixture is a
    # `git mv` into tests/poison/ (see this directory's README row), which changes its
    # depth under the repo root.
    for candidate in (start, *start.parents):
        if (candidate / "MANIFEST.sha256").exists():
            return candidate
    raise RuntimeError("oracle-shadow poison fixture: no MANIFEST.sha256 found above it")


_REAL = _find_repo_root(_Path(__file__).resolve().parent) / "tests" / "laws" / "m1" / "_fragment.py"
_spec = _ilu.spec_from_file_location("_fragment_real_redteam", _REAL)
_real = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_real)
for _name in dir(_real):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_real, _name)

REDTEAM_SHADOW_MARKER = "this is the poison fixture's _fragment.py, not the frozen one"
