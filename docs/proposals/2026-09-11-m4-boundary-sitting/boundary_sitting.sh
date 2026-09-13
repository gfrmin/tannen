#!/usr/bin/env bash
# scripts/boundary_sitting.sh — interactive driver for a MILESTONE BOUNDARY sitting
# (docs/SITTING.md; the M0→M1 queue was D0060, M1→M2 D0105, M2→M3 D0131 + D0138, M3→M4
# D0154, and this M4→M5 queue is ROADMAP.md §3 — every record blocked-on-owner, AT ANY TIER).
# OWNER-RUN, owner key present.
#
# THIS COPY is docs/proposals/2026-09-11-m4-boundary-sitting/boundary_sitting.sh, drafted for
# the M4 boundary. The original scripts/boundary_sitting.sh is never edited in place outside a
# sitting: the owner copies THIS FILE over it before running it (docs/SITTING.md), and that cp
# is expected custody drift, tolerated in unexpected_failures() below by name until step 7.
#
# WHAT THIS COPY CHANGES versus the committed M3 driver is tabulated in this directory's
# README.md. The shape, in one screen:
#
#   - RT-M4-02 IS TAKEN FIRST (D0246 A2). It is the only live high finding, its threat model
#     is the builder, and the repository is published: `make verify` green does not today mean
#     "no IO". Step 1 installs the derived doorway guard and its contract.
#   - EVERY M0-M3 RE-APPLICATION STEP IS GONE (M3's 2, 3, 3b, 4-4l, 5b, 8b). Each detector was
#     evaluated against the tree on 2026-09-13 and every one but one was an already-applied
#     skip. The one that was not is the argument for deleting them: M3 step 4b still compared
#     .github/workflows/ci.yml against the M0 proposal copy, which step 4f of the SAME driver had
#     since made stale — so the M3 driver, re-run today, would offer to install the M0-era
#     ci.yml over the corrected file. A step that re-offers finished work is not a guard (the
#     guards stay in the floor); it is a pointer into an older proposals directory, and D0152
#     item 6 is what a stale one of those costs. This copy reads ONE proposals directory.
#   - EVERY OWNER EDIT IS A DRAFTED `git apply` PATCH, applied, shown, watched where it is a
#     guard, and kept or reverted as ONE unit (offer_patch / keep_or_revert). M3 carried its
#     edits as anchored python heredocs; each re-implemented the three states "already applied /
#     applies / neither" by hand, and step 4f's got it wrong once (D0152 item 2). `git apply
#     --check` and `git apply -R --check` are those three states, computed.
#   - THE QUEUE IS SELECTED BY STATUS, AT ANY TIER (D0217 item 3). Tier C is accepted by flip and
#     signature; a Tier-A record needs the key only for its artifact, so it is accepted by flip.
#   - A QUEUE RECORD'S BINDINGS ARE UPGRADED BEFORE IT IS SIGNED (D0214's recommendation), each
#     upgrade gated on its artifact having actually landed in this run's tree.
#   - THE RECEIPT IS TAKEN BEHIND THE COMMIT CONFIRM (D0201 ruling 4): decline the commit and no
#     signed receipt attests to a sitting that did not happen.
#   - STEP 11 IS DELETED when D0205 (required_tags derived) and D0215 (no clock verdict in
#     DECISIONS.md) both land, and survives only as the fallback for a declined D0215.
#   - THE CLOSE TAG QUOTES THE FINDINGS LEDGER (RT-M4-07, D0249): the tag cannot be minted while
#     any standing finding is undispositioned, and its message carries the ledger's hash.
#   - AN SSH-AGENT IS STARTED WHEN NONE RUNS. Measured at the M3 sitting: no agent by default,
#     the bare `ssh-add` failed, the failure was accepted silently, and every signature prompted.
#
# Builder-drafted, and it signs nothing by itself: every signature is your key answering your
# passphrase, and every edit to author-key territory is shown before it is kept. Read this file
# end to end before running it — it drives your key. Its own bytes are in the custody set.
#
# Safe to re-run: every step detects work already done and skips it.
#
# ORDER IS LOAD-BEARING. Guards before the fixtures that poison them, fixtures before the
# custodian that names them, the custodian before the custody signature, and the close tag last.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1   # RT-M2-06 D5: no set -e here, so an unguarded cd would sign the wrong tree

MILESTONE="${1:-m4}"
# Derived, not hardcoded (D0122 item 5): the closing note names the NEXT milestone's Session A.
NEXT_MILESTONE="m$(( ${MILESTONE#m} + 1 ))"
OWNER_KEY="${TANNEN_OWNER_KEY:-$HOME/.ssh/tannen_owner}"
# ONE proposals directory. The M3 copy carried four (PROPOSALS, _M1, _M2, _M3) because its
# re-application steps compared against the sittings that drafted them; those steps are gone,
# and with them the variable that must be re-pointed every milestone and is read once (D0152
# item 6). The next milestone's copy re-points this one line.
PROPOSALS_M4="docs/proposals/2026-09-11-m4-boundary-sitting"
CANDIDATES="docs/redteam/fixture-candidates"
KEYREF="$OWNER_KEY"          # what ssh-keygen -Y sign is pointed at (key file, or .pub
                             # when the private half is loaded into an agent)
# The venv interpreter at a literal path, in isolated mode — the Makefile's spelling, for the
# same reason (RT-02, conferral ruling 3, D0063).
PY="$PWD/.venv/bin/python"
# REHEARSAL KNOBS (D0183, D0184). None of these is ever a sitting outcome.
#   TANNEN_SITTING_FAST=1            skip the long gates and the commit hooks, and say so.
#   TANNEN_SITTING_STOP_AFTER=<step> stop, exit 3, after that step completes.
#   TANNEN_SITTING_SCRATCH=<dir>     where the breadcrumbs below are written.
FAST="${TANNEN_SITTING_FAST:-0}"
# Everything this driver writes for its own use lives HERE, never inside the repository: an
# untracked file under the root is swept into the sitting commit by step 9 (D0153 artifact 3).
SCRATCH="${TANNEN_SITTING_SCRATCH:-$(mktemp -d "${TMPDIR:-/var/tmp}/tannen-sitting.XXXXXX")}"
mkdir -p "$SCRATCH"
# THE BREADCRUMBS. `steps`: one line per step header, so an abort can say how far it got and
# the rehearsal harness never parses this driver's prose (BRIEF §2, D0184). `prompts`:
# "<index> <step>" per prompt, so --abort-at N is chosen from a measurement (M3 README).
STEPS="$SCRATCH/steps"; : > "$STEPS"
PROMPTS="$SCRATCH/prompts"; : > "$PROMPTS"
PROMPT_N=0
CURRENT_STEP="(before step 0)"
# Load-bearing counts and ETAs are derived at the moment they are printed or not stated (owner
# ruling (3) of 2026-09-10, D0209). The wall clock is a dated measurement, never a prediction.
verify_eta() {
    local n
    n=$(uv run pytest --collect-only -q 2>/dev/null | awk '/tests? collected/ { print $1; exit }')
    printf '%s tests; last measured end to end at 33m31s on a clean tree (builder machine, 2026-09-09)' \
        "${n:-an unknown number of}"
}

say()  { printf '\n\033[1m== %s\033[0m\n' "$*"
         printf '%s\n' "$*" >> "$STEPS"
         case "$*" in "Step "*) CURRENT_STEP=$(printf '%s' "$*" | awk '{print $2}') ;; esac
         return 0; }
note_prompt() { PROMPT_N=$((PROMPT_N + 1)); printf '%d %s\n' "$PROMPT_N" "$CURRENT_STEP" >> "$PROMPTS"; }
note() { printf '   %s\n' "$*"; }
# A step about to be quiet for more than a moment says so FIRST, with this helper, so the
# rehearsal harness can hold the rule mechanically (D0069).
waiting() { printf '   [waiting] %s\n' "$*"; }
die()  { printf '\nsitting: STOP — %s\n' "$*" >&2
         # The two regimes differ either side of step 9's commit, and a minted close tag lives
         # outside the tree entirely (D0210): ask the refs and the tree, never infer from the step.
         if [ -s "$STEPS" ]; then
             printf 'reached: step %s   (every step this run announced: %s)\n' \
                 "$(awk '/^Step /{l=$2} END{print l}' "$STEPS")" "$STEPS" >&2
             tree_is_the_whole_story=1
             if git rev-parse -q --verify "refs/tags/$MILESTONE-close" >/dev/null 2>&1; then
                 tree_is_the_whole_story=0
                 printf '%s-close IS MINTED and owner-signed. That act is done, re-running does not undo\nit, and this run stopped AFTER the milestone was closed. Read what failed before\ndoing anything else; do not treat this as a place to resume from.\n' "$MILESTONE" >&2
             fi
             if [ -z "$(git status --porcelain 2>/dev/null)" ]; then
                 if [ "$tree_is_the_whole_story" = 1 ]; then
                     printf 'The tree is CLEAN: this sitting'"'"'s work is committed and nothing is half-applied.\nThis is a coherent place to stop; re-run to resume.\n' >&2
                 else
                     printf 'The tree is CLEAN, so there is nothing uncommitted to undo — but the tag above is\nnot in the tree, and it is what this run left behind.\n' >&2
                 fi
             else
                 printf 'The tree is DIRTY: edits are in the WORKING TREE, uncommitted, and the custody floor\nstays RED until step 7 signs it. Re-run to resume, or undo with:\n    git checkout -- . && git clean -fd\n' >&2
             fi
         fi
         exit 1; }
stop_after() { [ "${TANNEN_SITTING_STOP_AFTER:-}" = "$1" ] || return 0
               printf '\n   [rehearsal] stopping after step %s (TANNEN_SITTING_STOP_AFTER)\n' "$1" >&2
               exit 3; }
confirm() { local a; note_prompt; read -rp "$1 [y/N] " a; [[ "${a:-}" == [yY]* ]]; }
pause() { note_prompt; read -rp "   $1" _; }
# EDITOR and PAGER hold command LINES, not command names (2026-08-25): eval, as git does.
edit() { eval "${EDITOR:-nano}" '"$@"'; }
page() { eval "${PAGER:-less}" '"$@"'; }

sign_owner() {   # <file> <namespace>   -> writes <file>.sig
    # A pre-existing <file>.sig makes ssh-keygen ask "Overwrite (y/n)?" and exit 0 WITHOUT
    # WRITING on any other answer (the real M1 sitting, 2026-08-30). Every call site reaches
    # here only when the existing signature is already invalid, so remove it first.
    rm -f -- "$1.sig"
    ssh-keygen -Y sign -f "$KEYREF" -n "$2" "$1" >/dev/null \
        || die "signature failed for $1 (namespace $2)"
    note "signed: $1.sig (namespace $2)"
}
verify_owner() { # <file> <namespace>   -> 0 if a valid owner signature is already there
    [ -f "$1.sig" ] && ssh-keygen -Y verify -f allowed_signers -I owner@tannen \
        -n "$2" -s "$1.sig" <"$1" >/dev/null 2>&1
}
# Accept-and-sign is ONE act that rolls back (D0064): a Tier-C record that says accepted with
# no signature beside it is a red gate, so a declined or mistyped passphrase must restore it.
# Unlike sign_owner this does not die: a failed signature leaves the record queued, which is a
# legal state and an answer, not a stop.
sign_owner_rollback() {  # <record>  -> 0 accepted and signed, 1 rolled back to blocked-on-owner
    sed -i 's/^status: blocked-on-owner$/status: accepted/' "$1"
    rm -f -- "$1.sig"
    if ssh-keygen -Y sign -f "$KEYREF" -n tannen-decision "$1" >/dev/null; then
        note "accepted and signed: $1.sig (namespace tannen-decision)"
        return 0
    fi
    sed -i 's/^status: accepted$/status: blocked-on-owner/' "$1"
    note "signature failed — left blocked-on-owner; nothing else changed"
    return 1
}
# Array first, never `while read … < <(ls)`: a confirm() in the body would read its answer from
# the next FILENAME (the M0 sitting, D0067).
sign_tier_c_records() {
    local signed=0 rec id tier status recs=()
    mapfile -t recs < <(ls -1 decisions/*.yaml | sort)
    for rec in "${recs[@]}"; do
        tier=$(sed -n 's/^tier: *//p' "$rec" | head -1)
        status=$(sed -n 's/^status: *//p' "$rec" | head -1)
        id=$(sed -n 's/^id: *//p' "$rec" | head -1)
        [ "$tier" = "C" ] || continue
        case "$status" in accepted) ;; *) continue ;; esac
        verify_owner "$rec" tannen-decision && continue
        printf '\n'
        page "$rec"
        note "-- $id ($rec): Tier C, status accepted, no owner signature"
        if confirm "Sign $id? (BRIEF §9.2: Tier C is affirmative signature only, never silence)"; then
            sign_owner "$rec" tannen-decision
            signed=$((signed + 1))
        else
            note "left unsigned — the Tier-C guard will report it until it is signed or"
            note "its status is changed to rejected/blocked-on-owner"
        fi
    done
    note "$signed record(s) signed this pass"
}
# The tolerated failures before step 7, by name and nothing wider. See the M3 copy's comment
# for the two output shapes this reads (custodian's one-line FAIL, check_manifest's count line
# plus indented detail) — unchanged here. ONE path's drift is tolerated by name: this driver's
# own, which the owner's cp creates before anything has run.
unexpected_failures() {   # <captured output> -> prints the failures step 7 will not fix
    local tolerated='custody set hashes do not verify|custody\.sha256\.sig absent|custody\.sha256\.sig does not verify|custody floor violated|custody drift: scripts/boundary_sitting\.sh'
    printf '%s\n' "$1" | grep -E ': FAIL|^  - ' \
        | grep -Ev "$tolerated" \
        | grep -Ev '^[a-z_]+: FAIL \([0-9]+ violation\(s\)\)$'
}

regen_manifest_row() {   # author-key territory: caller confirms before calling
    grep -v "  $1\$" MANIFEST.sha256 > MANIFEST.tmp \
        && sha256sum "$1" >> MANIFEST.tmp && mv MANIFEST.tmp MANIFEST.sha256
}
manifest_row_current() {  # <path> -> true when MANIFEST.sha256's row matches the bytes
    local want
    want=$(sha256sum "$1") || return 1
    grep -qxF "$want" MANIFEST.sha256
}
driver_custody_current() {  # true when THIS driver's bytes match the row custody.sha256 was signed over
    local want
    want=$(sha256sum scripts/boundary_sitting.sh) || return 1
    grep -qxF "$want" governance/custody.sha256
}
readme_row_absent() {     # <fixture> -> true when README.md carries no TABLE ROW for it
    # THE ANCHOR IS THE LEADING PIPE (D0131 item 1): prose naming a fixture never starts a line
    # with "| `name/` |", so an explanation of why a row is missing cannot satisfy this.
    ! grep -q "^| \`$1/\` |" tests/poison/README.md
}
add_manifest_rows() {    # every file under a directory (sealed dirs carry a row each)
    local dir="$1" files=()
    mapfile -t files < <(find "$dir" -type f -not -path '*/__pycache__/*' | sort)
    for f in "${files[@]}"; do
        git add -- "$f"   # D0034: a manifest row must name a committed artifact
        grep -q "  $f\$" MANIFEST.sha256 || sha256sum "$f" >> MANIFEST.tmp.add
    done
    [ -f MANIFEST.tmp.add ] && { cat MANIFEST.tmp.add >> MANIFEST.sha256; rm -f MANIFEST.tmp.add; }
    return 0
}
move_into_corpus() {     # <candidate dir> <tests/poison/name>
    # `git mv` when the candidate is tracked — the real sitting, which starts from a committed
    # tree. A rehearsal in worktree mode carries uncommitted drafts as untracked copies, which
    # `git mv` refuses; moving them and staging the result is the same end state.
    if [ -n "$(git ls-files -- "$1")" ]; then
        git mv "$1" "$2" || die "git mv $1 failed"
    else
        mkdir -p "$(dirname "$2")" && mv "$1" "$2" || die "mv $1 failed"
        git add -- "$2"
    fi
}
# A FIXTURE MOVE CARRIES ITS BINDINGS WITH IT, derived rather than listed (D0152's ruling for
# D0141: "in the same breath as the move"). M3 retargeted D0141 and D0199 by name, one block
# each, and this driver's first rehearsal still broke three records nobody had named — D0245,
# D0246 and D0248 bind doorway-network-residue's README. Every record whose target sits under
# the candidate directory is rewritten; a SIGNED record is refused before anything is written,
# because its signature covers those bytes and the key is the owner's.
retarget_bindings() {    # <candidate dir> <tests/poison/name>
    python3 - "$1" "$2" <<'PY'
import pathlib, re, sys

old, new = (a.rstrip("/") + "/" for a in sys.argv[1:3])
target = re.compile(r'^(\s*target:\s*"?)' + re.escape(old), re.M)
edits, signed = [], []
for rec in sorted(pathlib.Path("decisions").glob("*.yaml")):
    out, n = target.subn(lambda m: m.group(1) + new, rec.read_text(encoding="utf-8"))
    if n:
        (signed if rec.with_name(rec.name + ".sig").exists() else edits).append((rec, out, n))
if signed:
    sys.exit("a signed record binds " + old + " — retargeting it would break its signature:\n  "
             + "\n  ".join(str(rec) for rec, _, _ in signed))
for rec, out, _ in edits:
    gone = [t for t in re.findall(r'^\s*target:\s*"?(' + re.escape(new) + r'[^"\s]*)', out, re.M)
            if not pathlib.Path(t).exists()]
    if gone:
        sys.exit(f"{rec}: the retargeted binding still does not resolve: {gone[0]}")
for rec, out, n in edits:
    rec.write_text(out, encoding="utf-8")
    print(f"   retargeted {n} binding(s) in {rec}")
print(f"   {len(edits)} record(s) retargeted from {old}")
PY
}
commit_with_hook_retry() {   # regen-projections may rewrite files on the first try
    local hook=()
    if [ "$FAST" = 1 ]; then
        skipping_gate "the pre-commit hooks (~12 minutes; check_decisions is most of it)"
        hook=(--no-verify)
    fi
    git add -A && git commit "${hook[@]}" -m "$1" && return 0
    git add -A && git commit "${hook[@]}" -m "$1"
}
# EVERY LONG GATE GOES THROUGH THIS ONE LINE, so a fast run cannot quietly become a green one.
# If you are reading this line in a transcript from a REAL sitting, TANNEN_SITTING_FAST was set
# in the owner's environment and the receipt attests to a gate that did not run (D0181).
skipping_gate() { printf '   [TANNEN_SITTING_FAST] NOT RUN: %s\n' "$*"; }

# ------------------------------------------------------- patches (every owner edit is one)
# A drafted patch is in exactly one of three states, and git computes all three: already
# applied (reverse applies), applies, or neither (the tree moved since drafting — refused, never
# forced). The return status says which.
patch_files() { sed -n 's|^+++ b/||p' "$1"; }
offer_patch() {  # <patch> -> 0 freshly applied (caller must keep_or_revert), 1 already applied, 2 missing/neither
    local patch="$1" err
    if [ ! -f "$patch" ]; then
        note "MISSING draft: $patch — nothing offered"; return 2
    fi
    if git apply -R --check "$patch" >/dev/null 2>&1; then
        note "already applied — skipped ($(basename "$patch"))"; return 1
    fi
    if ! err=$(git apply --check "$patch" 2>&1); then
        note "$(basename "$patch") neither applies nor is already applied — the tree moved since"
        note "it was drafted. Nothing was changed; hand it back to a builder session:"
        printf '%s\n' "$err" | sed 's/^/     /'
        return 2
    fi
    git apply "$patch" || die "git apply failed after --check passed: $patch"
    note "applied $(basename "$patch") — the exact bytes follow:"
    git apply --stat "$patch" | sed 's/^/   /'
    page "$patch"
    return 0
}
keep_or_revert() {  # <patch> <prompt> -> 0 kept (manifest rows refreshed), 1 reverted
    local f
    if confirm "$2"; then
        # Refresh a row only where one EXISTS. Custody membership and MANIFEST rows are
        # independent sets: calling regen_manifest_row on a custody-only file (Makefile,
        # policy.yaml, check_manifest.py …) would CREATE a row and silently enlarge the frozen
        # set at a sitting (the M3 copy's step 4f comment). Derived from the patch, not listed.
        while IFS= read -r f; do
            [ -f "$f" ] && grep -q "  $f\$" MANIFEST.sha256 && regen_manifest_row "$f"
        done < <(patch_files "$1")
        return 0
    fi
    git apply -R "$1" || die "could not revert $(basename "$1") — the working tree needs hand repair"
    return 1
}
# Whether an item has LANDED in this tree, asked of the artifact rather than remembered from an
# answer: a resumed sitting has no memory of what was accepted, and step 8's APPLIED-BY lines
# and step 3's D0243 rewrite must be true on a re-run too. One marker per artifact, each a line
# the drafted patch writes and nothing else in the tree carries.
# Each marker is reconciled with its draft patch and with queue_upgrades.py's own detectors.
landed() {
    case "$1" in
        doorway)            [ -f scripts/check_doorway.py ] && grep -q 'id = "shell-no-subprocess"' governance/importlinter.toml ;;
        shell-shape)        grep -q '"shell-no-subprocess": \["tannen"\]' scripts/check_manifest.py ;;
        policy-sentence)    grep -q 'WHAT SPENDGUARD DOES AND DOES NOT DO' governance/policy.yaml ;;
        current-envelope)   grep -q '^def current_milestone(' scripts/check_manifest.py ;;
        derived-tags)       grep -q '^def derive_required_tags(' scripts/check_tag_signers.py ;;
        verdict-out)        ! grep -qF 'f"Attention receipt: **{' scripts/gen_projections.py ;;
        roadmap-wiring)     grep -q 'id: regen-roadmap' .pre-commit-config.yaml && grep -q 'scripts/gen_roadmap.py' Makefile ;;
        delegations-marker) ! grep -q '^\$marker of ' DELEGATIONS.md ;;
        readme-corrections) grep -q 'frozen law file FORWARD' tests/poison/README.md ;;
        ledger)             [ -f docs/redteam/LEDGER.yaml ] ;;
        fixture:*)          [ -d "tests/poison/${1#fixture:}" ] ;;
        *)                  return 1 ;;
    esac
}
said_landed() { if landed "$1"; then printf 'LANDED'; else printf 'NOT LANDED this sitting'; fi; }

# ------------------------------------------------------- the lock (D0152 item 4, D0153)
# A boundary sitting is a one-run ceremony. Keyed on the worktree; FD 9 is held for the life of
# the process, so the kernel drops it on exit, die, kill or crash.
LOCKDIR="${TMPDIR:-/var/tmp}"
LOCKFILE="$LOCKDIR/tannen-sitting-$(printf '%s' "$PWD" | sha256sum | cut -c1-16).lock"
if command -v flock >/dev/null 2>&1; then
    exec 9>"$LOCKFILE" || die "cannot open the sitting lock at $LOCKFILE"
    flock -n 9 || die "another boundary sitting is already running against this worktree.
       lock: $LOCKFILE
       A sitting is a one-run ceremony; two concurrent runs produced D0153's three artifacts.
       If you are certain no other run is live, the lock is released the moment that process
       exits — check with: fuser -v $LOCKFILE"
else
    note "NOTE: flock(1) is not on PATH, so the single-run guard is NOT ARMED for this run."
    note "Nothing will stop a second invocation against this worktree (D0152 item 4)."
fi

# ---------------------------------------------------------------- 0. preconditions
say "Step 0 — boundary sitting, $MILESTONE. Precondition: a green gate and a read queue"
[ -x "$PY" ] || die "no interpreter at $PY — run 'uv sync --frozen' first"
[ -f "$OWNER_KEY" ] || die "no owner key at $OWNER_KEY (set TANNEN_OWNER_KEY)"
grep -q '^owner@tannen ' allowed_signers || die "owner@tannen is not enrolled in allowed_signers"
# RESUMED is decided by artifacts only a sitting creates (RT-M2-06 D1), never by any dirt at all:
# (a) a tracked modification other than this driver's own copy; (b) untracked owner signatures
# or receipts; (c) the close tag. Stray dirt is reported, not acted on.
RESUMED=0
[ -n "$(git status --porcelain --untracked-files=no | grep -v ' scripts/boundary_sitting\.sh$')" ] && RESUMED=1
[ -n "$(git ls-files --others --exclude-standard -- 'decisions/*.yaml.sig' 'governance/*.sig' 'receipts/')" ] && RESUMED=1
git rev-parse -q --verify "refs/tags/$MILESTONE-close" >/dev/null 2>&1 && RESUMED=1
if [ "$RESUMED" = 1 ]; then
    note "Sitting artifacts are already present — a signature, a receipt, or the close tag —"
    note "so this is a RESUMED sitting. Half-applied sitting work is custody drift by"
    note "construction, so the precondition gate would read red for this sitting's own doing."
    note "Step 9 runs the gate that must be green, once the edits are complete."
    if confirm "Show what is already changed?"; then
        git status --short | page
    fi
else
    STRAY=$(git status --porcelain | grep -v ' scripts/boundary_sitting\.sh$')
    if [ -n "$STRAY" ]; then
        note "The tree is not clean, and none of it looks like sitting work:"
        printf '%s\n' "$STRAY" | sed 's/^/    /'
        note "The gate below may read red for reasons that are not this sitting's."
    fi
if confirm "Run 'make verify' now (recommended — nothing should be signed over a red gate)?"; then
    # Asked in both modes so the prompt sequence is identical fast or slow. The announcement
    # names the regime this run is in, because there are three and only one runs the suite
    # (owner ruling 2 of 2026-09-10, D0208; D0151, D0206).
    if [ "$FAST" = 1 ]; then
        note "The gate below is the custodian alone: TANNEN_SITTING_FAST is set, so make"
        note "verify does not run here at all. Rehearsal only — it establishes nothing about"
        note "the suite, and the harness counts every skip so a fast run cannot read as full."
    elif driver_custody_current; then
        waiting "the full gate: $(verify_eta). It streams below; nothing to do but watch."
    else
        note "This driver's bytes do not match its row in governance/custody.sha256. That is"
        note "the cp that installed it, and it is drift on a custody-set member — so"
        note "check_manifest, verify's FIRST recipe line, fails and make stops there. What"
        note "runs below is that one guard: frozen paths, seals, required signatures and"
        note "tier-c consistency, all of it, minus this file's own expected drift. It is NOT"
        note "the suite, and it is not the precondition — the 'make verify' you ran BEFORE"
        note "the cp is the only one that could establish that (D0151, D0206; docs/SITTING.md)."
        waiting "the floor check only — seconds. The full gate it stands in for is $(verify_eta)."
    fi
    verify_log=$(mktemp -t tannen-verify.XXXXXX)
    if [ "$FAST" = 1 ]; then
        skipping_gate "make verify at step 0 — the cheap floor still runs below"
        bash scripts/custodian.sh --check-only > "$verify_log" 2>&1
        verify_rc=$?
        cat "$verify_log"
    else
        make verify 2>&1 | tee "$verify_log"
        verify_rc=${PIPESTATUS[0]}
    fi
    verify_out=$(cat "$verify_log"); rm -f "$verify_log"
    if [ "$verify_rc" -ne 0 ]; then
        unexpected=$(unexpected_failures "$verify_out")
        [ -z "$unexpected" ] || die "verify is red — fixing it is builder work; sign nothing yet:
$unexpected"
        # The continuation line claims only what the run established; the pytest anchor is
        # anchored because an unanchored / passed/ once matched a record TITLE (D0208).
        gate_guards=$(printf '%s\n' "$verify_out" | grep -cE '^check_[a-z_]+: (OK|FAIL)')
        if printf '%s\n' "$verify_out" | grep -qE '^[0-9]+ passed'; then
            note "green except the custody set, which is this sitting's step 7 — continuing"
        else
            note "no unexpected failure — and that is ALL this established. The run reached"
            note "$gate_guards of verify's guards and never reached the suite, so"
            note "check_decisions, pytest, the laws report and lint-imports did not run here."
            if [ "$FAST" = 1 ]; then
                note "The gate was the custodian alone (TANNEN_SITTING_FAST), by request."
            else
                note "make stopped at check_manifest, which is where this driver's own custody"
                note "drift is seen."
            fi
            note "The precondition is the 'make verify' from before the cp (D0151, D0206)."
        fi
    fi
fi
fi
# THE QUEUE IS ROADMAP.md §3, NOT THE DIGEST. The digest's "Requires owner" section filters
# tier == "C" and cannot see a Tier-A record that needs the key — D0217, D0229 and D0241 are all
# three such records, and at M3 the same filter is why D0191 and D0195's items had nowhere to
# land. §3 is a query over status at any tier (D0216). This shows the COMMITTED copy, whose
# freshness the gate above (or the one before the cp) checked via tests/test_roadmap.py.
if confirm "Show the owner queue (ROADMAP.md §3 — every record blocked-on-owner, at any tier)?"; then
    sed -n '/^## 3\. /,/^## 4\. /p' ROADMAP.md | page
fi

say "Optional — an ssh-agent holding the key, so you type the passphrase once"
# THREE STATES, TWO REMEDIES, AND THE M3 COPY TOLD THEM APART NOT AT ALL. `ssh-add -l` exits 0
# when an agent holds identities, 1 when an agent runs and holds none, and 2 when no agent is
# reachable. The M3 copy offered a bare `ssh-add` in every non-0 case and ignored its status —
# and on the owner's machine at the M3 sitting no agent runs by default, so the offer failed,
# nothing said so, and every signature after it prompted for the passphrase (M3 sitting
# measurement, carried in this directory's README). "Key not loaded" wants ssh-add; "no agent"
# wants an agent first. An agent THIS RUN starts is stopped when the run exits, by any route —
# the passphrase attests presence for this sitting, not for the rest of the login session.
note "A boundary sitting signs several artifacts. Loading the key means one passphrase for"
note "the whole sitting; you are present for all of it, which is what the passphrase attests."
key_fp=$(ssh-keygen -lf "$OWNER_KEY.pub" 2>/dev/null | awk '{print $2}')
ssh-add -l >/dev/null 2>&1; agent_rc=$?
if [ "$agent_rc" -eq 2 ]; then
    note "NO ssh-agent is reachable (ssh-add -l exit 2). Loading a key needs one first."
    if confirm "Start an ssh-agent for this sitting (stopped again when the driver exits)?"; then
        if eval "$(ssh-agent -s)" >/dev/null && [ -n "${SSH_AGENT_PID:-}" ]; then
            trap 'ssh-agent -k >/dev/null 2>&1' EXIT
            note "agent started (pid $SSH_AGENT_PID); it is stopped when this driver exits"
            ssh-add -l >/dev/null 2>&1; agent_rc=$?
        else
            note "ssh-agent did not start — signing uses the key file; expect a prompt per signature"
        fi
    fi
fi
if [ "$agent_rc" -ne 2 ] && [ -n "$key_fp" ] && ssh-add -l 2>/dev/null | grep -qF "$key_fp"; then
    KEYREF="$OWNER_KEY.pub"
    note "key already loaded in the agent"
elif [ "$agent_rc" -ne 2 ]; then
    note "an agent is running but does not hold $OWNER_KEY (ssh-add -l exit $agent_rc)"
    if confirm "ssh-add $OWNER_KEY now?"; then
        if ssh-add "$OWNER_KEY"; then
            KEYREF="$OWNER_KEY.pub"
        else
            note "ssh-add FAILED (exit $?) — signing falls back to the key file, so expect one"
            note "passphrase prompt per signature. Nothing else is affected."
        fi
    fi
else
    note "no agent: signing uses the key file directly; expect one passphrase prompt per signature"
fi
export TANNEN_OWNER_KEY="$KEYREF"

stop_after 0

# ---------------------------------------------------------------- 1. the doorway (RT-M4-02)
say "Step 1 — the shell's IO doorway is a hand-written list, and subprocess is not on it (RT-M4-02, D0229 item 2, D0248)"
# FIRST, BY THE OWNER'S REVIEW (D0246 A2). RT-M4-01 is inert while every ceiling is zero; this
# finding is live, its threat model is the builder, and the repository is published — so a gate
# runs off this machine and `make verify` green does not today mean "no IO". Frozen L4.9 scans
# the shell against a hand-written NETWORK literal and never looks at subprocess or os at all;
# the kernel-no-io contract forbids both but its source_modules is tannen.kernel alone.
#
# What installs here is the owner-key half. The superseding frozen L4.9 that derives from it is
# M5 Session A's (a successor law has no legal home inside M4 — D0241, the spec-table guard).
note "RT-M4-02 is the one live high finding. L4.9 enforces 'the only IO doorway is oracles/'"
note "for the shell over a HAND-WRITTEN network list, and does not scan subprocess or os at all:"
note "subprocess.run(['curl', url]) in tannen.store reads the world with make verify green."
note ""
note "The patch installs three things, reverted together if you decline:"
note "  scripts/check_doorway.py  a guard that DERIVES the network set — any import whose static"
note "                            module-level closure reaches socket/ssl — and refuses os.system/"
note "                            popen/exec/spawn shell-outs, outside the named doors (D0248)"
note "  shell-no-subprocess       an import-linter contract over the WHOLE package"
note "  custody + make verify     the guard joins the custody set and the gate"
note "Its poison fixture installs at step 5 and its custodian line at step 6."
DOORWAY_MARKER="reads the world outside the doorway"   # check_doorway.py's own message
P="$PROPOSALS_M4/doorway-guard.patch"
if offer_patch "$P"; then
    fx=""
    for d in "tests/poison/doorway-network-residue" "$CANDIDATES/doorway-network-residue"; do
        [ -d "$d/src" ] && { fx="$d"; break; }
    done
    waiting "running the new guard against this tree (must pass) and its poison (must fail) — seconds"
    tree_out=$("$PY" -I -P scripts/check_doorway.py 2>&1); tree_rc=$?
    printf '%s\n' "$tree_out" | sed 's/^/     /'
    if [ -n "$fx" ]; then
        fx_out=$("$PY" -I -P scripts/check_doorway.py --root "$fx" 2>&1); fx_rc=$?
        if [ "$fx_rc" -ne 0 ] && printf '%s\n' "$fx_out" | grep -qF "$DOORWAY_MARKER"; then
            # The poison is MEANT to fail. Its summary line is restated the way the custodian states
            # a bitten poison, so the second FAST rehearsal's "unexpected failure lines" (empty is the
            # goal) stops listing a run that behaved; every violation line follows word for word.
            printf '%s\n' "$fx_out" \
                | sed -e 's/^check_doorway: FAIL (\(.*\))$/check_doorway fails its poison as required (\1)/' \
                      -e 's/^/     /'
        else
            printf '%s\n' "$fx_out" | sed 's/^/     /'
        fi
    else
        fx_rc=0; fx_out=""
    fi
    if [ "$tree_rc" -ne 0 ]; then
        note "THE GUARD IS RED ON THIS TREE. Keeping it reddens every gate from here; decline and"
        note "hand it back to a builder session unless the output names a real IO read."
    elif [ -z "$fx" ]; then
        note "no poison fixture found to watch it fail against — a guard nobody has watched fail"
        note "is not yet a guard (CONTRIBUTING.md). Keeping it is your call; step 5 cannot help."
    elif [ "$fx_rc" -eq 0 ] || ! printf '%s\n' "$fx_out" | grep -qF "$DOORWAY_MARKER"; then
        note "the guard did NOT fail its poison for its own reason — it is weakened as drafted."
    else
        note "green on this tree, red on its poison for its own reason: watched failing first."
    fi
    if keep_or_revert "$P" "Keep the doorway guard, its contract, and their custody and gate rows?"; then
        note "kept. check_manifest will not shape-check the new contract until step 3's row lands."
    else
        note "reverted — all of it. RT-M4-02 stays live: make verify green still does not mean"
        note "no IO, and its fixture is not offered at step 5."
    fi
fi

stop_after 1

# ---------------------------------------------------------------- 1b. Tier-C safety net
say "Step 1b — Tier-C records already recorded accepted (a safety net; usually empty)"
note "Since D0064 the guard refuses a Tier-C record that says accepted without a signature, so"
note "a committed repo cannot hold one. Anything found here reached accepted in the WORKING TREE."
sign_tier_c_records

stop_after 1b

# ---------------------------------------------------------------- 2. the policy sentence
say "Step 2 — policy.yaml says SpendGuard enforces the envelope, and it does not (D0240 item 1, D0238)"
note "The owner's ruling (D0240): a budget file is an AUTHORISATION, a property of the caller,"
note "not of the library. The defective artifact is the sentence, not the frozen spend laws."
note "A precondition to the first nonzero envelope (D0240 item 4)."
P="$PROPOSALS_M4/policy-envelope-sentence.patch"
if offer_patch "$P"; then
    if keep_or_revert "$P" "Keep the corrected sentence (policy.yaml is re-signed next)?"; then
        note "kept. The custody row for policy.yaml is regenerated at step 7."
    else
        note "reverted — policy.yaml goes on claiming what SpendGuard does not do, and a"
        note "precondition to the first spend stays open (D0243 reports it as policy-sentence)."
    fi
fi
verify_owner governance/policy.yaml tannen-policy \
    || { note "re-signing policy.yaml"; sign_owner governance/policy.yaml tannen-policy; }

stop_after 2

# ---------------------------------------------------------------- 3. check_manifest
say "Step 3 — check_manifest compares ceilings with the largest envelope, and locks nothing (D0240 item 3, D0244 item 1, D0229 item 5)"
note "ONE FILE, EVERY CHANGE TO IT IN THIS STEP, and the reason is D0243. Its strict node reads"
note "'is scripts/check_manifest.py still byte-identical to the defective version?' — so ANY"
note "byte changed here reads as the envelope fix having landed. The shell contract's shape row"
note "(for step 1's contract) is therefore offered only on top of the envelope patch, never alone."
note ""
note "The envelope patch carries two changes signed or declined together (D0244 item 1): the"
note "comparison against the CURRENT milestone's envelope, derived from MANIFEST.sha256's rows,"
note "and the pre-budget lock — a nonzero envelope or ceiling is refused while L4.4's third node"
note "is unretired or the CLI clamp is absent (D0242 item 3). Both are inert today."
P="$PROPOSALS_M4/check-manifest-current-envelope.patch"
if offer_patch "$P"; then
    waiting "check_manifest on the patched file — seconds; only custody drift may fail here"
    cm_out=$("$PY" -I -P scripts/check_manifest.py 2>&1)
    cm_unexpected=$(unexpected_failures "$cm_out" | grep -v 'custody drift:' || true)
    if [ -z "$cm_unexpected" ]; then
        # Only custody drift, which step 7's signature exists to resolve: the summary is restated
        # so the rehearsal does not list an expected state as a failure; every drift line follows.
        printf '%s\n' "$cm_out" \
            | sed -e 's/^check_manifest: FAIL (\(.*\))$/check_manifest: \1, every one custody drift — expected until step 7 signs/' \
                  -e 's/^/     /'
    else
        printf '%s\n' "$cm_out" | sed 's/^/     /'
        note "UNEXPECTED check_manifest failures above — read them before keeping."
    fi
    if keep_or_revert "$P" "Keep both changes to check_manifest.py (current envelope + pre-budget lock)?"; then
        note "kept. check_manifest.py is custody-set with no manifest row; step 7 covers it."
    else
        note "reverted — the max-over-all-envelopes comparison stays, the lock stays a test file"
        note "a builder can delete, and two preconditions to the first spend stay open."
    fi
fi
if landed current-envelope && landed doorway; then
    P="$PROPOSALS_M4/check-manifest-shell-contract.patch"
    if offer_patch "$P"; then
        if keep_or_revert "$P" "Keep the shape row that pins shell-no-subprocess to the whole package?"; then
            note "kept. Narrowing the new contract's source_modules is now a red gate (RT-02, D0056)."
        else
            note "reverted — check_manifest skips unknown contract ids, so shell-no-subprocess can be"
            note "narrowed to one module with every guard green."
        fi
    fi
elif landed doorway; then
    note "the shell contract's shape row is NOT offered: the envelope patch did not land, and"
    note "D0243 would read any byte change to check_manifest.py as that fix. The contract stays"
    note "unshaped until the next sitting."
fi
# D0243's strict node goes RED as each precondition lands, and updating it is part of the
# ceremony (D0244 item 3 — the redness IS the announcement). The expected set is written from
# what LANDED in this tree, never from the node's own detector: computing it from
# unmet_spend_preconditions() would make the node a tautology.
if python3 - <<'PY'
import pathlib, re, sys

def has(path, text):
    return text in pathlib.Path(path).read_text(encoding="utf-8")

still_open = []
if not has("governance/policy.yaml", "WHAT SPENDGUARD DOES AND DOES NOT DO"):
    still_open.append("policy-sentence")
if not re.search(r"^def current_milestone\(", pathlib.Path("scripts/check_manifest.py").read_text(), re.M):
    still_open.append("current-envelope")
still_open += ["successor-law", "clamp"]   # both owed by M5 Session A (D0241); nothing here lands them

t = pathlib.Path("tests/test_spend_preconditions.py")
src = t.read_text(encoding="utf-8")
pat = re.compile(r'^(    assert open_now == )\{[^}\n]*\}$', re.M)
hits = pat.findall(src)
if len(hits) != 1:
    sys.exit(f"tests/test_spend_preconditions.py: expected one `assert open_now == {{…}}` line, found {len(hits)} — update by hand")
want = "{" + ", ".join(f'"{i}"' for i in still_open) + "}"
new = pat.sub(lambda m: m.group(1) + want, src)
if new == src:
    print("   D0243's strict node already names exactly the open set: " + want)
    sys.exit(1)
t.write_text(new, encoding="utf-8")
print("   D0243's strict node now expects " + want)
PY
then
    git --no-pager diff tests/test_spend_preconditions.py
    waiting "running tests/test_spend_preconditions.py — a few seconds"
    TANNEN_NO_EVIDENCE=1 uv run pytest -q tests/test_spend_preconditions.py 2>&1 | tail -3 \
        || note "the node did not run — step 9's gate will"
fi

stop_after 3

# ---------------------------------------------------------------- 4. required_tags derived
say "Step 4 — required_tags lags one milestone at every boundary, for the fifth time (D0205, D0229 item 4)"
note "tag-roles.yaml lists 9 required tags; git holds 10. m4-laws-freeze is deletable today with"
note "no guard noticing — D0095's enumeration-that-lags, now at its fifth recurrence (RT-M4-06)."
note "The patch derives the set from the frozen specs (D0205) and refuses a non-empty hand list."
note "It is what deletes step 11: the tags this sitting mints need no hand edit afterwards."
note "It also sets the custodian-tag-signer fixture's own list to [] so that fixture keeps"
note "failing for exactly its original reasons. Its poison fixture installs at step 5."
P="$PROPOSALS_M4/required-tags-derived.patch"
if offer_patch "$P"; then
    waiting "check_tag_signers on this tree with the derivation — seconds; must be green"
    "$PY" -I -P scripts/check_tag_signers.py 2>&1 | sed 's/^/     /'
    if keep_or_revert "$P" "Keep the derived required_tags (guard, tag-roles.yaml, tests, fixture)?"; then
        note "kept. Both scripts/check_tag_signers.py and governance/tag-roles.yaml are frozen and"
        note "custody-set; their manifest rows were refreshed, and step 7 re-signs custody."
    else
        note "reverted — all four files. The enumeration stays, and so does step 11's reason to exist."
    fi
fi
if ! landed derived-tags && ! grep -q '^  - m4-laws-freeze$' governance/tag-roles.yaml; then
    note ""
    note "Without the derivation, m4-laws-freeze can still be required by hand. m4-close cannot be"
    note "added here — it does not exist until step 10 — so it lags to the next sitting, the"
    note "lag of one that D0095 accepts. Adding it here keeps it under step 7's one signature."
    if confirm "Add m4-laws-freeze to the hand-maintained required_tags instead?"; then
        python3 - <<'PY' || die "tag-roles.yaml's required_tags is not the expected shape — add it by hand"
import pathlib, sys
p = pathlib.Path("governance/tag-roles.yaml")
src = p.read_text(encoding="utf-8")
anchor = "required_tags:\n"
if src.count(anchor) != 1:
    sys.exit(1)
end = src.index(anchor) + len(anchor)
p.write_text(src[:end] + "  - m4-laws-freeze\n" + src[end:], encoding="utf-8")
PY
        regen_manifest_row governance/tag-roles.yaml
        git --no-pager diff governance/tag-roles.yaml
    else
        note "declined — m4-laws-freeze stays deletable with no guard noticing (D0229 item 4)."
    fi
fi

stop_after 4

# ---------------------------------------------------------------- 4b. D0215
say "Step 4b — minting the close tag reddens the commit it attests (D0215)"
note "DECISIONS.md renders a FRESH/STALE verdict computed from the clock and the tag set, and"
note "check_decisions compares the stored line with today's computation. A commit contains"
note "neither, so every close tag this project has minted names a commit that fails the gate"
note "(measured on m3-close, CI 34481481487; control af41fe8, D0215)."
note "The patch removes the claim from the file that cannot keep it: DECISIONS.md carries only"
note "what its commit contains, the verdict lives in the dated digest, and check_decisions still"
note "computes and prints it at run time. With D0205, this is what deletes step 11."
P="$PROPOSALS_M4/decisions-verdict-out.patch"
if offer_patch "$P"; then
    "$PY" -I -P scripts/gen_projections.py >/dev/null || die "projection generation failed on the patched generator"
    git --no-pager diff --stat DECISIONS.md
    if keep_or_revert "$P" "Keep the clock verdict out of DECISIONS.md (generator, guard and tests)?"; then
        note "kept, and DECISIONS.md regenerated in the new shape."
    else
        "$PY" -I -P scripts/gen_projections.py >/dev/null || true
        note "reverted, and DECISIONS.md regenerated in the old shape. Step 11 will run, and the"
        note "close tag will again name a commit that fails the gate once minted."
    fi
fi

stop_after 4b

# ---------------------------------------------------------------- 4c. D0217 (1)(2)
say "Step 4c — ROADMAP.md is checked on every commit and regenerated by nothing (D0217 items 1 and 2)"
note "A regen-roadmap pre-commit hook beside regen-projections, and gen_roadmap.py in make"
note "projections. Both files are custody-set. tests/test_roadmap.py moves with them: its check that"
note "the hook is absent would otherwise go red the moment it exists. Item (3) — the queue this"
note "sitting reads by status at any tier — is this driver's own step 8."
P="$PROPOSALS_M4/roadmap-wiring.patch"
if offer_patch "$P"; then
    if keep_or_revert "$P" "Keep the roadmap hook and make target?"; then
        "$PY" -I -P scripts/gen_roadmap.py >/dev/null || note "ROADMAP.md did not regenerate — step 9 retries"
        note "kept. ROADMAP.md's own regeneration sentence reads the hook, so it was regenerated."
    else
        note "reverted — ROADMAP.md stays stale after every record until someone types the command."
    fi
fi

stop_after 4c

# ---------------------------------------------------------------- 4d. D0229 (1)
say "Step 4d — a frozen file carries an unexpanded shell variable (D0229 item 1)"
note "DELEGATIONS.md:41 reads '\$marker of 2026-09-07': the publication sitting's applier wrote"
note "\\\$marker inside a plain python string, so the variable was never substituted. The m4-laws-"
note "freeze tag quotes delegation 1 and the file's hash, not the whole file, so it carries no"
note "copy of the defect forward. m4-close will quote the corrected file's hash."
P="$PROPOSALS_M4/delegations-marker.patch"
if offer_patch "$P"; then
    if keep_or_revert "$P" "Keep the corrected founding-ratification line (frozen; manifest row refreshed)?"; then
        note "kept."
    else
        note "reverted — the frozen file keeps its literal \$marker."
    fi
fi

stop_after 4d

# ---------------------------------------------------------------- 4e. D0229 (3b)
say "Step 4e — two installed fixtures' prose recommends a fix that was measured and is not the fix (D0229 item 3, D0204)"
note "tests/poison/oracle-shadow-spoofed/README.md and tests/poison/README.md still recommend"
note "a package-qualified import; D0204 measured that it leaves the decoy winning, and the real"
note "fix is a forward supersession — Tier-A builder work. Plus _delta_model.py's header"
note "mis-citation. All inside tests/poison/, so custody-set and frozen."
P="$PROPOSALS_M4/poison-readme-corrections.patch"
if offer_patch "$P"; then
    if keep_or_revert "$P" "Keep the corrected fixture prose (manifest rows refreshed)?"; then
        note "kept."
    else
        note "reverted — the fixtures keep recommending the measured non-fix."
    fi
fi

stop_after 4e

# ---------------------------------------------------------------- 5. poison fixtures
say "Step 5 — install the poison fixtures (author-key territory)"
note "Three fixtures, each offered only when its guard landed this run (a fixture ahead of its"
note "guard leaves the custodian permanently red — D0104). The obligation to install them sits on"
note "the guard's closing record, not on the draft (D0246 A4):"
note "  doorway-network-residue   RT-M4-02 — the step-1 guard, D0248"
note "  tag-roles-derived         D0205 — the step-4 derivation; its bundle is GENERATED here"
note "  oracle-shadow-cross-file  D0229 item 3 — the cross-file disarm no single-file run can see"
note "NOT offered, and why: spend-fold-forged-reservation (RT-M4-01) and code-address-closure"
note "(RT-M4-04) have no guard — the pre-budget sitting and a future session own those."
FIXTURES="doorway-network-residue tag-roles-derived oracle-shadow-cross-file"
fixture_guard_landed() {
    case "$1" in
        doorway-network-residue)  landed doorway ;;
        tag-roles-derived)        landed derived-tags ;;
        oracle-shadow-cross-file) true ;;   # its guard (plugin.py) already bites (SUPERSESSIONS.md)
        *)                        return 1 ;;
    esac
}
for fixture in $FIXTURES; do
    if [ -d "tests/poison/$fixture" ]; then
        note "already installed: $fixture"
        continue
    fi
    [ -d "$CANDIDATES/$fixture" ] || { note "MISSING candidate: $fixture"; continue; }
    if ! fixture_guard_landed "$fixture"; then
        note "not offered: $fixture — its guard did not land at this sitting"
        continue
    fi
    if confirm "Install $fixture into tests/poison/?"; then
        move_into_corpus "$CANDIDATES/$fixture" "tests/poison/$fixture"
        if [ -f "tests/poison/$fixture/make-fixture.sh" ]; then
            # Generated HERE, never shipped pre-built (conferral ruling 6): an opaque bundle you
            # did not watch being made is one you are taking on trust.
            note "generating $fixture's bundle now, with a key that exists only inside the fixture"
            bash "tests/poison/$fixture/make-fixture.sh" || die "make-fixture.sh failed for $fixture"
        fi
        retarget_bindings "$CANDIDATES/$fixture" "tests/poison/$fixture" \
            || die "could not retarget the bindings naming $CANDIDATES/$fixture — nothing is signed yet; retarget by hand and re-run"
        add_manifest_rows "tests/poison/$fixture"
        note "installed with $(find "tests/poison/$fixture" -type f -not -path '*/__pycache__/*' | wc -l) manifest row(s)"
    else
        note "declined — $fixture stays a candidate, and step 6 leaves out its poison line."
    fi
done
# README rows and suite rows, per INSTALLED fixture only. Guarded on the directory as well as
# the row so the index never claims a fixture the owner declined one loop earlier, and the rows
# file's own prose cannot satisfy readme_row_absent (D0131 item 1).
for fixture in $FIXTURES; do
    [ -d "tests/poison/$fixture" ] || continue
    if readme_row_absent "$fixture"; then
        rows="$PROPOSALS_M4/poison-readme-row-$fixture.md"
        [ -f "$rows" ] || { note "MISSING README row draft: $rows"; continue; }
        cat "$rows" >> tests/poison/README.md
        regen_manifest_row tests/poison/README.md
        note "tests/poison/README.md: row added for $fixture"
    fi
done
# THE SUITE MUST LEARN EACH FIXTURE IN THE SAME STEP, or tests/test_governance_scripts.py's
# completeness pass reads it as installed-and-unexercised and the gate goes red (D0213, D0152
# item 6's shape). That file is builder-writable, so no signature — but it moves with the corpus.
#
# INSERTED BY ANCHOR, NOT PATCHED. Two POISON rows appended to one list are two patches with the
# same context, and the second stops applying the moment the first has — so every SUBSET of
# accepted fixtures would need a patch of its own. Each fixture's rows are a snippet under suite/,
# placed before the list's (or the map's) closing line, and a snippet already present is skipped.
wire_suite() {  # <fixture> -> 0 wired or already wired
    python3 - "$1" "$PROPOSALS_M4/suite" <<'PY'
import pathlib, sys

fixture, drafts = sys.argv[1], pathlib.Path(sys.argv[2])
t = pathlib.Path("tests/test_governance_scripts.py")
src = t.read_text(encoding="utf-8")


def before_close(text, opener, closer, block):
    end = text.index(closer, text.index(opener))
    return text[:end + 1] + block + text[end + 1:]


poison = drafts / f"{fixture}.poison.py"
dedicated = drafts / f"{fixture}.dedicated.py"
if poison.exists():
    block = poison.read_text(encoding="utf-8")
    if block in src:
        sys.exit(0)
    if src.count("\nPOISON = [\n") != 1:
        sys.exit("tests/test_governance_scripts.py: the POISON list is not found exactly once — wire by hand")
    src = before_close(src, "\nPOISON = [\n", "\n]\n", block)
elif dedicated.exists():
    entry, function = dedicated.read_text(encoding="utf-8").split("# --- function ---\n", 1)
    if entry in src:
        sys.exit(0)
    anchor = "\n\ndef test_every_installed_fixture_is_exercised_by_this_suite"
    if src.count("\nDEDICATED = {\n") != 1 or src.count(anchor) != 1:
        sys.exit("tests/test_governance_scripts.py: DEDICATED or the completeness test is not found exactly once — wire by hand")
    src = before_close(src, "\nDEDICATED = {\n", "\n}\n", entry)
    src = src.replace("These five deviate", "These deviate", 1)   # a count in prose rots (D0209)
    src = src.replace(anchor, "\n\n" + function.rstrip("\n") + "\n" + anchor, 1)
else:
    sys.exit(f"no suite draft for {fixture} under {drafts}")
t.write_text(src, encoding="utf-8")
print(f"   tests/test_governance_scripts.py: {fixture} wired into the suite")
PY
}
for fixture in $FIXTURES; do
    [ -d "tests/poison/$fixture" ] || continue
    wire_suite "$fixture" \
        || die "could not wire $fixture into tests/test_governance_scripts.py — the completeness test would be red; hand back to a builder"
done

# Installing a fixture MOVES files, and a binding naming a candidate path stops resolving the
# instant it does (D0141 at M2, D0199 at M3, D0245/D0246/D0248 in this driver's first
# rehearsal). retarget_bindings now moves them with the fixture; this is the backstop for any
# other shape of breakage. Asked as narrowly as it can be put, streamed.
binding_targets=$(grep -h -A1 'type: pytest' decisions/*.yaml \
    | grep 'target:' | sed 's/.*target: *//' | tr -d '"' | sort -u | wc -l)
waiting "checking the decision bindings still resolve — about $(( (binding_targets + 5) / 6 )) minutes ($binding_targets pytest bindings; output streams below, with still stretches between batches)"
bindings_log=$(mktemp -t tannen-bindings.XXXXXX)
if [ "$FAST" = 1 ]; then
    # SKIPPED WHOLE: there is no cheap half, and the one hatch that shortens it is RT-08.
    skipping_gate "check_decisions entirely — a fast run cannot say whether a binding broke"
    : > "$bindings_log"
else
    "$PY" -I -P scripts/check_decisions.py 2>&1 | tee "$bindings_log"
fi
broken=$(grep -E 'binding does not resolve — (target does not exist|not listed in MANIFEST)' "$bindings_log" || true)
rm -f "$bindings_log"
[ -z "$broken" ] || die "a decision binding stopped resolving when the fixtures moved:
$broken
  Retarget it to the installed tests/poison/ path — builder work on an unsigned record.
  Nothing has been signed; the fixtures stay installed and step 5 will skip them next run."

stop_after 5

# ---------------------------------------------------------------- 6. the custodian
say "Step 6 — the custodian itself (trust root; yours alone to apply)"
# THE DRAFT IS ASSEMBLED FROM WHAT STEP 5 INSTALLED, not shipped whole. The M3 copy installed a
# whole-file draft and had to warn: "if you declined the fixture there, decline here too, or hunk
# 1a will refuse the named fixture as NOT INSTALLED and step 7 will stop the sitting." A warning
# is the wrong shape for a dependency the driver can compute. Each fixture's poison line is a
# delimited hunk in $PROPOSALS_M4/custodian-hunks/, inserted only for an installed fixture, so a
# declined fixture cannot strand a line that refuses it — and the diff you read is exactly what
# lands. The whole-file custodian.sh beside this driver is the all-accepted assembly, for review.
build_custodian() {  # -> writes the candidate to "$SCRATCH/custodian.sh"; prints the hunks used
    python3 - "$SCRATCH/custodian.sh" "$PROPOSALS_M4/custodian-hunks" $FIXTURES <<'PY'
import pathlib, sys

out, hunk_dir, fixtures = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3:]
src = pathlib.Path("scripts/custodian.sh").read_text(encoding="utf-8")
# The anchor is the live line that opens the completeness pass (M3's hunk 1c), so every new
# poison line lands above the loop that checks each installed fixture was reached.
anchor = "# --- M3 DRAFT HUNK 1c (D0154 item 1; D0152 item 6; the derived half) ---------\n"
if src.count(anchor) != 1:
    sys.exit(f"scripts/custodian.sh: the completeness-pass anchor is not unique ({src.count(anchor)}) — assemble by hand")
used = []
for fx in fixtures:
    if not pathlib.Path("tests/poison", fx).is_dir():
        continue
    hunk = (hunk_dir / f"{fx}.sh").read_text(encoding="utf-8")
    if hunk in src:
        continue
    src = src.replace(anchor, hunk + anchor)
    used.append(fx)
out.write_text(src, encoding="utf-8")
print(" ".join(used))
PY
}
hunks_used=$(build_custodian) || die "could not assemble the custodian draft"
if [ -z "$hunks_used" ] || cmp -s scripts/custodian.sh "$SCRATCH/custodian.sh"; then
    note "every installed fixture already has its poison line — skipped"
else
    note "Read the whole diff. This file is the guard of the guards; every line you accept is"
    note "a line you are vouching for. Hunks assembled for: $hunks_used"
    pause "Enter for the diff (q quits the pager)..."
    diff -u scripts/custodian.sh "$SCRATCH/custodian.sh" | page
    if confirm "Install this custodian?"; then
        cp "$SCRATCH/custodian.sh" scripts/custodian.sh
        regen_manifest_row scripts/custodian.sh
        note "running it — every guard must FAIL its poison, for its own marker. The custody set"
        note "hashes and signature are the two expected failures until step 7."
        waiting "running the newly installed custodian — a few seconds"
        custodian_out=$(bash scripts/custodian.sh --check-only 2>&1); custodian_rc=$?
        printf '%s\n' "$custodian_out"
        if [ "$custodian_rc" -ne 0 ]; then
            unexpected=$(unexpected_failures "$custodian_out")
            [ -z "$unexpected" ] || die "custodian RED after the patch, for something step 7 will not fix:
$unexpected
  do not go further; this is the point of running it here"
            note "only the custody set is outstanding, as expected — every other check green"
        fi
    else
        note "declined — the installed fixtures stay unwatched by the floor, and the custodian's"
        note "completeness pass will say so at step 7."
    fi
fi

stop_after 6

# ---------------------------------------------------------------- 7. the custody set
say "Step 7 — sign the custody set (D0061: what MANIFEST.sha256 cannot be)"
note "The custody set is the stable subset — the guards, the trust root, the poison corpus —"
note "and signing it costs one signature per sitting. With step 11 deleted, it is THE one."
note "COST, so you accept it knowingly: after this, ANY edit to a listed path turns the"
note "gate red until the next sitting re-signs. That is the intended property for guards."
"$PY" -I -P scripts/gen_custody.py || die "custody generation failed"
if confirm "Review the custody set before signing it?"; then
    page governance/custody.sha256
fi
verify_owner governance/custody.sha256 tannen-custody \
    || sign_owner governance/custody.sha256 tannen-custody
note "the custodian again, now that the signature it requires exists — THIS is the run that"
note "validates steps 1-6, and nothing after it should be attempted if it is red"
bash scripts/custodian.sh --check-only \
    || die "custodian RED with the custody set signed — hand back to the builder; sign nothing further"

stop_after 7

# ---------------------------------------------------------------- 8. resolve the queue
say "Step 8 — the records this sitting resolves (ROADMAP.md §3, at any tier)"
# SELECTED BY STATUS, AT ANY TIER (D0217 item 3). The M3 copy tested `tier: C` before it read a
# status, so a Tier-A record recorded blocked-on-owner reached ROADMAP.md and never reached the
# ceremony that would discharge it — three of this queue's ten are exactly that.
#
# THE TWO TIERS ARE ACCEPTED DIFFERENTLY, and the difference is the constitution's, not this
# driver's. Tier C is a one-way door: accepted and signed as one act, rolled back if the
# signature fails (D0064). Tier A is reversible by definition (BRIEF §9.2); it needed the key only
# because its ARTIFACT is custody-set, and that act happened at the step that applied it. So a
# Tier-A record is accepted by flipping its status, and carries no signature — which also means
# its bindings stay upgradable by a builder afterwards without a re-signature (D0214's cost).
#
# BINDINGS ARE UPGRADED BEFORE A TIER-C RECORD IS SIGNED (D0214's recommendation). A signature
# covers the record's whole bytes, so the one window in which an earned upgrade is cheap is this
# one. Each upgrade in queue_upgrades.py is gated on its artifact having LANDED in this tree, so
# a declined step earns no upgrade.
note "Every record still recorded blocked-on-owner is a question this sitting was convened to"
note "answer. Accepting one is the affirmative act; leaving it blocked is also an answer, and it"
note "queues to the next sitting without stopping any work."
applied_by() {  # <record id> -> the APPLIED-BY lines, computed from what landed
    case "$1" in
        D0214) note "APPLIED-BY: its recommendation is this step (upgrade before signing); its nine"
               note "            upgrades on already-signed records are step 8b." ;;
        D0215) note "APPLIED-BY: step 4b — $(said_landed verdict-out)." ;;
        D0217) note "APPLIED-BY: items (1)(2) at step 4c — $(said_landed roadmap-wiring); item (3) is"
               note "            this step's own selection, which is how you are reading this." ;;
        D0228) note "APPLIED-BY: NOTHING, and nothing can be drafted: it asks YOU which bucket, which"
               note "            task-scoped credential, and the policy line. Accepting it authorises"
               note "            no write. Recommended: leave it blocked and answer it in conversation." ;;
        D0229) note "APPLIED-BY: (1) step 4d — $(said_landed delegations-marker); (2) step 1 —"
               note "            $(said_landed doorway); (3) step 5 — $(said_landed fixture:oracle-shadow-cross-file)"
               note "            and step 4e — $(said_landed readme-corrections); (4) step 4 —"
               note "            $(said_landed derived-tags); (5) step 3 — $(said_landed current-envelope)." ;;
        D0238) note "APPLIED-BY: answered by D0240's ruling, not by its own recommendation (a). Its"
               note "            artifacts are D0240's: step 2 and step 3." ;;
        D0240) note "APPLIED-BY: (1) step 2 — $(said_landed policy-sentence); (3) step 3 —"
               note "            $(said_landed current-envelope). (2), the CLI clamp, is DEFERRED to M5"
               note "            Session A by D0241 and nothing here lands it." ;;
        D0241) note "APPLIED-BY: nothing — it records a deferral and carries two drafts steps 2-3 applied." ;;
        D0242) note "APPLIED-BY: (2) steps 2-3; (3) landed as D0243 (a test file) and folded into"
               note "            check_manifest at step 3 — $(said_landed current-envelope)." ;;
        D0244) note "APPLIED-BY: (1) step 3 — $(said_landed current-envelope); (2) the red team ran"
               note "            (D0245, D0246); (3) step 3 rewrote D0243's strict node." ;;
        D0247) note "APPLIED-BY: the cp that installed this driver, and every step above. Its binding"
               note "            to scripts/boundary_sitting.sh holds once step 7 has signed these bytes." ;;
        D0248) note "APPLIED-BY: step 1 — $(said_landed doorway); its fixture at step 5 —"
               note "            $(said_landed fixture:doorway-network-residue). The superseding L4.9 is M5's." ;;
        D0249) note "APPLIED-BY: step 8c's gate and step 10's refusal — $(said_landed ledger)." ;;
        *)     note "APPLIED-BY: NOTHING in this sitting. A yes authorises future work only." ;;
    esac
}
queue=(); mapfile -t queue < <(ls -1 decisions/*.yaml | sort)   # array first: see sign_tier_c_records
for rec in "${queue[@]}"; do
    grep -q '^status: blocked-on-owner$' "$rec" || continue
    rec_id=$(sed -n 's/^id: *//p' "$rec" | head -1)
    rec_tier=$(sed -n 's/^tier: *//p' "$rec" | head -1)
    printf '\n'
    # Shown in full: a signature over bytes the signer was not shown is not consent (M3 step 8).
    note "$rec_id — Tier $rec_tier, $(wc -l < "$rec") lines, shown in full"
    page "$rec"
    applied_by "$rec_id"
    if confirm "Accept $rec_id (resolved by this sitting)?"; then
        :
    else
        note "left blocked — it stays in ROADMAP.md §3 for the next sitting"
        continue
    fi
    cp -- "$rec" "$SCRATCH/record.bak"
    # queue_upgrades.py prints one "upgraded: …" line per upgrade and the record's path LAST, or
    # "<id>: nothing landed …" alone. Compare the LAST line: the first spelling compared the whole
    # output, never matched, and kept every upgrade without showing the diff or asking — found
    # by the FAST accept rehearsal of 2026-09-13, where this prompt was asked zero times.
    if up=$(python3 "$PROPOSALS_M4/queue_upgrades.py" "$rec_id" 2>&1); then
        if [ "$(printf '%s\n' "$up" | tail -n 1)" = "$rec" ]; then
            printf '%s\n' "$up" | sed '$d'
            git --no-pager diff --no-index -- "$SCRATCH/record.bak" "$rec" | tail -n +3
            # Spelled positively so the agenda generator reads the decline arm as the cost of n.
            if confirm "Keep these binding upgrades on $rec_id (earned by what landed above)?"; then
                note "upgrades kept — they are part of the bytes accepted (and, at Tier C, signed) below"
            else
                cp -- "$SCRATCH/record.bak" "$rec"
                note "upgrades reverted; the record is accepted with the bindings it had"
            fi
        else
            note "$up"
        fi
    else
        cp -- "$SCRATCH/record.bak" "$rec"
        note "binding upgrades did not apply ($up) — the record is accepted with the bindings it had"
    fi
    if [ "$rec_tier" = "C" ]; then
        sign_owner_rollback "$rec" || cp -- "$SCRATCH/record.bak" "$rec"
    else
        sed -i 's/^status: blocked-on-owner$/status: accepted/' "$rec"
        note "accepted (Tier $rec_tier: a status flip; a reversible record carries no signature)"
    fi
done
sign_tier_c_records

stop_after 8

# ---------------------------------------------------------------- 8b. D0214's nine
say "Step 8b — nine binding upgrades that needed the key that had just left the room (D0214)"
note "The M3 sitting earned nine upgrades on five records it had already signed. A builder"
note "prepared, measured and reverted them: editing a signed record's bindings breaks its"
note "signature. Each is edit-then-re-sign, ONE RECORD AT A TIME, so a mistyped passphrase leaves"
note "at most one record to repair rather than five."
for rec_id in D0131 D0154 D0171 D0176 D0195; do
    if ! out=$(python3 "$PROPOSALS_M4/upgrade_binding.py" "$rec_id" 2>&1); then
        note "$rec_id: ${out##*: }"
        continue
    fi
    rec="$out"
    git --no-pager diff -- "$rec"
    if confirm "Keep $rec_id's upgrades and re-sign it?"; then
        sign_owner "$rec" tannen-decision
        if verify_owner "$rec" tannen-decision; then
            note "$rec_id verifies against its new bytes."
        else
            git checkout -- "$rec"
            die "$rec_id does not verify after re-signing, and the edit has been reverted.
  Its OLD signature is over the old bytes, so the restore should leave it valid — confirm
  with: ssh-keygen -Y verify -f allowed_signers -I owner@tannen -n tannen-decision \\
    -s $rec.sig < $rec
  Do not continue until it does; a signed Tier-C record that fails to verify is read as
  accepted-without-authority and is a red gate with no builder-side fix."
        fi
    else
        git checkout -- "$rec"
        note "reverted — $rec_id keeps bindings that understate their enforcement."
    fi
done
# Editing records restales DECISIONS.md; regenerate now so the next check does not report it.
"$PY" -I -P scripts/gen_projections.py >/dev/null \
    || note "projection regeneration failed — step 9 will try again"

stop_after 8b

# ---------------------------------------------------------------- 8c. the findings ledger
say "Step 8c — no standing finding goes unaccounted for (RT-M4-07, D0249)"
# THE QUEUE HAD NO SERVICE RATE (D0246 A3). RT-05, RT-07, RT-10/-11/-12, RT-M1-02 and RT-M1-04 sat
# "unchanged" across four boundaries and required_tags lagged a fifth time, because the norm that
# the finder does not fix (D0104) only works if SOME session does, and nothing measured whether
# any did. This sitting is the first to run under the gate it proposes: every finding id any red
# team has filed must carry a disposition in docs/redteam/LEDGER.yaml — closed by a record,
# scheduled with a place and a record, deferred with a reason and a boundary to revisit, or ruled a
# non-goal with its BRIEF citation — or the close tag is refused at step 10.
#
# The gate is INLINE, not a script it calls. It runs under your key's custody signature from the
# moment this driver is re-signed at step 7; a script elsewhere in the tree would be one more
# thing the floor vouches for by name and a builder edits freely. Promoting it into make verify is
# a later ruling (D0249). The id set is derived from the reports' structure — `## RT-… —` headings
# and `| RT-… |` table rows — which is what a report IS, not a state another artifact holds.
ledger_gate() {  # -> 0 when every finding is dispositioned; prints the problems or the account
    "$PY" -I -P - <<'LEDGER_GATE'
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
LEDGER_GATE
}
waiting "checking every red-team finding against docs/redteam/LEDGER.yaml — seconds"
if ledger_out=$(ledger_gate 2>&1); then
    note "every finding carries a disposition. The open ones, which you are about to vouch for"
    note "in the close tag's message:"
    printf '%s\n' "$ledger_out" | page
    # ASKED SO THAT y MEANS "STANDS". The first spelling asked "Edit the ledger?", so an
    # accept-everything rehearsal opened the editor on the ledger — and an owner answering y to
    # every prompt out of habit would land in an editor over the file they meant to vouch for.
    if confirm "These dispositions stand as drafted (n opens the ledger in your editor)?"; then
        note "the ledger stands as drafted; its hash goes into the close tag at step 10"
    else
        edit docs/redteam/LEDGER.yaml || note "editor exited non-zero — the re-check below is the ground truth"
        if ledger_gate >/dev/null 2>&1; then
            note "re-checked: still complete — the edited ledger's hash goes into the close tag"
        else
            note "re-checked: now INCOMPLETE — step 10 will refuse the close tag until it is fixed"
        fi
    fi
else
    printf '%s\n' "$ledger_out" | sed 's/^/     /'
    note "the ledger does NOT account for every finding. Step 10 will refuse the close tag."
    if confirm "Open the ledger now to disposition them?"; then
        edit docs/redteam/LEDGER.yaml || note "editor exited non-zero — the re-check below is the ground truth"
        if ledger_gate >/dev/null 2>&1; then
            note "re-checked: complete"
        else
            note "re-checked: still incomplete — the sitting continues, and step 10 will refuse"
        fi
    else
        note "left incomplete — step 9 proceeds, and step 10 refuses to close (RT-M4-07)"
    fi
fi

stop_after 8c

# ---------------------------------------------------------------- 9. gate, commit, receipt
say "Step 9 — regenerate, verify, commit, and take the attention receipt"
# THE RECEIPT IS TAKEN BEHIND THE COMMIT CONFIRM (D0201 ruling 4). The M3 copy ran the full
# custodian — which WRITES AND SIGNS receipts/<today>.md — three commands before asking whether
# to commit, so a declined commit left a signed receipt attesting to presence at a sitting that
# did not happen. The confirm moves EARLIER, not the receipt later: moved after the commit, the
# receipt would sit outside the commit the close tag names. Here it stays inside that commit and
# ahead of the tag, so D0071's receipt-then-tag argument is untouched and only receipt-versus-
# commit order changes.
#
# AND A SITTING THAT CHANGED NOTHING TAKES NO RECEIPT. The owner ruled the edge case on
# 2026-09-09: "a receipt needs an act". The dirty-tree test gates the receipt as well as the
# commit, so a no-op boundary lets the receipt clock go stale — intended, not incidental.
"$PY" -I -P scripts/gen_projections.py || die "projection generation failed"
"$PY" -I -P scripts/gen_roadmap.py >/dev/null || die "roadmap generation failed"
waiting "the full gate, over everything this sitting changed: $(verify_eta)"
if [ "$FAST" = 1 ]; then
    skipping_gate "make verify at step 9 — the custodian still runs, and it writes the receipt"
    bash scripts/custodian.sh --check-only || die "custody floor red at step 9"
else
    make verify || die "verify red — stop here and hand back to the builder; sign no tag over a red gate"
fi
if [ -n "$(git status --porcelain)" ]; then
    git status --short
    if confirm "Commit the sitting — this is also what takes your attention receipt?"; then
        note "full custodian run — writes and signs receipts/$(date +%F).md"
        bash scripts/custodian.sh || die "custodian red — no receipt was signed"
        make digest
        # The receipt is an input to DECISIONS.md's receipt line (D0215) and ROADMAP.md's sources.
        "$PY" -I -P scripts/gen_projections.py || die "projection generation failed after the receipt"
        "$PY" -I -P scripts/gen_roadmap.py >/dev/null || die "roadmap generation failed after the receipt"
        commit_with_hook_retry "$MILESTONE boundary sitting: the doorway guard, the spend preconditions, required_tags derived, the clock out of DECISIONS.md, three fixtures, custody set, receipt" \
            || die "the commit failed twice — fix the hook before tagging; $MILESTONE-close must attest a commit that CONTAINS this sitting"
    else
        note "declined — nothing committed and NO receipt taken (D0201 ruling 4). Step 10 will"
        note "refuse to tag over the uncommitted work."
    fi
else
    note "nothing to commit, so no receipt is taken: a receipt needs an act (D0201 ruling 4)."
fi

stop_after 9

# ---------------------------------------------------------------- 10. the close tag
say "Step 10 — sign $MILESTONE-close, LAST"
if git rev-parse -q --verify "refs/tags/$MILESTONE-close" >/dev/null; then
    note "$MILESTONE-close already exists — skipped"
else
    # A tag names a COMMIT, and its message quotes working-tree hashes, so a dirty tree would
    # attest bytes absent from the commit it names (D0051, RT-M2-06 D2).
    [ -z "$(git status --porcelain)" ] || die "the tree is not clean, so $MILESTONE-close would attest a commit that does not contain this sitting's work — and would quote working-tree hashes absent from it (D0051). Commit step 9 first, then re-run."
    # RT-M4-07: a sitting that cannot account for every standing finding does not close.
    ledger_account=$(ledger_gate 2>&1) || die "the findings ledger does not account for every red-team finding, so this sitting cannot close (RT-M4-07, D0249):
$ledger_account
  Disposition them in docs/redteam/LEDGER.yaml, commit, and re-run; nothing is signed yet."

    note "This is the tag D0049 says only you may mint. Its message quotes the delegation, the"
    note "custody set and — new at this boundary — the findings ledger you are vouching for."
    msg=$(mktemp)
    {
        echo "$MILESTONE close — owner-signed (D0047, D0049)."
        echo
        echo "Closes milestone $MILESTONE: the frozen law suite is green and every law"
        echo "carries fresh passing evidence for the current descriptors."
        echo
        echo "Standing delegation in force at this signature (D0051: authority-bearing"
        echo "tags quote the delegation's hash alongside its text):"
        echo "  DELEGATIONS.md sha256 = $(sha256sum DELEGATIONS.md | cut -d' ' -f1)"
        echo "  governance/custody.sha256 sha256 = $(sha256sum governance/custody.sha256 | cut -d' ' -f1)"
        echo
        echo "Findings accounted for at this signature (RT-M4-07, D0249):"
        echo "  docs/redteam/LEDGER.yaml sha256 = $(sha256sum docs/redteam/LEDGER.yaml | cut -d' ' -f1)"
        printf '%s\n' "$ledger_account" | sed 's/^/  /'
        echo
        cat DELEGATIONS.md
    } > "$msg"
    page "$msg"
    if confirm "Sign $MILESTONE-close with this message?"; then
        git -c gpg.format=ssh -c user.signingkey="$KEYREF" \
            tag -s "$MILESTONE-close" -F "$msg" || die "tag signing failed"
        git -c gpg.format=ssh -c gpg.ssh.allowedSignersFile="$PWD/allowed_signers" \
            verify-tag "$MILESTONE-close" || die "$MILESTONE-close does not verify"
        # THE CHECKS STEP 11 USED TO BUY WITH A THIRTY-MINUTE GATE, bought here in seconds. The tag
        # set is an input to two guards; nothing else the tag touches is in a tracked file once
        # D0215 has landed.
        waiting "the tag-signer rule and the custody floor, with the close tag in the tag set — seconds"
        "$PY" -I -P scripts/check_tag_signers.py || die "check_tag_signers red with $MILESTONE-close minted"
        bash scripts/custodian.sh --check-only || die "custody floor red with $MILESTONE-close minted"
    else
        note "declined — no close tag. The sitting's commit and receipt stand; re-run to close."
    fi
    rm -f "$msg"
fi

stop_after 10

# ---------------------------------------------------------------- 11. fallback only
say "Step 11 — only if the clock verdict is still in DECISIONS.md"
# DELETED BY D0205 AND D0215, KEPT AS A FALLBACK. The M3 copy's step 11 did two things: added
# the tags this milestone minted to a hand-maintained required_tags (D0205 derives them; declined,
# step 4 already offered m4-laws-freeze under step 7's signature and m4-close lags one boundary),
# and regenerated DECISIONS.md after the tag because its attention-receipt line reads the tag set
# (D0215 removes that line; declined, the projection is stale the moment step 10 mints, and the
# tip is red until a commit regenerates it). Only the second can still be needed, and it needs
# no signature: a regeneration, and a commit whose hooks re-run check_decisions.
if landed verdict-out; then
    note "not needed — required_tags is derived or was set at step 4, and DECISIONS.md carries"
    note "nothing the tag set can change (D0205, D0215). No commit, no gate, no signature."
else
    "$PY" -I -P scripts/gen_projections.py || die "projection generation failed"
    if [ -n "$(git status --porcelain)" ]; then
        commit_with_hook_retry "$MILESTONE close: DECISIONS.md regenerated after the close tag (D0215 declined)" \
            || die "the projection commit failed twice — the tip stays red until it lands"
    fi
fi

stop_after 11

say "The sitting is closed"
note "Signed this sitting: the Tier-C records you accepted, governance/policy.yaml,"
note "governance/custody.sha256, the attention receipt, and $MILESTONE-close."
note ""
note "The receipt clock is now RUNNING: $MILESTONE-close is a boundary tag dated today, so"
note "Tier-B silence-as-consent lapses seven days from it unless a fresh receipt lands."
note ""
note "Owed elsewhere, not by this sitting: M5 Session A — the superseding L4.9 that derives from"
note "step 1's guard, and the CLI clamp with its successor law (D0241). The pre-budget sitting —"
note "RT-M4-01, and a FRESH spend namespace with the first nonzero ceiling (D0246 A5)."
note ""
note "Builder follow-ups (Tier A, no signature): upgrade the bindings on the Tier-A records"
note "accepted above, and open ${NEXT_MILESTONE^^} Session A in a fresh session, in a new worktree."
