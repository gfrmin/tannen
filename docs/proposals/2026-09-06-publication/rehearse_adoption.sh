#!/usr/bin/env bash
# rehearse_adoption.sh — run adopt_published_history.sh against a disposable copy of the
# local repository and a real rewritten history, and judge what it leaves behind.
#
# WHY. Adoption moves every branch in the repository the owner actually works in, resets four
# worktrees, and replaces eight signed tags. It is the one step of this whole package that
# writes to ~/git/tannen rather than to a clone, so it is the step least forgiving of being
# reasoned about instead of run. D0186 is the standing argument: a fix that looked obviously
# right would have deleted a milestone branch from the live repository, and it passed a green
# rehearsal because the fixture could not reach the path that mattered.
#
# THE FIXTURE IS THE POINT. A bare clone of ~/git/tannen with four worktrees on m0..m3 — the
# same shape as the real thing, including the trap that `git branch -f` refuses a branch
# checked out in a worktree. The published side is produced by actually running the
# publication rehearsal, so the commit map is a real map written by the real driver and
# signed, not a fixture the harness wrote to agree with itself.
#
# NOTHING HERE TOUCHES THE REAL REPO: it is read with `git clone` and nothing else.
set -euo pipefail
ROOT="${TANNEN_REHEARSE_ROOT:-$(cd "$(dirname "$0")/../../.." && pwd)}"
BARE_SRC="${TANNEN_BARE:-$(cd "$ROOT" && git rev-parse --git-common-dir)}"
BARE_SRC="$(cd "$BARE_SRC" && pwd)"
PKG="docs/proposals/2026-09-06-publication"
KEEP=0
[ "${1:-}" = "--keep" ] && KEEP=1

say()  { printf '\n\033[1m-- %s\033[0m\n' "$*"; }
note() { printf '   %s\n' "$*"; }
T0=$SECONDS
W=$(mktemp -d "${TMPDIR:-/var/tmp}/tannen-adoptrehearsal-XXXXXX")
cleanup() { [ "$KEEP" = 1 ] || rm -rf "$W"; }
trap cleanup EXIT

ROOT_HEAD_BEFORE=$(git -C "$ROOT" rev-parse HEAD)

say "A published history, produced by actually running the sitting"
PUB="$W/pub"
TANNEN_SITTING_FAST=1 TMPDIR="$W" bash "$ROOT/$PKG/rehearse_publication.sh" --keep > "$W/pub.log" 2>&1 \
    || { echo "the publication rehearsal failed; adoption cannot be rehearsed on top of it" >&2
         tail -20 "$W/pub.log" >&2; exit 1; }
# A GREEN publication run leaves the rewrite at $WORK/rw; an ABORT run moves it aside to
# rw-before-recovery (the recovery is a deletion, and --keep must not destroy what it exists
# to let you inspect). Accept either, and say which was found.
RW=$(find "$W" -maxdepth 3 -type d \( -name 'rw' -o -name 'rw-before-recovery' \) | head -1)
[ -n "$RW" ] && [ -d "$RW/.git" ] \
    || { echo "no rewritten clone kept by the publication rehearsal (looked for rw and rw-before-recovery under $W)" >&2
         find "$W" -maxdepth 3 -type d | sed 's/^/     /' | head -20 >&2; exit 1; }
note "published history at $RW ($(git -C "$RW" rev-list --all --count) commits, branch: $(git -C "$RW" rev-parse --abbrev-ref HEAD))"

say "A disposable copy of the local repository, with its four worktrees"
BARE="$W/bare"
git clone --bare --quiet --no-hardlinks "$BARE_SRC" "$BARE"
declare -A OLDTIP
for b in $(git -C "$BARE" for-each-ref --format='%(refname:strip=2)' refs/heads); do
    OLDTIP["$b"]=$(git -C "$BARE" rev-parse "$b")
done
for b in "${!OLDTIP[@]}"; do
    [ "$b" = master ] && continue
    git -C "$BARE" worktree add --quiet "$W/wt/$b" "$b" 2>/dev/null || note "could not add worktree for $b"
done
note "branches: ${!OLDTIP[*]}"
note "worktrees: $(git -C "$BARE" worktree list --porcelain | grep -c '^worktree ')"
VWT="$W/wt/m3"
if [ -d "$VWT" ]; then
    say "Syncing a venv in one worktree so the post-adoption guards actually run"
    ( cd "$VWT" && uv sync --frozen --quiet ) || note "uv sync failed; the guards will be skipped"
fi

say "Adopting"
set +e
ADOPT="${TANNEN_ADOPT_DRIVER:-$ROOT/$PKG/adopt_published_history.sh}"
[ "$ADOPT" = "$ROOT/$PKG/adopt_published_history.sh" ] || note "adopt driver OVERRIDDEN: $ADOPT"
bash "$ADOPT" --from "$RW" --ci-green --repo "$BARE" > "$W/adopt.log" 2>&1
ADOPT_RC=$?
set -e
sed 's/\x1b\[[0-9;]*m//g' "$W/adopt.log" | tail -40
note "adopt exited $ADOPT_RC"

say "Verdict"
FAILED=0
check() { local d="$1"; shift
    if "$@" >/dev/null 2>&1; then printf '   \033[32mok\033[0m   %s\n' "$d"
    else printf '   \033[31mFAIL\033[0m %s\n' "$d"; FAILED=$((FAILED + 1)); fi; }
equal() { [ "$1" = "$2" ]; }
in_bare() { git -C "$BARE" "$@"; }

BK=$(in_bare for-each-ref --format='%(refname)' refs/backup | head -1); BK="${BK%/*/*}"
check "adoption succeeded (exit 0)"                       test "$ADOPT_RC" -eq 0
check "a backup namespace was created"                    test -n "$BK"
for b in "${!OLDTIP[@]}"; do
    check "branch $b moved off its pre-publication tip" \
        bash -c "[ \"\$(git -C '$BARE' rev-parse $b)\" != '${OLDTIP[$b]}' ]"
    check "branch $b's new tip is in the published history" \
        bash -c "git -C '$RW' cat-file -e \$(git -C '$BARE' rev-parse $b)^{commit}"
    check "branch $b's OLD tip is still reachable under the backup" \
        bash -c "[ \"\$(git -C '$BARE' rev-parse $BK/heads/$b 2>/dev/null)\" = '${OLDTIP[$b]}' ]"
done
for w in "$W"/wt/*; do
    [ -d "$w" ] || continue
    check "worktree $(basename "$w") is clean after the reset" \
        bash -c "[ -z \"\$(git -C '$w' status --porcelain)\" ]"
    check "worktree $(basename "$w") sits on its branch's new tip" \
        bash -c "[ \"\$(git -C '$w' rev-parse HEAD)\" = \"\$(git -C '$w' rev-parse \$(git -C '$w' rev-parse --abbrev-ref HEAD))\" ]"
done
for t in $(git -C "$RW" tag); do
    check "tag $t is the published object" \
        bash -c "[ \"\$(git -C '$BARE' rev-parse $t)\" = \"\$(git -C '$RW' rev-parse $t)\" ]"
done
check "master is EXACTLY the published head, not a remap of its old tip" \
    bash -c "[ \"\$(git -C '$BARE' rev-parse master)\" = \"\$(git -C '$RW' rev-parse HEAD)\" ]"
check "the rewrite attestation is present in the adopted master's tree" \
    bash -c "git -C '$BARE' ls-tree --name-only master receipts/ | grep -q REWRITE-"
check "no incoming namespace was left behind" \
    bash -c "[ -z \"\$(git -C '$BARE' for-each-ref refs/publication-incoming)\" ]"
if [ -d "$VWT/.venv" ]; then
    check "check_receipts is green on the adopted repository"   bash -c "cd '$VWT' && .venv/bin/python -I -P scripts/check_receipts.py"
    check "check_tag_signers is green on the adopted repository" bash -c "cd '$VWT' && .venv/bin/python -I -P scripts/check_tag_signers.py"
    check "the custodian is green on the adopted repository"     bash -c "cd '$VWT' && bash scripts/custodian.sh --check-only"
fi
check "the real repository's HEAD is untouched" equal "$ROOT_HEAD_BEFORE" "$(git -C "$ROOT" rev-parse HEAD)"

note "total $(( (SECONDS - T0) / 60 )) min"
[ "$KEEP" = 1 ] && note "kept: $W" || note "(--keep to inspect)"
if [ "$FAILED" -eq 0 ]; then
    printf '\n\033[32madoption rehearsal: the local repository takes the published history and stays green\033[0m\n'
    exit 0
fi
printf '\n\033[31madoption rehearsal: %d check(s) failed\033[0m\n' "$FAILED"
exit 1
