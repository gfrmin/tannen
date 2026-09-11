"""M4 law L4.9 — the doorway: no hidden IO in the shell (docs/specs/m4.md §6; BRIEF §5.3,
§5.7, P1).

FROZEN at m4-laws-freeze.

BRIEF §5.3: "the only IO doorway is `oracles/`, and the only way to read the world is
through a capture handle"; §5.7: the Clock oracle is the only source of time. The kernel's
half is already a guard (`governance/importlinter.toml`: `kernel-no-io`, `kernel-no-clock`).
The shell's half was prose until now: nothing stopped `tannen.store`, `tannen.executor` or
`tannen.incremental` importing a socket or a clock. This law is that half, frozen, so it
holds from Session B whether or not the matching import-linter contract — custody-set,
owner work — has been installed.

Two doors, named, each with a stated reason:
  network  only `tannen.oracles` (the doorway) and `tannen.r2` (the R2 client the store
           backend speaks through — a store transport, not a way to read the world);
  clock    only `tannen.oracles` (the Clock oracle) and `tannen.laws` (whose `run_at` is the
           RUNNER's time, per the evidence-record schema, never the kernel's).

The CLOCK set is DERIVED from the `kernel-no-clock` contract, so the two cannot drift. The
NETWORK set is NAMED here as residue: `kernel-no-io` lists `os`, `pathlib`, `tempfile` and
`io`, which the store, executor and CLI legitimately import, so it cannot be reused. What a
static scan cannot see — `importlib.import_module`, `__import__` — is stated, not claimed.
"""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

import pytest

pytest.importorskip("tannen.oracles", reason=(
    "M4 boundary not implemented yet (law suite frozen ahead of Session B); M4's laws go "
    "live together — docs/specs/m4.md §11"))

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC = REPO_ROOT / "src" / "tannen"

VALIDATION_REASON = (
    "a static property of the package's import graph: a model has no import graph to "
    "check, so the scanner itself carries a positive control instead (it must see an import "
    "planted in a synthetic source, and it must scan the real package)."
)

#: The network modules, named (residue — see the module docstring).
NETWORK = frozenset({
    "socket", "ssl", "http", "urllib", "urllib3", "requests", "httpx", "aiohttp",
    "asyncio", "ftplib", "smtplib", "boto3", "botocore", "websocket", "websockets", "grpc",
})
NETWORK_DOORS = ("tannen.oracles", "tannen.r2")
CLOCK_DOORS = ("tannen.oracles", "tannen.laws")


def _derived_clock_set() -> frozenset:
    config = tomllib.loads((REPO_ROOT / "governance" / "importlinter.toml").read_text(
        encoding="utf-8"))
    for contract in config["tool"]["importlinter"]["contracts"]:
        if contract.get("id") == "kernel-no-clock":
            return frozenset(contract["forbidden_modules"])
    raise AssertionError("governance/importlinter.toml has no kernel-no-clock contract")


CLOCK = _derived_clock_set()


def imports_of(source: str) -> set[str]:
    """The top-level names of every absolute import in `source`."""
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.add(node.module.split(".")[0])
    return found


def modules() -> dict[str, Path]:
    out: dict[str, Path] = {}
    for path in sorted(SRC.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        parts = path.relative_to(SRC.parent).with_suffix("").parts
        if parts[-1] == "__init__":
            parts = parts[:-1]
        out[".".join(parts)] = path
    return out


def _inside(module: str, doors: tuple) -> bool:
    return any(module == door or module.startswith(door + ".") for door in doors)


def violations(forbidden: frozenset, doors: tuple) -> list[tuple[str, list[str]]]:
    out = []
    for module, path in modules().items():
        if _inside(module, doors):
            continue
        bad = imports_of(path.read_text(encoding="utf-8")) & forbidden
        if bad:
            out.append((module, sorted(bad)))
    return out


def test_l4_9_no_module_outside_the_doorway_imports_the_network() -> None:
    found = violations(NETWORK, NETWORK_DOORS)
    assert found == [], f"network imports outside {NETWORK_DOORS}: {found} (BRIEF §5.3)"


def test_l4_9_no_module_outside_the_doorway_reads_a_clock() -> None:
    found = violations(CLOCK, CLOCK_DOORS)
    assert found == [], f"clock imports outside {CLOCK_DOORS}: {found} (BRIEF §5.7)"


def test_l4_9_the_clock_set_is_the_kernel_contracts_own() -> None:
    """Derived, and non-empty: an empty derived set would pass every scan while checking
    nothing."""
    assert CLOCK, "the kernel-no-clock contract lists no modules"


def test_l4_9_the_scanner_sees_what_it_is_looking_for() -> None:
    planted = ("import socket\nfrom urllib.request import urlopen\nimport os.path\n"
               "from . import sibling\nfrom time import monotonic\n")
    assert imports_of(planted) == {"socket", "urllib", "os", "time"}


def test_l4_9_the_scan_covers_the_package_it_guards() -> None:
    scanned = modules()
    for expected in ("tannen", "tannen.store", "tannen.executor", "tannen.incremental",
                     "tannen.cli", "tannen.oracles"):
        assert expected in scanned, f"the doorway scan does not reach {expected}"
