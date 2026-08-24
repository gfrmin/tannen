#!/usr/bin/env python3
"""gen_custody.py — generate governance/custody.sha256 from tier-c.yaml's custody set.

The custody file is the list of bytes the OWNER vouches for by signature. It is
generated, never hand-edited: the list a human reads (`custody.set` in
governance/tier-c.yaml) and the hashes a machine checks are one source (BRIEF §9).

    scripts/gen_custody.py            rewrite the custody file from the declared set
    scripts/gen_custody.py --check    exit 1 if the file is stale or the set has holes

Regenerating it does NOT re-sign it: governance/custody.sha256.sig is the owner's act at
a boundary sitting, and a regenerated file with a stale signature is exactly the alarm
the arrangement exists to raise.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Run under `python -I -P` (conferral ruling 3, D0063): isolated mode ignores
# PYTHONPATH, PYTHONHOME and user site-packages, and -P stops any directory being
# prepended to sys.path implicitly — including this script's own. The floor may depend
# only on tools the OS provides and paths named literally, so the one path this guard
# needs is named literally here, derived from __file__ rather than inherited.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _gov import REPO_ROOT, custody_declaration, custody_rows  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--check", action="store_true",
                        help="verify the custody file is current; write nothing")
    args = parser.parse_args()
    root = args.root.resolve()

    declaration = custody_declaration(root)
    if not declaration:
        print("gen_custody: no custody set declared in governance/tier-c.yaml", file=sys.stderr)
        return 1
    rows, problems = custody_rows(root)
    for problem in problems:
        print(f"gen_custody: FAIL — {problem}", file=sys.stderr)
    target = root / declaration["file"]
    content = "".join(f"{row}\n" for row in rows)

    if args.check:
        current = target.read_text(encoding="utf-8") if target.exists() else None
        if current != content:
            print(f"gen_custody: FAIL — {declaration['file']} is stale; "
                  "run scripts/gen_custody.py", file=sys.stderr)
            return 1
        if problems:
            return 1
        print(f"gen_custody: OK — {len(rows)} custody path(s) current")
        return 0

    if problems:
        return 1
    target.write_text(content, encoding="utf-8")
    print(f"gen_custody: wrote {declaration['file']} ({len(rows)} path(s))")
    if (sig := target.with_name(target.name + ".sig")).exists():
        print("gen_custody: NOTE — the existing owner signature no longer covers this "
              f"content. Re-signing {sig.name} is a boundary-sitting act.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
