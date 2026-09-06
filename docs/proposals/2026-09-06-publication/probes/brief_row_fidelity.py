#!/usr/bin/env python3
"""The measurement behind patch 05 — run it rather than trusting the table in the patch.

`brief_row` is a required field of every concept record and NOTHING reads it, so a record
can misreport what frozen BRIEF §2 says about who owns a concept while the whole gate stays
green. This probe implements the two teeth patch 05 proposes and prints both directions.

Not a guard: it lives under docs/proposals/ and is wired into no gate. It exists so the
numbers in patch 05 can be reproduced, and so the owner can re-measure at the sitting
against whatever the tree looks like then rather than against what it looked like on
2026-09-06.

    .venv/bin/python docs/proposals/2026-09-06-publication/probes/brief_row_fidelity.py

Exit status is 0 always: a probe that fails the build is a guard, and installing a guard
from docs/proposals/ is what patch 05 is asking the owner to do deliberately.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from _gov import load_yaml  # noqa: E402

#: The constellation vocabulary. A hand-written enumeration, which CLAUDE.md's standing
#: rule says a guard may not depend on — see patch 05, "What this does not close".
TOKENS = ("pkm", "life-agent", "proplang", "renavon", "tannen")


def norm(text: str) -> str:
    """Markdown emphasis is not content. Measured: without this, 2 of 8 faithful records
    fail on backticks and bold alone (similarity 0.990/0.991, prose identical)."""
    return re.sub(r"\s+", " ", re.sub(r"[`*]", "", text)).strip()


def brief_rows(brief_md: Path) -> dict[str, str]:
    """BRIEF §2's table as {normalised Concept cell: normalised Owner cell}."""
    rows: dict[str, str] = {}
    for line in brief_md.read_text(encoding="utf-8").splitlines():
        if line.startswith("|") and line.count("|") >= 4 and not line.startswith("|---"):
            cells = line.split("|")
            rows[norm(cells[1])] = norm(cells[2])
    return rows


def owners_in(text: str) -> set[str]:
    lowered = text.lower()
    return {token for token in TOKENS if token in lowered}


def main() -> int:
    root = REPO_ROOT
    brief_text = norm((root / "BRIEF.md").read_text(encoding="utf-8"))
    rows = brief_rows(root / "BRIEF.md")
    records = sorted((root / "concepts").glob("*.yaml"))

    print(f"{'record':<26} {'BRIEF §2 owners':<20} {'sources[].repo':<20} tooth1  tooth2")
    print("-" * 88)
    t1_bad = t2_bad = 0
    for path in records:
        record = load_yaml(path)
        quoted = re.search(r'"([^"]+)"', record["brief_row"])
        if quoted is None:
            print(f"{path.stem:<26} brief_row quotes nothing")
            t1_bad += 1
            continue
        span = norm(quoted.group(1))

        tooth1 = span in brief_text
        t1_bad += not tooth1

        owner_cell = rows.get(span)
        if owner_cell is None:
            want: set[str] = set()
            tooth2 = False
        else:
            want = owners_in(owner_cell)
            got = owners_in(" ".join(source["repo"] for source in record["sources"]))
            declared = set((record.get("brief_row_divergence") or {}).get("omits", ()))
            tooth2 = want == got | declared
        t2_bad += not tooth2

        got_str = ",".join(
            sorted(owners_in(" ".join(s["repo"] for s in record["sources"])))
        )
        print(
            f"{path.stem:<26} {','.join(sorted(want)):<20} {got_str:<20} "
            f"{'ok' if tooth1 else 'RED':<7} {'ok' if tooth2 else 'RED'}"
        )

    print()
    print(f"tooth 1 (quoted span verbatim in BRIEF.md): {len(records) - t1_bad}/{len(records)} ok")
    print(f"tooth 2 (owner set matches sources[].repo): {len(records) - t2_bad}/{len(records)} ok")
    print()
    print(
        "Expected TODAY: 8/8 and 8/8 — D0180's withdrawal is ruled but not yet executed in\n"
        "the tracked tree (D0181: it cannot be, until patch 06 lands). Once the sitting\n"
        "executes it, tooth 2 goes 7/8 with provenance-ref-grammar RED, and that RED is the\n"
        "EXPECTED true positive until the record carries patch 05's `brief_row_divergence`\n"
        "declaration. Any other RED, at any time, is drift."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
