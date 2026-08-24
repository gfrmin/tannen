#!/usr/bin/env python3
"""Apply D0052: binding strength as a schema field, and mark this batch honestly.

Owner-applied at the boundary sitting, because half of it edits a frozen path
(governance/schemas/decision-record.schema.json). The two halves must land together:
`additionalProperties: false` is set on the binding object, so a record carrying
`strength:` fails validation until the schema allows it, and a schema allowing it while
no record uses it reports `0 documentary` — a false number, which is worse than none.

Idempotent: re-running changes nothing.

SEQUENCING HAZARD (proposal §"read before applying"): do NOT add `documentary` to the
ratchet's enforced comparisons on the same day. Land the field, mark the bindings, let
ONE digest carry the true numbers, and only then ratchet. A digest generated before the
field exists establishes a documentary=0 baseline, and the first honest mark after it
reads as a breach — the ratchet would be punishing accurate self-reporting.
"""

import pathlib
import sys

#: Bindings whose target records an intent rather than enforcing it: a drafted patch
#: awaiting the owner's key, a report, a checklist. Each is (record sequence, target);
#: only the FIRST binding with that target is marked, which in D0049 is the `file`
#: binding — its `manifest` sibling on the same path is genuinely enforced.
DOCUMENTARY = [
    ("0027", "docs/OPENING.md"),
    ("0036", "docs/proposals/2026-08-24-custodian-tag-ordering.md"),
    ("0037", "docs/OPENING.md"),
    ("0048", "docs/proposals/2026-08-24-policy-in-repo-mechanics.md"),
    ("0049", "DELEGATIONS.md"),
    ("0049", "docs/proposals/2026-08-24-custodian-close-tag-signer.md"),
    ("0050", "docs/proposals/2026-08-24-custodian-signer-role-table.md"),
    ("0052", "docs/proposals/2026-08-24-binding-strength-grade.md"),
    ("0053", "docs/proposals/2026-08-24-policy-in-repo-mechanics.md"),
    ("0059", "docs/redteam/2026-08-24-m0-boundary.md"),
    ("0059", "docs/redteam/fixture-candidates/README.md"),
    ("0060", "docs/redteam/fixture-candidates/README.md"),
    ("0061", "docs/SITTING.md"),
    ("0062", "docs/SITTING.md"),
    ("0063", "docs/proposals/2026-08-25-boundary-sitting/brief-9.1-amendment.md"),
]

SCHEMA_OLD = '''          "target": { "type": "string", "minLength": 1 },
          "detail":'''

SCHEMA_NEW = '''          "target": { "type": "string", "minLength": 1 },
          "strength": {
            "enum": ["enforced", "documentary"],
            "description": "enforced: the target mechanically prevents or detects violation of this decision (a frozen path, a passing test, a consumed config key, a guard). documentary: the target records the intent — a drafted patch awaiting owner application, a prose rule no guard states — and detects nothing. Absent is read as 'enforced', so records written before this field existed keep their meaning; new records state it."
          },
          "detail":'''


def main() -> int:
    root = pathlib.Path(__file__).resolve().parents[3]
    schema = root / "governance/schemas/decision-record.schema.json"
    text = schema.read_text()
    if '"strength"' in text:
        print("schema: strength field already present")
    elif text.count(SCHEMA_OLD) != 1:
        sys.exit("schema: anchor not found exactly once — the file moved under the patch")
    else:
        schema.write_text(text.replace(SCHEMA_OLD, SCHEMA_NEW))
        print(f"schema: added strength to {schema.relative_to(root)}")

    marked = already = 0
    for seq, target in DOCUMENTARY:
        matches = sorted((root / "decisions").glob(f"{seq}-*.yaml"))
        if len(matches) != 1:
            sys.exit(f"decisions/{seq}-*.yaml: expected exactly one record, found {len(matches)}")
        path = matches[0]
        text = path.read_text()
        needle = f"    target: {target}\n"
        if needle not in text:
            sys.exit(f"{path.name}: no binding targets {target}")
        head, _, tail = text.partition(needle)
        if tail.startswith("    strength:"):
            already += 1
            continue
        path.write_text(head + needle + "    strength: documentary\n" + tail)
        marked += 1
    print(f"records: {marked} binding(s) marked documentary, {already} already marked")
    print("\nNow: regenerate the manifest row for the schema (it is frozen), then let a")
    print("builder session run `make projections` and `make digest`. That digest is the")
    print("first baseline for the documentary count — do not ratchet it before then.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
