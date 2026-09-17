#!/usr/bin/env python3
"""measure_dogfood_candidates.py — build `.dogfood/measurement.json` (docs/specs/m5.md §2)
from an owner-authored candidate list, run ON THE OWNER'S MACHINE, AFTER the gate sitting's
signature (D0268; Tier-C door `renavon-first-contact`). This script itself never reads
Renavon source: it counts lines in files the INPUT already names.

WHAT THIS SCRIPT DOES NOT DO. It does not choose which Renavon sources are candidates,
whether one has a `visible_export`, or which tannen operators its parser would require —
those are judgement calls over Renavon source, made by whoever runs this on the owner's
machine, and recorded in `--input`. This script owes exactly one mechanical fact: `loc/1`,
"non-blank physical lines that are not only a comment" (docs/specs/m5.md §2), counted over
the files the input names. `select()` is printed at the end as a PREVIEW of what L5.4 would
compute — it is not a choice; "L5.4 then selects the vertical and nobody chooses it"
(D0257 ask (2)).

INPUT (`--input`, YAML):

    root: /path/to/a/renavon/checkout          # never committed; local to this machine
    candidates:
      - source: some-parser
        visible_export: true
        parser_files: [src/parsers/some_parser.py]
        operators: [select, project]

`parser_files` are relative to `root`. `operators` is the input's own judgement, not
derived here — `tannen.dogfood.select` (and L5.4) check membership against
`tannen.kernel.ops.OPERATORS` when the measurement is actually used; this script only
checks it as a courtesy, so a typo is caught before `.dogfood/measurement.json` is written
rather than after.

OUTPUT (`--out`, default `.dogfood/measurement.json`): `measurement/1` (docs/specs/m5.md
§2) — `source`, `visible_export` and `operators` copied from the input; `parser_files` and
`parser_loc` computed here.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

#: `loc/1`'s comment marker per extension — the one thing this script must get right to
#: own the counter. An extension not listed refuses rather than guessing (silently
#: counting comment lines as code would inflate the very number BRIEF §8 minimises on).
COMMENT_PREFIXES: dict[str, tuple[str, ...]] = {
    ".py": ("#",), ".pyi": ("#",), ".pyx": ("#",),
    ".rb": ("#",), ".sh": ("#",), ".bash": ("#",),
    ".yaml": ("#",), ".yml": ("#",), ".toml": ("#",),
    ".js": ("//",), ".jsx": ("//",), ".mjs": ("//",), ".cjs": ("//",),
    ".ts": ("//",), ".tsx": ("//",),
    ".go": ("//",), ".rs": ("//",), ".java": ("//",), ".kt": ("//",), ".swift": ("//",),
    ".c": ("//",), ".h": ("//",), ".cpp": ("//",), ".hpp": ("//",), ".cc": ("//",),
    ".sql": ("--",), ".lua": ("--",),
}


def count_loc(path: Path) -> int:
    """`loc/1`: non-blank physical lines that are not only a comment (docs/specs/m5.md
    §2). A line counts unless stripping whitespace leaves it empty, or leaves it starting
    with the extension's line-comment marker — code followed by a trailing comment still
    counts, because it is not ONLY a comment. Block comments are not addressed by the spec
    and are not addressed here."""
    prefixes = COMMENT_PREFIXES.get(path.suffix.lower())
    if prefixes is None:
        raise ValueError(
            f"no loc/1 comment rule for extension {path.suffix!r} ({path}) — add one to "
            "COMMENT_PREFIXES before counting, rather than guess and silently miscount"
        )
    text = path.read_text(encoding="utf-8", errors="replace")
    return sum(
        1 for line in text.splitlines()
        if (stripped := line.strip()) and not stripped.startswith(prefixes)
    )


def build_candidate(root: Path, entry: dict) -> dict:
    for key in ("source", "visible_export", "parser_files", "operators"):
        if key not in entry:
            raise ValueError(f"candidate missing {key!r}: {entry}")
    files = [str(f) for f in entry["parser_files"]]
    if not files:
        raise ValueError(f"candidate {entry['source']!r} names no parser_files")
    loc = sum(count_loc(root / f) for f in files)
    return {
        "source": entry["source"],
        "visible_export": bool(entry["visible_export"]),
        "parser_files": files,
        "parser_loc": loc,
        "operators": list(entry["operators"]),
    }


def check_operators(candidates: list[dict]) -> list[str]:
    """A courtesy pre-check, not the authority — L5.4 is (docs/specs/m5.md §2: membership
    is decided against tannen.kernel.ops.OPERATORS, derived from the package, never listed
    here). Import failure (no tannen install on this machine) degrades to skipping the
    check rather than refusing to write the measurement at all."""
    try:
        from tannen.kernel.ops import OPERATORS
    except ImportError:
        return []
    known = set(OPERATORS)
    return sorted({
        op for candidate in candidates for op in candidate["operators"] if op not in known
    })


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, required=True,
                        help="YAML candidate list (see this script's docstring)")
    parser.add_argument("--out", type=Path, default=Path(".dogfood/measurement.json"))
    parser.add_argument("--preview-selection", action="store_true",
                        help="print what L5.4's rule would select over this measurement "
                             "(a preview, never a choice — tannen must be importable)")
    args = parser.parse_args()

    spec = yaml.safe_load(args.input.read_text(encoding="utf-8"))
    root = Path(spec["root"]).expanduser()
    if not root.is_dir():
        print(f"root does not exist or is not a directory: {root}", file=sys.stderr)
        return 2
    entries = spec.get("candidates") or []
    if not entries:
        print("input names no candidates", file=sys.stderr)
        return 2

    candidates = [build_candidate(root, entry) for entry in entries]
    sources = [c["source"] for c in candidates]
    if len(set(sources)) != len(sources):
        dupes = sorted({s for s in sources if sources.count(s) > 1})
        print(f"input names a source more than once (L5.4 would refuse this whole): "
              f"{dupes}", file=sys.stderr)
        return 2
    unknown = check_operators(candidates)
    if unknown:
        print(f"operator(s) not in tannen.kernel.ops.OPERATORS (L5.4 would refuse this "
              f"whole): {unknown}", file=sys.stderr)
        return 2

    measurement = {"tannen": "measurement/1", "counter": "loc/1", "candidates": candidates}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(measurement, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.out} ({len(candidates)} candidate(s))")
    for c in candidates:
        print(f"  {c['source']}: visible_export={c['visible_export']} "
              f"parser_loc={c['parser_loc']} operators={c['operators']}")

    if args.preview_selection:
        try:
            from tannen.dogfood import SelectionRefused, select
        except ImportError:
            print("tannen.dogfood not importable — cannot preview a selection", file=sys.stderr)
            return 1
        try:
            chosen = select(measurement)
            print(f"preview only, NOT a choice — L5.4 over this measurement selects: {chosen}")
        except SelectionRefused as exc:
            print(f"preview only, NOT a choice — L5.4 over this measurement refuses: {exc}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
