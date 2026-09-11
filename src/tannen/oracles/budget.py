"""The budget a SpendGuard admission is checked against (docs/specs/m4.md §4; decisions D0220,
D0236).

A budget names a `scope` (the spend period a capture is charged to — a milestone), a `unit`
(the exact money unit every price is an integer count of) and `ceilings` (an integer per
oracle kind, and a `total`). It is refused by name only where it is not an exact envelope —
a float, boolean or negative ceiling, a ceilings value that is not a mapping, a file that is
not a mapping. A budget that simply names no scope or no unit LOADS, and authorises nothing:
that is `budget.yaml` as frozen at M0, which refuses every novel invocation until an owner
sitting gives it a scope, a unit and a nonzero ceiling (Tier-C door 1). Other top-level keys
(`version`, `currency`) are carried by the file for other readers and ignored here; ceilings
stay YAML integers because `scripts/check_manifest.py` compares them numerically.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from tannen.oracles.errors import BudgetError

__all__ = ["Budget", "load_budget"]


@dataclass(frozen=True)
class Budget:
    scope: str | None
    unit: str | None
    ceilings: Mapping[str, int]


def load_budget(source: Mapping[str, Any] | str | os.PathLike[str]) -> Budget:
    """A `Budget` from a mapping or from a YAML file's path."""
    if isinstance(source, Mapping):
        data: Any = source
    elif isinstance(source, (str, os.PathLike)):
        import yaml

        try:
            data = yaml.safe_load(Path(source).read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise BudgetError(f"{source}: not YAML: {exc}") from exc
    else:
        raise BudgetError(f"a budget is a mapping or a path, not {type(source).__name__}")
    if not isinstance(data, Mapping):
        raise BudgetError(f"a budget is a mapping, not {type(data).__name__}")

    names = {}
    for field in ("scope", "unit"):
        value = data.get(field)
        if value is not None and not isinstance(value, str):
            raise BudgetError(f"budget {field} is a str, not {value!r}")
        names[field] = value or None

    ceilings = data.get("ceilings")
    ceilings = {} if ceilings is None else ceilings
    if not isinstance(ceilings, Mapping):
        raise BudgetError(f"budget ceilings is a mapping of kind to integer, not {ceilings!r}")
    for kind, ceiling in ceilings.items():
        if not isinstance(kind, str) or type(ceiling) is not int or ceiling < 0:
            raise BudgetError(
                f"budget ceiling {kind!r}: {ceiling!r} is not a non-negative integer — money is "
                "exact, and a ceiling is a count of the budget's unit"
            )
    return Budget(names["scope"], names["unit"], MappingProxyType(dict(ceilings)))
