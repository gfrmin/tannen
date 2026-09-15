"""Bind a frozen M5 law helper (named `_dogfood_bind`, not `_frozen_bind`: helper stems are unique across milestone directories or the oracle-shadow guard refuses the run, D0165) FROM ITS BYTES, by file location (docs/specs/m5.md §10).

FROZEN at m5-laws-freeze. M4's `tests/laws/m4/_frozen_bind.py` is the forward fix for the
naming hazard three red teams found (RT-M1-01, RT-M2-01, RT-M3-04): a frozen law file that
says `import _model` receives whatever module holds that NAME. Its loader is private to M4's
directory, so M5 carries its own, under the same two rules and for the same measured reasons:

  * NEVER READ `sys.modules` BEFORE LOADING. Every call executes the file afresh and
    overwrites any entry under the name it uses; a cached answer is the channel a decoy uses.
  * NEVER LEAVE A BARE STEM BEHIND. M5's helpers live under a private dotted name that no
    bare import can reach and `tannen.laws.plugin`'s oracle-shadow check does not read.

Each M5 law file reaches this module with a four-line `spec_from_file_location` bootstrap;
nothing here is imported by name.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

__all__ = ["m5"]

_HERE = Path(__file__).resolve().parent
_PRIVATE = "tannen_frozen_m5"


def _execute(name: str, path: Path) -> ModuleType:
    """Execute `path` as module `name`, registered BEFORE execution and removed again if
    execution raises."""
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


def m5(stem: str) -> ModuleType:
    """The M5 helper `tests/laws/m5/<stem>.py`, from its bytes, under a private dotted name."""
    if not stem.startswith("_") or "/" in stem or "." in stem:
        raise ValueError(f"not a law-helper stem: {stem!r}")
    return _execute(f"{_PRIVATE}.{stem}", _HERE / f"{stem}.py")
