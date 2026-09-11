"""Bind a frozen law helper FROM ITS BYTES, by file location (docs/specs/m4.md §8).

FROZEN at m4-laws-freeze. This is the forward fix for the naming hazard three red teams
found (RT-M1-01, RT-M2-01, RT-M3-04): `tests/laws` has no `__init__.py`, so a frozen law
file that says `import _delta_model` receives whatever module holds that NAME in
`sys.modules` — and a decoy that claims the name first wins, `__file__` and all. A
package-qualified import does not close it (SUPERSESSIONS.md, measured: the dotted entry
in `sys.modules` wins the same way, and the `__init__.py` files it needs break the eight
sibling frozen M3 files at collection). What closes it is to execute the frozen bytes from
their location and never ask `sys.modules` what a name means.

Two rules, and each is here because its absence was measured:

  * NEVER READ `sys.modules` BEFORE LOADING. Every call executes the file afresh and
    overwrites any entry under the name it uses; a cached answer is exactly the channel
    a decoy uses.
  * NEVER LEAVE A BARE STEM BEHIND. `tannen.laws.plugin`'s oracle-shadow guard reads
    `sys.modules` once, at the END of collection, for every bare stem under
    `tests/laws/m*/_*.py`. A loader that keeps a frozen module installed under its bare
    name silences that guard for every law file it does not bind (measured: 52 passed,
    exit 0, under a decoy that aborts the run without it). So M4's own helpers live under a
    private dotted name, and M3's are BORROWED under their bare names for the duration of
    the load — `_delta_subject.py` does its own bare `import _delta_model`, so both names
    must be held across both loads — and put back exactly as they were found.

Each M4 law file reaches this module with a four-line `spec_from_file_location`
bootstrap; nothing here is imported by name.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

__all__ = ["m3", "m4"]

_HERE = Path(__file__).resolve().parent
_M3 = _HERE.parent / "m3"
_PRIVATE = "tannen_frozen_m4"


def _execute(name: str, path: Path) -> ModuleType:
    """Execute `path` as module `name`, registered BEFORE execution (a module's own
    top-level code may look itself up) and removed again if execution raises."""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load frozen helper {path}")
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True  # no __pycache__ inside a sealed directory
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    finally:
        sys.dont_write_bytecode = previous
    return module


def m3() -> tuple[ModuleType, object]:
    """(the frozen M3 model, the frozen M3 tannen subject), loaded as a PAIR from
    `tests/laws/m3/`'s bytes. The bare names are borrowed and restored."""
    stems = ("_delta_model", "_delta_subject")
    prior = {stem: sys.modules.get(stem) for stem in stems}
    try:
        model = _execute("_delta_model", _M3 / "_delta_model.py")
        subject = _execute("_delta_subject", _M3 / "_delta_subject.py")
        return model, subject.TANNEN
    finally:
        for stem, was in prior.items():
            if was is None:
                sys.modules.pop(stem, None)
            else:
                sys.modules[stem] = was


def m4(stem: str) -> ModuleType:
    """The M4 helper `tests/laws/m4/<stem>.py`, from its bytes, under a private dotted
    name that no bare import can reach and no oracle-shadow check reads."""
    if not stem.startswith("_") or "/" in stem or "." in stem:
        raise ValueError(f"not a law-helper stem: {stem!r}")
    return _execute(f"{_PRIVATE}.{stem}", _HERE / f"{stem}.py")
