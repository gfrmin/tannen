"""Law discovery and law descriptors (BRIEF §6, P6; `docs/specs/m0.md` §5–§6).

The milestone's law set is read from the frozen law files themselves — never from a
hand-maintained list, which could drift from the tests it claims to describe. A law's
*descriptor* is what makes "fresh evidence for current descriptors" (BRIEF §5.11)
mechanically checkable: it is `H(kind="law", name, code_hash, params_hash)` where

- `code_hash` addresses the law files that define the law, and
- `params_hash` addresses the implementation the run was made against.

Change either and the descriptor changes, so every previously recorded verdict stops
applying to the current state — which is precisely what staleness means.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterable
from pathlib import Path

from tannen.kernel.descriptor import descriptor_id
from tannen.kernel.encoding import content_address
from tannen.kernel.refs import ref_for_bytes

__all__ = [
    "LAWS_DIR",
    "discover_laws",
    "find_root",
    "implementation_subject",
    "law_descriptor",
    "law_id_of",
    "law_sort_key",
    "milestone_label",
    "milestones",
]

LAWS_DIR = Path("tests") / "laws"
IMPLEMENTATION_DIR = Path("src") / "tannen"

#: `test_l0_10_...` → L0.10. The law id is part of the frozen test's name, so the
#: mapping needs no registry to fall out of date.
LAW_TEST_RE = re.compile(r"^test_l(\d+)_(\d+)(?:_|$)")
MILESTONE_DIR_RE = re.compile(r"^m(\d+)(b?)$")
DESCRIPTOR_KIND = "law"


def find_root(start: Path | None = None) -> Path:
    """The repo root: the nearest ancestor carrying MANIFEST.sha256."""
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "MANIFEST.sha256").exists():
            return candidate
    return current


def law_id_of(function_name: str) -> str | None:
    match = LAW_TEST_RE.match(function_name)
    return f"L{match.group(1)}.{match.group(2)}" if match else None


def law_sort_key(law: str) -> tuple[int, int]:
    """L0.2 before L0.10 — law ids are numbers, and reports are read by humans."""
    major, _, minor = law.lstrip("L").partition(".")
    return int(major), int(minor)


def milestone_label(directory_name: str) -> str:
    """`m0` → `M0` (the spelling the evidence-record schema pins)."""
    match = MILESTONE_DIR_RE.match(directory_name)
    if not match:
        raise ValueError(f"not a milestone directory name: {directory_name!r}")
    return f"M{match.group(1)}{match.group(2)}"


def milestones(root: Path) -> list[str]:
    laws = root / LAWS_DIR
    if not laws.is_dir():
        return []
    return sorted(p.name for p in laws.iterdir() if p.is_dir() and MILESTONE_DIR_RE.match(p.name))


def discover_laws(root: Path, milestone: str) -> dict[str, dict[str, frozenset[str]]]:
    """`{law_id: {law-file relpath: {test function names}}}` for one milestone.

    Parsed statically: discovery must not depend on the tests being importable, so a
    pre-implementation tree still reports the full law set as missing evidence rather
    than reporting nothing at all.
    """
    found: dict[str, dict[str, set[str]]] = {}
    directory = root / LAWS_DIR / milestone
    for path in sorted(directory.glob("test_*.py")):
        rel = path.relative_to(root).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            law = law_id_of(node.name)
            if law is not None:
                found.setdefault(law, {}).setdefault(rel, set()).add(node.name)
    return {
        law: {rel: frozenset(names) for rel, names in sorted(modules.items())}
        for law, modules in sorted(found.items(), key=lambda item: law_sort_key(item[0]))
    }


def implementation_subject(root: Path) -> str:
    """Ref of the harness the laws are run against (`params_hash`).

    Since M1 (law L1.17, RT-09) this is `tannen.laws.harness.harness_subject`: the whole of
    `src/tannen` plus the files that decide how hard a law was tested. Narrowing it to a
    guessed dependency set would let an edit elsewhere silently inherit an old verdict.
    """
    from tannen.laws.harness import harness_subject  # local: harness is a leaf, discovery is not

    return harness_subject(root)


def law_descriptor(root: Path, law: str, module_paths: Iterable[str], subject: str | None = None) -> str:
    """The current descriptor of one law (see the module docstring)."""
    code_hash = content_address(
        {rel: ref_for_bytes((root / rel).read_bytes()) for rel in sorted(module_paths)}
    )
    return descriptor_id(
        kind=DESCRIPTOR_KIND,
        name=law,
        code_hash=code_hash,
        params_hash=subject if subject is not None else implementation_subject(root),
    )
