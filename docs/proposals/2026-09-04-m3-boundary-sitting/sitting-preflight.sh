#!/usr/bin/env bash
# Preflight for the M3 boundary sitting. READ-ONLY: it changes nothing, signs nothing.
#
# Run it in ~/git/tannen (NOT a worktree) BEFORE you copy the driver in. Order matters:
# the precondition is the `make verify` you run BEFORE the cp, because the cp is custody
# drift on a custody-set member, and check_manifest is verify's FIRST recipe line — so
# every `make verify` after the cp stops in seconds without reaching the suite
# (D0151, D0206, D0208).
#
#   bash sitting-preflight.sh [--with-gate]
#
# --with-gate runs the full `make verify` (~33 min). Without it the gate is only reported,
# not run, and the preflight says so rather than implying a green it did not see.

set -uo pipefail

CLEARED_SHA=00c66cfe9af8e9fd1bb9867d30bc6a28f11985bace41d8b5c5a3a367692ca595
DRIVER_SRC=docs/proposals/2026-09-04-m3-boundary-sitting/boundary_sitting.sh
OWNER_KEY="${TANNEN_OWNER_KEY:-$HOME/.ssh/tannen_owner}"  # same default the driver uses (:58)
WITH_GATE=0
[ "${1:-}" = "--with-gate" ] && WITH_GATE=1

BAD=0 WARN=0
ok()   { printf '  \033[32mok\033[0m    %s\n' "$1"; }
bad()  { printf '  \033[31mNO\033[0m    %s\n' "$1"; BAD=$((BAD+1)); }
warn() { printf '  \033[33mwarn\033[0m  %s\n' "$1"; WARN=$((WARN+1)); }
head_() { printf '\n\033[1m%s\033[0m\n' "$1"; }

head_ "Where you are"
root=$(git rev-parse --show-toplevel 2>/dev/null) || { echo "not a git repo"; exit 2; }
if [ -f "$root/.git" ]; then
    bad "this is a WORKTREE ($root). The sitting runs in the real checkout — the close tag
        and the receipt are signed against that tree. cd ~/git/tannen first."
else
    ok "real checkout: $root"
fi
branch=$(git rev-parse --abbrev-ref HEAD)
[ "$branch" = master ] && ok "on master" || warn "on '$branch', not master"

head_ "The tree"
if [ -z "$(git status --porcelain)" ]; then
    ok "clean — nothing half-applied, and step 0 will not read this as a RESUMED sitting"
else
    bad "DIRTY. Step 0 treats a dirty tree as a resumed sitting and SKIPS its gate:"
    git status --short | sed 's/^/        /'
fi

head_ "The driver you are about to install"
if [ ! -f "$DRIVER_SRC" ]; then
    bad "$DRIVER_SRC not found"
else
    have=$(sha256sum "$DRIVER_SRC" | cut -d' ' -f1)
    if [ "$have" = "$CLEARED_SHA" ]; then
        ok "sha256 matches the bytes the 2026-09-10 clearance run cleared"
    else
        bad "sha256 ${have:0:12}… is NOT the cleared ${CLEARED_SHA:0:12}…
        Only a green run clears the driver, and it clears the bytes it ran (D0068).
        Re-rehearse before the sitting, or install the cleared bytes."
    fi
fi

head_ "Your key (D0185 — without this you type the passphrase ~10 times)"
if [ ! -f "$OWNER_KEY" ]; then
    warn "no key at $OWNER_KEY — set OWNER_KEY if it lives elsewhere"
elif ssh-add -l 2>/dev/null | grep -qF "$(ssh-keygen -lf "$OWNER_KEY" 2>/dev/null | awk '{print $2}')"; then
    ok "owner key is in ssh-agent — signing will be silent"
else
    warn "owner key NOT in ssh-agent. Run:  ssh-add $OWNER_KEY
        Step 0 offers to do this for you; doing it first is calmer."
fi

head_ "The floor"
if custodian_out=$(bash scripts/custodian.sh --check-only 2>&1); then
    ok "custodian --check-only green (run --check-only always: D0177)"
else
    bad "custodian --check-only RED — fix before signing anything:"
    printf '%s\n' "$custodian_out" | tail -5 | sed 's/^/        /'
fi

head_ "The remote (advisory — nothing enforces this yet)"
if git ls-remote --exit-code origin >/dev/null 2>&1; then
    local_head=$(git rev-parse HEAD)
    remote_head=$(git ls-remote origin master 2>/dev/null | awk '{print $1}')
    if [ "$local_head" = "$remote_head" ]; then
        ok "origin/master already holds this HEAD — the pre-sitting state is witnessed"
    else
        warn "origin/master is at ${remote_head:0:9}, local HEAD is ${local_head:0:9}.
        FLOOR-AUDIT §3(a) makes one attack family conditional on a remote that has NOT
        received the prior state. Pushing HEAD before you start closes that, and costs
        nothing. Nothing in the driver or docs/SITTING.md requires it — that gap is
        queued, not landed."
    fi
else
    warn "origin unreachable — skipped"
fi

head_ "The precondition gate"
if [ "$WITH_GATE" = 1 ]; then
    echo "  running make verify — this is the one that counts, and it must be BEFORE the cp"
    if make verify; then ok "make verify GREEN"; else bad "make verify RED — sign nothing"; fi
else
    warn "NOT RUN. Re-run with --with-gate, or run 'make verify' yourself, BEFORE the cp.
        This preflight has not seen a green gate and does not imply one."
fi

printf '\n'
if [ "$BAD" -gt 0 ]; then
    printf '\033[31mNO-GO — %d blocking, %d advisory\033[0m\n' "$BAD" "$WARN"; exit 1
fi
printf '\033[32mGO — 0 blocking, %d advisory\033[0m\n' "$WARN"
cat <<'NEXT'

Then, in this order:
  1. cp docs/proposals/2026-09-04-m3-boundary-sitting/boundary_sitting.sh scripts/
  2. bash scripts/boundary_sitting.sh m3
Step 0 will report check_manifest FAIL on that cp. That is correct and expected: it is
drift on a custody-set member, step 7 re-signs it, and the gate you ran above — before
the cp — is the precondition. The one after it cannot be.
NEXT
