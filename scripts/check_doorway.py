#!/usr/bin/env python3
"""check_doorway.py — the shell reads the world only through the doorway (RT-M4-02; BRIEF
§5.3, §5.7, P1; D0229 item (2); D0248).

BRIEF §5.3: "the only IO doorway is `oracles/`, and the only way to read the world is
through a capture handle". The kernel's half has been a guard since M0
(`governance/importlinter.toml`: `kernel-no-io`). The shell's half is frozen L4.9
(`tests/laws/m4/test_l4_doorway.py`), and the M3→M4 red team measured two holes in it:

  - its network set is a HAND-WRITTEN literal, so live socket-opening stdlib modules
    (`imaplib`, `poplib`, `socketserver`, `xmlrpc.client`) are simply absent from it;
  - `subprocess` and `os`'s shell-outs are not scanned at all, so
    `subprocess.run(["curl", url])` in `tannen.store` reads the world with every gate green.

This guard closes both without a hand-maintained list (D0171 ruling (3), D0211):

  NETWORK   An import is refused outside the doors when its module-level STATIC import
            closure reaches a SEED. The set of network modules is therefore DERIVED — from
            the source of the interpreter running this guard — rather than enumerated, so a
            module nobody thought to list is caught the day it is imported.
  PROCESS   An import whose static closure reaches a PROCESS seed (`subprocess`,
            `_posixsubprocess`, `multiprocessing`, `pty`), or a call to one of `os`'s spawners
            under any name `os` is bound to, is refused outside the process doors. A child
            process can read the world through any binary on PATH, so it is refused as a
            capability, derived like the network set (RT-M5-03).

THE SEEDS are the one irreducible constant, and they are the operating system's socket
primitives rather than a list of protocols: every stdlib or third-party route to the
network bottoms out in `_socket` (and TLS in `_ssl`), so a closure that reaches neither
cannot open a connection. Naming protocols instead is exactly the enumeration L4.9 froze.

THE DOORS are exact module names in governance/doors.yaml, each with its reason there. That
file is custody-set (RT-M5-05), so widening a door is the owner's signature, and a module added
under a door's package is not a door until it is listed (RT-M5-03).

WHAT THIS DOES NOT CLAIM, stated rather than implied:
  - Dynamic imports. `importlib.import_module(name)` and `__import__(name)` with a computed
    name are invisible to a static scan. `tannen.cli` legitimately uses the former to load a
    PIPELINE module named on the command line — that module is the operator's code, not
    this package's, and nothing here scans it.
  - Code the interpreter did not ship. The closure is resolved against the interpreter that
    runs the guard (`.venv/bin/python -I -P` at the gate); a different environment can
    derive a different set. The positive controls below refuse to run at all if the
    derivation stops seeing a known network module or starts seeing a known local one.
  - Anything reached through `ctypes`, `cffi` or a C extension's own internals.

Exits non-zero on any violation. `--root` points it at a fixture tree.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import sys
from pathlib import Path

# Run under `python -I -P` (conferral ruling 3, D0063): the one path this guard needs is
# named literally, derived from __file__ rather than inherited from the environment.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _gov import Failures, REPO_ROOT  # noqa: E402

#: The operating system's socket primitives (see the module docstring). Irreducible: the
#: only constant the network rule rests on.
SEEDS = frozenset({"socket", "_socket", "ssl", "_ssl"})

#: The process rule's seeds, derived the same way as the network rule's (RT-M5-03 (b)): an
#: import whose static closure reaches one of these can create a process. `webbrowser`
#: reaches `subprocess` without reaching a socket, and a by-name list missed it.
PROCESS_SEEDS = frozenset({"subprocess", "_posixsubprocess", "multiprocessing", "pty"})

#: `os` attributes that create a process or replace this one. Prefix matches, so the
#: exec*/spawn*/posix_spawn*/fork* families are covered whole.
OS_PROCESS_PREFIXES = ("system", "popen", "exec", "spawn", "posix_spawn", "fork")

#: The doors are EXACT module names, read from custody-set governance/doors.yaml (RT-M5-05):
#: widening one is the owner's signature, and a new module under a door's package is not a
#: door until it is listed there (RT-M5-03 (c)). Always this checkout's file, never --root's,
#: so a tree under judgement cannot choose its own doors.
def _doors() -> tuple[tuple[str, ...], tuple[str, ...]]:
    import yaml
    data = yaml.safe_load((REPO_ROOT / "governance" / "doors.yaml").read_text(encoding="utf-8"))
    return tuple(data["network"]), tuple(data["process"])


NETWORK_DOORS, PROCESS_DOORS = _doors()

#: The marker the custodian and the suite key on. One phrase for both rules, so a single
#: fixture carrying both kinds of payload has one marker to fail for.
MARKER = "reads the world outside the doorway"

#: Positive controls on the derivation itself (produce-the-failure): if the closure stops
#: seeing a module that opens sockets, or starts seeing one that cannot, the derived set is
#: wrong and every verdict below it is worthless — so the guard refuses to give one.
MUST_REACH = ("imaplib", "http.client")
MUST_NOT_REACH = ("os", "pathlib", "json")
MUST_REACH_PROCESS = ("subprocess", "webbrowser")
MUST_NOT_REACH_PROCESS = ("os", "pathlib", "json")
#: Modules the scan must reach in a real shell, so a scan over nothing cannot pass.
MUST_SCAN = ("tannen.store", "tannen.executor", "tannen.cli")


def _inside(module: str, doors: tuple[str, ...]) -> bool:
    return module in doors


def locate(name: str) -> Path | None:
    """The source file of `name`, found WITHOUT importing anything.

    `importlib.util.find_spec("a.b")` imports package `a` to read its `__path__`, and a
    guard that executes a third-party package's `__init__` to decide whether that package
    is safe has already lost. So only the top-level name goes through `find_spec` (which
    locates without executing), and submodules are found by walking the package's
    `submodule_search_locations` on disk. A builtin or compiled module has no source and
    is a leaf: it can still BE a seed, matched by name.
    """
    parts = name.split(".")
    try:
        spec = importlib.util.find_spec(parts[0])
    except (ImportError, ValueError):
        return None
    if spec is None:
        return None
    if len(parts) == 1:
        origin = spec.origin
        return Path(origin) if origin and origin.endswith(".py") else None
    locations = list(spec.submodule_search_locations or [])
    found: Path | None = None
    for part in parts[1:]:
        found = None
        for loc in locations:
            base = Path(loc)
            if (base / part / "__init__.py").is_file():
                found = base / part / "__init__.py"
                locations = [str(base / part)]
                break
            if (base / f"{part}.py").is_file():
                found = base / f"{part}.py"
                locations = []
                break
        if found is None:
            return None
    return found


def _package_of(name: str, path: Path) -> str:
    return name if path.name == "__init__.py" else name.rpartition(".")[0]


def import_time_names(name: str, path: Path) -> set[str]:
    """Absolute names imported when `name` is IMPORTED — its module level only.

    Function bodies do not run at import, so they are not descended into; class bodies and
    `if`/`try` blocks do run, so they are (`http.client` imports `ssl` inside a `try`). A
    relative import is resolved against the module's own package. A dotted name also names
    its parents, since importing `a.b` executes `a`.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, ValueError):
        return set()
    package = _package_of(name, path)
    names: set[str] = set()
    stack: list[ast.AST] = list(tree.body)
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue
        if isinstance(node, ast.Import):
            names |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package.split(".")
                base = base[: len(base) - (node.level - 1)] if node.level > 1 else base
                prefix = ".".join(p for p in base if p)
                module = ".".join(p for p in (prefix, node.module or "") if p)
            else:
                module = node.module or ""
            if module:
                names.add(module)
                # `from pkg import sub` may import a submodule; include it where one exists.
                names |= {f"{module}.{alias.name}" for alias in node.names
                          if alias.name != "*" and locate(f"{module}.{alias.name}")}
        stack.extend(ast.iter_child_nodes(node))
    with_parents: set[str] = set()
    for n in names:
        parts = n.split(".")
        with_parents |= {".".join(parts[:i]) for i in range(1, len(parts) + 1)}
    return with_parents


_REACHES: dict[tuple[str, frozenset[str]], bool] = {}


def reaches_seed(name: str, seeds: frozenset[str] = SEEDS) -> bool:
    """Whether importing `name` can, through module-level imports, load a SEED.

    Iterative rather than recursive (third-party closures run hundreds deep), and memoised
    per name. A cycle is not a route: a name already on the path contributes nothing new.
    """
    if (name, seeds) in _REACHES:
        return _REACHES[(name, seeds)]
    seen: set[str] = set()
    frontier = [name]
    hit = False
    while frontier and not hit:
        current = frontier.pop()
        if current in seen:
            continue
        seen.add(current)
        if current.split(".")[0] in seeds or current in seeds:
            hit = True
            break
        if _REACHES.get((current, seeds)):
            hit = True
            break
        path = locate(current)
        if path is None:
            continue
        frontier.extend(n for n in import_time_names(current, path) if n not in seen)
    _REACHES[(name, seeds)] = hit
    return hit


def shell_modules(root: Path) -> dict[str, Path]:
    package = root / "src" / "tannen"
    out: dict[str, Path] = {}
    for path in sorted(package.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        parts = path.relative_to(package.parent).with_suffix("").parts
        if parts[-1] == "__init__":
            parts = parts[:-1]
        out[".".join(parts)] = path
    return out


def every_import(tree: ast.Module) -> list[tuple[int, str]]:
    """Every absolute import anywhere in the module, function bodies included — a scan of
    the PACKAGE's own code asks what it can do, not only what it does at import."""
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [(node.lineno, alias.name) for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.append((node.lineno, node.module))
    return found


def os_process_calls(tree: ast.Module) -> list[tuple[int, str]]:
    """`os.<spawner>` attribute uses under any name `os` is bound to (RT-M5-03 (a): `import os
    as o; o.system(...)`), and names imported `from os` that are spawners."""
    bound = {"os"} | {alias.asname for node in ast.walk(tree) if isinstance(node, ast.Import)
                      for alias in node.names if alias.name == "os" and alias.asname}
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                and node.value.id in bound and node.attr.startswith(OS_PROCESS_PREFIXES)):
            found.append((node.lineno, f"os.{node.attr}"))
        elif isinstance(node, ast.ImportFrom) and node.module == "os":
            found += [(node.lineno, f"os.{alias.name}") for alias in node.names
                      if alias.name.startswith(OS_PROCESS_PREFIXES)]
    return found


def check(root: Path, fail: Failures) -> int:
    for name in MUST_REACH:
        if not reaches_seed(name):
            fail.add(f"positive control: the derived closure says {name} cannot reach a "
                     f"socket — the derivation is broken, so no verdict is given")
    for name in MUST_NOT_REACH:
        if reaches_seed(name):
            fail.add(f"positive control: the derived closure says {name} reaches a socket "
                     f"— the derivation over-approximates, so no verdict is given")
    for name in MUST_REACH_PROCESS:
        if not reaches_seed(name, PROCESS_SEEDS):
            fail.add(f"positive control: the derived closure says {name} cannot create a "
                     f"process — the derivation is broken, so no verdict is given")
    for name in MUST_NOT_REACH_PROCESS:
        if reaches_seed(name, PROCESS_SEEDS):
            fail.add(f"positive control: the derived closure says {name} can create a process "
                     f"— the derivation over-approximates, so no verdict is given")
    modules = shell_modules(root)
    missing = [m for m in MUST_SCAN if m not in modules]
    if not modules or missing:
        fail.add(f"positive control: the scan does not reach {missing or 'any module'} under "
                 f"{root / 'src' / 'tannen'} — a scan over nothing passes everything")
    if fail.messages:
        return len(modules)

    for module, path in modules.items():
        rel = path.relative_to(root)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = every_import(tree)
        if not _inside(module, NETWORK_DOORS):
            for lineno, name in imports:
                if name.split(".")[0] == "tannen":
                    continue
                if reaches_seed(name):
                    fail.add(f"{rel}:{lineno}: network — {module} imports {name}, whose import "
                             f"closure reaches a socket; it {MARKER} (BRIEF §5.3, RT-M4-02)")
        if not _inside(module, PROCESS_DOORS):
            for lineno, name in imports:
                # One finding per import: one the network rule already refused is not repeated.
                refused = not _inside(module, NETWORK_DOORS) and reaches_seed(name)
                if name.split(".")[0] != "tannen" and not refused and reaches_seed(name, PROCESS_SEEDS):
                    fail.add(f"{rel}:{lineno}: process — {module} imports {name}; a child "
                             f"process {MARKER} (BRIEF §5.3, RT-M4-02)")
            for lineno, call in os_process_calls(tree):
                fail.add(f"{rel}:{lineno}: process — {module} uses {call}; a child process "
                         f"{MARKER} (BRIEF §5.3, RT-M4-02)")
    return len(modules)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=REPO_ROOT,
                        help="tree whose src/tannen is scanned (a poison fixture points here)")
    args = parser.parse_args()
    root = args.root.resolve()
    fail = Failures("check_doorway")
    scanned = check(root, fail)
    return fail.finish(
        f"{scanned} module(s) scanned; no network import outside {', '.join(NETWORK_DOORS)} "
        f"and no process creation outside {', '.join(PROCESS_DOORS)} (seeds: "
        f"{', '.join(sorted(SEEDS))})"
    )


if __name__ == "__main__":
    raise SystemExit(main())
