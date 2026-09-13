#!/usr/bin/env bash
# Preflight for the M4 boundary sitting. READ-ONLY: it changes nothing, signs nothing, and
# starts no agent.
#
# Run it in ~/git/tannen (NOT a worktree) BEFORE you copy the driver in. The precondition is
# the `make verify` you run BEFORE the cp: the cp is custody drift on a custody-set member and
# check_manifest is verify's FIRST recipe line, so every `make verify` after the cp stops in
# seconds without reaching the suite (D0151, D0206, D0208).
#
#   bash sitting-preflight.sh [--with-gate]
#
# --with-gate runs the full `make verify` (~33 min). Without it the gate is only reported,
# not run, and the preflight says so rather than implying a green it did not see.

set -uo pipefail

HERE=docs/proposals/2026-09-11-m4-boundary-sitting
DRIVER_SRC="$HERE/boundary_sitting.sh"
# THE CLEARED BYTES LIVE IN ONE FILE, read by this preflight and by gen_agenda.py alike. It is
# written only by the session that runs a full, non-FAST rehearsal green, and it names the sha256
# that run cleared (D0068; M3 README: "only a green run clears the driver, and it clears the bytes
# it ran"). Absent means NOT CLEARED, and that is a blocking NO — not a warning.
CLEARED_FILE="$HERE/CLEARED.sha256"
OWNER_KEY="${TANNEN_OWNER_KEY:-$HOME/.ssh/tannen_owner}"  # the driver's own default
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
[ "$branch" = master ] && ok "on master" || warn "on '$branch', not master (m4 merges into master before the sitting)"

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
    cleared=$([ -f "$CLEARED_FILE" ] && awk '$2 == "boundary_sitting.sh" { print $1 }' "$CLEARED_FILE")
    if [ -z "$cleared" ]; then
        bad "NOT CLEARED: $CLEARED_FILE names no cleared bytes. These drafts have had FAST
        rehearsals only, which skip both make verify legs and check_decisions entirely.
        A full --from head rehearsal must go green first (D0068)."
    elif [ "$have" = "$cleared" ]; then
        ok "sha256 matches the bytes the clearance run cleared (${cleared:0:12}…)"
    else
        bad "sha256 ${have:0:12}… is NOT the cleared ${cleared:0:12}…
        Only a green run clears the driver, and it clears the bytes it ran. Re-rehearse."
    fi
fi

head_ "Your key — three states, two remedies"
# ssh-add -l: exit 0 an agent holds identities; 1 an agent runs and holds none; 2 no agent.
# The M3 preflight and driver treated every non-0 the same, and at the M3 sitting no agent ran
# by default: the offered ssh-add failed silently and every signature prompted.
if [ ! -f "$OWNER_KEY" ]; then
    warn "no key at $OWNER_KEY — set TANNEN_OWNER_KEY if it lives elsewhere"
else
    fp=$(ssh-keygen -lf "$OWNER_KEY" 2>/dev/null | awk '{print $2}')
    listed=$(ssh-add -l 2>/dev/null); agent_rc=$?
    if [ "$agent_rc" -eq 2 ]; then
        warn "NO ssh-agent is running (ssh-add -l exit 2), so ssh-add alone cannot help. Run:
        eval \"\$(ssh-agent -s)\" && ssh-add $OWNER_KEY
        in the shell you will run the driver from. Step 0 also offers to start one, stopped on exit."
    elif [ -n "$fp" ] && printf '%s\n' "$listed" | grep -qF "$fp"; then
        ok "owner key is in ssh-agent — signing will be silent"
    else
        warn "an agent is running but does not hold the owner key (ssh-add -l exit $agent_rc). Run:
        ssh-add $OWNER_KEY"
    fi
fi

head_ "The floor"
if custodian_out=$(bash scripts/custodian.sh --check-only 2>&1); then
    ok "custodian --check-only green (run --check-only always: D0177)"
else
    bad "custodian --check-only RED — fix before signing anything:"
    printf '%s\n' "$custodian_out" | tail -5 | sed 's/^/        /'
fi

head_ "The findings ledger (RT-M4-07 — step 10 refuses the close tag without it)"
if [ -f docs/redteam/LEDGER.yaml ]; then
    ok "docs/redteam/LEDGER.yaml present — the driver checks coverage at steps 8c and 10"
else
    bad "docs/redteam/LEDGER.yaml is absent, so step 10 cannot close this sitting"
fi

head_ "The remote (advisory — nothing enforces this, D0210)"
if git ls-remote --exit-code origin >/dev/null 2>&1; then
    local_head=$(git rev-parse HEAD)
    remote_head=$(git ls-remote origin master 2>/dev/null | awk '{print $1}')
    if [ "$local_head" = "$remote_head" ]; then
        ok "origin/master already holds this HEAD — the pre-sitting state is witnessed"
    else
        warn "origin/master is at ${remote_head:0:9}, local HEAD is ${local_head:0:9}.
        Pushing HEAD before you start closes FLOOR-AUDIT §3(a) and costs nothing (D0210)."
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
cat <<NEXT

Then, in this order:
  1. cp $DRIVER_SRC scripts/
  2. bash scripts/boundary_sitting.sh m4
Step 0 will report check_manifest FAIL on that cp. That is correct and expected: it is drift
on a custody-set member, step 7 re-signs it, and the gate you ran above — before the cp — is
the precondition. The one after it cannot be.
NEXT
