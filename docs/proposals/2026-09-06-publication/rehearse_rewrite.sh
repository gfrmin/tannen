#!/usr/bin/env bash
# Rehearsal for the publication history rewrite (D0176). Run before the sitting, never
# at it: this proves the mechanics and measures what breaks, so the sitting executes a
# known sequence instead of exploring one. D0068's discipline — the M2 sitting's five
# defects (D0147-D0151) were all found by executing a rehearsal, none by reading.
#
# DISPOSABLE SCRATCH ONLY. It clones; it never writes to the source repository. Point
# WORK at a temporary directory you are willing to lose.
#
#   WORK=$(mktemp -d) ./docs/proposals/2026-09-06-publication/rehearse_rewrite.sh
#
# What it does NOT rehearse, and cannot: the four owner-signed tags and the owner
# signature on the rewrite attestation. Step 10 points allowed_signers' owner line at the
# BUILDER key so the chain can be exercised end to end; that substitution is the one part
# of this script that is a simulation rather than a measurement, and it is why the
# receipt signature failures in step 11 are expected rather than findings.
set -uo pipefail

WORK=${WORK:?set WORK to a disposable directory}
SRC=${SRC:-$HOME/git/tannen}                       # the bare repo with the live worktrees
REAL=${REAL:-$(cd "$(dirname "$0")/../../.." && pwd)}   # this working tree
FR=${FR:-$(command -v git-filter-repo)}
BUILDER_KEY=${BUILDER_KEY:-$HOME/.ssh/tannen_builder}
RW=$WORK/rw

say() { printf '\n=== %s\n' "$*"; }
ok()  { printf '    [ok] %s\n' "$*"; }
bad() { printf '    [BAD] %s\n' "$*"; }

[ -x "$FR" ] || { echo "git-filter-repo not found; set FR"; exit 1; }
rm -rf "$RW"

say "1. clone all refs into a disposable working repo"
git clone --quiet "$SRC" "$RW" || exit 1
cd "$RW" || exit 1
git fetch --quiet origin '+refs/heads/*:refs/remotes/origin/*'
for b in m0 m1 m2 m3; do git branch --quiet -f "$b" "origin/$b" 2>/dev/null; done
git remote remove origin
printf '    branches: %s\n' "$(git branch --format='%(refname:short)' | tr '\n' ' ')"
printf '    tags:     %s\n' "$(git tag | tr '\n' ' ')"
printf '    commits:  %s\n' "$(git rev-list --all --count)"

say "2. pre-rewrite state: tag object, tagged commit, tagger date"
: > "$WORK/tags_before.txt"
for t in $(git tag); do
  printf '%s\t%s\t%s\t%s\n' "$t" "$(git rev-parse "$t")" "$(git rev-list -n1 "$t")" \
    "$(git for-each-ref "refs/tags/$t" --format='%(taggerdate:iso-strict)')" >> "$WORK/tags_before.txt"
done
sed 's/^/    /' "$WORK/tags_before.txt"
printf '    tag-roles trust_root pin: %s\n' \
  "$(grep -A2 'trust_root:' governance/tag-roles.yaml | awk '/object/{print $2}')"

say "3. the snapshots, before"
git rev-list --all | while read -r c; do
  git ls-tree -r --name-only "$c" -- concepts/snapshots 2>/dev/null
done | sort -u | sed 's/^/    /'

say "4. RUN THE REWRITE"
"$FR" --force --invert-paths \
  --path concepts/snapshots/credence-functor-seam \
  --path concepts/snapshots/derive-decide-split \
  --path concepts/snapshots/exactness-and-the-door \
  --path concepts/snapshots/frozen-oracle-protocol \
  --path concepts/snapshots/pkm-determinism \
  --path concepts/snapshots/pkm-event-identity \
  --path concepts/snapshots/provenance-ref-grammar 2>&1 | tail -5 | sed 's/^/    /'

say "5. did the bytes leave EVERY commit of EVERY ref?"
left=$(git rev-list --all | while read -r c; do
  git ls-tree -r --name-only "$c" -- concepts/snapshots 2>/dev/null; done | sort -u)
printf '%s\n' "$left" | sed 's/^/    surviving: /'
if printf '%s' "$left" | grep -qE 'pkm|proplang|life-agent|renavon'; then
  bad "sibling bytes still present in some commit"
else
  ok "no sibling snapshot bytes in any commit of any ref"
fi
# NOT a clean-run assertion: the concept RECORDS still cite these repositories by URL,
# document, section and commit, and BRIEF.md names them all. Excision removes the borrowed
# TEXT, never the citation. See the package README, "What excision does NOT remove".
printf '    citations that remain (by design): '
grep -ho 'https://github.com/[a-z-]*/[a-z-]*' concepts/*.yaml | sort -u | tr '\n' ' '; echo
printf '    commits after: %s\n' "$(git rev-list --all --count)"

say "6. the commit map"
MAP=.git/filter-repo/commit-map
printf '    lines: %s   well-formed pairs: %s   dropped-to-nothing: %s\n' \
  "$(wc -l < "$MAP")" \
  "$(grep -c '^[0-9a-f]\{40\} [0-9a-f]\{40\}$' "$MAP")" \
  "$(grep -c '^[0-9a-f]\{40\} 0\{40\}$' "$MAP")"

say "7. what the rewrite did to the eight signed tags"
while IFS=$'\t' read -r t obj cmt date; do
  if git rev-parse -q --verify "refs/tags/$t" >/dev/null; then
    same=$([ "$(git rev-parse "$t")" = "$obj" ] && echo SAME || echo CHANGED)
    git -c gpg.format=ssh -c gpg.ssh.allowedSignersFile=allowed_signers \
      verify-tag "$t" >/dev/null 2>&1 && sig=VERIFIES || sig=BROKEN
    printf '    %-18s object %-7s signature %s\n' "$t" "$same" "$sig"
  else
    printf '    %-18s GONE\n' "$t"
  fi
done < "$WORK/tags_before.txt"

say "8. re-create the four BUILDER tags at their original dates, and verify"
export GIT_CONFIG_GLOBAL=/dev/null
git config user.name t
git config user.email builder@tannen
git config gpg.format ssh
git config user.signingkey "$BUILDER_KEY"
for t in m0-laws-freeze m1-laws-freeze m2-laws-freeze m3-laws-freeze; do
  line=$(grep -P "^$t\t" "$WORK/tags_before.txt")
  oldcmt=$(printf '%s' "$line" | cut -f3); date=$(printf '%s' "$line" | cut -f4)
  new=$(awk -v o="$oldcmt" '$1==o{print $2}' "$MAP")
  msg=$(git for-each-ref "refs/tags/$t" --format='%(contents)' | sed '/BEGIN SSH SIGNATURE/,$d')
  git tag -d "$t" >/dev/null
  GIT_COMMITTER_DATE="$date" git tag -s -m "$msg" "$t" "$new" 2>&1 | sed 's/^/      /'
  if git -c gpg.format=ssh -c gpg.ssh.allowedSignersFile=allowed_signers \
       verify-tag "$t" >/dev/null 2>&1; then
    printf '    %-18s re-signed, verifies, date %s\n' \
      "$t" "$(git for-each-ref "refs/tags/$t" --format='%(taggerdate:iso-strict)')"
  else
    bad "$t re-signed but does NOT verify"
  fi
done

say "9. the rewrite attestation (no receipt is edited)"
ATT=receipts/REWRITE-rehearsal.md
{
  printf '# History rewrite — rehearsal\n\n- decision: D0176\n- map:\n'
  awk '$1 ~ /^[0-9a-f]{40}$/ && $2 ~ /^[0-9a-f]{40}$/ {print "  - " $1 " -> " $2}' "$MAP"
} > "$ATT"
printf '    %s map lines (the real one carries the COMPLETE map, not just receipt HEADs)\n' \
  "$(grep -c ' -> ' "$ATT")"

say "10. sign it, and (SIMULATION) map owner@tannen to the builder key"
ssh-keygen -Y sign -f "$BUILDER_KEY" -n tannen-rewrite "$ATT" 2>&1 | sed 's/^/    /'
BK=$(awk '/^builder@tannen/{print $2" "$3}' allowed_signers)
sed -i "s|^owner@tannen ssh-ed25519 .*|owner@tannen $BK|" allowed_signers
ok "owner@tannen now resolves to the builder key — receipt signatures below WILL fail"

say "11. the receipt chain: shipped guard vs patched guard"
cp "$REAL/scripts/_gov.py" scripts/_gov.py
printf '  -- shipped --\n'
"$REAL/.venv/bin/python" -I -P scripts/check_receipts.py 2>&1 | sed 's/^/    /'
patch -p1 -s < "$REAL/docs/proposals/2026-09-06-publication/patches/02-check-receipts-rewrite-map.patch"
printf '  -- patched --\n'
"$REAL/.venv/bin/python" -I -P scripts/check_receipts.py 2>&1 | sed 's/^/    /'

say "12. NEGATIVE CONTROL — attestation removed (must go red again)"
mv "$ATT" "$WORK/held.md"; mv "$ATT.sig" "$WORK/held.sig"
"$REAL/.venv/bin/python" -I -P scripts/check_receipts.py 2>&1 | head -4 | sed 's/^/    /'
mv "$WORK/held.md" "$ATT"; mv "$WORK/held.sig" "$ATT.sig"

say "13. NEGATIVE CONTROL — attestation unsigned (must go red)"
mv "$ATT.sig" "$WORK/held.sig"
"$REAL/.venv/bin/python" -I -P scripts/check_receipts.py 2>&1 | head -3 | sed 's/^/    /'
mv "$WORK/held.sig" "$ATT.sig"

say "14. NEGATIVE CONTROL — map tampered (must go red twice: signature AND lookup)"
cp "$ATT" "$WORK/held.md"
sed -i 's/-> [0-9a-f]\{40\}/-> 1111111111111111111111111111111111111111/' "$ATT"
"$REAL/.venv/bin/python" -I -P scripts/check_receipts.py 2>&1 | head -4 | sed 's/^/    /'
cp "$WORK/held.md" "$ATT"

say "DONE — nothing outside $WORK was written"
