"""The import surface a pinned dependent may use (`tannen.SURFACE`; D0275, BRIEF §1.1).

The two lists in `src/tannen/__init__.py` are kept by hand, so this file derives what they must
cover from the tree: every module under the package is classified by exactly one entry, every
entry names a module that exists, and every surface module imports. A new module fails here
until it is classified, which is the point — nothing becomes a promise to a dependent by being
added. Within a surface module the promise is its `__all__`, so a surface module that binds a
public name must declare one, and no name in it may come from a not-surface module.
"""

from __future__ import annotations

import importlib
from collections.abc import Iterable
from pathlib import Path
from types import ModuleType

import tannen

PACKAGE_ROOT = Path(tannen.__file__).resolve().parent


def modules_in_tree(root: Path) -> frozenset[str]:
    """Every module under the package at `root`, dotted, the package itself excluded."""

    def dotted(path: Path) -> str:
        parts = path.relative_to(root.parent).with_suffix("").parts
        return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)

    found = (p for p in root.rglob("*.py") if "__pycache__" not in p.parts)
    return frozenset(dotted(p) for p in found) - {root.name}


def covering(module: str, entries: Iterable[str]) -> tuple[str, ...]:
    return tuple(e for e in entries if module == e or module.startswith(e + "."))


def unclassified(modules: Iterable[str], entries: Iterable[str]) -> list[str]:
    listed = tuple(entries)
    return sorted(m for m in modules if not covering(m, listed))


def doubled(modules: Iterable[str], entries: Iterable[str]) -> list[str]:
    listed = tuple(entries)
    return sorted(m for m in modules if len(covering(m, listed)) > 1)


def stale(modules: Iterable[str], entries: Iterable[str]) -> list[str]:
    return sorted(set(entries) - set(modules))


def public_bindings(module: ModuleType) -> list[str]:
    """Public names the module binds, defined or imported, its own submodules aside.

    Deliberately wider than "defined here": a constant has no `__module__`, so asking where a
    value came from misses a module of constants, and binding any public name is what obliges
    a surface module to say in `__all__` which of them it promises.
    """

    def own_submodule(value: object) -> bool:
        return isinstance(value, ModuleType) and value.__name__.startswith(module.__name__ + ".")

    return sorted(
        name
        for name, value in vars(module).items()
        if not name.startswith("_") and not own_submodule(value)
    )


def origin(value: object) -> str:
    """The module a value comes from; a module is its own origin. A constant has none."""
    if isinstance(value, ModuleType):
        return value.__name__
    return getattr(value, "__module__", None) or ""


def leaks(module: ModuleType, not_surface: Iterable[str]) -> list[str]:
    """Names in `__all__` whose value comes from a not-surface module, or is one."""
    hidden = tuple(not_surface)
    return sorted(
        name
        for name in getattr(module, "__all__", ())
        if covering(origin(getattr(module, name)), hidden)
    )


ENTRIES = (*tannen.SURFACE, *tannen.NOT_SURFACE)
TREE = modules_in_tree(PACKAGE_ROOT)


def test_the_derivation_sees_the_tree() -> None:
    """A check that can see: an empty or truncated walk would make every test below vacuous."""
    assert {"tannen.kernel.rel", "tannen.cli", "tannen.oracles.transports"} <= TREE
    assert len(TREE) > 30


def test_every_module_is_classified() -> None:
    missing = unclassified(TREE, ENTRIES)
    assert missing == [], (
        "these modules are neither surface nor declared not-surface; classify each in "
        f"src/tannen/__init__.py before a dependent can see it — {missing}"
    )


def test_no_module_is_classified_twice() -> None:
    overlap = doubled(TREE, ENTRIES)
    assert overlap == [], f"entries overlap on {overlap}"


def test_every_entry_names_a_module_in_the_tree() -> None:
    gone = stale(TREE, ENTRIES)
    assert gone == [], f"these entries name no module in the tree: {gone}"


SURFACE_MODULES = sorted(m for m in TREE if covering(m, tannen.SURFACE))


def test_every_surface_module_imports() -> None:
    for module in SURFACE_MODULES:
        importlib.import_module(module)


def test_every_surface_module_states_its_promise() -> None:
    """A surface module that binds any public name says which it promises, in `__all__`."""
    silent = [
        m
        for m in SURFACE_MODULES
        if not hasattr(mod := importlib.import_module(m), "__all__") and public_bindings(mod)
    ]
    assert silent == [], f"surface modules with public names and no __all__: {silent}"


def test_every_promised_name_resolves() -> None:
    modules = [importlib.import_module(m) for m in SURFACE_MODULES]
    missing = [
        f"{mod.__name__}.{name}"
        for mod in modules
        for name in getattr(mod, "__all__", ())
        if not hasattr(mod, name)
    ]
    assert missing == [], f"__all__ names that do not exist: {missing}"


def test_no_promised_name_comes_from_a_not_surface_module() -> None:
    back_door = {
        m: found
        for m in SURFACE_MODULES
        if (found := leaks(importlib.import_module(m), tannen.NOT_SURFACE))
    }
    assert back_door == {}, f"__all__ re-exports from not-surface modules: {back_door}"


def small_tree(tmp_path: Path) -> frozenset[str]:
    package = tmp_path / "tannen"
    (package / "kernel").mkdir(parents=True)
    for name in ("__init__.py", "kernel/__init__.py", "kernel/rel.py", "brand_new.py"):
        (package / name).write_text("", encoding="utf-8")
    return modules_in_tree(package)


def test_a_new_module_is_unclassified_until_listed(tmp_path: Path) -> None:
    """The guard watched failing, on a tree built for it."""
    modules = small_tree(tmp_path)
    assert modules == {"tannen.kernel", "tannen.kernel.rel", "tannen.brand_new"}
    assert unclassified(modules, ("tannen.kernel",)) == ["tannen.brand_new"]
    assert unclassified(modules, ("tannen.kernel", "tannen.brand_new")) == []


def test_an_overlapping_entry_is_caught(tmp_path: Path) -> None:
    modules = small_tree(tmp_path)
    assert doubled(modules, ("tannen.kernel", "tannen.kernel.rel")) == ["tannen.kernel.rel"]
    assert doubled(modules, ("tannen.kernel", "tannen.kernelx")) == []


def test_a_stale_entry_is_caught(tmp_path: Path) -> None:
    modules = small_tree(tmp_path)
    assert stale(modules, ("tannen.kernel", "tannen.gone")) == ["tannen.gone"]
    assert stale(modules, ("tannen.kernel",)) == []


def test_an_entry_does_not_cover_a_name_it_merely_prefixes() -> None:
    assert unclassified({"tannen.kernelx"}, ("tannen.kernel",)) == ["tannen.kernelx"]


def test_the_promise_checks_see_a_silent_module_and_a_back_door() -> None:
    """Both `__all__` checks watched failing, on modules built for them."""
    hidden = ModuleType("tannen.hidden")
    exec("class Transport: pass\ndef connect(): pass\nCLIENT = Transport()", hidden.__dict__)
    silent = ModuleType("tannen.silent")
    exec("LIMIT = 3", silent.__dict__)
    assert public_bindings(silent) == ["LIMIT"]
    package = ModuleType("tannen.pkg")
    package.sub = ModuleType("tannen.pkg.sub")
    assert public_bindings(package) == []
    front = ModuleType("tannen.front")
    front.Transport, front.connect, front.CLIENT = hidden.Transport, hidden.connect, hidden.CLIENT
    front.hidden = hidden
    front.__all__ = ["Transport", "connect", "CLIENT", "hidden"]
    assert leaks(front, ("tannen.hidden",)) == ["CLIENT", "Transport", "connect", "hidden"]
    assert leaks(front, ("tannen.elsewhere",)) == []
