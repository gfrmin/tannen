"""M5 law L5.2 — the doorway, DERIVED: successor of L4.9 (docs/specs/m5.md §7; BRIEF §5.3,
§5.7, P1; RT-M4-02; D0248).

FROZEN at m5-laws-freeze. Supersedes `tests/laws/m4/test_l4_doorway.py` FORWARD as a whole
file: L4.9 is retained, unedited, and still runs — it is weaker, not false — and
MANIFEST.sha256's supersession notes point from it to here (D0106 ruling 2, D0225's pattern).

BRIEF §5.3: "the only IO doorway is `oracles/`, and the only way to read the world is through a
capture handle"; §5.7: the Clock oracle is the only source of time. L4.9 froze the shell's half
over a HAND-WRITTEN network set and did not scan process creation at all, so `imaplib`,
`poplib`, `socketserver`, `xmlrpc.client`, `subprocess.run(["curl", …])` and `os.system(…)`
all read the world with L4.9 green (RT-M4-02). The custody-set guard `scripts/check_doorway.py`
closed both holes at the M4 boundary sitting (D0248). This law is the frozen judge of the same
property, and it RESTATES the guard's derivation rather than importing it: a frozen check that
delegates to an owner-editable script would change meaning whenever the script does. The two
are then held together by the differential clause below, so drift between them is a red law.

THREE RULES, and what each forbidden set is derived from:

  NETWORK  outside `tannen.oracles`, `tannen.r2` and `tannen.laws`, no import whose STATIC
           module-level import closure reaches a SEED. The seeds are the operating system's
           socket primitives — the one irreducible constant — so the network set is derived
           from the interpreter's own sources, never listed. `tannen.laws` is the evidence
           RUNNER (hypothesis, pytest, jsonschema all reach a socket), a door for this rule only.
  PROCESS  outside `tannen.oracles` and `tannen.r2`, no import of a module the
           `shell-no-subprocess` contract in governance/importlinter.toml forbids (DERIVED from
           that contract), and no use of an `os` process primitive (`system`, `popen`, `exec*`,
           `spawn*`, `posix_spawn*`, `fork*`: named, as POSIX's primitives are, not as a list of
           tools). `tannen.laws` is NOT a door here.
  CLOCK    outside `tannen.oracles` and `tannen.laws`, no import of a module the
           `kernel-no-clock` contract forbids (DERIVED, as L4.9 derived it).

LIMITS — stated as limits, not left as silence (D0248 item (5)):
  - Dynamic imports. `importlib.import_module(name)` and `__import__(name)` with a computed name
    are invisible to a static scan; `tannen.cli` loads a PIPELINE module that way, and that
    module is the operator's code, not this package's.
  - The closure is resolved against the interpreter running this law. A different environment
    can derive a different set; the positive controls refuse a derivation that stops seeing a
    known network module or starts seeing a known local one.
  - The `os` rule matches the literal name `os`: `import os as o; o.system(…)` is not seen.
  - The process rule refuses process MODULES BY NAME, not by closure: a stdlib module that
    itself spawns a child (`webbrowser`, for one) is not refused on that ground.
  - Anything reached through `ctypes`, `cffi` or a C extension's own internals.
"""

from __future__ import annotations

import ast
import importlib.util
import re
import subprocess
import sys
import tomllib
from collections import Counter
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
CORPUS = REPO_ROOT / ".dogfood" / "corpus.json"

if not CORPUS.is_file():
    pytest.skip(
        "M5 dogfood corpus absent — every M5 law goes live together when an authorised corpus "
        "is present at .dogfood/corpus.json (docs/specs/m5.md §8)",
        allow_module_level=True,
    )

pytest.importorskip("tannen.dogfood", reason=(
    "M5 dogfood not implemented yet (law suite frozen ahead of Session B); M5's laws go "
    "live together — docs/specs/m5.md §8"))

VALIDATION_REASON = (
    "a static property of the package's import graph: a model has no import graph to check. "
    "The derivation carries positive controls instead, the residue fixture is its negative "
    "control, and the differential clause holds it to scripts/check_doorway.py."
)

GUARD = REPO_ROOT / "scripts" / "check_doorway.py"
FIXTURE = REPO_ROOT / "tests" / "poison" / "doorway-network-residue"

SEEDS = frozenset({"socket", "_socket", "ssl", "_ssl"})
OS_PROCESS_PREFIXES = ("system", "popen", "exec", "spawn", "posix_spawn", "fork")

NETWORK_DOORS = ("tannen.oracles", "tannen.r2", "tannen.laws")
PROCESS_DOORS = ("tannen.oracles", "tannen.r2")
CLOCK_DOORS = ("tannen.oracles", "tannen.laws")

MUST_REACH = ("imaplib", "http.client")
MUST_NOT_REACH = ("os", "pathlib", "json")
MUST_SCAN = ("tannen", "tannen.store", "tannen.executor", "tannen.incremental", "tannen.cli",
             "tannen.oracles")


def _contract(contract_id: str) -> frozenset:
    config = tomllib.loads((REPO_ROOT / "governance" / "importlinter.toml").read_text(
        encoding="utf-8"))
    for contract in config["tool"]["importlinter"]["contracts"]:
        if contract.get("id") == contract_id:
            return frozenset(contract["forbidden_modules"])
    raise AssertionError(f"governance/importlinter.toml has no {contract_id} contract")


PROCESS = _contract("shell-no-subprocess")
CLOCK = _contract("kernel-no-clock")


# ------------------------------------------------------------------ the derivation


def _locate(name: str) -> Path | None:
    """The source file of `name`, found WITHOUT importing anything: only the top-level name
    goes through `find_spec` (which locates without executing); submodules are found by
    walking the package's search locations on disk."""
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
                found, locations = base / part / "__init__.py", [str(base / part)]
                break
            if (base / f"{part}.py").is_file():
                found, locations = base / f"{part}.py", []
                break
        if found is None:
            return None
    return found


def _import_time_names(name: str, path: Path) -> set[str]:
    """Absolute names imported when `name` is IMPORTED: module level, class bodies and
    `if`/`try` blocks, never function bodies. Relative imports resolve against the module's
    package; a dotted name also names its parents."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, ValueError):
        return set()
    package = name if path.name == "__init__.py" else name.rpartition(".")[0]
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
                module = ".".join(p for p in (".".join(p for p in base if p), node.module or "")
                                  if p)
            else:
                module = node.module or ""
            if module:
                names.add(module)
                names |= {f"{module}.{alias.name}" for alias in node.names
                          if alias.name != "*" and _locate(f"{module}.{alias.name}")}
        stack.extend(ast.iter_child_nodes(node))
    return {".".join(n.split(".")[:i]) for n in names for i in range(1, len(n.split(".")) + 1)}


_REACHES: dict[str, bool] = {}


def reaches_seed(name: str) -> bool:
    """Whether importing `name` can, through module-level imports, load a SEED. Iterative and
    memoised; a cycle is not a route."""
    if name in _REACHES:
        return _REACHES[name]
    seen: set[str] = set()
    frontier = [name]
    hit = False
    while frontier and not hit:
        current = frontier.pop()
        if current in seen:
            continue
        seen.add(current)
        if current.split(".")[0] in SEEDS or _REACHES.get(current):
            hit = True
            break
        path = _locate(current)
        if path is not None:
            frontier.extend(n for n in _import_time_names(current, path) if n not in seen)
    _REACHES[name] = hit
    return hit


# ------------------------------------------------------------------ the scan


def modules(root: Path) -> dict[str, Path]:
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


def _inside(module: str, doors: tuple) -> bool:
    return any(module == door or module.startswith(door + ".") for door in doors)


def _imports(tree: ast.Module) -> list[tuple[int, str]]:
    """Every absolute import anywhere in the module, function bodies included: a scan of the
    package's own code asks what it CAN do, not only what it does at import."""
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [(node.lineno, alias.name) for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.append((node.lineno, node.module))
    return found


def _os_process_uses(tree: ast.Module) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                and node.value.id == "os" and node.attr.startswith(OS_PROCESS_PREFIXES)):
            found.append((node.lineno, f"os.{node.attr}"))
        elif isinstance(node, ast.ImportFrom) and node.module == "os":
            found += [(node.lineno, f"os.{alias.name}") for alias in node.names
                      if alias.name.startswith(OS_PROCESS_PREFIXES)]
    return found


def violations(root: Path, rule: str) -> list[tuple[str, int, str]]:
    """(file relative to root, line, what) for every breach of `rule` under root/src/tannen."""
    out: list[tuple[str, int, str]] = []
    for module, path in modules(root).items():
        rel = path.relative_to(root).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = _imports(tree)
        if rule == "network" and not _inside(module, NETWORK_DOORS):
            out += [(rel, line, name) for line, name in imports
                    if name.split(".")[0] != "tannen" and reaches_seed(name)]
        elif rule == "process" and not _inside(module, PROCESS_DOORS):
            out += [(rel, line, name) for line, name in imports
                    if name.split(".")[0] in PROCESS]
            out += [(rel, line, call) for line, call in _os_process_uses(tree)]
        elif rule == "clock" and not _inside(module, CLOCK_DOORS):
            out += [(rel, line, name) for line, name in imports if name.split(".")[0] in CLOCK]
    return sorted(out)


# ------------------------------------------------------------------ the law


def test_l5_2_no_module_outside_the_network_doors_reaches_a_socket() -> None:
    found = violations(REPO_ROOT, "network")
    assert found == [], f"network imports outside {NETWORK_DOORS}: {found} (BRIEF §5.3)"


def test_l5_2_no_module_outside_the_process_doors_creates_a_process() -> None:
    found = violations(REPO_ROOT, "process")
    assert found == [], f"process creation outside {PROCESS_DOORS}: {found} (BRIEF §5.3)"


def test_l5_2_no_module_outside_the_clock_doors_reads_a_clock() -> None:
    found = violations(REPO_ROOT, "clock")
    assert found == [], f"clock imports outside {CLOCK_DOORS}: {found} (BRIEF §5.7)"


def test_l5_2_the_derivations_see_what_they_must_and_nothing_they_must_not() -> None:
    """Produce-the-failure on the derivation itself: a closure that stops seeing a module
    that opens sockets, or starts seeing one that cannot, makes every verdict above worthless.
    The two contract-derived sets must be non-empty, or a scan against them checks nothing."""
    assert all(reaches_seed(name) for name in MUST_REACH), \
        f"the derived closure no longer sees a socket behind {MUST_REACH}"
    assert not any(reaches_seed(name) for name in MUST_NOT_REACH), \
        f"the derived closure over-approximates: one of {MUST_NOT_REACH} reaches a socket"
    assert PROCESS, "the shell-no-subprocess contract forbids no module"
    assert CLOCK, "the kernel-no-clock contract forbids no module"


def test_l5_2_the_scan_covers_the_package_it_guards() -> None:
    scanned = modules(REPO_ROOT)
    missing = [name for name in MUST_SCAN if name not in scanned]
    assert not missing, f"the doorway scan does not reach {missing}"


def test_l5_2_the_residue_fixture_fails_exactly_its_six_payloads() -> None:
    """RT-M4-02's fixture (D0246 A4): the payloads L4.9 passed. Exactly six — two process, four
    network — and the controls beside them (the runner door, the doorway itself, filesystem
    IO) produce nothing."""
    found = Counter()
    for rule in ("network", "process", "clock"):
        for rel, _line, _what in violations(FIXTURE, rule):
            found[(rel.removeprefix("src/tannen/"), rule)] += 1
    assert found == Counter({
        ("store.py", "process"): 1,
        ("executor.py", "process"): 1,
        ("cli.py", "network"): 1,
        ("incremental.py", "network"): 1,
        ("export.py", "network"): 2,
    }), f"the residue fixture is not failed exactly by its payloads: {dict(found)}"


_GUARD_LINE = re.compile(r"^\s+- (src/tannen/[^:]+):(\d+): (network|process) — ")


@pytest.mark.parametrize("tree", ["repository", "residue-fixture"])
def test_l5_2_the_law_and_the_guard_agree(tree: str) -> None:
    """The differential clause. The law restates the guard's derivation rather than importing
    it, so the two could drift; here they must name the same (file, line, rule) triples, over
    the real tree and over the fixture. The guard runs as the gate runs it, `-I -P`."""
    root = REPO_ROOT if tree == "repository" else FIXTURE
    run = subprocess.run([sys.executable, "-I", "-P", str(GUARD), "--root", str(root)],
                         capture_output=True, text=True, check=False, cwd=REPO_ROOT)
    guard = sorted({(m.group(1), int(m.group(2)), m.group(3))
                    for m in map(_GUARD_LINE.match, (run.stdout + run.stderr).splitlines()) if m})
    law = sorted({(rel, line, rule) for rule in ("network", "process")
                  for rel, line, _what in violations(root, rule)})
    assert guard == law, f"the law and scripts/check_doorway.py disagree over {tree}: " \
                         f"guard {guard}, law {law}\n{run.stdout}{run.stderr}"
    assert (run.returncode == 0) == (law == []), \
        f"the guard's exit code disagrees with its own violations over {tree}"
