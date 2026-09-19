#!/usr/bin/env bash
# Prints the m5-close tag message, the same shape as m4-close's (D0051, RT-M4-07, D0249).
# Run from the repository root, on a clean tree, after the sitting's commit.
set -euo pipefail
[ -z "$(git status --porcelain)" ] || { echo "tag-message: the tree is not clean (D0051)" >&2; exit 1; }
ledger=$(.venv/bin/python -I -P docs/proposals/2026-09-11-m4-boundary-sitting/ledger_gate.py)
echo "m5 close — owner-signed (D0047, D0049)."
echo
echo "Closes milestone m5: the frozen law suite is green, L5.1-L5.10 carry fresh passing"
echo "evidence on the owner's machine with the authorised corpus present and zero skips, and"
echo "the pipeline behind that evidence is the reviewed one pinned by D0273 (D0270, D0272)."
echo
echo "Standing delegation in force at this signature (D0051: authority-bearing"
echo "tags quote the delegation's hash alongside its text):"
echo "  DELEGATIONS.md sha256 = $(sha256sum DELEGATIONS.md | cut -d' ' -f1)"
echo "  governance/custody.sha256 sha256 = $(sha256sum governance/custody.sha256 | cut -d' ' -f1)"
echo
echo "Findings accounted for at this signature (RT-M4-07, D0249):"
echo "  docs/redteam/LEDGER.yaml sha256 = $(sha256sum docs/redteam/LEDGER.yaml | cut -d' ' -f1)"
printf '%s\n' "$ledger" | sed 's/^/  /'
echo
cat DELEGATIONS.md
