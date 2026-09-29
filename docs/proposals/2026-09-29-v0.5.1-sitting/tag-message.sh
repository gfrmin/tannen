#!/usr/bin/env bash
# Prints the v0.5.1 tag message (D0276). Run from the repository root, on a clean tree, after
# the sitting's commit. A version tag attests the tree at the version pyproject.toml carries,
# so it refuses to speak for a tree that carries another one.
set -euo pipefail
want=0.5.1
[ -z "$(git status --porcelain)" ] || { echo "tag-message: the tree is not clean (D0051)" >&2; exit 1; }
have=$(sed -n 's/^version = "\(.*\)"$/\1/p' pyproject.toml)
[ "$have" = "$want" ] || { echo "tag-message: pyproject.toml carries $have, not $want (D0276)" >&2; exit 1; }
echo "v$want — owner-signed (D0276)."
echo
echo "Attests the tree at version $want, the first tag that carries the import surface a"
echo "pinned dependent may use: tannen.SURFACE, each module's __all__ (D0275). It is not a"
echo "milestone gate: it closes no milestone, and it matches no boundary pattern, so it starts"
echo "no receipt clock (governance/tag-roles.yaml)."
echo
echo "Standing delegation in force at this signature (D0051: authority-bearing"
echo "tags quote the delegation's hash alongside its text):"
echo "  DELEGATIONS.md sha256 = $(sha256sum DELEGATIONS.md | cut -d' ' -f1)"
echo "  governance/custody.sha256 sha256 = $(sha256sum governance/custody.sha256 | cut -d' ' -f1)"
echo
cat DELEGATIONS.md
