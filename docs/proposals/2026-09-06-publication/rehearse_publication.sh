#!/usr/bin/env bash
# rehearse_publication.sh — run publication_sitting.sh END TO END, with no human and without
# the owner's key, against a disposable clone of this repo. Modelled on
# scripts/rehearse_sitting.sh, which does the same for the boundary driver. (D0183)
#
# WHY THIS EXISTS. The publication driver rewrites every commit, re-signs all eight tags
# including the trust root, and spends the receipt chain's no-rewrite guarantee — and until
# 2026-09-06 it had only ever been NARRATED (`--dry-run`, D0182), never executed. D0068:
# three consecutive M0->M1 sittings stopped on defects one end-to-end run would have found in
# seconds, each spending the owner's attention. Reading this driver against the guards found
# eight more (D0183 §1); this harness is what confirms each fix and finds the ones reading
# missed.
#
# WHAT A GREEN RUN PROVES: step order, quoting, every patch applying, every manifest row
# refreshed, the rewrite, the re-tagging at original dates, the attestation, and that the
# sitting arrives at a green `make verify` on the REWRITTEN history with nothing uncommitted.
#
# WHAT IT CANNOT PROVE: custody. The clone enrols a THROWAWAY owner key; the real key is
# passphrase-protected and unattended signing is exactly what that passphrase exists to
# prevent. The signatures a rehearsal produces are structurally correct and attest to
# nothing. Read a green run as "the mechanism works", never as "the sitting happened". It
# also cannot rehearse GitHub: `gh repo create` and the push stay narration in the driver.
#
# NOTHING HERE TOUCHES THE REAL REPO. Its only access is `git clone` and a read-only
# `git diff`; the driver's own rewrite clone ($TANNEN_REWRITE_WORK) is placed INSIDE this
# harness's temporary directory. The verdict re-checks that the real repo's HEAD and status
# are what they were, as a positive control on that claim.
#
#   rehearse_publication.sh                 # HEAD + uncommitted work: what the owner is
#                                           # about to run. Must be green.
#   rehearse_publication.sh --from head     # the committed tree only (negative control:
#                                           # TANNEN_REHEARSE_DRIVER=<old driver>)
#   rehearse_publication.sh --keep          # keep the clone and the rewrite for inspection
#   rehearse_publication.sh --abort-at N    # answer n to the Nth prompt instead of y, and
#                                           # judge what an ABORTED sitting leaves behind
#
# WHY --abort-at EXISTS. Every prompt above is answered y, so the one path the owner most
# wants rehearsed — something looks wrong in the irreversible middle, they answer n — was
# the one path never executed. Each `confirm` failure is `die`, which is `exit 1` with no
# trap and no rollback, so "is that recoverable?" was a question answered by reading the
# driver rather than by running it. It is not any more. With TANNEN_SITTING_FAST=1 an abort
# run costs about a minute. N is a prompt index, and the verdict asserts WHICH step it
# landed on — a wrong index fails loudly instead of passing on the wrong abort.
#
# Environment: TANNEN_REHEARSE_DRIVER overlays some other driver (how the harness is tested
# against its own history — `git show <sha>:…/publication_sitting.sh > old.sh`);
# TANNEN_BUILDER_KEY defaults to ~/.ssh/tannen_builder (unattended; no passphrase);
# TMPDIR defaults to /var/tmp — the clone, two venvs and a rewrite need disk, not tmpfs.
set -euo pipefail
ROOT="${TANNEN_REHEARSE_ROOT:-$(cd "$(dirname "$0")/../../.." && pwd)}"
cd "$ROOT"
PKG="docs/proposals/2026-09-06-publication"

MODE=worktree KEEP=0 ABORT_AT=0 ABORT_STEP="${TANNEN_ABORT_STEP:-6}"
while [ $# -gt 0 ]; do
    case "$1" in
        --from) MODE="$2"; shift 2 ;;
        --keep) KEEP=1; shift ;;
        --abort-at) ABORT_AT="$2"; shift 2 ;;
        *) echo "usage: $0 [--from head|worktree] [--keep] [--abort-at N]" >&2; exit 2 ;;
    esac
done
case "$ABORT_AT" in ''|*[!0-9]*) echo "--abort-at takes a prompt index" >&2; exit 2 ;; esac
case "$MODE" in head|worktree) ;; *) echo "--from must be head or worktree" >&2; exit 2 ;; esac

say()  { printf '\n\033[1m-- %s\033[0m\n' "$*"; }
note() { printf '   %s\n' "$*"; }

T0=$SECONDS
WORK=$(mktemp -d "${TMPDIR:-/var/tmp}/tannen-pubrehearsal-XXXXXX")
CLONE="$WORK/repo"
RW="$WORK/rw"                        # the driver's $TANNEN_REWRITE_WORK
SITTING="$WORK/sitting"              # the driver's $TANNEN_SITTING_SCRATCH
STEPFILE="$SITTING/steps"            # ...and the breadcrumb it appends a step to
LOG="$WORK/transcript.txt"
STAMPED="$WORK/transcript.stamped"   # same lines, each prefixed with elapsed seconds
SILENCE_LIMIT=25                     # seconds the driver may be quiet without saying so
cleanup() { [ "$KEEP" = 1 ] || rm -rf "$WORK"; }
trap cleanup EXIT

# The isolation claim is verified at the end, so record the real repo's state first.
# Tracked files, plus untracked ones outside the directories a builder drafts in while a
# three-hour run is going (docs/, decisions/, digest/): the driver never legitimately writes
# under the real root at all, and this is the positive control on that.
ROOT_HEAD_BEFORE=$(git rev-parse HEAD)
root_state() { git -C "$ROOT" status --porcelain --untracked-files=no
               git -C "$ROOT" ls-files --others --exclude-standard | grep -vE '^(docs|decisions|digest)/' || true; }
ROOT_STATUS_BEFORE=$(root_state)

say "Building a disposable clone at $CLONE (mode: $MODE)"
git clone --quiet --no-hardlinks "$ROOT" "$CLONE"
git -C "$CLONE" config user.name  "rehearsal"
git -C "$CLONE" config user.email "rehearsal@invalid"
git -C "$CLONE" config commit.gpgsign false
# The real repository has a master branch; a clone of a WORKTREE does not. Create it so
# the fixture exercises the same path the owner will (D0186): an earlier publish-shape
# fix was harmless on the create-branch path and would have deleted the owner's milestone
# branch on the master-exists path, and this clone could not tell the two apart.
git -C "$CLONE" branch master HEAD 2>/dev/null && :
git -C "$CLONE" config tag.gpgsign false
note "cloned $(git -C "$CLONE" rev-parse --short HEAD) with $(git -C "$CLONE" tag | wc -l) tag(s)"

if [ "$MODE" = worktree ]; then
    # The owner's real run starts from the tree as it stands, so the rehearsal does too.
    # --binary carries any patch files; --exclude-standard keeps .venv and other ignored
    # noise out.
    git -C "$ROOT" diff HEAD --binary > "$WORK/worktree.patch"
    if [ -s "$WORK/worktree.patch" ]; then
        git -C "$CLONE" apply --index "$WORK/worktree.patch"
        note "applied $(git -C "$CLONE" diff --cached --stat | tail -1 | sed 's/^ *//')"
    fi
    while IFS= read -r -d '' f; do
        mkdir -p "$CLONE/$(dirname "$f")"
        cp -a "$ROOT/$f" "$CLONE/$f"
    done < <(git -C "$ROOT" ls-files --others --exclude-standard -z)
fi

# The artifact under test is the driver as it stands NOW, or the one named in
# TANNEN_REHEARSE_DRIVER. The driver is not custody-set (it lives under docs/proposals/),
# so unlike rehearse_sitting.sh there is no ordering hazard around gen_custody here.
DRIVER="${TANNEN_REHEARSE_DRIVER:-$ROOT/$PKG/publication_sitting.sh}"
[ -f "$DRIVER" ] || { echo "no driver at $DRIVER" >&2; exit 1; }
cp -a "$DRIVER" "$CLONE/$PKG/publication_sitting.sh"
if [ -n "${TANNEN_REHEARSE_DRIVER:-}" ]; then
    note "driver under test: $DRIVER (OVERRIDDEN — not the working tree)"
elif git -C "$ROOT" diff --quiet HEAD -- "$PKG/publication_sitting.sh"; then
    note "driver under test: $PKG/publication_sitting.sh, unmodified since HEAD"
else
    note "driver under test: $PKG/publication_sitting.sh from the WORKING TREE (differs from HEAD)"
fi

say "Minting a throwaway owner key (the real one is passphrase-protected, by design)"
KEY="$WORK/rehearsal_owner"
ssh-keygen -q -t ed25519 -N '' -C rehearsal-owner@invalid -f "$KEY"
# APPENDED, never substituted: the real owner and builder public halves must stay enrolled
# or brief-freeze and the four close/freeze tags stop verifying before the driver has done
# anything. Two principals may share a name in allowed_signers; verify succeeds if any line
# for that principal matches.
printf 'owner@tannen %s\n' "$(cut -d' ' -f1,2 "$KEY.pub")" >> "$CLONE/allowed_signers"
note "enrolled $(ssh-keygen -lf "$KEY.pub" | awk '{print $2}') as a second owner@tannen"

say "Making the fixture's own edit consistent (allowed_signers is frozen and in custody)"
( cd "$CLONE"
  grep -v '  allowed_signers$' MANIFEST.sha256 > MANIFEST.tmp
  sha256sum allowed_signers >> MANIFEST.tmp
  mv MANIFEST.tmp MANIFEST.sha256 )

say "Syncing the clone's venv (the gate runs .venv/bin/python at a literal path)"
( cd "$CLONE" && uv sync --frozen --quiet )
( cd "$CLONE" && .venv/bin/python -I -P scripts/gen_custody.py >/dev/null )
# custody.sha256's bytes just moved (allowed_signers' hash), so the real owner's signature
# over the OLD bytes no longer verifies. Re-sign with the throwaway — the key everything
# else in this rehearsal signs with — so the fixture's own setup does not manufacture a
# failure indistinguishable from a real one (rehearse_sitting.sh, same reasoning).
( cd "$CLONE" && rm -f governance/custody.sha256.sig
  ssh-keygen -Y sign -f "$KEY" -n tannen-custody governance/custody.sha256 >/dev/null )
# allowed_signers is an input to the DECISIONS.md freshness hash, so the projection restales.
( cd "$CLONE" && .venv/bin/python -I -P scripts/gen_projections.py >/dev/null )
# A sitting starts from a committed repo, and the fixture's edits must not masquerade as
# sitting work: commit them (hooks not yet armed — this is fixture, not the thing under
# test, and check-decisions alone is ~20 minutes).
( cd "$CLONE" && git add -A && git commit -q -m "rehearsal fixture: enrol a throwaway owner key" )
note "fixture committed as $(git -C "$CLONE" rev-parse --short HEAD)"
if ( cd "$CLONE" && .venv/bin/pre-commit install --install-hooks >/dev/null 2>&1 ); then
    note "pre-commit hooks armed in the clone"
else
    note "WARNING: pre-commit hooks NOT installed — the commit steps run unguarded, so a"
    note "hook failure at the real sitting would not show up here. Fix before trusting a pass."
fi

# Post-conditions are judged against what THIS run changed (rehearse_sitting.sh, D0120):
# snapshot the tags and receipts the clone starts with.
: > "$WORK/tags_before.txt"
for t in $(git -C "$CLONE" tag); do
    printf '%s\t%s\t%s\t%s\n' "$t" "$(git -C "$CLONE" rev-parse "$t")" \
        "$(git -C "$CLONE" rev-list -n1 "$t")" \
        "$(git -C "$CLONE" for-each-ref "refs/tags/$t" --format='%(taggerdate:iso-strict)')" \
        >> "$WORK/tags_before.txt"
done
RECEIPTS_BEFORE=" $(cd "$CLONE" && ls receipts/ 2>/dev/null | tr '\n' ' ')"
COMMITS_BEFORE=$(git -C "$CLONE" rev-list --all --count)
CLONE_BRANCH_BEFORE=$(git -C "$CLONE" rev-parse --abbrev-ref HEAD)
CLONE_HEAD_BEFORE=$(git -C "$CLONE" rev-parse HEAD)
# The strings the sitting must remove from HISTORY, read off the record before the driver
# withdraws it — so this file never has to carry them, which would defeat the check the
# moment the harness itself is committed.
mapfile -t NEEDLES < <(git -C "$CLONE" show HEAD:concepts/provenance-ref-grammar.yaml \
    | "$CLONE/.venv/bin/python" -c '
import sys, yaml
r = yaml.safe_load(sys.stdin)
for s in r["sources"]:
    if "renavon" in s["repo"].lower():
        print(s["section"]); print(s["commit"]); print(s["snapshot"]["sha256"])
')
note "${#NEEDLES[@]} strings must leave the history (read from the record, not written here)"

if [ "$ABORT_AT" -gt 0 ]; then
    say "Running the driver — n to prompt #$ABORT_AT (expected: step $ABORT_STEP), y to the rest"
else
    say "Running the driver — y to every prompt, transcript at $LOG"
fi
# Answers come from a FILE, not from `yes |`: a pipe that outlives the driver dies of
# SIGPIPE, and under pipefail that becomes the pipeline's status (rehearse_sitting.sh).
# bash prints a `read -p` prompt only when stdin is a terminal, so nothing marks the
# prompts in the transcript: the verdict identifies the abort by the last STEP header
# instead, which is printed unconditionally.
awk -v n="$ABORT_AT" 'BEGIN { for (i = 1; i <= 2000; i++) print (i == n ? "n" : "y") }' > "$WORK/answers"
stamp() {   # stdin -> stdout unchanged; a copy with elapsed seconds to $1 (D0069)
    local line start=$SECONDS
    : > "$1"
    while IFS= read -r line || [ -n "$line" ]; do
        printf '%d\t%s\n' "$((SECONDS - start))" "$line" >> "$1"
        printf '%s\n' "$line"
    done
}
T_DRIVER=$SECONDS
set +e
( cd "$CLONE" && env \
    SSH_AUTH_SOCK= \
    TANNEN_OWNER_KEY="$KEY" \
    TANNEN_BUILDER_KEY="${TANNEN_BUILDER_KEY:-$HOME/.ssh/tannen_builder}" \
    TANNEN_REWRITE_WORK="$RW" \
    TANNEN_SITTING_SCRATCH="$SITTING" \
    PAGER=cat \
    TERM=dumb \
    bash "$PKG/publication_sitting.sh" ) < "$WORK/answers" 2>&1 \
    | stamp "$STAMPED" > "$LOG"
DRIVER_RC=${PIPESTATUS[0]}   # the NEXT line after the pipeline, always: an assignment
set -e                       # in between would replace PIPESTATUS with its own status
note "driver exited $DRIVER_RC after $(wc -l < "$LOG") lines and $(( (SECONDS - T_DRIVER) / 60 )) min"

# ------------------------------------------------------------------ verdict
# Each check is what a green sitting MUST leave behind, phrased so that a failure names the
# thing that is missing rather than the check that noticed. Cheap guards are RE-RUN here;
# the 45-minute gate (`make verify` on the rewritten history) is the driver's own step 9,
# and it is trusted through the driver's exit status — the driver dies if it is red.
[ "$ABORT_AT" -gt 0 ] || say "Verdict"
FAILED=0
check() {  # <description> <command...>
    local desc="$1"; shift
    if "$@" >/dev/null 2>&1; then printf '   \033[32mok\033[0m   %s\n' "$desc"
    else printf '   \033[31mFAIL\033[0m %s\n' "$desc"; FAILED=$((FAILED + 1)); fi
}
in_rw()    { ( cd "$RW" && "$@" ); }
in_clone() { ( cd "$CLONE" && "$@" ); }
absent()   { ! grep -q "$1" "$2"; }
equal()    { [ "$1" = "$2" ]; }
empty()    { [ -z "$("$@" 2>/dev/null)" ]; }
verify_tag() { in_rw git -c gpg.format=ssh -c gpg.ssh.allowedSignersFile="$RW/allowed_signers" verify-tag "$1"; }
tag_date_unchanged() {
    local before now
    before=$(awk -F'\t' -v t="$1" '$1==t {print $4}' "$WORK/tags_before.txt")
    now=$(in_rw git for-each-ref "refs/tags/$1" --format='%(taggerdate:iso-strict)')
    [ -n "$before" ] && [ "$before" = "$now" ]
}
silences() {
    awk -v limit="$SILENCE_LIMIT" '
        {
            t = $0 + 0
            line = substr($0, index($0, "\t") + 1)
            if (NR > 1 && !armed && t - pt > limit)
                printf "%3ds of silence after: %s\n", t - pt, pl
            if (line ~ /== /)          armed = 0
            if (line ~ /\[waiting\]/) armed = 1
            pt = t; pl = line
        }' "$1"
}
speaks_up() { [ -z "$(silences "$1")" ]; }
# The isolation check compares a snapshot taken BEFORE the driver ran with one taken after,
# so ANY edit to the worktree during the run — including the operator's own, in another
# window — shows up as a failure that reads like the driver wrote into the real repository.
# It has already been misread once. Name the difference rather than leaving it to be guessed.
root_state_diff() {
    local now; now=$(root_state)
    [ "$ROOT_STATUS_BEFORE" = "$now" ] && return 0
    note "what differs (before -> after). If you edited the tree while this ran, it is you:"
    diff <(printf '%s\n' "$ROOT_STATUS_BEFORE") <(printf '%s\n' "$now") | sed 's/^/     /' | head -20
    note "the driver never writes under $ROOT; HEAD is checked separately and above."
}

present() { grep -q "$1" "$2"; }
# Which step a run reached is the DRIVER's fact, so the driver states it: say() appends
# every header it prints to $TANNEN_SITTING_SCRATCH/steps, and this reads the last one that
# names a step. The first spelling of this scraped the transcript for the header text, which
# is a second copy of the driver's step vocabulary living out here — BRIEF §2's
# duplication-is-drift, and D0183 finding (m) in miniature. It also had teeth: the pattern
# was wrong, grep matched nothing, and under `set -euo pipefail` the failing substitution
# killed the harness mid-verdict instead of failing one check. Hence `|| true` at every bare
# substitution below, and a check that the breadcrumb had anything in it at all.
last_step() { awk '/^Step /{last=$2} END{print last}' "$STEPFILE" 2>/dev/null; }
reached_step() { awk -v s="$1" '$1=="Step" && $2==s {f=1} END{exit !f}' "$STEPFILE" 2>/dev/null; }

if [ "$ABORT_AT" -gt 0 ]; then
    say "Verdict — an ABORTED sitting: n at prompt #$ABORT_AT"
    LAST_STEP=$(last_step || true)
    note "last step the driver recorded: ${LAST_STEP:-<none>} (expected $ABORT_STEP)"
    check "the driver left a step breadcrumb at all"                   test -s "$STEPFILE"
    check "the repo is still on its own branch, not master"            equal "$(in_clone git rev-parse --abbrev-ref HEAD)" "$CLONE_BRANCH_BEFORE"
    check "and that branch still exists"                               in_clone git rev-parse -q --verify "$CLONE_BRANCH_BEFORE"
    check "the driver refused to continue (exit 1, not a completion)"  test "$DRIVER_RC" -eq 1
    check "and said so, rather than dying silently"                    present 'publication: STOP' "$LOG"
    check "the abort landed on step $ABORT_STEP"                       equal "$LAST_STEP" "$ABORT_STEP"
    # Isolation still holds on the abort path — the same positive control as a green run.
    check "the real repo's HEAD is untouched"     equal "$ROOT_HEAD_BEFORE" "$(git -C "$ROOT" rev-parse HEAD)"
    check "the real repo's working tree is untouched" equal "$ROOT_STATUS_BEFORE" "$(root_state)"
    root_state_diff
root_state_diff   # names what changed, if anything: a bare FAIL here reads as a driver bug
    # What the abort leaves in the repo the owner is actually sitting in.
    # TWO REGIMES, and the negative control is what found the second one. Before step A the
    # sitting has applied patches but committed nothing, so the tree is DIRTY and the custody
    # floor is RED — scripts/custodian.sh is patched and custody.sha256 is not re-signed until
    # step G. That is the correct outcome, not a defect, and asserting cleanliness there would
    # report a working abort as breakage. The recovery differs too, so each is checked on its
    # own terms and performed rather than described.
    if reached_step A; then
        REGIME="after the sitting's first commit"
        check "nothing was left uncommitted in the sitting's own clone" test -z "$(in_clone git status --porcelain)"
        check "the sitting's pre-rewrite commit is HEAD, and it is the only one added" \
            equal "$(in_clone git rev-list --all --count)" "$((COMMITS_BEFORE + 1))"
        check "and its parent is the state the driver started from" \
            equal "$(in_clone git rev-parse HEAD^)" "$CLONE_HEAD_BEFORE"
    else
        REGIME="before the sitting's first commit"
        check "no commit was added, since step A was never reached" \
            equal "$(in_clone git rev-list --all --count)" "$COMMITS_BEFORE"
        check "the tree is dirty, as an abort before the first commit must leave it" \
            test -n "$(in_clone git status --porcelain)"
    fi
    note "regime: $REGIME"
    # The claim the whole abort question turns on: the repo was never rewritten, only the
    # throwaway clone was. Checked per tag rather than in aggregate, so a failure names one.
    while IFS=$'\t' read -r t obj cmt _date; do
        check "tag $t still points where it did (no rewrite reached the repo)" \
            equal "$(in_clone git rev-parse "$t")" "$obj"
        check "tag $t still verifies in the repo" bash -c \
            "cd '$CLONE' && git -c gpg.format=ssh -c gpg.ssh.allowedSignersFile=allowed_signers verify-tag '$t'"
    done < "$WORK/tags_before.txt"
    check "no rewrite attestation was written" bash -c "! ls '$CLONE'/receipts/REWRITE-*.md >/dev/null 2>&1"
    # And the stopping point is coherent, not merely intact. check_decisions is omitted on
    # purpose: it runs a pytest per binding (~20 min) and would make an abort rehearsal cost
    # as much as the sitting. That is a stated gap in this run, not a claim about the guard.
    if reached_step A; then
        for g in check_manifest check_concepts check_tag_signers check_receipts check_laws; do
            check "$g is green at the stopping point" in_clone .venv/bin/python -I -P "scripts/$g.py"
        done
        check "the custodian is green at the stopping point, with no tolerances" \
            in_clone bash scripts/custodian.sh --check-only
    else
        check "the custody floor is RED at the stopping point, as an applied-but-unsigned patch must leave it" \
            bash -c "! ( cd '$CLONE' && bash scripts/custodian.sh --check-only >/dev/null 2>&1 )"
    fi
    # The rewrite clone: disposable by construction, and the recovery is performed here
    # rather than described, because "just rm -rf it" is exactly the kind of claim this
    # harness exists to stop taking on trust.
    if [ -d "$RW/.git" ]; then
        note "rewrite clone present at $RW ($(in_rw git rev-list --all --count) commits)"
        check "the rewrite clone is outside the real repo" bash -c \
            "case '$RW' in '$ROOT'/*) exit 1 ;; *) exit 0 ;; esac"
        check "nothing in the repo references it"          empty in_clone git grep -l -- "$RW"
    else
        note "no rewrite clone: the abort came before step 5"
    fi
    say "Recovery, performed"
    # The recovery IS the deletion, so it is performed either way — but under --keep the
    # rewrite is moved aside rather than destroyed, or the flag would delete the very thing
    # it exists to let you inspect. $RW is gone from where the driver left it in both cases,
    # which is what the check below actually asserts.
    if [ "$KEEP" = 1 ]; then mv "$RW" "$WORK/rw-before-recovery" && note "rewrite kept at $WORK/rw-before-recovery"
    else rm -rf "$RW"; fi
    if ! reached_step A; then
        note "before step A the recovery is an undo, not a deletion: git checkout -- . && git clean -fd"
        ( cd "$CLONE" && git checkout -- . && git clean -fdq ) || true
        check "after the undo the tree is clean again" test -z "$(in_clone git status --porcelain)"
    fi
    check "after recovery the repo's custody floor is green" \
        in_clone bash scripts/custodian.sh --check-only
    check "and the real repo is still untouched" equal "$ROOT_HEAD_BEFORE" "$(git -C "$ROOT" rev-parse HEAD)"
    say "Unexpected failure lines in the transcript (the STOP itself is expected)"
    awk '
      /fails its poison as required/ { next }
      /publication: STOP/            { next }
      /^[+-]/ { next }
      /^ .*(printf|echo|bad\(\))/ { next }
      /: FAIL|FAILED|Traceback|command not found|No such file|Error [0-9]|error:|fatal:/ {
          printf "%d:%s\n", NR, $0
      }' "$LOG" | head -40
    say "Transcript: $LOG (timed copy: $STAMPED)"
    note "total $(( (SECONDS - T0) / 60 )) min"
    [ "$KEEP" = 1 ] && note "kept: clone $CLONE" || note "(--keep to inspect the clone)"
    if [ "$FAILED" -eq 0 ]; then
        printf '\n\033[32mabort rehearsal: n stops the sitting at a coherent, reversible point\033[0m\n'
        if reached_step A; then
            printf 'the repo keeps the pre-rewrite commit, clean and green; the rewrite was only ever\nin a temp clone\n'
        else
            printf 'nothing was committed and nothing was rewritten; the applied patches undo with\ngit checkout -- . && git clean -fd, which this run performed\n'
        fi
        exit 0
    fi
    printf '\n\033[31mabort rehearsal: %d check(s) failed\033[0m\n' "$FAILED"
    exit 1
fi

check "the driver ran to completion (exit 0)"            test "$DRIVER_RC" -eq 0
check "the sitting left the repo on its own branch, not master" \
    equal "$(in_clone git rev-parse --abbrev-ref HEAD)" "$CLONE_BRANCH_BEFORE"
check "and did not delete it"  in_clone git rev-parse -q --verify "$CLONE_BRANCH_BEFORE"
check "and recorded every step through the last one"     equal "$(awk 'END{print}' "$STEPFILE" 2>/dev/null || true)" "The sitting is closed"
check "no step aborted the sitting"                      absent 'publication: STOP' "$LOG"
check "no silence over ${SILENCE_LIMIT}s went unannounced"     speaks_up "$STAMPED"
# Isolation, as a positive control rather than a promise.
check "the real repo's HEAD is untouched"                equal "$ROOT_HEAD_BEFORE" "$(git -C "$ROOT" rev-parse HEAD)"
check "the real repo's working tree is untouched"        equal "$ROOT_STATUS_BEFORE" "$(root_state)"
check "the rewrite happened in $RW"                      test -d "$RW/.git"
if [ -d "$RW/.git" ]; then
    check "no commit lost to the rewrite (the sitting adds one before it, one after)" \
        test "$(in_rw git rev-list --all --count)" -ge "$COMMITS_BEFORE"
    while IFS=$'\t' read -r t _obj _cmt _date; do
        check "tag $t exists in the rewritten history"   in_rw git rev-parse -q --verify "refs/tags/$t"
        check "tag $t verifies against allowed_signers"  verify_tag "$t"
        check "tag $t keeps its original tagger date"    tag_date_unchanged "$t"
    done < "$WORK/tags_before.txt"
    check "check_tag_signers is green on the rewritten history" in_rw .venv/bin/python -I -P scripts/check_tag_signers.py
    check "trust_root.object is the re-signed brief-freeze tag object" equal \
        "$(in_rw awk '/^trust_root:/{f=1} f && /object:/{print $2; exit}' governance/tag-roles.yaml)" \
        "$(in_rw git rev-parse brief-freeze)"
    check "no sibling snapshot path survives in ANY commit of ANY ref" empty bash -c \
        "cd '$RW' && git log --all --name-only --format= -- concepts/snapshots | sort -u | grep -v '^concepts/snapshots/semiring-relations/' | grep -v '^\$'"
    for needle in "${NEEDLES[@]}"; do
        check "withdrawn string (${#needle} chars) is in NO commit of ANY ref, any path" empty \
            in_rw git log --all --format=%h -S "$needle"
    done
    check "and the three needles were non-empty (the check had an input set)" test "${#NEEDLES[@]}" -eq 3
    check "a rewrite attestation exists"                 bash -c "ls '$RW'/receipts/REWRITE-*.md >/dev/null 2>&1"
    check "and its signature verifies under tannen-rewrite" bash -c \
        "cd '$RW' && for a in receipts/REWRITE-*.md; do ssh-keygen -Y verify -f allowed_signers -I owner@tannen -n tannen-rewrite -s \"\$a.sig\" < \"\$a\" || exit 1; done"
    check "check_receipts resolves the chain through the attestation" bash -c \
        "cd '$RW' && .venv/bin/python -I -P scripts/check_receipts.py | grep -q remapped"
    check "check_receipts is green"                      in_rw .venv/bin/python -I -P scripts/check_receipts.py
    check "check_manifest is green (frozen rows refreshed, custody signed)" in_rw .venv/bin/python -I -P scripts/check_manifest.py
    check "check_concepts is green and counts pin-only citations" bash -c \
        "cd '$RW' && .venv/bin/python -I -P scripts/check_concepts.py | grep -q 'by pin'"
    check "the custodian is green with no tolerances"    in_rw bash scripts/custodian.sh --check-only
    check "brief_row fidelity: 8/8 with the divergence declared" bash -c \
        "cd '$RW' && .venv/bin/python -I -P $PKG/probes/brief_row_fidelity.py | grep -q 'tooth 2 (owner set matches sources\[\].repo): 8/8 ok'"
    PINS_MEASURED=$(in_rw bash -c "grep -rh '      path: concepts/snapshots/' concepts/*.yaml | sort -u | wc -l")
    PINS_POLICY=$(in_rw awk '/expected_citation_pins:/{print $2; exit}' governance/policy.yaml)
    check "expected_citation_pins ($PINS_POLICY) equals the measured pin count ($PINS_MEASURED)" equal "$PINS_POLICY" "$PINS_MEASURED"
    check "nothing was left uncommitted in the rewritten clone" test -z "$(in_rw git status --porcelain)"
    check "the rewritten clone carries exactly one branch" \
        equal "$(in_rw git for-each-ref --format=%\(refname\) refs/heads | wc -l)" "1"
    check "and that branch is master, so the public default is master" \
        equal "$(in_rw git rev-parse --abbrev-ref HEAD)" "master"
    NEW_RECEIPT=""
    for _r in "$CLONE"/receipts/*.md; do
        [ -e "$_r" ] || continue
        case "$RECEIPTS_BEFORE" in *" $(basename "$_r") "*) continue ;; esac
        case "$_r" in *REWRITE-*) continue ;; esac
        NEW_RECEIPT="$_r"; break
    done
    check "this sitting took a fresh attention receipt (pre-rewrite)" test -n "$NEW_RECEIPT"
    check "and signed it"                                test -f "$NEW_RECEIPT.sig"
    check "nothing was left uncommitted in the pre-rewrite clone" test -z "$(in_clone git status --porcelain)"
    note "residue, measured not asserted: $(in_rw bash -c "git grep -ic renavon | awk -F: '{s+=\$2} END {print s\" hits in \"NR\" files\"}'")"
fi

if ! speaks_up "$STAMPED"; then
    say "Silences the owner would read as a hang"
    silences "$STAMPED"
    note "announce each with waiting() in the driver, or fix whatever made it slow"
fi

say "Unexpected failure lines in the transcript (empty is the goal)"
awk '
  /fails its poison as required/ { next }
  /^[+-]/ { next }                         # unified-diff bodies shown to the owner
  /^ .*(printf|echo|bad\(\))/ { next }
  /publication: STOP|: FAIL|FAILED|Traceback|command not found|No such file|Error [0-9]|error:|fatal:/ {
      printf "%d:%s\n", NR, $0
  }' "$LOG" | head -40

say "Transcript: $LOG (timed copy: $STAMPED)"
note "total $(( (SECONDS - T0) / 60 )) min; driver $(( (SECONDS - T_DRIVER) / 60 )) min"
[ "$KEEP" = 1 ] && note "kept: clone $CLONE, rewrite $RW" || note "(--keep to inspect the clone and the rewrite)"
if [ "$FAILED" -eq 0 ]; then
    printf '\n\033[32mrehearsal: the publication sitting completes\033[0m — mechanics only; the real key signs nothing here\n'
else
    printf '\n\033[31mrehearsal: %d check(s) failed\033[0m — fix the driver before the owner runs it\n' "$FAILED"
fi
exit "$FAILED"
