#!/usr/bin/env python3
"""check_laws.py — every frozen law declares how it was validated; every retired law
names a live successor (decision D0129; BRIEF §8, §9.1).

Two gaps this closes, both named by D0094:

  - Under the frozen-oracle protocol a law becomes unrewritable at exactly the moment it
    is an `importorskip`, so `pytest tests/laws/<m>` prints the same "N skipped" whether
    the laws are correct, contradictory or nonsense (D0093 was an unsatisfiable axiom
    frozen with every guard green). A law file must therefore SAY how it was validated:
    `VALIDATED_BY` naming a model check, or `VALIDATION_REASON` saying why the family
    cannot be model-checked. Neither is enforcement of correctness — it makes the gap
    COUNTABLE, which is the bargain `unenforced_reason` already strikes for decisions.
  - A law found wrong after its milestone closed is superseded FORWARD (D0106 ruling 2),
    and the retired node must stay honest: `governance/laws.yaml` names it, its
    successor law, and the record. This guard refuses an entry whose successor does not
    exist, whose node is not in the frozen file, or which cites no record.

Parsed STATICALLY, like `tannen.laws.discovery`: the check must not depend on the law
files being importable, or a pre-implementation tree would report nothing at all instead
of reporting the whole set.

Exits non-zero on any violation.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

# Run under `python -I -P` (conferral ruling 3, D0063): isolated mode ignores
# PYTHONPATH, PYTHONHOME and user site-packages, and -P stops any directory being
# prepended to sys.path implicitly — including this script's own. The floor may depend
# only on tools the OS provides and paths named literally, so the one path this guard
# needs is named literally here, derived from __file__ rather than inherited.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _gov import Failures, load_yaml, parse_manifest, REPO_ROOT  # noqa: E402

LAWS_DIR = Path("tests") / "laws"
REGISTRY = Path("governance") / "laws.yaml"
LAW_TEST_RE = re.compile(r"^test_l(\d+)_(\d+)(?:_|$)")
MILESTONE_DIR_RE = re.compile(r"^m(\d+)b?$")

#: The two declarations, and the rule: exactly one of them, at module level, a non-empty
#: string. A file carrying both is not an error — `test_l2_sources.py` model-checks one of
#: its two laws and states a reason for the other — but a file carrying neither is.
DECLARATIONS = ("VALIDATED_BY", "VALIDATION_REASON")


def module_declarations(tree: ast.Module) -> dict[str, str | None]:
    """Module-level `NAME = <str>` assignments among DECLARATIONS."""
    found: dict[str, str | None] = {}
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if isinstance(target, ast.Name) and target.id in DECLARATIONS:
                value = node.value
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    found[target.id] = value.value
                elif isinstance(value, ast.JoinedStr) or value is None:
                    found[target.id] = None
                else:
                    # an implicitly-concatenated literal, the usual way a long reason is
                    # written: fold it if every part is a plain string.
                    try:
                        folded = ast.literal_eval(value)
                    except Exception:
                        folded = None
                    found[target.id] = folded if isinstance(folded, str) else None
    return found


def law_nodes(tree: ast.Module) -> dict[str, set[str]]:
    """`{law id: {test function names}}` in one parsed law file."""
    out: dict[str, set[str]] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            match = LAW_TEST_RE.match(node.name)
            if match:
                out.setdefault(f"L{match.group(1)}.{match.group(2)}", set()).add(node.name)
    return out


def required_from(root: Path) -> int:
    """The first milestone whose frozen law files must declare their validation.

    M0 and M1 were frozen and sealed before the rule existed, so adding a declaration to
    one would be an edit to a frozen path. They are exempt and COUNTED, never silently
    skipped (D0129).
    """
    path = root / REGISTRY
    if not path.exists():
        return 0
    value = ((load_yaml(path) or {}).get("validation") or {}).get("declarations_required_from")
    match = MILESTONE_DIR_RE.match(str(value or ""))
    return int(match.group(1)) if match else 0


def check_declarations(root: Path, fail: Failures) -> tuple[int, int]:
    """Every law file at or after `declarations_required_from` declares one of
    DECLARATIONS; returns (declared, exempt)."""
    floor = required_from(root)
    seen = 0
    exempt = 0
    manifest = root / "MANIFEST.sha256"
    frozen = parse_manifest(manifest) if manifest.exists() else {}
    for directory in sorted((root / LAWS_DIR).iterdir() if (root / LAWS_DIR).is_dir() else []):
        if not directory.is_dir() or not MILESTONE_DIR_RE.match(directory.name):
            continue
        milestone = int(MILESTONE_DIR_RE.match(directory.name).group(1))
        for path in sorted(directory.glob("test_*.py")):
            rel = path.relative_to(root).as_posix()
            if rel in frozen and milestone < floor:
                exempt += 1
                continue
            if rel not in frozen:
                # Not yet frozen: it is Session A's working copy, and demanding a
                # declaration of a file still being written would be a guard firing at
                # the author rather than at the record.
                continue
            seen += 1
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            declared = module_declarations(tree)
            present = {name: value for name, value in declared.items() if value}
            if not present:
                fail.add(
                    f"{rel}: declares neither VALIDATED_BY nor VALIDATION_REASON — a frozen "
                    "law whose validation nobody wrote down is not merely unvalidated, it is "
                    "unrepresentable (D0094 §3)"
                )
                continue
            target = present.get("VALIDATED_BY")
            if target:
                module, _, check = target.partition("::")
                model = root / module
                if not model.exists():
                    fail.add(f"{rel}: VALIDATED_BY names a missing file: {module}")
                elif check and f"def {check}(" not in model.read_text(encoding="utf-8"):
                    fail.add(f"{rel}: VALIDATED_BY names {check}, which {module} does not define")
    return seen, exempt


def check_supersessions(root: Path, fail: Failures) -> int:
    """Every retired law node names a live successor and the record that retired it."""
    path = root / REGISTRY
    if not path.exists():
        return 0
    registry = load_yaml(path) or {}
    lists = {}
    for key in ("superseded", "pending"):
        value = registry.get(key) or []
        if not isinstance(value, list):
            fail.add(f"{REGISTRY}: `{key}` must be a list")
            value = []
        lists[key] = value
    active = {str(entry.get("node")) for entry in lists["superseded"] if entry.get("node")}
    for entry in lists["pending"]:
        if str(entry.get("node")) in active:
            fail.add(
                f"{REGISTRY}: {entry.get('node')} is in BOTH superseded and pending — an "
                "entry is either active or awaiting the change that retires it, never both"
            )
    entries = lists["superseded"] + lists["pending"]
    for entry in entries:
        node = entry.get("node", "<unnamed>")
        for field in ("node", "successor", "record", "reason"):
            if not entry.get(field):
                fail.add(f"{REGISTRY}: entry {node} has no {field}")
        file_part, _, function = str(entry.get("node", "")).partition("::")
        target = root / file_part
        if not target.exists():
            fail.add(f"{REGISTRY}: {node} names a file that does not exist")
            continue
        tree = ast.parse(target.read_text(encoding="utf-8"), filename=str(target))
        names = {name for nodes in law_nodes(tree).values() for name in nodes}
        if function not in names:
            fail.add(
                f"{REGISTRY}: {node} is not a law node in {file_part} — a retired node that "
                "has moved or been renamed is a supersession pointing at nothing"
            )
        successor = str(entry.get("successor", ""))
        if successor and not _successor_exists(root, successor):
            fail.add(
                f"{REGISTRY}: {node} names successor {successor}, which no law file defines — "
                "a claim retired with nothing carrying it forward is a claim dropped (D0106)"
            )
        record = entry.get("record")
        if record and not _record_exists(root, str(record)):
            fail.add(f"{REGISTRY}: {node} cites {record}, which decisions/ does not contain")
    return len(entries)


def _successor_exists(root: Path, law: str) -> bool:
    for directory in (root / LAWS_DIR).iterdir() if (root / LAWS_DIR).is_dir() else []:
        if not directory.is_dir():
            continue
        for path in directory.glob("test_*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            if law in law_nodes(tree):
                return True
    return False


def _record_exists(root: Path, record: str) -> bool:
    """By declared id, never by filename arithmetic: a record's slug is free text and the
    `id:` line is the thing check_decisions validates."""
    return any(
        f"\nid: {record}\n" in path.read_text(encoding="utf-8")
        for path in (root / "decisions").glob("*.yaml")
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    fail = Failures("check_laws")
    files, exempt = check_declarations(root, fail)
    retired = check_supersessions(root, fail)
    return fail.finish(
        f"{files} frozen law file(s) declare their validation, {exempt} exempt "
        f"(frozen before the rule — the `unvalidated` residue, D0129); {retired} "
        "superseded/pending node(s) name a live successor"
    )


if __name__ == "__main__":
    sys.exit(main())
