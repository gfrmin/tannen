#!/usr/bin/env bash
# preflight.sh — everything that can be checked BEFORE the sitting, in about ten seconds.
#
# It deliberately does NOT re-implement the driver's own checks. The custody floor, the key
# passphrase paths, the patch applicability and the step order are the driver's to report, so
# this runs `publication_sitting.sh --dry-run` and passes its verdict through (BRIEF §2:
# one implementation, not two — the same reason patch 07 makes the custodian delegate).
# What it adds is everything OUTSIDE the repository, which the driver cannot see: the tools
# the rewrite needs, GitHub, disk, and whether the destination already exists.
set -uo pipefail
cd "$(dirname "$0")/../../.." || exit 1
PKG="docs/proposals/2026-09-06-publication"
SLUG="${TANNEN_PUBLISH_SLUG:-gfrmin/tannen}"

say()  { printf '\n\033[1m== %s\033[0m\n' "$*"; }
ok()   { printf '   \033[32mok\033[0m   %s\n' "$*"; }
bad()  { printf '   \033[31mNO\033[0m   %s\n' "$*"; FAILED=$((FAILED + 1)); }
warn() { printf '   \033[33m!\033[0m    %s\n' "$*"; }
FAILED=0

say "Tools the sitting needs and cannot install"
command -v git-filter-repo >/dev/null && ok "git-filter-repo ($(git-filter-repo --version 2>&1 | head -1))" \
    || bad "git-filter-repo is NOT installed — step 5 cannot run"
command -v uv >/dev/null && ok "uv ($(uv --version 2>&1))" || bad "uv is not installed"
command -v gh >/dev/null && ok "gh" || bad "gh is not installed — you cannot create the repository"
command -v ssh-keygen >/dev/null && ok "ssh-keygen" || bad "ssh-keygen missing"

say "Room to work"
AVAIL=$(df -Pk "${TMPDIR:-/var/tmp}" | awk 'NR==2 {print int($4/1048576)}')
[ "$AVAIL" -ge 5 ] && ok "${AVAIL}G free in ${TMPDIR:-/var/tmp} (a clone, two venvs and a rewrite)" \
    || bad "only ${AVAIL}G free in ${TMPDIR:-/var/tmp}"

say "GitHub"
if gh auth status >/dev/null 2>&1; then
    ok "authenticated as $(gh api user --jq .login 2>/dev/null || echo '?')"
    SC=$(gh auth status 2>&1 | grep -o "Token scopes:.*" | head -1)
    case "$SC" in *"'repo'"*) ok "$SC" ;; *) warn "$SC — 'repo' is needed to create the repository" ;; esac
else
    bad "gh is not authenticated — run: gh auth login"
fi
if gh repo view "$SLUG" --json name >/dev/null 2>&1; then
    bad "$SLUG ALREADY EXISTS — the sitting's final step would collide with it"
else
    ok "$SLUG does not exist yet"
fi

say "The repository itself"
[ -z "$(git status --porcelain)" ] && ok "working tree is clean (a sitting starts from a committed repo)" \
    || { bad "working tree is NOT clean; whatever is here rides into commit A:"
         git status --porcelain | sed 's/^/          /' | head -10; }
[ -f .git ] || [ -d .git ] && ok "on branch $(git rev-parse --abbrev-ref HEAD)"
if [ -n "$(git log --branches --not master 2>/dev/null)" ]; then
    warn "some branch is ahead of master; the sitting publishes master's history"
else
    ok "nothing is ahead of master"
fi

say "The driver's own verdict (delegated, not duplicated)"
OUT=$(bash "$PKG/publication_sitting.sh" --dry-run 2>&1); RC=$?
printf '%s\n' "$OUT" | sed -n '/Keys —/,/^$/p' | sed 's/^/   /'
if [ "$RC" -eq 0 ]; then ok "publication_sitting.sh --dry-run exits 0"
else bad "publication_sitting.sh --dry-run exits $RC — read it before going further"; fi
printf '%s\n' "$OUT" | grep -q 'passphrase-protected and NOT in ssh-agent' \
    && warn "the owner key is not in this shell's agent: ssh-add it HERE, then re-run me"

say "Verdict"
if [ "$FAILED" -eq 0 ]; then
    printf '\n\033[32mpreflight: clear\033[0m — the sitting can start from this terminal\n'
    exit 0
fi
printf '\n\033[31mpreflight: %d blocker(s)\033[0m — fix them before the sitting\n' "$FAILED"
exit 1
