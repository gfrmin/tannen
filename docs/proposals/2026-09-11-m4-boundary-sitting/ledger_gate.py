#!/usr/bin/env python3
"""The RT-M4-07 gate: a boundary sitting may not close while a red-team finding is unaccounted for.

    .venv/bin/python -I -P ledger_gate.py [--root DIR]

Every finding id in docs/redteam/*.md must have exactly one row in docs/redteam/LEDGER.yaml,
carrying a valid disposition, and every row must name a finding that exists. Exit 0 prints a
summary and the rows that are not closed; exit 1 prints one line per problem.

The id set is DERIVED from the reports' own structure — `## RT-… —` headings and `| RT-… |`
table rows — never listed here, so a new report joins the gate by existing (D0171 ruling (3)).
It is a check that the ledger covers the reports, not a reading of any finding's state: what a
finding's status IS lives in the ledger row, which the owner confirms at the sitting.

Standalone on purpose: the M4 driver embeds this source verbatim, so it imports only the
standard library and yaml, and resolves --root to the current directory by default.
(D0246 A3, RT-M4-07, D0249.)
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

ID = r"RT-[A-Z0-9]+(?:-[0-9]+)*"
HEADING = re.compile(rf"^#{{1,6}} +({ID}) +—", re.M)
TABLE_ROW = re.compile(rf"^\| *({ID}) *\|", re.M)
RECORD = re.compile(r"^D[0-9]{4}$")

REQUIRED = {
    "closed": ("record",),
    "scheduled": ("where", "record"),
    "deferred": ("reason", "revisit"),
    "non-goal": ("cite",),
}
BASE = ("id", "report", "severity", "disposition")
ALLOWED = set(BASE) | {"record", "where", "reason", "revisit", "cite", "note"}


def derived_ids(root: Path) -> dict[str, set[str]]:
    """Every finding id per report, from headings and table rows."""
    found: dict[str, set[str]] = {}
    for report in sorted((root / "docs" / "redteam").glob("*.md")):
        text = report.read_text(encoding="utf-8")
        rel = report.relative_to(root).as_posix()
        for match in [*HEADING.findall(text), *TABLE_ROW.findall(text)]:
            found.setdefault(match, set()).add(rel)
    return found


def problems(root: Path) -> tuple[list[str], list[dict]]:
    out: list[str] = []
    derived = derived_ids(root)

    # Positive control: a derivation that found nothing would pass every ledger.
    for must in ("RT-01", "RT-M4-07"):
        if must not in derived:
            out.append(f"the id derivation did not find {must} in docs/redteam/*.md — "
                       "the gate is measuring its own pattern, not the reports")
    if not derived:
        return out + ["no finding ids derived at all — refusing to call an empty set covered"], []

    ledger_path = root / "docs" / "redteam" / "LEDGER.yaml"
    if not ledger_path.exists():
        return out + [f"{ledger_path.relative_to(root)} does not exist"], []
    data = yaml.safe_load(ledger_path.read_text(encoding="utf-8")) or {}
    rows = data.get("findings")
    if not isinstance(rows, list):
        return out + ["LEDGER.yaml has no `findings:` list"], []

    seen: Counter = Counter()
    good: list[dict] = []
    for n, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            out.append(f"row {n}: not a mapping")
            continue
        rid = row.get("id")
        label = rid if isinstance(rid, str) else f"row {n}"
        seen[rid] += 1
        for key in BASE:
            if not row.get(key):
                out.append(f"{label}: missing `{key}`")
        for key in sorted(set(row) - ALLOWED):
            out.append(f"{label}: unknown field `{key}`")
        disposition = row.get("disposition")
        if disposition and disposition not in REQUIRED:
            out.append(f"{label}: disposition `{disposition}` is not one of "
                       f"{', '.join(REQUIRED)}")
        for key in REQUIRED.get(disposition, ()):
            if not row.get(key):
                out.append(f"{label}: disposition `{disposition}` requires `{key}`")
        record = row.get("record")
        if record is not None:
            if not (isinstance(record, str) and RECORD.match(record)):
                out.append(f"{label}: record `{record}` is not a Dnnnn id")
            elif not list((root / "decisions").glob(f"{record[1:]}-*.yaml")):
                out.append(f"{label}: record {record} has no decisions/{record[1:]}-*.yaml")
        if disposition == "non-goal" and not str(row.get("cite", "")).startswith("BRIEF §"):
            out.append(f"{label}: a non-goal must cite a BRIEF § clause")
        if isinstance(rid, str):
            if rid not in derived:
                out.append(f"{label}: no report in docs/redteam/ names this finding "
                           "(an orphan row)")
            elif row.get("report") and row["report"] not in derived[rid]:
                out.append(f"{label}: report `{row['report']}` does not name it; it appears "
                           f"in {', '.join(sorted(derived[rid]))}")
        good.append(row)

    for rid, count in sorted((k, v) for k, v in seen.items() if isinstance(k, str) and v > 1):
        out.append(f"{rid}: {count} rows — exactly one is allowed")
    for rid in sorted(set(derived) - set(seen)):
        out.append(f"{rid}: no ledger row — named in {', '.join(sorted(derived[rid]))} "
                   "and dispositioned nowhere (RT-M4-07)")
    return out, good


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path.cwd())
    root = parser.parse_args().root.resolve()
    found, rows = problems(root)
    if found:
        print(f"ledger_gate: FAIL ({len(found)} problem(s)) — the sitting cannot close")
        for line in found:
            print(f"  - {line}")
        return 1
    counts = Counter(row["disposition"] for row in rows)
    print(f"ledger_gate: OK — {len(rows)} finding(s) accounted for: "
          + ", ".join(f"{counts[d]} {d}" for d in REQUIRED if counts[d]))
    for row in rows:
        if row["disposition"] == "closed":
            continue
        detail = row.get("where") or row.get("cite") or " ".join(str(row.get("reason", "")).split())
        extra = f" (revisit {row['revisit']})" if row.get("revisit") else ""
        print(f"  {row['id']:<9} {row['disposition']:<9} {detail[:110]}{extra}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
