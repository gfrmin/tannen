# Poison fixture candidate (RT-M3-04): a decoy that answers to the frozen M3 oracle's
# name AND reports the frozen file's path as its own `__file__`.
#
# `tests/poison/oracle-shadow-model/` covers the NAIVE shadow — a decoy honest about
# where it lives — which the shipped guard catches (verified 2026-09-05). This one
# covers the variant it does not: `__file__` is a plain attribute, and a module that
# sets it to the frozen path passes `_oracle_shadow_problem`'s identity comparison
# outright. Measured against the shipped guard: `check_differential` — BRIEF §6's
# differential kill criterion, frozen L3.12 — was answered 1,400 times by a stub that
# returns None, with 38 M3 law nodes green, 16 fresh evidence records written, and
# `check_manifest` reporting "frozen paths intact; seals unbroken; custody set current".
#
# It bites only against the widened check in this directory's .patch, which compares the
# CODE the module answers with against a fresh load of the frozen file. Staged here and
# not in tests/poison/ for that reason: installing it before the patch would leave the
# custodian permanently red, which is the opposite of what a poison fixture is for.
import importlib.util as _ilu
from pathlib import Path as _Path


def _find_repo_root(start: _Path) -> _Path:
    # Same walk as tannen.laws.discovery.find_root, and deliberately not a hardcoded
    # parent count: installing this fixture is a `git mv` into tests/poison/, which
    # changes its depth under the repo root.
    for candidate in (start, *start.parents):
        if (candidate / "MANIFEST.sha256").exists():
            return candidate
    raise RuntimeError("oracle-shadow-spoofed poison fixture: no MANIFEST.sha256 above it")


_FROZEN = _find_repo_root(_Path(__file__).resolve().parent) / "tests" / "laws" / "m3" / "_delta_model.py"
_spec = _ilu.spec_from_file_location("_delta_model_real_redteam", _FROZEN)
_real = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_real)

# Re-export everything, so a run looks identical to a run against the frozen module...
for _name in dir(_real):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_real, _name)

# ...including `__all__`, which the loop above skips. A decoy that controls its own
# `__all__` is the reason the .patch reads the export list off the FROZEN reference and
# never off the module under test: the first spelling of the patch enumerated
# `module.__all__ or dir(module)`, so `__all__ = []` fingerprinted nothing and passed.
# Measured, then fixed, then re-measured — the evasion exits non-zero under the patch as
# shipped here.
__all__ = list(getattr(_real, "__all__", ()))

# ...except the one function that decides whether tannen agrees with the oracle at all.
# `*args` rather than the real signature on purpose: the payload is that NOTHING is
# checked, and a stub that has to track the oracle's arity would be one more thing to
# keep in step with a frozen file.
def check_differential(*args, **kwargs):  # noqa: ANN002, ANN003, ANN201, D103
    return None


# THE LIE. Without this line the shipped guard catches the decoy on the first comparison;
# with it, the decoy is indistinguishable from the frozen module to any check that asks
# the module where it came from instead of what it contains.
__file__ = str(_FROZEN)

REDTEAM_SHADOW_MARKER = (
    "oracle-shadow-spoofed: this is the fixture's _delta_model.py reporting the frozen "
    "tests/laws/m3/_delta_model.py as its own __file__"
)
