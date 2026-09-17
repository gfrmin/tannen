"""The M5 vertical imports nothing from the constellation (BRIEF §1; D0211; D0171 ruling
(3)). UNFROZEN — `tests/laws` is sealed at `m5-laws-freeze` (D0056) and the vertical's
home was still open when that froze (D0265), so this cannot be a law file; it is a normal,
editable guard that lands ahead of B2 and is exercised once the vertical exists.

WHY THIS EXISTS BESIDE lint-imports' own `no-cross-repo` CONTRACT (governance/importlinter.
toml): that contract's `source_modules = ["tannen"]` scans the `tannen` package. The
vertical is deliberately NOT under `src/tannen/` — D0268 keeps it off git, reached by
`corpus/1`'s `pipeline` field (`MODULE:CALLABLE`) through environment wiring — so it is
invisible to that contract (measured in B1; see the m5 gate-sitting prep README). This
guard scans exactly the one file the contract cannot reach.

THE FORBIDDEN LIST IS DERIVED, never hand-copied (D0171 ruling (3)): read from
governance/importlinter.toml's `no-cross-repo` contract at import time, so a name added or
removed there moves this guard with it rather than drifting from a second, stale copy.

Skips cleanly with no `.dogfood/corpus.json` (nothing to scan before B2 writes one); watched
FAILING on a planted `import renavon` before being trusted green.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import sys
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS = REPO_ROOT / ".dogfood" / "corpus.json"


def forbidden_modules(root: Path = REPO_ROOT) -> frozenset[str]:
    """The `no-cross-repo` contract's `forbidden_modules`, read out of
    governance/importlinter.toml — never listed here (D0171 ruling (3))."""
    data = tomllib.loads((root / "governance" / "importlinter.toml").read_text(encoding="utf-8"))
    for contract in data["tool"]["importlinter"]["contracts"]:
        if contract.get("id") == "no-cross-repo":
            return frozenset(contract["forbidden_modules"])
    raise AssertionError("governance/importlinter.toml carries no 'no-cross-repo' contract "
                         "to derive the forbidden list from")


def locate(name: str) -> Path | None:
    """The source file of a top-level module name, found WITHOUT importing it
    (`find_spec` locates but does not execute) — the same discipline check_doorway.py
    uses and for the same reason: a guard that must execute a module to judge it has
    already lost."""
    try:
        spec = importlib.util.find_spec(name)
    except (ImportError, ValueError):
        return None
    if spec is None or spec.origin is None or not spec.origin.endswith(".py"):
        return None
    return Path(spec.origin)


def _package_of(name: str, path: Path) -> str:
    return name if path.name == "__init__.py" else name.rpartition(".")[0]


def import_time_names(name: str, path: Path) -> set[str]:
    """Absolute names a module imports at MODULE LEVEL (function bodies do not run at
    import and are not descended into; class/if/try bodies do run and are)."""
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
                module = ".".join(p for p in (".".join(p for p in base if p), node.module or "") if p)
            else:
                module = node.module or ""
            if module:
                names.add(module)
        stack.extend(ast.iter_child_nodes(node))
    return {part for n in names for part in
            [".".join(n.split(".")[:i]) for i in range(1, len(n.split(".")) + 1)]}


def first_forbidden_import(module_name: str, forbidden: frozenset[str]) -> str | None:
    """The first forbidden name reached by `module_name`'s static, module-level import
    closure, BFS'd and memoised — `None` if none is. A name IS forbidden if it equals or
    is a submodule of a forbidden top-level name."""
    seen: set[str] = set()
    frontier = [module_name]
    while frontier:
        name = frontier.pop()
        if name in seen:
            continue
        seen.add(name)
        top = name.split(".")[0]
        if top in forbidden:
            return top
        path = locate(name)
        if path is None:
            continue
        frontier.extend(import_time_names(name, path) - seen)
    return None


def _pipeline_module(pipeline: str) -> str:
    module, _colon, _attr = pipeline.partition(":")
    if not module:
        raise ValueError(f"corpus/1 pipeline is MODULE:CALLABLE, not {pipeline!r}")
    return module


def test_the_verticals_pipeline_imports_nothing_from_the_constellation() -> None:
    if not CORPUS.is_file():
        pytest.skip("M5 dogfood corpus absent — nothing to scan before B2 writes "
                    ".dogfood/corpus.json")
    pipeline = json.loads(CORPUS.read_text(encoding="utf-8"))["pipeline"]
    module = _pipeline_module(pipeline)
    hit = first_forbidden_import(module, forbidden_modules())
    assert hit is None, (
        f"the vertical's pipeline module {module!r} reaches forbidden constellation module "
        f"{hit!r} (BRIEF §1; governance/importlinter.toml no-cross-repo)"
    )


# ------------------------------------------------------------ watched, before being trusted


def test_the_derivation_reaches_the_configured_forbidden_names() -> None:
    """A positive control on the derivation itself: it must see what
    governance/importlinter.toml actually lists, not an empty set from a mis-typed
    contract id (the D0174 lesson — a refusal nobody has seen fire proves only half)."""
    forbidden = forbidden_modules()
    assert "renavon" in forbidden
    assert "pkm" in forbidden
    assert len(forbidden) >= 6


def test_watched_failing_on_a_planted_cross_repo_import(tmp_path: Path, monkeypatch) -> None:
    """Before this guard is trusted green, it must be watched RED: a planted vertical
    module importing `renavon` at module level, scanned exactly as the real check above
    scans a real one."""
    monkeypatch.syspath_prepend(str(tmp_path))
    (tmp_path / "renavon.py").write_text("# a stand-in for the forbidden package\n")
    (tmp_path / "planted_vertical.py").write_text(
        "import renavon\n\n\ndef pipeline(oracles, store, input_ref):\n    return renavon.parse(input_ref)\n"
    )
    importlib.invalidate_caches()
    hit = first_forbidden_import("planted_vertical", forbidden_modules())
    assert hit == "renavon", "the planted import was not caught — the derivation is not trusted"


def test_a_clean_planted_module_is_not_flagged(tmp_path: Path, monkeypatch) -> None:
    """The mirror of the failing case: a vertical that imports nothing forbidden must not
    be flagged (a guard that flags everything is as useless as one that flags nothing)."""
    monkeypatch.syspath_prepend(str(tmp_path))
    (tmp_path / "clean_vertical.py").write_text(
        "import json\n\n\ndef pipeline(oracles, store, input_ref):\n    return json.dumps({})\n"
    )
    importlib.invalidate_caches()
    assert first_forbidden_import("clean_vertical", forbidden_modules()) is None
