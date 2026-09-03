# Poison fixture candidate (RT-M2-01): a decoy module named exactly like the frozen M2
# oracle (tests/laws/m2/_model.py). It faithfully re-exports the real module so a run
# looks identical unless something is specifically checking WHICH module answered to the
# name. plugin.py's oracle-shadow check does NOT do that for `_model`: it pins the single
# name `_fragment` (plugin.py:50-51). THAT IS THE FINDING. This fixture bites only against the
# widened check RT-M2-01 asks for, which is why it is staged here and not in tests/poison/.
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
    raise RuntimeError("oracle-shadow-model poison fixture: no MANIFEST.sha256 found above it")


_REAL = _find_repo_root(_Path(__file__).resolve().parent) / "tests" / "laws" / "m2" / "_model.py"
_spec = _ilu.spec_from_file_location("_model_real_redteam", _REAL)
_real = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_real)
for _name in dir(_real):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_real, _name)

REDTEAM_SHADOW_MARKER = "this is the poison fixture's _model.py, not the frozen tests/laws/m2/_model.py"
