#!/usr/bin/env bash
# scripts/boundary_sitting.sh — interactive driver for a MILESTONE BOUNDARY sitting
# (docs/SITTING.md; the M0→M1 queue was D0060, the M1→M2 queue was D0105, the M2→M3 queue
# was D0131 + D0138, and this M3→M4 queue is D0154). OWNER-RUN, owner key present.
#
# THIS COPY is docs/proposals/2026-09-04-m3-boundary-sitting/boundary_sitting.sh, tuned
# for the M3 boundary. Per CLAUDE.md's build protocol, the original
# scripts/boundary_sitting.sh is never edited in place outside a sitting — the owner
# copies THIS FILE over it before running (step 0 of D0154's queue), the same way step 6
# below replaces scripts/custodian.sh. That copy is itself expected custody drift,
# tolerated in unexpected_failures() below by name.
#
# WHAT THIS COPY CHANGES versus the committed M2 driver is tabulated in this directory's
# README.md. FIVE of the changes are defects the M2 sitting left behind, and two of them
# would have stopped this one:
#
#   - Step 5's D0141 retarget block tests the PRE-state, so it re-arms on its own success:
#     the phrase its guard greps for is the phrase the M2 sitting's own replacement WROTE
#     into D0141. Its guard is true today, its python then finds zero matches for the text
#     it means to replace, and `|| die` stops the sitting mid-step-5 (D0152 item 1 — this
#     is where both of D0153's concurrent runs stopped). Now tested on the POST-state.
#   - Step 6 diffed against $PROPOSALS_M1/custodian.sh. At M2 that directory shipped no
#     custodian, so the step printed "already applied — skipped" and the fixture that
#     sitting installed never got its poison line (D0152 item 6). At M3 it is worse than
#     a skip: the M1 draft is now OLDER than the live file, so the step would offer to
#     REVERT three publication-sitting changes. Now $PROPOSALS_M3 (D0196).
#   - Step 4f's skip-guard reads one file its decline branch reverts three of, so a tree
#     where the Makefile is edited and the other two are not reads as "already applied"
#     forever. That is how ci.yml's comment was lost and never re-offered (D0152 item 2,
#     D0153 artifact 1). Now the guard tests the whole set the branch writes.
#   - The sitting had no lock. Two concurrent runs of a one-run ceremony produced D0153.
#     Now an flock, taken before step 0 and held for the run.
#   - "712 tests" was written on 2026-08-31 and the suite is now 842 (D0154 item 9). Every
#     count and every ETA in this file is re-measured at drafting time.
#
# Builder-drafted, and it signs nothing by itself: every signature is your key answering
# your passphrase, and every edit to author-key territory (scripts/custodian.sh,
# allowed_signers, tests/poison/, their MANIFEST rows) is shown as a diff and confirmed
# at the keyboard before it lands. Read this file end to end before running it — it
# drives your key. Its own bytes are in the custody set, so a change to it is visible.
#
# Safe to re-run: every step detects work already done and skips it. It is designed to
# be stopped and resumed — one step (the Tier-C signature guard) deliberately hands back
# to a builder session and waits.
#
# ORDER IS LOAD-BEARING. The close tag is signed LAST, after the rule requiring closes to
# be owner-signed is installed and its poison fixture proves the rule bites — so the
# first owner-signed close this project mints is validated by the very rule it obeys.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1   # RT-M2-06 D5: no set -e here, so an unguarded cd would sign the wrong tree

MILESTONE="${1:-m3}"
# The milestone whose Session A the closing note points at. Derived, not hardcoded: the
# M1 driver's closing note said "open M1 Session A in a fresh session" while every
# neighbouring line interpolated $MILESTONE, so the one line an owner reads LAST named the
# milestone that had just ended (D0122 item 5).
NEXT_MILESTONE="m$(( ${MILESTONE#m} + 1 ))"
OWNER_KEY="${TANNEN_OWNER_KEY:-$HOME/.ssh/tannen_owner}"
# FOUR proposal directories now, and the layering is deliberate. PROPOSALS (M0→M1),
# PROPOSALS_M1 (M1→M2) and PROPOSALS_M2 (M2→M3) still name the sittings that drafted the
# artifacts steps 3/4/4b/5/6 compare against; every one of those comparisons is
# already-applied — a no-op skip — as of this milestone, and pointing them at a new directory
# would make them offer a second time what the owner already installed. PROPOSALS_M3 is this
# sitting's own directory, used only where THIS milestone adds something new.
#
# PROPOSALS_M2 was promoted from "this sitting's own" to "a previous sitting's" by nothing
# more than the M2 sitting happening. That promotion is the whole hazard: step 6 diffs a
# custodian draft against the live file, and at M2 it was still pointed at PROPOSALS_M1,
# whose directory shipped no custodian.sh — so the step printed "already applied — skipped"
# and the fixture that sitting had just installed never got its poison line (D0152 item 6,
# the M1→M2 red-team pass's one critical finding left half-installed). Step 6 below reads
# PROPOSALS_M3. A variable that must be re-pointed every milestone and is only read once is
# a variable that will be forgotten once; the README tabulates this row for that reason.
#
# The M2 driver carried an exception here — step 5b's row for check-decisions-file-skip,
# which readme_row_absent() was written to unstick. MEASURED CLOSED on 2026-09-08: the row
# is at tests/poison/README.md:96, so D0131 item (1) is done and the guard worked. The note
# stays as the record of why readme_row_absent() is shaped the way it is, because the class
# of defect it closes — prose satisfying a grep meant for enforcement — recurs in this file
# twice more (step 2's docstring anchor, step 5's D0141 guard).
PROPOSALS="docs/proposals/2026-08-25-boundary-sitting"
PROPOSALS_M1="docs/proposals/2026-08-27-m1-boundary-sitting"
PROPOSALS_M2="docs/proposals/2026-08-31-m2-boundary-sitting"
PROPOSALS_M3="docs/proposals/2026-09-04-m3-boundary-sitting"
CANDIDATES="docs/redteam/fixture-candidates"
KEYREF="$OWNER_KEY"          # what ssh-keygen -Y sign is pointed at (key file, or .pub
                             # when the private half is loaded into an agent)
# The venv interpreter at a literal path, in isolated mode — the same spelling the Makefile
# uses and for the same reason (RT-02, conferral ruling 3, D0063). `uv run` would resolve
# through pyproject.toml and uv.lock, which are builder-controlled; a script that drives the
# owner's key should not take its interpreter from the party it is checking on.
PY="$PWD/.venv/bin/python"
# REHEARSAL KNOBS. None of these is ever a sitting outcome: the harness reads exit status
# and artifacts, never a knob. Ported from the publication sitting, which had them and this
# driver did not — which is why every boundary rehearsal to date has cost one to two hours
# and why the abort path has never once been executed (D0183, D0184).
#   TANNEN_SITTING_FAST=1            skip the three long gates and the commit hooks. Every
#                                    step still RUNS; the custodian, the signing, the
#                                    fixtures and the tag are untouched. ~10 minutes.
#   TANNEN_SITTING_STOP_AFTER=<step> stop, exit 3, after that step completes. A partial run
#                                    cannot read as green: the harness checks the status.
#   TANNEN_SITTING_SCRATCH=<dir>     where the breadcrumb below is written.
FAST="${TANNEN_SITTING_FAST:-0}"
# Everything this driver writes for its own use lives HERE, never inside the repository:
# an untracked file under the root is swept into the sitting commit by step 9's `git add -A`
# (D0153 artifact 3 — an evidence root rode 36 records into the M2 sitting commit), and
# step 0's own stray-dirt check would report it as work the sitting did not do.
SCRATCH="${TANNEN_SITTING_SCRATCH:-$(mktemp -d "${TMPDIR:-/var/tmp}/tannen-sitting.XXXXXX")}"
mkdir -p "$SCRATCH"
# THE BREADCRUMB: one line per step, appended as the step is announced. A `die` is exit 1
# with no trap, so after an abort this is what says how far the sitting got — to you at the
# keyboard, and to scripts/rehearse_sitting.sh, which must not learn this driver's state by
# parsing this driver's prose (BRIEF §2: one implementation, not two; and the first spelling
# of exactly that check, in the publication harness, matched nothing and killed the harness
# mid-verdict under set -e rather than failing one check — D0184).
STEPS="$SCRATCH/steps"; : > "$STEPS"
# A SECOND BREADCRUMB, for the one question the publication harness left the operator to
# guess. Its `--abort-at N` takes a 1-based PROMPT index, but nothing anywhere maps a prompt
# index to a step: the operator asserts which step they think N falls in and the verdict
# checks the assertion, so choosing N at all means counting `confirm` call sites by hand and
# hoping none of the conditional ones fired. Several are inside conditionals, so the mapping
# genuinely depends on repo state and cannot be read off the source.
#
# The driver knows the answer as it happens, so it writes it down: one line per prompt,
# "<index> <step>". A harness can then map an abort to its step exactly instead of asserting
# one, and — more usefully — can print the whole map after a green run so the NEXT run's N is
# chosen from a measurement rather than a count of grep hits.
PROMPTS="$SCRATCH/prompts"; : > "$PROMPTS"
PROMPT_N=0
CURRENT_STEP="(before step 0)"
# How long the gate takes, measured not guessed, and re-measured at every boundary because
# the number only ever grows. M0's "a minute" (2026-08-25, 174 tests) became M1's "15-20
# minutes" (537 tests), then M2's "35-40 minutes" (712 tests, 2026-08-31, D0139).
#
# RE-MEASURED FOR M3 ON 2026-09-09, on the builder's machine, from a clean tree: `make
# verify` green end to end in 33m31s over 842 tests, of which pytest alone is 19m16s
# (1156.68s; 840 passed, 1 skipped, 1 xfailed) and check_decisions is most of the rest.
#
# Note what the numbers did: the suite grew 18% (712 -> 842) and pytest got FASTER in
# absolute terms (21m40s -> 19m16s), so the total moved barely at all. That is worth
# stating, because the M2 comment's framing — "the number only ever grows" — would have
# licensed writing a bigger figure without measuring, and the figure would have been wrong
# in the direction that matters least. The rule is not "assume growth", it is "measure".
#
# This is not cosmetic. An owner watching a still terminal for forty minutes against a
# twenty-minute promise concludes it is hung — which is precisely what happened at the M0
# sitting, twice, before the driver ever reached its first question (D0069). The promise
# has to be the measurement.
# RULING (3) OF 2026-09-10 reaches this line: "load-bearing counts and ETAs in generated or
# operator-facing documents are derived at generation time or not stated." This was a
# hand-maintained count in the most operator-facing text the ceremony has, and the class it
# belongs to has already rotted twice in this proposal alone — M2's "712 tests" survived into
# this draft's first cut after the suite reached 842, and the README's step count sat at 24
# for three steps after they landed. Neither was catchable by any guard: prose is not
# executable, which is exactly why the rule has to reach it.
#
# So the COUNT is derived at the moment it is printed. `pytest --collect-only -q` costs 1.2s
# measured, against a gate of half an hour, so carrying it by hand was never a saving. The
# WALL CLOCK cannot be derived without running the thing it predicts, so it is stated as what
# it is — a dated measurement on named hardware — and never as a bare prediction that reads
# like one. `set -uo pipefail` is on and `set -e` is not, so a failed collection leaves `n`
# empty and the caller still gets a sentence.
verify_eta() {
    local n
    n=$(uv run pytest --collect-only -q 2>/dev/null | awk '/tests? collected/ { print $1; exit }')
    printf '%s tests; last measured end to end at 33m31s on a clean tree (builder machine, 2026-09-09)' \
        "${n:-an unknown number of}"
}

# The `return 0` is load-bearing: without it say() returns the status of its last command,
# and a caller under `set -e` would abort on a step header.
say()  { printf '\n\033[1m== %s\033[0m\n' "$*"
         printf '%s\n' "$*" >> "$STEPS"
         case "$*" in "Step "*) CURRENT_STEP=$(printf '%s' "$*" | awk '{print $2}') ;; esac
         return 0; }
# Both prompt helpers count, because BOTH consume a line of the harness's answers file — the
# publication driver has no pause() at all, so its indices count confirms only and porting its
# arithmetic unexamined would have been off by one per pause.
note_prompt() { PROMPT_N=$((PROMPT_N + 1)); printf '%d %s\n' "$PROMPT_N" "$CURRENT_STEP" >> "$PROMPTS"; }
note() { printf '   %s\n' "$*"; }
# A step about to be quiet for more than a moment says so FIRST, and says it with this
# helper rather than an ordinary note, so scripts/rehearse_sitting.sh can check the rule
# mechanically: in a rehearsal transcript, every silence longer than 25 seconds must have
# one of these lines directly above it. An owner watching a still terminal cannot tell
# waiting from hung — at the M0 sitting they could not, and killed the driver twice at its
# own first question (D0069). Stating the expected duration is the whole fix; the harness
# exists to keep it stated as the driver grows.
waiting() { printf '   [waiting] %s\n' "$*"; }
die()  { printf '\nsitting: STOP — %s\n' "$*" >&2
         # An abort is exit 1 with no trap, so this is the only place that can say what the
         # run leaves behind. The two regimes differ either side of step 9's commit, and an
         # owner who has just been stopped mid-ceremony should not have to work out which
         # one they are in.
         if [ -s "$STEPS" ]; then
             printf 'reached: step %s   (every step this run announced: %s)\n' \
                 "$(awk '/^Step /{l=$2} END{print l}' "$STEPS")" "$STEPS" >&2
             # ASK THE TREE, DO NOT INFER FROM THE STEP. The first spelling of this branched
             # on whether step 9 appeared in the breadcrumb, as a proxy for "has committed" —
             # and step 9's commit is a CONFIRM the owner may decline, so a run that reached
             # step 9, declined the commit, and was then stopped by step 10's dirty-tree
             # refusal was told its tree was clean and there was nothing to undo. Measured on
             # 2026-09-09 by rehearsing exactly that decline: the advice was wrong in the one
             # situation this message exists for. `git status` costs nothing and cannot be
             # wrong about it.
             # AND THE TREE IS NOT THE WHOLE ACCOUNT OF THIS CEREMONY. Asking git status
             # instead of the step number was the right correction and an incomplete one: a
             # minted, owner-signed close tag lives OUTSIDE the working tree. Four die() sites
             # are downstream of `git tag -s` — the verify-tag check on the next line, and step
             # 11's projection, custodian and `make verify` failures — and step 10 has just
             # required the tree to be clean, so all four take the CLEAN branch and tell an
             # owner "nothing is half-applied" while their own signature stands over a sitting
             # that failed. The likeliest of the four is step 11's final gate going red at the
             # close, which is exactly the moment the advice matters. Found 2026-09-10, by
             # asking what a mid-ceremony push would strand and discovering the ceremony
             # already strands it. `git rev-parse` costs nothing and cannot be wrong about it.
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
# Stop cleanly AFTER a named step, so a partial run can be inspected in minutes rather than
# hours. Exit 3, never 0: a partial run must not read as a completed sitting.
stop_after() { [ "${TANNEN_SITTING_STOP_AFTER:-}" = "$1" ] || return 0
               printf '\n   [rehearsal] stopping after step %s (TANNEN_SITTING_STOP_AFTER)\n' "$1" >&2
               exit 3; }
confirm() { local a; note_prompt; read -rp "$1 [y/N] " a; [[ "${a:-}" == [yY]* ]]; }
pause() { note_prompt; read -rp "   $1" _; }
# EDITOR and PAGER hold command LINES, not command names: `emacsclient -nw -a 'emacs -nw'`
# and `less -FRX` are both ordinary settings, and this driver runs in the owner's own shell
# with the owner's own habits in it. Quoting the expansion asks the kernel for a program
# whose filename contains those spaces — the `command not found` this printed on
# 2026-08-25 — while merely unquoting it would word-split the owner's own quoting apart.
# `eval` is what git does for the same reason (`eval "$editor" '"$@"'`); the filename stays
# quoted through the eval, so a path with a space in it still arrives as one argument.
edit() { eval "${EDITOR:-nano}" '"$@"'; }
page() { eval "${PAGER:-less}" '"$@"'; }

sign_owner() {   # <file> <namespace>   -> writes <file>.sig
    # A pre-existing <file>.sig makes ssh-keygen ask "Overwrite (y/n)?" — and on any
    # answer but y it exits 0 WITHOUT WRITING, so the die below never fires and the
    # "signed:" note lies. Confirmed at the real M1 sitting (2026-08-30, step 7): the
    # prompt landed right after the pager and a passphrase, got a stray non-y, and the
    # custodian went red one line later over the untouched Aug-26 custody signature.
    # M0 never saw this — no path had a prior signature then. Every call site reaches
    # here only when the existing signature is already invalid (verify_owner failed, or
    # the file was just edited), so remove it rather than leave a prompt to mis-answer.
    rm -f -- "$1.sig"
    ssh-keygen -Y sign -f "$KEYREF" -n "$2" "$1" >/dev/null \
        || die "signature failed for $1 (namespace $2)"
    note "signed: $1.sig (namespace $2)"
}
verify_owner() { # <file> <namespace>   -> 0 if a valid owner signature is already there
    [ -f "$1.sig" ] && ssh-keygen -Y verify -f allowed_signers -I owner@tannen \
        -n "$2" -s "$1.sig" <"$1" >/dev/null 2>&1
}
# A FIRST sitting cannot start from a fully green gate, and pretending otherwise is how
# the driver stopped on 2026-08-25 (D0065). The custodian requires governance/custody.sha256
# and its owner signature; the set hashes scripts/custodian.sh, so it can only be
# regenerated after the custodian is installed and only signed after that — both step 7.
# Until then those two failures ARE the agenda, not a red gate. Everything else is a red
# gate. This names the tolerated two and nothing more; once step 7 is done it matches
# nothing and the checks below are ordinary ones.
# Deliberately NOT tolerated in general: check_manifest's per-file "custody drift" — that
# is the channel that says a file the owner signed for has changed, and it must still stop
# the sitting at step 0, where nothing has been touched yet and drift means someone edited
# a guard outside this driver. The lines below are the custodian's redundant second channel
# for the same fact, which step 7 answers by regenerating and re-signing.
#
# ONE exception, scoped by name, not by pattern: scripts/boundary_sitting.sh itself. This
# sitting's own header says the owner copies THIS FILE over the real one before running it
# (the same move step 6 makes for custodian.sh), and that copy is drift against the custody
# set signed at the LAST sitting — before this driver has done anything. Tolerating drift
# on this one path, by its literal name, is not the same defect the general tolerance above
# was written to avoid: it does not hide a change to any OTHER guard, and it stops meaning
# anything the moment step 7 re-signs, same as the rest.
#
# TWO OUTPUT SHAPES, one filter. scripts/custodian.sh's bad() prints one self-contained
# line, "custodian: FAIL — <message>" — marker and detail together, which is what every
# pattern above was written against. scripts/check_manifest.py's Failures.finish() prints
# a bare count on its own line ("check_manifest: FAIL (N violation(s))") and each violation
# on the NEXT line, indented ("  - <message>"), with no "FAIL" on it at all — this is
# EXACTLY the shape check_manifest's own per-file custody drift arrives in (confirmed
# directly: `check_manifest: FAIL (1 violation(s))` then `  - custody drift:
# scripts/boundary_sitting.sh changed since...` on the line below). A filter matching only
# lines containing ": FAIL" — the M0-era form — NEVER SEES that second line, so a pattern
# aimed at it silently excuses nothing; the count line survives as "unexpected" and stops
# the sitting at its own first question. Caught by rehearsing this copy, not by reading it.
# So: keep both a "<script>: FAIL (N violation(s))" line AND an indented "  - " detail line,
# apply the same patterns to both, and — the part that closes the gap — drop a bare count
# line entirely once no detail line beneath it can still be pending. There is exactly one
# script (check_manifest) that can emit this shape at step 0, exactly one violation it can
# have here (this file's own drift), so counting is unambiguous without parsing the number.
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
    # sha256sum's output IS the manifest row format (regen_manifest_row appends it
    # verbatim), so a whole-line fixed-string match is the exact comparison, not a proxy.
    local want
    want=$(sha256sum "$1") || return 1
    grep -qxF "$want" MANIFEST.sha256
}
driver_custody_current() {  # true when THIS driver's bytes match the row custody.sha256 was signed over
    # governance/custody.sha256 rows are `sha256sum` output verbatim, exactly as
    # MANIFEST.sha256's are, so a whole-line fixed-string match is the comparison itself and
    # not a proxy for one. This is the question "will step 0's gate get past check_manifest",
    # asked directly of the state rather than inferred from the step number.
    local want
    want=$(sha256sum scripts/boundary_sitting.sh) || return 1
    grep -qxF "$want" governance/custody.sha256
}
readme_row_absent() {     # <fixture> -> true when README.md carries no TABLE ROW for it
    # THE ANCHOR IS THE LEADING PIPE, and that is the whole fix (D0131 item 1). The M1
    # driver asked `grep -q '<fixture>' tests/poison/README.md` — does this name appear
    # anywhere in the file — and step 5, earlier in the same sitting, appends a rows file
    # whose PROSE names check-decisions-file-skip while explaining that its row comes at
    # step 5b. The explanation satisfied the grep, so step 5b read "already added" and the
    # row has never been offered: the sentence stating why the row is absent was what
    # guaranteed it stayed absent. A table row starts at column 1 with "| `name/` |";
    # prose never does. Verified against the live README on 2026-08-31 — the anchor finds
    # lint-imports-kernel (line 36) and oracle-shadow (line 58) as present, and correctly
    # reports check-decisions-file-skip absent despite its prose mention on line 52.
    ! grep -q "^| \`$1/\` |" tests/poison/README.md
}
add_manifest_rows() {    # every file under a directory (sealed dirs carry a row each)
    local dir="$1" files=()
    mapfile -t files < <(find "$dir" -type f | sort)   # never `while read … done < <(…)`; see below
    for f in "${files[@]}"; do
        # D0034: a manifest row must name a COMMITTED artifact. `git mv` tracks what was
        # already in the repo, but the tag-signer bundle is generated here at the sitting
        # (conferral ruling 6) and so is untracked — manifesting it without staging it
        # leaves check_manifest red until the step-9 commit, which check_manifest gates.
        git add -- "$f"
        grep -q "  $f\$" MANIFEST.sha256 || sha256sum "$f" >> MANIFEST.sha256
    done
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
# EVERY LONG GATE GOES THROUGH THIS ONE LINE, so a fast run cannot quietly become a green
# one: the transcript says what was not run, and the rehearsal harness greps for it.
#
# `--no-verify` here is the ONE place this project permits it, and the permission is narrow:
# TANNEN_SITTING_FAST is a rehearsal knob, the harness runs against a disposable clone with a
# throwaway key, and D0181 refused --no-verify for a real commit even under a direct owner
# ruling. If you are reading this line in a transcript from a REAL sitting, something is
# wrong — TANNEN_SITTING_FAST was set in the owner's environment and the receipt attests to
# a gate that did not run.
skipping_gate() { printf '   [TANNEN_SITTING_FAST] NOT RUN: %s\n' "$*"; }

# ------------------------------------------------------- the lock (D0152 item 4, D0153)
# A BOUNDARY SITTING IS A ONE-RUN CEREMONY, and until now nothing said so. On 2026-09-04 two
# invocations of this driver ran against one worktree by accident. Both stopped at the same
# defect and were killed by hand; between them they reverted a file no gate could see, wrote
# two attention receipts at one HEAD, and swept an untracked evidence root into the sitting
# commit (D0153, three artifacts). None of that is a defect in any single step — it is the
# absence of this lock.
#
# Keyed on the worktree, not on the milestone: the thing that must not happen twice is two
# runs against ONE tree, and a rehearsal in a disposable clone has a different path and so a
# different lock. FD 9 is held open for the life of the process; the kernel drops it on exit,
# including on a `die`, a kill, or a crash — there is no stale lockfile to clean up.
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
    note "Nothing will stop a second invocation against this worktree (D0152 item 4). Install"
    note "util-linux, or make certain by hand that this is the only run."
fi

# ---------------------------------------------------------------- 0. preconditions
say "Step 0 — boundary sitting, $MILESTONE. Precondition: a green gate and a read queue"
[ -x "$PY" ] || die "no interpreter at $PY — run 'uv sync --frozen' first"
[ -f "$OWNER_KEY" ] || die "no owner key at $OWNER_KEY (set TANNEN_OWNER_KEY)"
grep -q '^owner@tannen ' allowed_signers || die "owner@tannen is not enrolled in allowed_signers"
# D0122 item 5: on a RESUMED sitting this offer is a trap, and a fatal one. Steps 1-8 flip
# record statuses, write .sig files, amend frozen text and move fixtures; every one of those
# is custody drift or a stale projection by the time it is done. unexpected_failures()
# tolerates exactly two patterns plus this file's own name — by design, because at step 0 of
# a FRESH sitting nothing else should be dirty — so the gate an owner is invited to run
# "before signing anything" goes red over the work they already did, and die() stops the
# sitting they came back to finish. The gate that must be green is step 9's, after the
# sitting's edits are complete; this one is a precondition on a clean tree and nothing more.
# RT-M2-06 D1 CORRECTS THE FIRST SPELLING OF THIS TEST. It asked "is anything other than
# this file dirty", which is not the same question: a single stray untracked file — an
# editor backup, a leftover MANIFEST.tmp, the owner's own notes — set RESUMED=1, SKIPPED the
# precondition gate entirely, and told the owner "this is a RESUMED sitting" on no evidence.
# A fresh sitting could then begin over a red gate with the one check that exists to prevent
# exactly that silently switched off. Resumption is now decided by artifacts only THIS
# SITTING creates, and stray dirt is reported rather than acted on.
RESUMED=0
# (a) a TRACKED modification other than this driver's own copy (the documented precondition
#     for running it at all, tolerated by name in unexpected_failures until step 7 re-signs).
[ -n "$(git status --porcelain --untracked-files=no | grep -v ' scripts/boundary_sitting\.sh$')" ] && RESUMED=1
# (b) untracked artifacts nothing but a sitting produces: owner signatures and the receipt.
[ -n "$(git ls-files --others --exclude-standard -- 'decisions/*.yaml.sig' 'governance/*.sig' 'receipts/')" ] && RESUMED=1
# (c) and the last act of all, which leaves the tree clean behind it (RT-M2-06 D3).
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
    # Dirt that is NOT sitting-shaped does not mean "resumed", and must never silently
    # disable the gate — but the owner should know it is there before the gate reads red.
    STRAY=$(git status --porcelain | grep -v ' scripts/boundary_sitting\.sh$')
    if [ -n "$STRAY" ]; then
        note "The tree is not clean, and none of it looks like sitting work:"
        printf '%s\n' "$STRAY" | sed 's/^/    /'
        note "The gate below may read red for reasons that are not this sitting's."
    fi
if confirm "Run 'make verify' now (recommended — nothing should be signed over a red gate)?"; then
    # Capturing output and DISPLAYING it are two different acts, and `$( )` only does the
    # first. The gate TOOK the better part of a minute when this comment was written —
    # 174 tests, ten law suites and a batched pytest run inside check_decisions — and it
    # printed nothing at all until it was over, so the sitting read as hung at its own
    # first question (owner, 2026-08-25; killed twice before it ever reached step 1). The
    # number is left in the past tense on purpose: at M3 the same gate is 842 tests and
    # over half an hour, so the failure it describes is now forty times easier to hit, not
    # forty times less likely. A driver that spends the owner's
    # attention owes them a visible reason to keep waiting. tee does both jobs: the run
    # streams to the terminal, and the log is what unexpected_failures reads afterwards.
    # PIPESTATUS must be read on the very NEXT line — any command in between, an
    # assignment included, replaces it.
    # THE CONFIRM ABOVE IS ASKED IN BOTH MODES, and that is deliberate. The publication
    # driver spells its fast path `if FAST ... elif confirm ...`, so under FAST the confirm
    # never reads a line and every later prompt index shifts by one — which is why its
    # rehearsal mappings all have to say "under TANNEN_SITTING_FAST=1". Asking the question
    # and then skipping the work keeps the prompt sequence identical in both modes, so an
    # --abort-at index means the same thing fast or slow.
    # THE BANNER MUST NOT APPEAR ON A GATE THAT CANNOT RUN (owner ruling 2, 2026-09-10).
    # docs/SITTING.md installs this driver with a cp, `scripts/boundary_sitting.sh` is a
    # custody-set member, and `check_manifest.py` is the FIRST recipe line of the verify
    # target — so in the normal case make stops at line one and the gate below is over in
    # seconds. The previous spelling advertised half an hour for it, and the advertisement
    # is what let this proposal's own README claim twice that the gate had been exercised
    # (D0151, D0206). Ask the tree which case this is instead of announcing one of them.
    #
    # The old line also read "about about 35 minutes" — `waiting "…about $VERIFY_ETA"` over
    # a value that already began "about" — through five rehearsals and into the transcript
    # nobody read that closely. Both halves of that sentence are the same defect.
    # Three cases, because there are three, and the announcement has to name the one it is
    # in. Collapsing them is how the old single banner came to describe a run that does not
    # happen — which is the defect this whole branch exists to correct.
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
        # AND THE CONTINUATION LINE CLAIMS ONLY WHAT THIS RUN ESTABLISHED (same ruling).
        # "green except the custody set" is true and reads like something much stronger: it
        # means no unexpected failure appeared, in a run that in the ordinary case got nine
        # lines in. Which case this was is a fact about the output, so read it there. The
        # pytest anchor is `^[0-9]+ passed` and the anchoring is not style — an unanchored
        # / passed/ matched D0117's TITLE in the queue this same step prints, and reported
        # an empty gate as having run a suite. check_decisions captures its own pytest
        # output (scripts/check_decisions.py:211-214, capture_output=True), so the only
        # line of this shape that can reach the log is verify's own `uv run pytest -q`.
        gate_guards=$(printf '%s\n' "$verify_out" | grep -cE '^check_[a-z_]+: (OK|FAIL)')
        if printf '%s\n' "$verify_out" | grep -qE '^[0-9]+ passed'; then
            note "green except the custody set, which is this sitting's step 7 — continuing"
        else
            note "no unexpected failure — and that is ALL this established. The run reached"
            note "$gate_guards of verify's six guards and never reached the suite, so"
            note "check_decisions, pytest, the laws report and lint-imports did not run here."
            # AND THE CAUSE IS NAMED ONLY WHERE IT WAS OBSERVED. Under FAST the gate is the
            # custodian alone and `make` never ran, so blaming check_manifest here would be
            # this correction committing the error it corrects — asserting a mechanism the
            # run did not exercise. Two regimes, two sentences, neither guessed.
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
if confirm "Show the digest's owner queue (what this sitting is for)?"; then
    latest_digest=$(ls -1 digest/*.md 2>/dev/null | tail -1)
    [ -n "$latest_digest" ] && sed -n '/## Requires owner/,/^## /p' "$latest_digest" | page
fi

say "Optional — load the key into ssh-agent so you type the passphrase once"
note "A boundary sitting signs several artifacts. Loading the key means one passphrase"
note "for the whole sitting; you are present for all of it, which is what the passphrase"
note "attests. Without the agent, expect one prompt per signature."
if ssh-add -l 2>/dev/null | grep -q "$(ssh-keygen -lf "$OWNER_KEY.pub" | awk '{print $2}')"; then
    KEYREF="$OWNER_KEY.pub"
    note "key already loaded in the agent"
elif confirm "ssh-add $OWNER_KEY now?"; then
    ssh-add "$OWNER_KEY" && KEYREF="$OWNER_KEY.pub"
fi
export TANNEN_OWNER_KEY="$KEYREF"

stop_after 0

# ---------------------------------------------------------------- 1. Tier-C signatures
# THE LIST IS READ INTO AN ARRAY FIRST, and every loop in this file that asks the owner a
# question does the same. `while read rec; do … done < <(ls …)` redirects the WHOLE LOOP's
# stdin to the file list, so a confirm() in the body takes its answer from the next
# FILENAME rather than from the keyboard — and takes it silently, because bash prints a
# `read -p` prompt only when stdin is a terminal. The loop then skips every other record
# and reports "left unsigned" for a question nobody was asked. That is exactly what step 1
# did at the M0 sitting on 2026-08-25, in the two loops that decide whether Tier-C records
# get signed — which is to say, in the sitting's entire purpose (D0067).
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
say "Step 1 — Tier-C records already recorded accepted (a safety net; usually empty)"
note "Since D0064 the guard refuses a Tier-C record that says accepted without a"
note "signature, so a committed repo cannot hold one. Anything found here reached"
note "accepted in the WORKING TREE — worth looking at before signing it. The records"
note "this sitting is convened to resolve are queued as blocked-on-owner and come up at"
note "step 8, where accepting and signing are one act."
note ""
note "Signing pins the record's bindings too, so a later binding upgrade (D0045) needs a"
note "re-signature. At Tier-C volume — five doors, owner-touched by definition — that is"
note "the cheap side of the trade."
sign_tier_c_records

stop_after 1

# ---------------------------------------------------------------- 2. builder handoff
say "Step 2 — the guard that makes step 1 mean something (builder work)"
# RT-M2-06 D4: this used to grep "affirmative signature only", whose ONLY match is the
# module docstring at check_decisions.py:13 — so deleting the enforcement while leaving the
# docstring made this step report "present". Anchor on the message the guard EMITS instead.
if grep -q "Tier-C record accepted without an owner signature" scripts/check_decisions.py; then
    note "Tier-C signature check is present in scripts/check_decisions.py — skipped"
else
    note "scripts/check_decisions.py does not yet REQUIRE those signatures (RT-06), so"
    note "nothing stops the next Tier-C record from being accepted by assertion. That"
    note "patch is builder work and lands after the signatures exist, or the gate would"
    note "have been red before you could sign."
    note ""
    note "Ask the builder session: \"land the RT-06 Tier-C signature check and re-run make verify\"."
    pause "Enter once the builder reports green (or Ctrl-C and re-run this script later)..."
    grep -q "affirmative signature only" scripts/check_decisions.py \
        || die "still not present — re-run this script when it is"
fi

stop_after 2

# ---------------------------------------------------------------- 3. policy clause
say "Step 3 — policy.yaml: in-repo mechanics are Tier A (D0048, D0053)"
if grep -q '^in_repo_mechanics:' governance/policy.yaml; then
    note "clause already present — skipped"
elif confirm "Read the proposal first?"; then
    page docs/proposals/2026-08-24-policy-in-repo-mechanics.md
fi
if ! grep -q '^in_repo_mechanics:' governance/policy.yaml; then
    cat "$PROPOSALS/policy-append.yaml" >> governance/policy.yaml
    git --no-pager diff governance/policy.yaml
    if confirm "Keep this clause?"; then
        rm -f governance/policy.yaml.sig
    else
        git checkout -- governance/policy.yaml
        note "reverted — D0048 and D0053 stay documentary"
    fi
fi
verify_owner governance/policy.yaml tannen-policy \
    || { note "re-signing policy.yaml"; sign_owner governance/policy.yaml tannen-policy; }

stop_after 3

# ---------------------------------------------------------------- 3b. the push clause
say "Step 3b — policy.yaml excludes the push this repository now makes daily (D0195 item 3)"
# in_repo_mechanics was written when this repo had no remote. Its covers list grants Tier A
# over "pushing to a private origin already configured in this repo"; its excludes list
# withholds it from "pushing to any remote other than a private origin already configured
# here". Origin is now PUBLIC. Read literally, the routine act performed after every commit
# is excluded from the tier that authorises it.
#
# The authority is real and lies elsewhere — external_surface.publishing: this-repo-public,
# plus owner-signed D0115 and D0176 — so nothing done since publication was unauthorised.
# What is wrong is that the clause a session actually READS to decide whether it may push
# says the opposite of the clause that governs. A rule that is right only if you know to
# ignore it is the shape D0108 is about.
#
# D0195 offers TWO shapes and says the choice is the owner's, so this step offers both
# rather than choosing. It does not recommend by ordering alone: B is offered first because
# D0195's own argument for it is BRIEF §2 (one rule in one place), and that argument is
# quoted below so you can disagree with it.
if ! grep -q 'pushing to a private origin already configured in this repo' governance/policy.yaml; then
    note "already amended — skipped"
else
    note "SHAPE B (offered first): delete both push clauses and let external_surface be the"
    note "only place in this file that speaks about remotes. D0195's argument is BRIEF §2 —"
    note "one rule in one place — and the observation that in_repo_mechanics has no business"
    note "describing external surface at all."
    note ""
    note "SHAPE A: keep both clauses and widen them to name the published origin, so a"
    note "session reading in_repo_mechanics alone still gets a true answer. The argument"
    note "for A is that a session which never reaches external_surface is the exact session"
    note "this clause exists to answer, and deleting the clause answers it with silence."
    note ""
    note "Either way policy.yaml is re-signed below: it is custody-set and named in"
    note "required_signatures, and an edited signed file with a stale signature is a red"
    note "floor, not a pending task."
    SHAPE=""
    if confirm "Take SHAPE B — delete both push clauses (external_surface speaks alone)?"; then
        SHAPE=B
    elif confirm "Take SHAPE A instead — widen both clauses to name the published origin?"; then
        SHAPE=A
    fi
    if [ -n "$SHAPE" ]; then
        if SHAPE="$SHAPE" python3 - <<'PY'
import os, pathlib, sys

shape = os.environ["SHAPE"]
f = pathlib.Path("governance/policy.yaml")
src = f.read_text(encoding="utf-8")

covers_old = "    - pushing to a private origin already configured in this repo\n"
excl_old = "    - pushing to any remote other than a private origin already configured here\n"
for name, text in (("covers", covers_old), ("excludes", excl_old)):
    if src.count(text) != 1:
        sys.exit(f"policy.yaml: the {name} push clause is not the expected text "
                 f"({src.count(text)} matches) — amend by hand")

if shape == "B":
    src = src.replace(covers_old, "").replace(excl_old, "")
else:
    src = src.replace(
        covers_old,
        "    - pushing to an origin this repository is published to under\n"
        "      external_surface.publishing\n",
    ).replace(
        excl_old,
        "    - pushing to any remote external_surface.publishing does not name\n",
    )
f.write_text(src, encoding="utf-8")
print(f"   policy.yaml amended, shape {shape}")
PY
        then
            git --no-pager diff governance/policy.yaml
            if confirm "Keep this amendment and re-sign policy.yaml?"; then
                rm -f governance/policy.yaml.sig
                sign_owner governance/policy.yaml tannen-policy
                note "amended and re-signed. The custody row for policy.yaml is regenerated"
                note "at step 7, which is also where the set is re-signed."
            else
                git checkout -- governance/policy.yaml
                note "reverted — the clause still excludes the push this repo makes daily,"
                note "and D0195 item (3) stays open for the next sitting."
            fi
        else
            note "the amendment did not apply cleanly (message above) — nothing was changed."
        fi
    else
        note "declined both shapes — D0195 item (3) stays open. Nothing was edited."
    fi
fi
stop_after 3b

# ---------------------------------------------------------------- 4. binding strength
say "Step 4 — binding strength as a schema field (D0052; frozen path)"
if grep -q '"strength"' governance/schemas/decision-record.schema.json; then
    note "already applied — skipped"
else
    note "The schema is frozen, so the builder cannot apply this. It lands together with"
    note "the honest marking of this batch: a schema that allows the field while no record"
    note "uses it reports '0 documentary', which is a false number rather than no number."
    if confirm "Read the proposal?"; then
        page docs/proposals/2026-08-24-binding-strength-grade.md
    fi
    if confirm "Apply $PROPOSALS/apply_binding_strength.py?"; then
        "$PY" -I -P "$PROPOSALS/apply_binding_strength.py" || die "applier failed"
        git --no-pager diff --stat governance/schemas decisions
        if confirm "Diff is what the proposal describes — keep it?"; then
            regen_manifest_row governance/schemas/decision-record.schema.json
        else
            git checkout -- governance/schemas decisions
            note "reverted"
        fi
    fi
fi

stop_after 4

# ---------------------------------------------------------------- 4b. frozen text
say "Step 4b — the two frozen files the sitting amends"
if grep -q 'Metric calibration' BRIEF.md; then
    note "BRIEF §9.1 amendment already applied — skipped"
    # D0122 item 4: "applied" and "manifested" are two facts, and this branch used to check
    # only the first. The failure advice further down sends the owner to an editor OUTSIDE
    # this driver ("apply the two blocks in any editor and re-run"); on that re-run the grep
    # above is true, control lands HERE, and regen_manifest_row is never reached — so
    # BRIEF.md's bytes and its MANIFEST row disagree in silence until step 9's gate fails on
    # a frozen path, one full sitting after the mistake that caused it. Checking the row
    # costs one sha256sum.
    if ! manifest_row_current BRIEF.md; then
        note ""
        note "BUT BRIEF.md's MANIFEST.sha256 row does not match its bytes — the amendment"
        note "landed outside this driver, and the frozen-path row was never regenerated."
        note "Left alone this is a red gate at step 9, five signatures from here."
        if confirm "Regenerate BRIEF.md's MANIFEST row now (author-key territory)?"; then
            regen_manifest_row BRIEF.md
            git --no-pager diff MANIFEST.sha256
        fi
    fi
else
    note "Two additive bullets for BRIEF §9.1: the metric-calibration rule, and the"
    note "distinction between a signature as presence and a signature as authorisation."
    note "Both were conferral rulings; neither is stated by any artifact today."
    if confirm "Read the drafted amendment?"; then
        page "$PROPOSALS/brief-9.1-amendment.md"
    fi
    note "BRIEF.md is owner text and frozen — apply the two blocks in your editor."
    if confirm "Open BRIEF.md now?"; then
        edit BRIEF.md || note "editor exited non-zero — the diff below is the ground truth"
        # An empty diff is not a decision to put to the owner. Offering "keep it?" over
        # nothing invites a y that rewrites a manifest row for an unchanged file and reads
        # afterwards as though the amendment landed. The step is idempotent, so saying
        # plainly that nothing happened is the honest outcome.
        if git diff --quiet -- BRIEF.md; then
            note "BRIEF.md unchanged — the amendment has NOT landed. Apply the two blocks in"
            note "any editor ($PROPOSALS/brief-9.1-amendment.md) and re-run; this step returns."
        else
            git --no-pager diff BRIEF.md
            if confirm "Keep this edit?"; then
                regen_manifest_row BRIEF.md
            else
                git checkout -- BRIEF.md
            fi
        fi
    fi
fi
if diff -q .github/workflows/ci.yml "$PROPOSALS/ci.yml" >/dev/null; then
    note "ci.yml already current — skipped"
else
    note "ci.yml is frozen, so the builder cannot add the fetch-depth the new guards need:"
    note "a shallow checkout arrives without tags, which the custody floor refuses (RT-15),"
    note "and without the history the receipt chain walks."
    diff -u .github/workflows/ci.yml "$PROPOSALS/ci.yml" | page
    if confirm "Install this ci.yml?"; then
        cp "$PROPOSALS/ci.yml" .github/workflows/ci.yml
        regen_manifest_row .github/workflows/ci.yml
    fi
fi

stop_after 4b

# ---------------------------------------------------------------- 4c. signed-record binding upgrades
say "Step 4c — D0070's two drafted binding upgrades, on D0049 and D0063 (D0105 item 3)"
note "A binding on a SIGNED Tier-C record cannot be edited between sittings (the"
note "signature covers the record's whole bytes) — D0070 drafted these at the M0->M1"
note "sitting and left them for the next one to apply and re-sign. D0063's needs step 4b"
note "landed first (BRIEF.md must actually say 'Metric calibration' for its manifest"
note "binding to mean anything); D0049's needs a corruption fix found while drafting"
note "this: a missing newline swallowed its third binding into the second's prose,"
note "silently dropping the documentary binding to the custodian-close-tag-signer"
note "proposal (confirmed live 2026-08-27 — 'raw dashes: 2, parsed bindings: 2' where 3"
note "were written; every OTHER decisions/*.yaml file was checked the same way and none"
note "else has this defect). Restoring it and adding the new binding are one edit below."
if ! grep -q 'Metric calibration' BRIEF.md; then
    note "BRIEF.md does not yet carry step 4b's amendment — D0063's upgrade needs that"
    note "first. Apply step 4b, then re-run this script; it resumes here."
else
    if grep -q 'target: scripts/custodian.sh' decisions/0049-*.yaml; then
        note "D0049 already upgraded — skipped"
    elif confirm "Fix D0049's swallowed binding and add manifest:scripts/custodian.sh?"; then
        python3 - <<'PY'
import glob, pathlib
path = pathlib.Path(glob.glob("decisions/0049-*.yaml")[0])
src = path.read_text()
broken = ("once the owner applies it (D0045).  - type: manifest\n"
          "    target: DELEGATIONS.md\n")
assert src.count(broken) == 1, "expected corruption pattern not found — check by hand"
fixed = ("once the owner applies it (D0045).\n"
         "  - type: manifest\n"
         "    target: DELEGATIONS.md\n")
src = src.replace(broken, fixed)
anchor = src.rstrip().rsplit("\n", 1)[-1] + "\n"   # the file's own last line (links: [...])
assert anchor.startswith("links: ["), f"expected a links: line last, got {anchor!r}"
addition = (
    "  - type: manifest\n"
    "    target: scripts/custodian.sh\n"
    "    detail: >-\n"
    "      ENFORCED, added at the M1 boundary sitting (2026-08-27): the second binding\n"
    "      above described the drafted custodian patch as documentary, pending the\n"
    "      owner applying it; the patch (the *-close signer case) landed at the M0->M1\n"
    "      sitting and scripts/custodian.sh is in MANIFEST.sha256, so this upgrades the\n"
    "      claim from documentary to enforced.\n"
)
src = src[: -len(anchor)] + addition + anchor
path.write_text(src)
PY
        git --no-pager diff decisions/0049-*.yaml
        if confirm "Keep this edit and re-sign D0049?"; then
            rm -f decisions/0049-*.yaml.sig
            sign_owner "$(ls decisions/0049-*.yaml)" tannen-decision
        else
            git checkout -- decisions/0049-*.yaml
            note "reverted — D0049 keeps its corrupted binding and stale-looking signature"
        fi
    fi
    if grep -q 'target: BRIEF.md' decisions/0063-*.yaml; then
        note "D0063 already upgraded — skipped"
    elif confirm "Add manifest:BRIEF.md to D0063?"; then
        python3 - <<'PY'
import glob, pathlib
path = pathlib.Path(glob.glob("decisions/0063-*.yaml")[0])
src = path.read_text()
anchor = src.rstrip().rsplit("\n", 1)[-1] + "\n"
assert anchor.startswith("links: ["), f"expected a links: line last, got {anchor!r}"
addition = (
    "  - type: manifest\n"
    "    target: BRIEF.md\n"
    "    detail: >-\n"
    "      ENFORCED, added at the M1 boundary sitting (2026-08-27): ruling 5's\n"
    "      amendment (the metric-calibration bullet and the signature-as-presence-vs-\n"
    "      authorisation distinction) is applied to BRIEF.md at this sitting's step 4b,\n"
    "      and BRIEF.md is in MANIFEST.sha256, so the prior documentary binding\n"
    "      upgrades to enforced.\n"
)
src = src[: -len(anchor)] + addition + anchor
path.write_text(src)
PY
        git --no-pager diff decisions/0063-*.yaml
        if confirm "Keep this edit and re-sign D0063?"; then
            rm -f decisions/0063-*.yaml.sig
            sign_owner "$(ls decisions/0063-*.yaml)" tannen-decision
        else
            git checkout -- decisions/0063-*.yaml
            note "reverted — D0063 keeps its documentary-only binding"
        fi
    fi
fi

stop_after 4c

# ---------------------------------------------------------------- 4d. the operating manual
say "Step 4d — CLAUDE.md tells every session to run a command that checks nothing (D0108)"
if grep -q 'lint-imports --config governance/importlinter.toml' CLAUDE.md; then
    note "CLAUDE.md already passes the config — skipped"
else
    note "CLAUDE.md's Verification block says 'uv run lint-imports'. Run exactly as"
    note "written it prints 'Could not read any configuration.' and reads NO contracts:"
    note "they moved to governance/importlinter.toml as RT-02's resolution (D0063 ruling"
    note "3). The Makefile and scripts/custodian.sh were both updated to pass --config;"
    note "the manual was not, and it is the file an agent follows at the start of every"
    note "session. CI was never unprotected — it runs the Makefile. The instruction is"
    note "what is wrong, and it fails in the direction that reads as green."
    note ""
    note "TWO FILES MOVE TOGETHER, and that is the whole reason this is a step and not a"
    note "one-line hand edit. tests/test_operating_manual.py (D0111) compares the manual"
    note "against 'make verify' and tolerates exactly this divergence BY NAME. The moment"
    note "CLAUDE.md is correct that test FAILS ON PURPOSE — 'D0108 is FIXED ... delete the"
    note "entry from KNOWN_DIVERGENCES' — and step 9's gate would stop this sitting over"
    note "it, after fifteen minutes, with your key out. So the fix and the retirement of"
    note "its tolerance are one edit, confirmed once, reverted together."
    if python3 - <<'PY'
import pathlib, sys

manual = pathlib.Path("CLAUDE.md")
src = manual.read_text(encoding="utf-8")
old = "uv run lint-imports               # kernel has no IO; no cross-repo imports\n"
new = ("uv run lint-imports --config governance/importlinter.toml   "
       "# kernel has no IO; no cross-repo imports\n")
if src.count(old) != 1:
    sys.exit("CLAUDE.md's lint-imports line is not the expected one — apply by hand")

test = pathlib.Path("tests/test_operating_manual.py")
tsrc = test.read_text(encoding="utf-8")
# The COMMENT goes with the entry. A tolerance map whose entry is gone but whose comment
# still explains why the entry is there is the same class of defect as the stale CLAUDE.md
# line this step exists to fix — prose describing a state the code left behind.
block = """#: The one divergence that exists today, and why it is still here. D0108 is Tier C: the fix
#: is one line in CLAUDE.md, which is frozen AND custody-set, so only the owner may make it.
#: When they do, this test fails with the message below and the entry gets deleted in the
#: same sitting. A SECOND entry should never be added without a decision record saying why.
KNOWN_DIVERGENCES = {
    ("import-linter", None, "governance/importlinter.toml"): "D0108",
}
"""
replacement = """#: Empty since the M1 boundary sitting, where D0108's one-line fix to CLAUDE.md landed and
#: this entry was deleted in the same step (D0113). The map stays as the declared home for a
#: tolerated divergence: a new entry needs a decision record saying why the manual and the
#: gate are allowed to disagree, and the tests below keep one honest once it exists.
KNOWN_DIVERGENCES: dict[tuple[str, str | None, str | None], str] = {}
"""
if tsrc.count(block) != 1:
    sys.exit("KNOWN_DIVERGENCES is not the expected block — apply by hand")

manual.write_text(src.replace(old, new), encoding="utf-8")
test.write_text(tsrc.replace(block, replacement), encoding="utf-8")
PY
    then
        git --no-pager diff CLAUDE.md tests/test_operating_manual.py
        if confirm "Keep BOTH edits?"; then
            regen_manifest_row CLAUDE.md
            note "D0108 is applied. Step 8 will offer to accept and sign the record; this"
            note "step is what makes accepting it there true rather than aspirational."
        else
            git checkout -- CLAUDE.md tests/test_operating_manual.py
            note "reverted — both files. CLAUDE.md keeps the line that checks nothing, and"
            note "D0111 keeps tolerating it; leave D0108 blocked at step 8 to match."
        fi
    else
        note "the edit did not apply cleanly (message above) — nothing was changed."
        note "Leave D0108 blocked at step 8 and hand it back to a builder session."
    fi
fi

stop_after 4d

# ---------------------------------------------------------------- 4e. the law registry
say "Step 4e — the supersession registry's real hinge is conftest.py, not laws.yaml (D0131 item 3, as RT-M2-02 corrects it)"
if grep -q '^    - scripts/check_laws\.py$' governance/tier-c.yaml; then
    note "already in the custody set — skipped"
else
    note "D0131 item (3) asked for scripts/check_laws.py AND governance/laws.yaml in the"
    note "custody set: 'a guard that can retire a frozen law, and the data it reads'."
    note "THE M2 RED TEAM SHOWED THE SECOND HALF DOES NOT WORK (RT-M2-02, D0141)."
    note ""
    note "conftest.py:24 reads SUPERSEDED_REGISTRY = ROOT/'governance'/'laws.yaml'. That"
    note "line does not read the registry — IT CHOOSES WHICH FILE IS THE REGISTRY. Point"
    note "it at a second file and a law is retired with laws.yaml BYTE-IDENTICAL and its"
    note "signature verifying. Reproduced: the pin in tests/test_law_validation.py caps the"
    note "real registry at one entry and passed unmodified throughout. Signing the data"
    note "while the pointer stays builder-editable buys nothing at all."
    note ""
    note "SO THE SET IS conftest.py AND scripts/check_laws.py — the two files that decide"
    note "where the registry lives. check_laws.py hardcodes the same path (line 44) and is"
    note "the only guard in NEITHER the manifest nor the custody set, while eight sibling"
    note "scripts are custody-set."
    note ""
    note "governance/laws.yaml IS DELIBERATELY LEFT OUT, and this is the trade to weigh:"
    note "custodying it would make every future pending→superseded promotion an owner act"
    note "at a sitting, which is exactly the two-line builder move D0128 was designed to"
    note "make cheap. Left out, the residual attack is not 'edit a line' but 'invent a"
    note "successor law and a decision record' — which check_laws.py already refuses"
    note "unless both exist (check_laws.py:16-18), and which leaves a written trail. If"
    note "you want the stronger property anyway, add '- governance/laws.yaml' to the same"
    note "block by hand before answering; nothing below depends on its absence."
    note ""
    note "NOT PROPOSED, and the reason matters: tests/test_law_validation.py. It is the"
    note "file the attack also edits, so freezing it is tempting — but it changes at every"
    note "milestone by design (it pins the current registry's single entry by name), and"
    note "custodying it would halt Session B until a sitting. The answer to that file is"
    note "D0131 item (4), the step below: get check_laws.py into the gate directly, so it"
    note "no longer reaches the gate only as a subprocess of the file under attack."
    note ""
    note "COST, stated before you sign it: after this, ANY edit to conftest.py turns the"
    note "gate red until the next sitting re-signs. conftest.py is the composition root"
    note "for the evidence plugin and the Hypothesis profile — M2 edited it once, for"
    note "D0128. Expect roughly one sitting-sized edit per milestone, not none."
    if python3 - <<'PY'
import pathlib, sys

p = pathlib.Path("governance/tier-c.yaml")
src = p.read_text(encoding="utf-8")
# conftest.py sits with the repo-root files it belongs to; check_laws.py with its eight
# sibling guards, in the order they run. Anchored on the line AFTER each insertion point
# so a reordering of the block fails loudly here instead of silently misplacing a path.
edits = [
    ("    - .pre-commit-config.yaml\n", "    - conftest.py\n"),
    ("    - scripts/check_receipts.py\n", "    - scripts/check_laws.py\n"),
]
for anchor, addition in edits:
    if src.count(anchor) != 1:
        sys.exit(f"tier-c.yaml's custody block is not the expected shape at {anchor.strip()!r} — apply by hand")
    if addition in src:
        sys.exit(f"{addition.strip()!r} is already present — apply by hand")
    src = src.replace(anchor, anchor + addition)
p.write_text(src, encoding="utf-8")
PY
    then
        git --no-pager diff governance/tier-c.yaml
        if confirm "Add conftest.py and scripts/check_laws.py to the custody set?"; then
            regen_manifest_row governance/tier-c.yaml
            note "added. Step 7 regenerates governance/custody.sha256 from this list and"
            note "signs it; until then check_manifest reports the set as stale, which is"
            note "this sitting working rather than this sitting broken."
        else
            git checkout -- governance/tier-c.yaml
            note "reverted — the registry's pointer stays builder-editable and RT-M2-02"
            note "stays open. Say so in the receipt; a declined finding is a decision."
        fi
    else
        note "the edit did not apply cleanly (message above) — nothing was changed."
    fi
fi

stop_after 4e

# ---------------------------------------------------------------- 4f. gate wiring
say "Step 4f — check_laws.py reaches the gate only through the file an attacker edits (D0131 item 4, D0152 item 2)"
# THE GUARD BELOW TESTS ALL THREE FILES THE DECLINE BRANCH REVERTS, and at M2 it tested one
# (D0152 item 2). It asked only `grep -q 'scripts/check_laws.py' Makefile` while the decline
# branch ran `git checkout -- Makefile .github/workflows/ci.yml tests/test_law_validation.py`.
# The set the guard read was a strict SUBSET of the set the branch wrote, so any state where
# the Makefile edit survived and the other two did not read as "already applied — skipped"
# for ever.
#
# That state is not hypothetical: it is the tree you are standing in. D0153 records two
# concurrent runs of this driver, one of which reverted the other's work; the Makefile line
# and the docstring landed, ci.yml's comment did not, and no gate could see the difference
# because the lost bytes are a comment. The subset guard is why it was never re-offered.
# MEASURED 2026-09-08: Makefile:40 runs check_laws.py, tests/test_law_validation.py's
# docstring is corrected, and .github/workflows/ci.yml has no mention of check_laws at all.
gate_wiring_complete() {
    grep -q 'scripts/check_laws\.py' Makefile \
        && grep -q 'RT-M2-02' .github/workflows/ci.yml \
        && grep -q '`make verify` step in its own right' tests/test_law_validation.py
}
if gate_wiring_complete; then
    note "already wired in all three files — skipped"
else
    note "scripts/check_laws.py has run at every commit since D0129 — but only as a"
    note "SUBPROCESS launched from tests/test_law_validation.py. RT-M2-02 is why that is"
    note "the wrong shape: the attack on the supersession registry edits that very file,"
    note "and a guard reachable only through the thing it guards is a guard with an off"
    note "switch. Step 4e signed the registry's two pointers; this step gives the guard"
    note "its own way in."
    note ""
    note "TWO OF THE THREE EDITS ARE ALREADY IN THE TREE. The Makefile line and the"
    note "docstring landed at the M2 sitting; ci.yml's comment was reverted by a second,"
    note "concurrent run of this driver and never re-offered, because the guard that"
    note "decides whether to offer read only the Makefile (D0153 artifact 1, D0152 item"
    note "2). The block below applies each file independently and says which it touched."
    note ""
    note "AND CI.YML'S HEADER IS NOW FALSE TWICE OVER. It says 'this file has never"
    note "actually run: the repo has no remote' and that adding one is an unopened"
    note "Tier-C door. The door was opened by D0115 and walked through at the"
    note "publication sitting (D0176); this workflow first ran on 2026-09-08 and has"
    note "taken a full 'make verify' on every push since. D0195 item (2) files it. It is"
    note "corrected in the same replacement — one frozen file, one edit, one manifest row."
    note ""
    note "LIVENESS IS ALREADY PROVEN, so this does not add an unproven guard to the floor:"
    note "tests/test_law_validation.py builds five trees in tmp_path where check_laws MUST"
    note "exit non-zero. What it lacked at M2 was a tests/poison/ fixture and a custodian"
    note "matrix line, so the custodian could not say the guard has teeth. THAT GAP CLOSES"
    note "IN THIS SITTING: step 5 installs tests/poison/check-laws-dropped-successor/ and"
    note "step 6's custodian draft carries its poison line (D0154 item 7, D0199)."
    if python3 - <<'PY'
import pathlib, sys

# Each file is applied INDEPENDENTLY and each reports one of three states. The script
# refuses only when a file is in neither the pre- nor the post-state, because that is the
# only case where it cannot tell "already done" from "changed underneath me". This shape
# is the fix for D0152 item 2: a partial application must be completable, not skipped.
touched, already = [], []

def edit(path, old, new, marker):
    """marker present -> already applied; old present -> apply; neither -> refuse."""
    f = pathlib.Path(path)
    src = f.read_text(encoding="utf-8")
    if marker in src:
        already.append(path)
        return src, False
    if src.count(old) != 1:
        sys.exit(f"{path}: neither applied nor in the expected pre-state "
                 f"({src.count(old)} matches for the anchor) — apply by hand")
    touched.append(path)
    return src.replace(old, new), True

# --- 1. the Makefile: the whole functional change, one line ------------------------
mk_anchor = "\t$(UNHATCH) $(PY) -I -P scripts/check_receipts.py\n"
mk_add    = "\t$(UNHATCH) $(PY) -I -P scripts/check_laws.py\n"
mk_src, mk_do = edit("Makefile", mk_anchor, mk_anchor + mk_add, "scripts/check_laws.py")

# --- 2. ci.yml: the paragraph D0153 lost, AND the header D0195 item (2) falsified ---
ci_old = """# This file has never actually run: the repo has no remote (D0061 rationale, and the
# reason `make verify` on one machine is currently the whole enforcement surface).
# Adding a remote is a Tier-C door in its own right (external-bytes); when it opens, the
# justification is the receipt chain's need for an unrewritable witness, not backup.
"""
ci_new = """# Since the M2 boundary the gate also runs scripts/check_laws.py directly: every frozen
# law file declares how it was validated, and every retired law names a live successor and
# a decision record (D0129, D0131 item 4). It reached the gate before this only from
# tests/test_law_validation.py — the file RT-M2-02's attack on the supersession registry
# edits, so a guard reachable only through the thing it guards.
#
# THIS FILE NOW RUNS. It first ran on 2026-09-08, against the published repository. The
# paragraph that stood here until the M3 boundary sitting said the opposite: that the file
# "has never actually run: the repo has no remote", and that adding one was "a Tier-C door
# in its own right". Both halves were true when written and both were false long before
# anyone read them again — the door was opened by D0115 and walked through by D0176's
# publication sitting. `make verify` on one machine is no longer the whole enforcement
# surface, and that matters beyond bookkeeping: D0191 asserted a Python floor that no local
# run could falsify and CI falsified it on its first pass (D0194). A claim only one machine
# can check is a claim this project should not rest on. Filed as D0195 item (2), corrected
# here because this file is frozen and custody-set and a sitting is the only place it moves.
"""
ci_src, ci_do = edit(".github/workflows/ci.yml", ci_old, ci_new, "RT-M2-02")

# --- 3. the docstring that would otherwise start lying ------------------------------
t_old = """It also drives `scripts/check_laws.py`, which is not yet in `make verify` — the Makefile
and the CI workflow are custody-set, so wiring it in waits for the M2 boundary sitting
(D0131). Reaching a guard from pytest in the meantime is the D0070/D0123 pattern: the
custodian is the floor, and pytest is the distance between weakening a guard and finding
out.
"""
t_new = """It also drives `scripts/check_laws.py`, which since the M2 boundary sitting is a
`make verify` step in its own right (D0131 item 4). Driving it from pytest as well is
not redundant: the five trees below make it FAIL, which the gate's success path never
does — the custodian is the floor, and pytest is the distance between weakening a guard
and finding out.
"""
# The marker must not span the docstring's line break: the file reads "... is a\n`make
# verify` step ...", so an anchor beginning "a `make verify`" matches nothing and the edit
# refuses a file that is already correct. Caught by running this block against the tree.
t_src, t_do = edit("tests/test_law_validation.py", t_old, t_new,
                   "`make verify` step in its own right")

if not touched:
    sys.exit("all three files are already wired — nothing to do (the guard should have skipped)")
if mk_do: pathlib.Path("Makefile").write_text(mk_src, encoding="utf-8")
if ci_do: pathlib.Path(".github/workflows/ci.yml").write_text(ci_src, encoding="utf-8")
if t_do:  pathlib.Path("tests/test_law_validation.py").write_text(t_src, encoding="utf-8")
print("   already applied: " + (", ".join(already) or "none"))
print("   edited now:      " + ", ".join(touched))
PY
    then
        git --no-pager diff Makefile .github/workflows/ci.yml tests/test_law_validation.py
        if confirm "Wire check_laws.py into the gate (whichever of the three edits were outstanding)?"; then
            # ci.yml ONLY. Custody membership and MANIFEST rows are independent sets and
            # this is where that bites: the Makefile is in the custody set and has NO
            # manifest row (nor do .pre-commit-config.yaml, governance/policy.yaml,
            # scripts/_gov.py, check_decisions.py or gen_projections.py). Calling
            # regen_manifest_row on it would not refresh a row — it would CREATE one,
            # silently enlarging the frozen-path set at a sitting, which is a Tier-C-shaped
            # change nobody asked for. Step 7's gen_custody.py is what covers the Makefile.
            # tests/test_law_validation.py is in neither set, by design (D0131 item 3).
            regen_manifest_row .github/workflows/ci.yml
            note "wired. Step 9's gate is the first run that includes it; if check_laws"
            note "goes red there it is reporting a real defect in the law registry, not a"
            note "defect in this step."
        else
            git checkout -- Makefile .github/workflows/ci.yml tests/test_law_validation.py
            note "reverted — all three, including any that were already applied before this"
            note "step ran. Re-run the sitting to be offered them again: the guard above now"
            note "reads the whole set, so a partial state is offered rather than skipped."
        fi
    else
        note "the edit did not apply cleanly (message above) — nothing was changed."
    fi
fi

stop_after 4f

# ---------------------------------------------------------------- 4g. projection drift
say "Step 4g — DECISIONS.md asserts the receipt is FRESH from a hash that cannot see the clock (RT-M2-05)"
if grep -q "attention-receipt line is not what today computes" scripts/check_decisions.py; then
    note "already applied — skipped"
else
    note "gen_decisions renders TWO things from the clock: the literal line"
    note "'Attention receipt: **FRESH** — …' (DECISIONS.md:10) and every Tier-B record's"
    note "effective status column. The freshness guard compares input_hash over"
    note "decisions/*.yaml AND NOTHING ELSE (check_decisions.py:334-341). Neither \`today\`"
    note "nor receipts/ is an input, and \`make verify\` never runs \`make projections\`."
    note ""
    note "SO ON 2026-09-08 THE FILE WILL STILL SAY 'FRESH — fresh until 2026-09-07' while"
    note "check_decisions prints STALE, and no guard will disagree. D0018's own decision"
    note "text promises the opposite: 'while stale … DECISIONS.md and the digest show the"
    note "accumulating blocks.' Nothing makes that true. Reproduced both ways on"
    note "2026-09-01: the shipped guard exits 0 at --today 2026-09-08 with the file"
    note "asserting FRESH; the patch below exits 1 with four violations naming the header"
    note "and D0006/D0014/D0020."
    note ""
    note "WHY THE FIX IS NOT A WIDER HASH. gen_digest already folds decisions/*.yaml.sig"
    note "and receipts/*.md* into its own input list, with a comment saying digest CONTENT"
    note "must be digest INPUT (gen_projections.py:196-202) — the same reasoning was simply"
    note "never carried one file over. But it would not be enough here: the receipt's bytes"
    note "do not change when it goes stale, only the date does, and \`today\` can never be a"
    note "file. So the guard compares the CLAIM the projection makes against the one this"
    note "run computes. It does not import gen_projections — a guard that re-renders through"
    note "the generator it audits renders the same mistake into both sides."
    note ""
    note "DISTINCT FROM RT-07 (digests are not hash-checked at all). Here the hash IS"
    note "checked and is simply blind to what varies. Why it stayed hidden: every session"
    note "so far added a record, which moves the hash and forces a regeneration. The drift"
    note "is only visible on a day when nothing lands."
    note ""
    note "AND IT TAKES A TEST FILE WITH IT, which a REHEARSAL found and reading did not."
    note "tests/test_tier_c_signatures.py builds a throwaway tree and writes a DECISIONS.md"
    note "that is a bare input-hash header — enough to satisfy the hash check, and from the"
    note "moment the patch below lands, not enough to be a fresh projection. Four of its"
    note "seven cases assert exit 0 and all four went red. The fixture is corrected in the"
    note "SAME edit, from receipt_state — the function the guard itself calls — so a tree"
    note "with no receipts/ states the STALE verdict it actually has rather than faking a"
    note "FRESH one. Landing the guard without it would close the sitting on a red suite."
    if python3 - <<'PY'
import pathlib, sys

p = pathlib.Path("scripts/check_decisions.py")
src = p.read_text(encoding="utf-8")

old_import = "    binding_strengths,\n    input_hash,\n"
new_import = "    binding_strengths,\n    effective_status,\n    input_hash,\n"
if src.count(old_import) != 1:
    sys.exit("check_decisions.py's _gov import block is not the expected shape — apply by hand")

anchor = '''        elif actual != expected:
            fail.add("DECISIONS.md is stale (input-hash mismatch) — run make projections; never hand-edit")
'''
addition = '''
    # RT-M2-05 (D0141): the hash above covers decisions/*.yaml and NOTHING ELSE, so it is
    # blind to the two things gen_decisions renders from the clock — the attention-receipt
    # verdict and every Tier-B record's effective status. `today` can never be a file, so
    # the fix is not a wider hash; it is to compare the CLAIM the projection makes against
    # the one this run computes. Left alone, DECISIONS.md goes on asserting
    # "Attention receipt: **FRESH**" after the receipt has gone stale, with every guard
    # green — the precise opposite of what D0018's own text promises ("while stale …
    # DECISIONS.md and the digest show the accumulating blocks").
    #
    # Compared, not re-rendered. Importing gen_projections here would make the guard depend
    # on the generator it audits, and a generator that renders the wrong thing would then
    # render it into both sides of the comparison.
    if projection.exists():
        body = projection.read_text(encoding="utf-8")
        want = f"Attention receipt: **{'FRESH' if receipts_fresh else 'STALE'}** — {receipt_detail}"
        if want not in body:
            fail.add(f"DECISIONS.md's attention-receipt line is not what today computes "
                     f"({want!r}) — run make projections")
        # Only the records whose status CAN move with the date. Checking every row would
        # duplicate the input hash for the ones that cannot, and would report one defect
        # twice under two names.
        for rec in valid_records:
            if rec.get("veto_by") is None:
                continue
            status = effective_status(rec, args.today, receipts_fresh)
            row = next((ln for ln in body.splitlines()
                        if ln.startswith(f"| {rec['id']} |")), None)
            if row is None:
                fail.add(f"DECISIONS.md has no row for {rec['id']} — run make projections")
            elif f"| {status} |" not in row:
                fail.add(f"DECISIONS.md reports {rec['id']} as something other than "
                         f"{status!r}, which is what today computes — run make projections")
'''
if src.count(anchor) != 1:
    sys.exit("check_decisions.py's projection-freshness block is not the expected one — apply by hand")

# THE THIRD FILE MOVES WITH THE OTHER TWO HERE TOO. tests/test_tier_c_signatures.py is
# neither frozen nor custody-set, so it needs no signature — but its `run()` helper writes
# a DECISIONS.md that is a bare header, and the check above turns four of its seven cases
# red the instant it lands. Same shape as step 4f (the Makefile and its docstring) and step
# 4i (the schema, the check, and the test). Found by rehearsing, not by reading: the M2
# rehearsal reported D0063 and D0064's bindings on this file as "pytest node fails".
t = pathlib.Path("tests/test_tier_c_signatures.py")
tsrc = t.read_text(encoding="utf-8")
t_import = "from _gov import git_env, input_hash  # noqa: E402\n"
t_import_new = "from _gov import git_env, input_hash, receipt_state  # noqa: E402\n"
t_dt = "import subprocess\nimport sys\n"
t_dt_new = "import datetime as dt\nimport subprocess\nimport sys\n"
t_old = '''        paths = sorted((root / "decisions").glob("*.yaml"))
        (root / "DECISIONS.md").write_text(header(input_hash(paths, root)))
'''
t_new = '''        #
        # RT-M2-05 gave the projection a SECOND thing it must carry: the attention-receipt
        # line this run computes, because the input hash above cannot see the clock. A bare
        # header stopped being a fresh projection the moment that check landed, and this
        # fixture said so by turning every exit-0 case below red. Rendered from
        # `receipt_state` — the function the guard itself calls — so a throwaway tree with
        # no receipts/ states the STALE verdict it actually has instead of faking a FRESH
        # one. The record cases are unaffected: none of them carries a veto_by, so the
        # guard's Tier-B row comparison has nothing to look for.
        paths = sorted((root / "decisions").glob("*.yaml"))
        fresh, detail = receipt_state(root, dt.date.fromisoformat(TODAY))
        (root / "DECISIONS.md").write_text(
            header(input_hash(paths, root))
            + f"\\nAttention receipt: **{'FRESH' if fresh else 'STALE'}** — {detail}\\n")
'''
for name, text in (("_gov import", t_import), ("stdlib imports", t_dt), ("run() helper", t_old)):
    if tsrc.count(text) != 1:
        sys.exit(f"tests/test_tier_c_signatures.py's {name} is not the expected shape "
                 f"({tsrc.count(text)} matches) — apply by hand")

p.write_text(src.replace(old_import, new_import).replace(anchor, anchor + addition),
             encoding="utf-8")
t.write_text(tsrc.replace(t_dt, t_dt_new).replace(t_import, t_import_new)
                 .replace(t_old, t_new), encoding="utf-8")
PY
    then
        git --no-pager diff scripts/check_decisions.py tests/test_tier_c_signatures.py
        if confirm "Make DECISIONS.md's date-dependent claims checkable?"; then
            note "applied. scripts/check_decisions.py is custody-set and carries no manifest"
            note "row, so there is nothing to re-manifest — step 7's gen_custody covers it."
            note "Step 9 regenerates projections BEFORE running the gate, so the new check"
            note "sees a freshly rendered file; if it fires there, read it as the projection"
            note "being stale rather than as this patch being wrong."
        else
            git checkout -- scripts/check_decisions.py tests/test_tier_c_signatures.py
            note "reverted — DECISIONS.md keeps asserting a freshness no guard can check."
            note "Both files revert together; the fixture is only correct beside the guard."
        fi
    else
        note "the edit did not apply cleanly (message above) — nothing was changed."
    fi
fi

stop_after 4g

# ---------------------------------------------------------------- 4h. D0123's batch
say "Step 4h — three signed Tier-C records now say something false in the present tense (D0123, D0131 item 7)"
note "D0123 deferred 'any binding upgrade they want' on the thirteen signed Tier-C records"
note "to this sitting, without naming which ones. Audited on 2026-09-01: THREE have an"
note "upgrade that is honest, and ten do not. Ten is the useful half of that answer —"
note "an upgrade is only real if the artifact now mechanically prevents or detects the"
note "violation, and inventing eleven more would make 'enforced' mean nothing."
note ""
note "  D0110  file: src/tannen/kernel/rel.py — detail says 'where the check WOULD go'."
note "         The check is there: _refuse_unwitnessed at rel.py:93, called from _init at"
note "         :155. A pytest binding on frozen L2.2 is added beside it."
note "  D0108  manifest: CLAUDE.md — detail says 'the text to correct'. It was corrected"
note "         at the M1 sitting (c5d53c9) and CLAUDE.md's manifest row pins the CORRECTED"
note "         bytes, so a regression turns check_manifest red."
note "  D0095  config: tag-roles.yaml#required_tags — detail says 'nothing here is enforced"
note "         yet ... upgrades when the owner applies either half'. Half (1) was applied"
note "         at M1. Half (2) was not, and the new text says so rather than rounding up."
note ""
note "AND TEN WITH NOTHING TO UPGRADE, so you can see the audit was two-sided: D0049 and"
note "D0063 were already upgraded at the M1 sitting (step 4c above will say 'skipped');"
note "D0036 at the opening sitting; D0060, D0061, D0105 are documentary BY NATURE and their"
note "own details say so; D0047 named no upgrade; D0106, D0115 and D0117 name mechanisms"
note "that are still unbuilt — D0117's evidence schema has not changed since M0."
note ""
note "EACH IS EDIT-THEN-SIGN, ONE RECORD AT A TIME, like step 4c and step 8. Batch-editing"
note "then batch-signing would leave every record edited and unsigned if one passphrase is"
note "mistyped — a red gate with no builder-side fix, which is the state D0070 and D0123"
note "exist to avoid. Each edit costs TWO failures until its signature lands: the record's"
note "own, and DECISIONS.md going stale. Step 9 regenerates the projection; step 11 does"
note "NOT, which is why this cannot be deferred to there."
for rec_id in D0110 D0108 D0095; do
    if ! out=$(python3 "$PROPOSALS_M2/upgrade_binding.py" "$rec_id" 2>&1); then
        note "$rec_id: ${out##*: }"
        continue
    fi
    rec="$out"
    git --no-pager diff -- "$rec"
    if confirm "Keep $rec_id's upgrade and re-sign it?"; then
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
        note "reverted — $rec_id keeps a binding whose detail is false in the present tense."
    fi
done
# REGENERATE NOW, not at step 9. Editing a decision record restales DECISIONS.md, and
# step 5 — before step 7, where the rehearsal harness still reports every ": FAIL" line —
# runs check_decisions to see whether moving the fixtures broke a binding. Without this the
# step prints "DECISIONS.md is stale (input-hash mismatch)" and, since RT-M2-05's check
# landed at 4g, three more lines about effective statuses. None of them stops the sitting
# (step 5 greps only for "binding does not resolve"), but all of them surface in the
# rehearsal's unexpected-failure list and in the owner's terminal as a red FAIL in the
# middle of a working sitting. Step 9 regenerates again; this one is idempotent and costs a
# second. Note that until M2 every record-editing step above was an already-applied skip,
# which is why no earlier sitting met this.
"$PY" -I -P scripts/gen_projections.py >/dev/null \
    || note "projection regeneration failed — step 9 will try again"

stop_after 4h

# ---------------------------------------------------------------- 4i. bindings_count
say "Step 4i — a guard checks that a record is well-formed, never that it says what its author meant (D0131 item 8 = D0106 item 1)"
if grep -q '"bindings_count"' governance/schemas/decision-record.schema.json; then
    note "already applied — skipped"
else
    note "D0049 carried a bindings list whose third entry had been folded into the second's"
    note "detail block. Schema-valid. Both remaining targets resolving. Every guard green."
    note "Silently one binding short of what its author wrote. D0106 item (1)'s answer is a"
    note "checksum over authorial intent: the author states the count, and the guard"
    note "compares it with the list. Same class as RT-10 — a binding satisfied by a target"
    note "that merely exists rather than one that enforces anything."
    note ""
    note "TWO HALVES, AND THEY MUST LAND TOGETHER. The schema has"
    note "\"additionalProperties\": false, so a record carrying bindings_count is INVALID"
    note "until the schema knows the field; and the field is inert decoration until"
    note "check_decisions reads it. Applying one without the other is worse than neither."
    note ""
    note "THE FIELD IS OPTIONAL, which is stage one of D0106's own three-stage plan"
    note "(optional -> backfill opportunistically -> tighten to required). All 142 existing"
    note "records validate unchanged against the patched schema — measured, 0 failures."
    note "DO NOT MASS-BACKFILL: a count computed as len(bindings) is a checksum of the"
    note "bytes over themselves and proves nothing. It accrues to records a human re-reads."
    note ""
    note "SO THE SUMMARY LINE REPORTS 0/142 AT FIRST, and that is deliberate. A check that"
    note "cannot fail is not a check (D0116); printing how many records the checksum"
    note "actually covers states that as a number instead of a silence, which is the move"
    note "D0129 made with check_laws.py's exempt count."
    note ""
    note "NO POISON FIXTURE THIS SITTING, said plainly rather than left to be noticed. Its"
    note "liveness is proven from pytest — tests/test_governance_scripts.py gets a test that"
    note "builds two records, one lying and one honest, and requires the guard to catch the"
    note "first WITHOUT flagging the second (otherwise the check is a ban on the field"
    note "rather than a comparison). A tests/poison/ fixture would also need a new tuned"
    note "custodian copy, and manufacturing one days before a deadline for a check that"
    note "currently covers zero records is the wrong trade. Queue it for M3."
    if python3 - <<'PY'
import pathlib, sys

schema = pathlib.Path("governance/schemas/decision-record.schema.json")
ssrc = schema.read_text(encoding="utf-8")
# SELF-GUARDED, not merely guarded by the shell grep above. The anchor below is the
# property this block inserts BEFORE, so it survives the first application unchanged and a
# second run would insert a duplicate JSON key and a duplicate Python block — both of which
# parse. Every other step's heredoc refuses on its own; this one must too, or the outer
# grep is a single point of failure. Caught by applying it twice in a sandbox.
if '"bindings_count"' in ssrc:
    sys.exit("bindings_count is already in the decision schema — nothing to do")
anchor = '''    "unenforced_reason": {'''
addition = '''    "bindings_count": {
      "type": "integer",
      "minimum": 0,
      "description": "Optional checksum over authorial intent (D0106 item 1): the number of bindings the author MEANT this record to carry. check_decisions.py fails when it disagrees with the actual length of `bindings`. Optional so records written before it existed stay valid; a new record states it. D0049 is the failure it is aimed at — a folded YAML list, still schema-valid, still resolving, silently one binding short."
    },
'''
if ssrc.count(anchor) != 1:
    sys.exit("the decision schema's unenforced_reason property is not where expected — apply by hand")

checker = pathlib.Path("scripts/check_decisions.py")
csrc = checker.read_text(encoding="utf-8")
decl = "    tier_c_queued: list[str] = []\n"
decl_new = decl + "    counted: list[str] = []\n"
canchor = '''        if not record["bindings"]:
            unenforced.append(f"{rid} ({record['title']}): {record['unenforced_reason']}")
'''
caddition = '''
        # D0106 item (1). A guard verifies that a record is WELL-FORMED, never that it says
        # what its author meant: D0049 carried a folded YAML list that was valid, resolved,
        # and was silently one binding short. `bindings_count` is the author's own count of
        # the same fact, so the two can be made to disagree out loud. Optional by design —
        # absent means the record makes no claim and nothing is checked, which is why the
        # summary reports the coverage rather than implying the checksum is universal.
        declared = record.get("bindings_count")
        if declared is not None:
            counted.append(rid)
            if declared != len(record["bindings"]):
                fail.add(
                    f"{rel}: bindings_count is {declared} but the record carries "
                    f"{len(record['bindings'])} binding(s) — the author's count and the "
                    "file's bytes disagree (D0106 item 1, the D0049 failure mode)."
                )
'''
summary = '''        f"{len(unenforced)} unenforced (with reasons); "
'''
summary_new = summary + '''        f"{len(counted)}/{len(record_paths)} declare bindings_count; "
'''
for name, text, count in (("declaration", decl, csrc.count(decl)),
                          ("unenforced block", canchor, csrc.count(canchor)),
                          ("summary line", summary, csrc.count(summary))):
    if count != 1:
        sys.exit(f"check_decisions.py's {name} is not the expected shape ({count} matches) — apply by hand")

# THE THIRD FILE MOVES WITH THE OTHER TWO. tests/test_governance_scripts.py is neither
# frozen nor custody-set, so it needs no signature — but the test below cannot pass until
# the schema knows the field, so landing it separately means landing it red. Same shape as
# step 4d (CLAUDE.md and its tolerance map) and step 4f (the Makefile and its docstring).
tests = pathlib.Path("tests/test_governance_scripts.py")
tsrc = tests.read_text(encoding="utf-8")
if "bindings_count that lies" in tsrc:
    sys.exit("the bindings_count regression test is already present — apply by hand")
tsrc += '''

def test_a_bindings_count_that_disagrees_with_the_list_is_caught(tmp_path: Path) -> None:
    """D0106 item (1). A guard verifies that a record is WELL-FORMED, never that it says
    what its author meant. D0049 carried a `bindings` list whose third entry had been
    folded into the second's `detail` block: schema-valid, both remaining targets
    resolving, every guard green, and the record silently one binding short of what it
    claimed. `bindings_count` is the author's own count of the same fact, so the two can
    be made to disagree out loud.

    Constructs its own tree (D0092: a regression test constructs the state that
    distinguishes the fixed code from the broken code, never observes it) rather than
    reading a tests/poison/ fixture — installing one there is the owner's act, and this
    sitting deliberately did not manufacture a new custodian copy for a check that today
    covers zero records.

    TWO records, because "check_decisions exited non-zero" alone would also be satisfied
    by a guard that rejects the FIELD rather than the DISAGREEMENT. The honest record must
    pass with its count present, or the check is a ban on the field and not a checksum.
    """
    root = tmp_path / "tree"
    (root / "decisions").mkdir(parents=True)
    common = ('tier: A\\n'
              'date: "2020-01-02"\\n'
              "rationale: D0106 item 1 probe.\\n"
              "reversibility: n/a (probe)\\n"
              "status: accepted\\n")
    (root / "decisions" / "0001-count-disagrees.yaml").write_text(
        "id: D0001\\n"
        "title: Probe -- the author counted three bindings and the file holds two\\n"
        + common +
        "decision: Claim three bindings and carry two, the way D0049 did.\\n"
        "bindings_count: 3\\n"
        "bindings:\\n"
        "  - type: file\\n"
        "    target: decisions\\n"
        "  - type: file\\n"
        "    target: decisions/0001-count-disagrees.yaml\\n"
        "    detail: >-\\n"
        "      and a third binding folded in here instead of written as its own list\\n"
        "      entry -- still valid YAML, still resolving, still one short.\\n",
        encoding="utf-8")
    (root / "decisions" / "0002-count-agrees.yaml").write_text(
        "id: D0002\\n"
        "title: Probe -- an honest count is not a violation\\n"
        + common +
        "decision: State the count and carry exactly that many bindings.\\n"
        "bindings_count: 1\\n"
        "bindings:\\n"
        "  - type: file\\n"
        "    target: decisions/0002-count-agrees.yaml\\n",
        encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k != "TANNEN_CHECK_DECISIONS_NESTED"}
    result = run([sys.executable, "scripts/check_decisions.py", "--root", str(root)], env=env)
    out = result.stdout + result.stderr
    assert result.returncode != 0, f"a bindings_count that lies went undetected:\\n{out}"
    assert "bindings_count is 3 but the record carries 2" in out, out
    assert "0002-count-agrees" not in out, (
        "the honest record was flagged too, so the check bans the field rather than "
        f"comparing it:\\n{out}")
'''

schema.write_text(ssrc.replace(anchor, addition + anchor), encoding="utf-8")
checker.write_text(
    csrc.replace(decl, decl_new).replace(canchor, canchor + caddition).replace(summary, summary_new),
    encoding="utf-8",
)
tests.write_text(tsrc, encoding="utf-8")
PY
    then
        git --no-pager diff governance/schemas/decision-record.schema.json \
            scripts/check_decisions.py tests/test_governance_scripts.py
        if confirm "Land bindings_count — schema field, the check AND its test, together?"; then
            regen_manifest_row governance/schemas/decision-record.schema.json
            note "applied. The schema is frozen, sealed AND custody-set — three reasons only"
            note "you could do this. The manifest row is refreshed; step 7 re-signs custody."
        else
            git checkout -- governance/schemas/decision-record.schema.json \
                scripts/check_decisions.py tests/test_governance_scripts.py
            note "reverted — all three. D0106 item 1 stays open; note it in the receipt."
        fi
    else
        note "the edit did not apply cleanly (message above) — nothing was changed."
    fi
fi

stop_after 4i

# ---------------------------------------------------------------- 4j. D0117
say "Step 4j — a verdict is one bit, and there is nowhere in an evidence record to put the rest (D0131 item 2 = D0117)"
if grep -q '"examined"' governance/schemas/evidence-record.schema.json; then
    note "already applied — skipped"
else
    note "D0117 is owner-accepted and unappliable by the builder on three counts:"
    note "governance/schemas/evidence-record.schema.json is MANIFEST-frozen, inside the"
    note "sealed governance/schemas, AND custody-set as governance/schemas/*.json."
    note ""
    note "THE SHAPE IS THE PART D0117 LEFT OPEN, so it is proposed here rather than assumed:"
    note "an optional \`examined\` object with law_nodes and test_cases. law_nodes is how many"
    note "of the law's test functions reported; test_cases counts INVOCATIONS, so"
    note "parametrised cases count one apiece. Measured on the real suite: L2.9 reports"
    note "{law_nodes: 1, test_cases: 34} — one node, thirty-four catalogue shapes — and L0.3"
    note "reports {2, 19}. The verdict bit cannot tell those from a law that ran once."
    note ""
    note "WHAT IT IS NOT, said plainly so the number is not over-read. test_cases is one tier"
    note "BELOW an example count: a single @given invocation is one test case here however"
    note "many examples hypothesis drew. It does not close D0114 — L1.9 would read"
    note "test_cases: 44 while D0114 records its effective evidence as exactly zero. D0117's"
    note "own rationale ranks this tier: 'an example count is the cheapest and the weakest'."
    note ""
    note "AND WHY THE OBVIOUS BETTER ANSWER IS NOT HERE. D0130's event() counts are exactly"
    note "what D0117 names third, and they are REACHABLE — but hypothesis writes its OWN"
    note "internal retry notes into the same undifferentiated dict (control.py:294-311 and"
    note "five internals sites). Wired in, M2's laws yield {'overlap: partial': 1700, ...}"
    note "and M0's yield a wall of version-dependent strategy reprs. There is no marker"
    note "separating a law's declared shape from hypothesis's bookkeeping. That is its own"
    note "record, not a rider on this one."
    note ""
    note "THREE FILES, AND THE ORDER IS PROVEN, NOT ASSUMED. additionalProperties is false,"
    note "so a record carrying \`examined\` is refused until the schema knows the field —"
    note "verified by running the code half alone against the unmodified schema, where every"
    note "write died with 'Additional properties are not allowed'. The schema CANNOT go"
    note "second. src/ carries no manifest row and no custody entry, so the two code files"
    note "need no signature; they ride along because a schema that permits a field nothing"
    note "writes is the same false promise step 4 names for D0052's \`strength\`."
    note ""
    note "format_version STAYS 0. D0117 anticipated a bump, but the evidence store is"
    note "gitignored and regenerated by make verify, and the five frozen conformance vectors"
    note "under tests/laws/evidence-vectors/ still parse — 2/2 positives accepted, 3/3"
    note "negatives rejected. A bump would force regenerating those for no reader's benefit."
    if python3 - <<'PY'
import pathlib, sys

schema = pathlib.Path("governance/schemas/evidence-record.schema.json")
ssrc = schema.read_text(encoding="utf-8")
if '"examined"' in ssrc:
    sys.exit("the evidence schema already carries `examined` — nothing to do")
anchor = '''    "verdict": { "enum": ["pass", "fail"] },
'''
addition = '''    "examined": {
      "type": "object",
      "additionalProperties": false,
      "required": ["law_nodes", "test_cases"],
      "properties": {
        "law_nodes": {
          "type": "integer",
          "minimum": 1,
          "description": "How many of the law's test functions reported a result. A record is written only when every one the frozen law file defines did (BRIEF §5.11), so at a given descriptor this is the law's whole node count."
        },
        "test_cases": {
          "type": "integer",
          "minimum": 1,
          "description": "How many test INVOCATIONS reported a result: parametrised cases counted one apiece, so this exceeds law_nodes exactly where a law is parametrised. NOT a count of generated examples — one @given invocation is one test case here however many examples it drew."
        }
      },
      "description": "What the run actually EXAMINED (D0117), beside the verdict of whether it passed. Optional: absent is read as 'this runner did not measure', so records written before this field existed keep their meaning, and absent stays distinct from a run that examined nothing. Present, it must be whole — a half-given measure is one a reader has to guess about."
    },
'''
if ssrc.count(anchor) != 1:
    sys.exit("the evidence schema's verdict property is not where expected — apply by hand")

ev = pathlib.Path("src/tannen/laws/evidence.py")
esrc = ev.read_text(encoding="utf-8")
e_old = '''    run_at: str | None = None,
) -> dict[str, Any]:
    """One record for one law run. `run_at` is the runner's wall clock, never the
    kernel's: the kernel has no clock (BRIEF P7)."""
    return {
'''
e_new = '''    run_at: str | None = None,
    examined: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """One record for one law run. `run_at` is the runner's wall clock, never the
    kernel's: the kernel has no clock (BRIEF P7).

    `examined` is WHAT THE RUN ACTUALLY EXAMINED (D0117). It is OMITTED when the caller
    has nothing to say rather than written as a zero: a record whose measure is absent
    and a record whose measure is nothing are different facts, and the first is what
    every record written before this field existed attests.
    """
    record: dict[str, Any] = {
'''
e_tail_old = '''        "environment": environment(),
    }
'''
e_tail_new = '''        "environment": environment(),
    }
    if examined is not None:
        record["examined"] = examined
    return record
'''
pl = pathlib.Path("src/tannen/laws/plugin.py")
psrc = pl.read_text(encoding="utf-8")
p_old = '''    observed: set[str] = field(default_factory=set)
'''
p_new = '''    observed: set[str] = field(default_factory=set)
    #: The NODE IDS that reported a result, not merely the function names. A parametrised
    #: law function is one entry in `observed` and one entry PER CASE here, and that gap is
    #: what D0117 is about: `observed` says the law ran, this says how much of it ran. A
    #: set and not a counter so a node reporting twice — a failure at setup and again at
    #: teardown — counts once.
    nodes: set[str] = field(default_factory=set)
'''
p_add_old = '''            run.observed.add(function)
'''
p_add_new = '''            run.observed.add(function)
            run.nodes.add(report.nodeid)
'''
p_emit_old = '''                seed=seed if run.uses_hypothesis else None,
'''
p_emit_new = '''                seed=seed if run.uses_hypothesis else None,
                examined={"law_nodes": len(run.observed), "test_cases": len(run.nodes)},
'''
for label, src, needle, want in (
    ("evidence.py's build_record signature", esrc, e_old, 1),
    ("evidence.py's return dict", esrc, e_tail_old, 1),
    ("plugin.py's _LawRun.observed field", psrc, p_old, 1),
    ("plugin.py's observed.add call sites", psrc, p_add_old, 2),
    ("plugin.py's build_record call", psrc, p_emit_old, 1),
):
    if src.count(needle) != want:
        sys.exit(f"{label} is not the expected shape ({src.count(needle)} of {want}) — apply by hand")

# SCHEMA FIRST. Proven, not assumed: with the code half alone against the unmodified
# schema every EvidenceStore.put raises "Additional properties are not allowed
# ('examined' was unexpected)" and the whole law suite dies. Written in this order so a
# half-applied step leaves the tree in the state that still runs.
schema.write_text(ssrc.replace(anchor, anchor + addition), encoding="utf-8")
ev.write_text(esrc.replace(e_old, e_new).replace(e_tail_old, e_tail_new), encoding="utf-8")
pl.write_text(
    psrc.replace(p_old, p_new).replace(p_add_old, p_add_new).replace(p_emit_old, p_emit_new),
    encoding="utf-8",
)
PY
    then
        git --no-pager diff governance/schemas/evidence-record.schema.json \
            src/tannen/laws/evidence.py src/tannen/laws/plugin.py
        if confirm "Land \`examined\` — schema, build_record AND the plugin, together?"; then
            regen_manifest_row governance/schemas/evidence-record.schema.json
            note "applied. Step 9's gate rebuilds the evidence store from scratch"
            note "(make verify rm -rf's it first), so the first gate run after this produces"
            note "a store where every record carries the field."
        else
            git checkout -- governance/schemas/evidence-record.schema.json \
                src/tannen/laws/evidence.py src/tannen/laws/plugin.py
            note "reverted — all three. D0117 stays accepted and unappliable; the evidence"
            note "record keeps saying only whether a law passed."
        fi
    else
        note "the edit did not apply cleanly (message above) — nothing was changed."
    fi
fi

stop_after 4j

# ---------------------------------------------------------------- 4k. the rehearsal
say "Step 4k — the rehearsal that vouches for a custody-set script is vouched for by nothing (RT-M3-06)"
# scripts/boundary_sitting.sh — this file — is custody-set. scripts/rehearse_sitting.sh is
# the 21KB harness whose entire purpose is to run it end to end before the owner's key does,
# and it is in NEITHER the custody set nor MANIFEST.sha256. D0068 makes a green rehearsal the
# driver's precondition, so the floor's confidence in the driver rests on a script the floor
# cannot see. Anyone who can edit it can make a broken sitting rehearse green.
#
# D0172(E) recorded the custody set as complete for scripts/. RT-M3-06 corrects that:
# MEASURED 2026-09-08, exactly two scripts are outside it — rehearse_sitting.sh and
# check_drift.py. Only the first is offered here, because only the first has a record asking
# for it. check_drift.py is named so the omission stays visible rather than becoming the next
# generation's "the set is complete".
if grep -q '^    - scripts/rehearse_sitting\.sh$' governance/tier-c.yaml; then
    note "already in the custody set — skipped"
else
    note "Adding it changes what a signature MEANS, which is why it is yours: from this"
    note "sitting on, your custody signature covers the harness as well as the driver, and"
    note "an edit to either shows as drift on the next custodian run."
    note ""
    note "THE COST, STATED: the harness is builder-edited between sittings — this very"
    note "sitting's draft adds --abort-at, an isolation positive control and a breadcrumb"
    note "reader to it. Every such edit will now redden the floor until the next sitting"
    note "re-signs, exactly as edits to this driver already do (unexpected_failures()"
    note "tolerates that one drift by name, and would need a second name)."
    note ""
    note "scripts/check_drift.py is ALSO outside the set. No record asks for it, so it is"
    note "not offered; it is named here so the gap is on the transcript."
    if python3 - <<'PY'
import pathlib, sys

f = pathlib.Path("governance/tier-c.yaml")
src = f.read_text(encoding="utf-8")
row = "    - scripts/rehearse_sitting.sh\n"
if row in src:
    sys.exit("tier-c.yaml: scripts/rehearse_sitting.sh is already in custody.set — "
             "nothing to add (running this twice would list it twice)")
anchor = "    - scripts/boundary_sitting.sh\n"
if src.count(anchor) != 1:
    sys.exit(f"tier-c.yaml: the boundary_sitting.sh custody row is not the expected text "
             f"({src.count(anchor)} matches) — add by hand")
f.write_text(src.replace(anchor, anchor + row), encoding="utf-8")
print("   tier-c.yaml: scripts/rehearse_sitting.sh added to custody.set")
PY
    then
        git --no-pager diff governance/tier-c.yaml
        if confirm "Add scripts/rehearse_sitting.sh to the custody set?"; then
            # tier-c.yaml IS frozen as well as custody-set, so both rows move.
            regen_manifest_row governance/tier-c.yaml
            note "added. Step 7 regenerates the custody set over it and re-signs; the"
            note "harness's bytes are covered from that signature onward."
        else
            git checkout -- governance/tier-c.yaml
            note "declined — RT-M3-06 stays open, and the rehearsal keeps vouching for a"
            note "custody-set script without being one."
        fi
    else
        note "the edit did not apply cleanly (message above) — nothing was changed."
    fi
fi
stop_after 4k

# ---------------------------------------------------------------- 4l. a fixture that lies
say "Step 4l — an installed fixture whose README still says it is not installed (D0152 item 5)"
# tests/poison/oracle-shadow-model/README.md was written while the fixture was staged under
# docs/redteam/fixture-candidates/, and the M2 sitting moved the fixture without moving the
# prose. It is frozen AND custody-set, so it could only ever be corrected here.
#
# D0152 item 5 names four false clauses. Reading the file turns up more than the record
# lists, which is itself the point — every one of them was true when written:
#   - the title still carries "**needs patch**";
#   - "which is why it is staged here and not in `tests/poison/`", written from inside
#     tests/poison/;
#   - two runnable commands whose PYTHONPATH names a directory that no longer exists, so
#     the one thing a reader would actually TYPE is the thing most certain to fail;
#   - a section headed "Patch this fixture needs before installation" describing work
#     D0142 shipped on 2026-09-01, before the fixture was installed at all.
if ! grep -q 'needs patch' tests/poison/oracle-shadow-model/README.md; then
    note "already corrected — skipped"
else
    note "Four corrections, and a fifth this sitting adds: the closing 'Known limit'"
    note "paragraph says the real fix is package-qualified imports in the frozen law"
    note "files, that RT-M1-01 said so at M1 and it was not done, and that RT-M2-01 is"
    note "the cost. RT-M3-04 has now said it a THIRD time, at a third consecutive"
    note "boundary, and the M3 pass demonstrated the next shape it takes — a decoy that"
    note "sets __file__ to the frozen path and walks past an identity check made of one"
    note "string comparison (tests/poison/oracle-shadow-spoofed/, installed 2026-09-07)."
    note "A recommendation on its third boundary is not a recommendation any more; the"
    note "paragraph is updated to say which sitting declined it, so the fourth reader"
    note "does not have to reconstruct that from three red-team reports."
    if python3 - <<'PY'
import pathlib, sys

f = pathlib.Path("tests/poison/oracle-shadow-model/README.md")
src = f.read_text(encoding="utf-8")
edits = [
    ("title",
     "# `oracle-shadow-model/` — **needs patch** — the M2 differential oracle answers to a name, not an identity",
     "# `oracle-shadow-model/` — the M2 differential oracle answers to a name, not an identity"),
    ("staged-here",
     "(`_oracle_shadow_problem`), **as widened by RT-M2-01**. Against the shipped check this fixture\ndoes not bite, which is why it is staged here and not in `tests/poison/`.",
     "(`_oracle_shadow_problem`), **as widened by D0142** in answer to RT-M2-01. Against the check as\nit stood when this fixture was written it did not bite, which is why it was staged outside\n`tests/poison/`; D0142 shipped first, and the M2 boundary sitting then installed it here."),
    ("command-path",
     "env PYTHONPATH=docs/redteam/fixture-candidates/oracle-shadow-model \\\n    uv run pytest -p bootstrap_shadow_model tests/laws/m2/test_l2_differential.py \\",
     "env PYTHONPATH=tests/poison/oracle-shadow-model \\\n    uv run pytest -p bootstrap_shadow_model tests/laws/m2/test_l2_differential.py \\"),
    # The "Verified" block below is a DATED TRANSCRIPT of a run made on 2026-09-01, when the
    # fixture really was under docs/redteam/fixture-candidates/. Its command and its output
    # are evidence, not instructions, and rewriting either would falsify the record of what
    # was actually run — the opposite of what this step is for. The first spelling of this
    # step edited the transcript's command line and left its output quoting the old path,
    # which was both a falsified record AND an internally inconsistent one. Only the header
    # changes, to say why the paths inside it differ from the ones above.
    ("verified-header",
     "**Verified** (2026-09-01, against the **shipped** check — i.e. the fixture reproduces the hole):",
     "**Verified** (2026-09-01, against the **shipped** check — i.e. the fixture reproduces the hole).\nThe paths in this transcript are the pre-installation ones, because that is where the fixture\nwas when it was run; it moved to `tests/poison/` at the M2 boundary sitting:"),
    ("patch-tense",
     "**Patch this fixture needs before installation** — `src/tannen/laws/plugin.py`, replacing the\nsingle-name constants at lines 50-51:",
     "**The patch this fixture needed, and which shipped before it was installed** (D0142,\n2026-09-01) — `src/tannen/laws/plugin.py`, replacing the single-name constants:"),
    ("known-limit",
     "CLAUDE.md's do-not-edit-a-frozen-law rule. RT-M1-01 said the same thing at M1 and it was not\ndone; RT-M2-01 is the cost of that.",
     "CLAUDE.md's do-not-edit-a-frozen-law rule. RT-M1-01 said the same thing at M1 and it was not\ndone; RT-M2-01 is the cost of that. **RT-M3-04 said it a third time**, at the M3 boundary, and\nshowed the next shape the hazard takes: a decoy that sets `__file__` to the frozen path walks\npast an identity check made of one string comparison. That produced a third fixture\n(`oracle-shadow-spoofed/`, installed 2026-09-07) and, again, not the fix. Three boundaries have\nnow chosen the cheaper defence; whoever reads this at M4 should treat the recommendation as\nstanding and overdue, not as new."),
]
missing = [name for name, old, _ in edits if src.count(old) != 1]
if missing:
    sys.exit("tests/poison/oracle-shadow-model/README.md: not the expected text for "
             + ", ".join(missing) + " — correct by hand")
for _, old, new in edits:
    src = src.replace(old, new)
f.write_text(src, encoding="utf-8")
print(f"   corrected {len(edits)} passages")
PY
    then
        git --no-pager diff tests/poison/oracle-shadow-model/README.md
        if confirm "Correct the fixture's README (frozen + custody-set; regenerates its manifest row)?"; then
            regen_manifest_row tests/poison/oracle-shadow-model/README.md
            note "corrected. The bytes and the row move together; step 7 re-signs the set."
        else
            git checkout -- tests/poison/oracle-shadow-model/README.md
            note "reverted — D0152 item 5 stays open, and the fixture keeps saying it is"
            note "staged somewhere it is not."
        fi
    else
        note "the correction did not apply cleanly (message above) — nothing was changed."
    fi
fi
stop_after 4l

# ---------------------------------------------------------------- 5. poison fixtures
say "Step 5 — install the red-team poison fixtures (author-key territory)"
note "Ten of the eleven below are installed already — the M0→M1 corpus plus"
note "oracle-shadow (RT-M1-01), check-decisions-file-skip (RT-M1-05) and"
note "oracle-shadow-model (RT-M2-01) — so the loop skips those ten. THE ELEVENTH IS"
note "check-laws-dropped-successor, and it is worth saying where it is NOT from."
note ""
note "IT IS NOT FROM THIS MILESTONE'S BOUNDARY RED TEAM. That pass ran on 2026-09-05"
note "(docs/redteam/2026-09-05-m3-boundary.md, D0174) and returned six findings, two"
note "critical — and its one fixture-shaped critical, RT-M3-04's _delta_model decoy,"
note "ALREADY LANDED, at the publication sitting of 2026-09-07, as oracle-shadow-"
note "spoofed. So the M2-era sentence that stood here — a sitting installing no new"
note "fixture is one whose red team found nothing or was never run — would have read"
note "false at this boundary in both directions. The red team found plenty; its"
note "fixture simply did not wait for the sitting."
note ""
note "WHAT INSTALLS HERE IS OLDER AND NARROWER: D0154 item (7). scripts/check_laws.py"
note "is the only custody-set guard with neither a fixture nor a poison line, so the"
note "guard that decides whether a retired law still carries its claim forward is the"
note "one guard the custody floor has never watched fail. Its behaviour IS tested — in"
note "tests/test_law_validation.py, which is unfrozen and uncustodied, and that is the"
note "gap: the claim rests on bytes no signature covers."
note ""
note "Installing one is a git mv, a manifest row per file, and a poison line in the"
note "custodian — the custodian replacement in step 6 already carries every line, so the"
note "fixtures must land first or it will fail on missing paths. A fixture whose guard"
note "patch has NOT landed stays out of this list on purpose (D0104's note on"
note "check-decisions-file-skip): installing it first leaves the custodian permanently red"
note "against a guard that is not shipped, which is what the marking convention prevents."
# The M2 driver left an instruction here for whoever drafted this one — "M3's pass appends
# its fixture names to the end of this list and adds a readme_row_absent block below for
# each" — and it is carried out: check-laws-dropped-successor is the last name in the list
# and its row block is the fourth below. M4's pass does the same. Keep the installed ones:
# the loop is idempotent and skipping them by name is how the sitting stays safe to re-run.
#
# check-laws-dropped-successor is in THIS list rather than in a step-5b-style pairing for
# the same reason oracle-shadow-model was: its guard already bites. scripts/check_laws.py
# needs no patch — it has refused a dropped successor since D0129, and the fixture's own
# README records both the refusal and the positive control that says the refusal is about
# the successor rather than about the tree being odd. What is new is only the custodian line
# that watches it fail, and that is hunk 5 of step 6.
#
# oracle-shadow-model (RT-M2-01) is the M2 pass's, and it is here rather than in a
# step-5b-style pairing because ITS GUARD PATCH IS ALREADY SHIPPED. D0142 widened
# src/tannen/laws/plugin.py in a builder session on 2026-09-01 — src/ carries no manifest
# row and no custody entry, so no signature was involved. That is the opposite of
# check-decisions-file-skip, whose patch touched custody-set scripts/check_decisions.py and
# therefore had to land in the same step as its fixture (D0103). Read the difference as the
# rule it is: a fixture goes in this list when its guard already bites, and in a 5b-shaped
# step when the patch needs the owner's key.
FIXTURES="lint-imports-kernel check-decisions-ratchet check-decisions-nested-hatch
          check-manifest-sealed check-manifest-unsigned-policy
          check-decisions-unsigned-tier-c custodian-tag-signer
          oracle-shadow check-decisions-file-skip
          oracle-shadow-model
          check-laws-dropped-successor"
if [ ! -d tests/poison/custodian-tag-signer ]; then
    note "The tag-signer fixture is a git bundle carrying a builder-signed close tag."
    note "It is generated HERE, at the sitting, and never shipped pre-built (conferral"
    note "ruling 6): a bundle is opaque, and an opaque artifact you did not watch being"
    note "made is one you are taking on trust — the one thing this corpus exists to avoid."
    rm -f "$CANDIDATES/custodian-tag-signer/repo.bundle"
    confirm "Generate it now (uses the builder key to sign the poison tag)?" \
        && bash "$CANDIDATES/custodian-tag-signer/make-fixture.sh"
fi
for fixture in $FIXTURES; do
    if [ -d "tests/poison/$fixture" ]; then
        note "already installed: $fixture"
        continue
    fi
    [ -d "$CANDIDATES/$fixture" ] || { note "MISSING candidate: $fixture"; continue; }
    if confirm "Install $fixture into tests/poison/?"; then
        git mv "$CANDIDATES/$fixture" "tests/poison/$fixture" || die "git mv failed"
        add_manifest_rows "tests/poison/$fixture"
        note "installed with $(find "tests/poison/$fixture" -type f | wc -l) manifest row(s)"
    fi
done
if readme_row_absent lint-imports-kernel; then
    if confirm "Add the new fixtures to the tests/poison/README.md table?"; then
        cat "$PROPOSALS/poison-readme-rows.md" >> tests/poison/README.md
        regen_manifest_row tests/poison/README.md
        git --no-pager diff tests/poison/README.md
    fi
fi
if [ -d tests/poison/oracle-shadow ] && readme_row_absent oracle-shadow; then
    if confirm "Add oracle-shadow (RT-M1-01) to the tests/poison/README.md table?"; then
        cat "$PROPOSALS_M1/poison-readme-rows.md" >> tests/poison/README.md
        regen_manifest_row tests/poison/README.md
        git --no-pager diff tests/poison/README.md
    fi
fi
# Guarded on the DIRECTORY as well as the row, like the block above it: the row must not
# be appended for a fixture the owner declined to install one loop earlier, or the index
# claims a fixture the corpus does not have — the mirror image of D0131 item (1), where the
# corpus had a fixture the index did not claim.
if [ -d tests/poison/oracle-shadow-model ] && readme_row_absent oracle-shadow-model; then
    if confirm "Add oracle-shadow-model (RT-M2-01) to the tests/poison/README.md table?"; then
        cat "$PROPOSALS_M2/poison-readme-rows.md" >> tests/poison/README.md
        regen_manifest_row tests/poison/README.md
        git --no-pager diff tests/poison/README.md
    fi
fi
# THIS MILESTONE'S ROW. Same two guards as the block above and for the same two reasons:
# readme_row_absent anchors on the leading pipe, so the rows file's own prose naming the
# fixture cannot satisfy it (D0131 item 1); and the directory test keeps the index from
# claiming a fixture the owner declined to install one loop earlier.
if [ -d tests/poison/check-laws-dropped-successor ] && readme_row_absent check-laws-dropped-successor; then
    if confirm "Add check-laws-dropped-successor (D0154 item 7) to the tests/poison/README.md table?"; then
        cat "$PROPOSALS_M3/poison-readme-rows.md" >> tests/poison/README.md
        regen_manifest_row tests/poison/README.md
        git --no-pager diff tests/poison/README.md
    fi
fi

# A BINDING THAT NAMES THE CANDIDATE PATH DIES THE INSTANT THE FIXTURE MOVES, and D0141
# carries one — docs/redteam/fixture-candidates/oracle-shadow-model/README.md. THIS WAS
# FOUND BY A REHEARSAL, not by reading: the check twenty lines below stopped the sitting
# with "a decision binding stopped resolving when the fixtures moved", exactly as it was
# written to. The check is right; leaving the owner to repair the record mid-sitting is
# what is wrong, and the repair belongs in the same breath as the move that causes it.
# At M1 the same shape was answered by DROPPING the binding before the sitting (D0104's
# note, quoted in step 5b below). That is a real answer and a lossy one: the installed
# fixture is sealed and manifested, so a binding pointing at it still names a real file,
# where a dropped binding names nothing. Retarget rather than drop.
# BUILDER WORK, NO SIGNATURE — and that is a fact about D0141 specifically, not a general
# licence: it is Tier A and unsigned. Were it Tier C and signed, D0063 ruling 2 would make
# its bindings as immutable as its text and the edit and the re-sign would have to be one
# act, which is the shape step 4h uses for D0110.
# The detail text is corrected in the same replacement. "Staged outside tests/poison/"
# stops being true the moment the git mv lands, and a true future tense left standing is a
# false present one — the same correction step 4h makes to D0110, for the same reason.
#
# THE GUARD BELOW TESTS THE POST-STATE, AND AT M2 IT TESTED THE PRE-STATE (D0152 item 1).
# It asked whether D0141 still MENTIONS the candidate path anywhere — and the replacement
# text this very block writes says "retargeted from docs/redteam/fixture-candidates/
# oracle-shadow-model/ by that same step". So the guard was satisfied by the sentence
# written to record that the work was done: it re-armed on its own success, fired against a
# FINISHED sitting, and the python below then found zero matches for the text it meant to
# replace and `die`d. That is where both of D0153's concurrent runs stopped.
#
# It is the same defect readme_row_absent() was written to close, eighty lines above, in the
# same step — prose satisfying a grep meant for enforcement. The cure is the same one the
# step's own neighbours already use (step 4g: "is the corrected text present?"): ask whether
# the record NAMES THE INSTALLED PATH, which is the condition the work establishes and
# nothing else can satisfy. D0152 forbids the other repair by name — rewording D0141's
# detail so the old grep stops matching would make the bug unreproducible without fixing it,
# "and a workaround that makes the bug unreproducible is worse than the bug".
if [ -d tests/poison/oracle-shadow-model ] \
   && ! grep -q 'target: tests/poison/oracle-shadow-model/README\.md' decisions/0141-*.yaml; then
    if confirm "Retarget D0141's binding to the installed tests/poison/ path?"; then
        python3 - <<'PY' || die "retarget_d0141: the binding is not the expected text — retarget it by hand"
import glob, pathlib, sys

hits = glob.glob("decisions/0141-*.yaml")
if len(hits) != 1:
    sys.exit(f"expected exactly one D0141 record, found {len(hits)}")
path = pathlib.Path(hits[0])
src = path.read_text(encoding="utf-8")
old = """  - type: file
    target: docs/redteam/fixture-candidates/oracle-shadow-model/README.md
    strength: documentary
    detail: >-
      RT-M2-01's fixture candidate — the `_model` decoy, staged outside tests/poison/ because
      installing it before the guard is widened would leave the custodian permanently red.
"""
new = """  - type: file
    target: tests/poison/oracle-shadow-model/README.md
    strength: documentary
    detail: >-
      RT-M2-01's poison fixture — the `_model` decoy. INSTALLED at the M2 boundary sitting,
      step 5, and retargeted from docs/redteam/fixture-candidates/oracle-shadow-model/ by
      that same step. It was staged outside tests/poison/ until then because installing it
      before D0142 widened the guard would have left the custodian permanently red against
      a check that did not yet exist; D0142 shipped first, so the fixture bites.
"""
if src.count(old) != 1:
    sys.exit(f"{path}: the candidate-path binding is not the expected text ({src.count(old)} matches)")
path.write_text(src.replace(old, new), encoding="utf-8")
print(path)
PY
        git --no-pager diff decisions/0141-*.yaml
    else
        note "declined — the check below will stop the sitting on this binding, and the"
        note "message it prints tells you the retarget to make. Nothing is signed yet."
    fi
else
    note "D0141 already names the installed path — skipped."
fi

# AND THE SAME SHAPE AGAIN, ONE MILESTONE ON — D0199's binding names the CANDIDATE path
# `docs/redteam/fixture-candidates/check-laws-dropped-successor/governance/laws.yaml`, and
# step 5 above `git mv`s that tree into tests/poison/. The instant it moves, the binding
# stops resolving.
#
# FOUND BY REHEARSING, NOT BY READING — twice over, and the second time is the interesting
# one. The FAST rehearsal of 2026-09-09 skipped the binding check twenty lines below (it is
# check_decisions, ten minutes, and FAST skips it whole), so the sitting completed green;
# the HARNESS's own post-condition then failed with "no Tier-C door is left unsigned",
# because check_decisions cannot reach its summary line when a binding does not resolve. The
# check that was supposed to catch it was skipped, and a different check caught it anyway.
# That is what a verdict with more than one route to the same fact is for.
#
# The remedy is D0152's, ruled for D0141 and applied here in the same breath as the move:
# retarget rather than drop. An installed fixture is sealed and manifested, so a binding
# pointing at it still names a real file, where a dropped binding names nothing. The detail
# text is corrected in the same replacement — "until the owner installs the tree under
# tests/poison/" stops being true the moment the git mv lands, and a true future tense left
# standing is a false present one.
#
# BUILDER WORK, NO SIGNATURE, and again that is a fact about D0199 specifically: it is Tier A
# and unsigned. Were it Tier C and signed, D0063 ruling 2 would make its bindings as immutable
# as its text and the edit and the re-sign would have to be one act (the shape step 4h uses).
# The guard tests the POST-state from the outset, because writing the pre-state form here —
# one block below the fix for exactly that defect — would be its own kind of comedy.
if [ -d tests/poison/check-laws-dropped-successor ] \
   && ! grep -q 'target: tests/poison/check-laws-dropped-successor/governance/laws\.yaml' decisions/0199-*.yaml; then
    if confirm "Retarget D0199's binding to the installed tests/poison/ path?"; then
        python3 - <<'PY' || die "retarget_d0199: the binding is not the expected text — retarget it by hand"
import glob, pathlib, sys

hits = glob.glob("decisions/0199-*.yaml")
if len(hits) != 1:
    sys.exit(f"expected exactly one D0199 record, found {len(hits)}")
path = pathlib.Path(hits[0])
src = path.read_text(encoding="utf-8")
old = """  - type: file
    target: docs/redteam/fixture-candidates/check-laws-dropped-successor/governance/laws.yaml
    strength: documentary
    detail: >-
      The defect itself — the supersession naming a successor no law file defines. Documentary
      and it must stay so until the owner installs the tree under `tests/poison/`: a fixture
      outside the corpus is unsealed and unmanifested, and enforces nothing.
"""
new = """  - type: file
    target: tests/poison/check-laws-dropped-successor/governance/laws.yaml
    strength: enforced
    detail: >-
      The defect itself — the supersession naming a successor no law file defines. INSTALLED at
      the M3 boundary sitting, step 5, and retargeted from
      docs/redteam/fixture-candidates/check-laws-dropped-successor/ by that same step. It was
      staged outside `tests/poison/` until then because a fixture outside the corpus is unsealed
      and unmanifested; from the sitting on it is sealed, manifested, and exercised by
      `scripts/custodian.sh`'s `poison check_laws` line on every run, which is the whole point
      of D0154 item (7) — the guard that can retire a frozen law had never been watched failing
      by the custody floor.
"""
if src.count(old) != 1:
    sys.exit(f"{path}: the candidate-path binding is not the expected text ({src.count(old)} matches)")
path.write_text(src.replace(old, new), encoding="utf-8")
print(path)
PY
        git --no-pager diff decisions/0199-*.yaml
    else
        note "declined — the binding check below WILL stop the sitting, because the tree it"
        note "names was moved by step 5 a moment ago. Retarget it by hand, or re-run and"
        note "accept. Nothing is signed yet."
    fi
else
    note "D0199 already names the installed path (or the fixture is not installed) — skipped."
fi

# Installing a fixture MOVES files, and a decision record whose binding names the candidate
# path stops resolving the instant it does. Nothing surfaces that until a guard runs, and
# the next guard run is step 9 — five signatures later. D0065's lesson points forward as
# well as back: put the check where being wrong is cheap.
# ONE question, asked as narrowly as it can be put: did moving those files leave a binding
# pointing at a path that is no longer there? Everything wider re-invents the false stop
# D0065 was about, one step earlier. A stale DECISIONS.md is the NORMAL state here (step 4
# edits records; step 9 regenerates), and a pytest-node binding cannot be green mid-sitting
# either — step 4b edits BRIEF.md, which is in the custody set, so check_manifest reports
# custody drift until step 7 re-signs. Both are the sitting working, not the sitting broken.
# A `git mv` produces exactly two messages, and these are they.
# "Up to a minute" was M0's measurement, when check_decisions had a handful of bindings.
# At M1 it re-ran 54 pytest bindings and took about TEN minutes — and that line's stale
# ETA plus a captured-and-silent run got the driver killed right here at the real M1
# sitting (2026-08-30, exit 130): the same still-terminal-reads-as-hung class as D0069,
# one step further in. Same cure as step 0's gate, and for the same reason: tee streams
# the run while the log keeps what the grep below needs. The rehearsal harness's silence
# rule stays satisfied — a [waiting] line arms until the next step header.
#
# THE COUNT IS DERIVED, and that is a fix, not a flourish. Written as the literal "54" it
# was already wrong by M2 — the real number is over seventy — and a promise the owner
# watches expire is the whole defect D0069 named. A number read off decisions/ at run time
# cannot go stale, and it is the same move D0142 made on the oracle set for the same
# reason: a hand-maintained constant in a governance script is a constant that is one
# milestone behind at every boundary. `grep -A1` over the records counts UNIQUE targets,
# which is what check_decisions batches — within one of its own reported figure, and an
# ETA is not an assertion. Six bindings a minute is the M1 measurement (54 in ~10), and
# the +5 rounds up rather than promising the owner the floor.
binding_targets=$(grep -h -A1 'type: pytest' decisions/*.yaml \
    | grep 'target:' | sed 's/.*target: *//' | tr -d '"' | sort -u | wc -l)
waiting "checking the decision bindings still resolve — about $(( (binding_targets + 5) / 6 )) minutes ($binding_targets pytest bindings; output streams below, with still stretches between batches)"
bindings_log=$(mktemp -t tannen-bindings.XXXXXX)
if [ "$FAST" = 1 ]; then
    # SKIPPED WHOLE, and the transcript says so. There is no cheap half: check_decisions
    # has no flag that resolves file targets without also collecting the pytest bindings
    # (measured — `--help` offers only --root and --today), and the one environment
    # variable that would shorten it, TANNEN_CHECK_DECISIONS_NESTED=1, is red-team finding
    # RT-08: it disables binding resolution entirely WHILE STILL PRINTING GREEN. A knob
    # that makes a guard lie is not a fast path. So a fast run says nothing at all about
    # whether the fixture move broke a binding, which is what this line records.
    skipping_gate "check_decisions entirely — a fast run cannot say whether a binding broke"
    : > "$bindings_log"
else
    "$PY" -I -P scripts/check_decisions.py 2>&1 | tee "$bindings_log"
fi
broken=$(grep -E 'binding does not resolve — (target does not exist|not listed in MANIFEST)' "$bindings_log" || true)
rm -f "$bindings_log"
[ -z "$broken" ] || die "a decision binding stopped resolving when the fixtures moved:
$broken
  Retarget it to the installed tests/poison/ path — builder work, no signature involved.
  Nothing has been signed; the fixtures stay installed and step 5 will skip them next run."

stop_after 5

# ---------------------------------------------------------------- 5b. RT-M1-05
say "Step 5b — land RT-M1-05: the guard patch and its fixture, together (D0103, D0105 item 2)"
note "scripts/check_decisions.py is custody-set — D0063's own binding on"
note "tests/test_governance_scripts.py runs it — so a builder session that patches it"
note "alone would cascade into a red gate on every commit after, before this sitting's"
note "step 7 could re-sign custody to absorb the drift (see D0103). The patch and the"
note "fixture below land here, staged into the SAME commit step 9 makes."
if grep -q 'RT-M1-05' scripts/check_decisions.py; then
    note "patch already applied — skipped"
else
    if confirm "Read the patch first?"; then
        page "$CANDIDATES/check-decisions-file-skip/rt-m1-05-check-decisions.patch"
    fi
    if confirm "Apply it (scripts/check_decisions.py, tests/test_governance_scripts.py)?"; then
        git apply "$CANDIDATES/check-decisions-file-skip/rt-m1-05-check-decisions.patch" \
            || die "patch did not apply cleanly — the tree has moved since it was drafted; land it by hand"
        git --no-pager diff --stat scripts/check_decisions.py tests/test_governance_scripts.py
    else
        note "declined — the fixture below only installs once the patch is applied, so it"
        note "is skipped too this pass"
    fi
fi
if grep -q 'RT-M1-05' scripts/check_decisions.py && [ ! -d tests/poison/check-decisions-file-skip ]; then
    if confirm "Install the check-decisions-file-skip fixture (RT-M1-05)?"; then
        # Only decisions/ and tests/ move — the .patch file stays at its documented path:
        # D0103 and D0104 both carry a binding to it there, and a git mv of the whole
        # candidate directory would break both the same way an earlier binding to
        # oracle-shadow's own candidate path broke when step 5 moved IT (D0104 dropped
        # that one rather than repeat the fragility here).
        mkdir -p tests/poison/check-decisions-file-skip
        git mv "$CANDIDATES/check-decisions-file-skip/decisions" \
               tests/poison/check-decisions-file-skip/decisions || die "git mv failed"
        git mv "$CANDIDATES/check-decisions-file-skip/tests" \
               tests/poison/check-decisions-file-skip/tests || die "git mv failed"
        add_manifest_rows tests/poison/check-decisions-file-skip
        note "installed with $(find tests/poison/check-decisions-file-skip -type f | wc -l) manifest row(s)"
    fi
fi
if [ -d tests/poison/check-decisions-file-skip ] && readme_row_absent check-decisions-file-skip; then
    if confirm "Add check-decisions-file-skip (RT-M1-05) to tests/poison/README.md?"; then
        cat "$PROPOSALS_M1/poison-readme-row-file-skip.md" >> tests/poison/README.md
        regen_manifest_row tests/poison/README.md
        git --no-pager diff tests/poison/README.md
    fi
fi

stop_after 5b

# ---------------------------------------------------------------- 6. the custodian
say "Step 6 — the custodian itself (trust root; yours alone to apply)"
# $PROPOSALS_M3/custodian.sh — THIS sitting's draft, and re-pointing it is the single most
# important edit in this copy of the driver.
#
# THIS LINE IS HOW D0152 ITEM 6 HAPPENED. The M1 driver read $PROPOSALS_M1 correctly, was
# carried forward verbatim into the M2 driver, and the M2 proposals directory shipped no
# custodian.sh at all — so the diff compared the live file against the already-installed M1
# draft, printed "already applied — skipped", and the poison fixture that same sitting had
# just installed never got its custodian line. The M1→M2 pass's one critical finding landed
# half-applied, and nothing noticed for a month.
#
# At M3 the same stale pointer is worse than a skip. MEASURED 2026-09-08: the live custodian
# and the M1 draft now DIFFER (the publication sitting moved the live file), so the guard
# takes the ELSE branch and offers to install a draft that is OLDER than what is installed.
# A `y` would revert FOUNDING_TAGS to its pre-rewrite pin, put back a 28-line inline
# receipt-chain loop D0176 delegated to check_receipts.py, and delete three poison
# invocations whose fixtures are still on disk — which the new completeness pass in this
# milestone's own draft (hunk 1c) would then redden at step 7, where tolerances stop and the
# `custodian --check-only || die` below is unconditional. The sitting would die in its
# irreversible middle over a floor its own new guard had reddened.
#
# THIS sitting's draft is the live custodian plus SEVEN delimited hunks, each mapped to a
# D0154 queue item in this directory's README.md: 1a/1b/1c close D0152 item 6 (the missing
# oracle-shadow-model line, plus the derived completeness pass that would have caught it and
# the missing-fixture refusal that pass needed); 2 finishes D0154 item 2 where D0177 left it;
# 3 excludes __pycache__ from the sealed-path find; 4 fixes the receipt chain, including a
# `prev_head` that is read but never assigned anywhere in the live file; 5 adds the first
# `poison` line check_laws.py has ever had. Read the diff against that list.
if diff -q scripts/custodian.sh "$PROPOSALS_M3/custodian.sh" >/dev/null; then
    note "already applied — skipped"
else
    note "Read the whole diff. This file is the guard of the guards; the poison corpus"
    note "keeps it honest, and every line you accept here is a line you are vouching for."
    note "Hunk 5 names tests/poison/check-laws-dropped-successor/, which step 5 installs —"
    note "if you declined it there, decline here too, or hunk 1a will refuse the named"
    note "fixture as NOT INSTALLED and step 7 will stop the sitting."
    note ""
    note "TWO OF THE SEVEN HUNKS EXCEED WHAT D0171 RULING (4) PROPOSES TO DO HERE, and"
    note "you should know that before you answer. That ruling splits D0154 by consequence:"
    note "IN are item 1, item 7 and item 2's receipt exit-status clause; OUT to a later"
    note "sitting are items 3, 4, 5, 6, 8, 9. Hunks 3 and 4 are items 4 and 3 — the"
    note "__pycache__ exclusion in the sealed-path find, and the receipt-chain fix."
    note "D0171 is UNSIGNED, so ruling (4) is not in force and this is not a violation;"
    note "it is a question the sitting has to answer either way, and answering it by not"
    note "noticing is the failure mode. The install is whole-file, so declining here"
    note "declines all seven and the builder re-cuts the draft to the ruled scope."
    note "Hunk 4 has an argument for inclusion: it fixes a prev_head that is READ and"
    note "never assigned anywhere in the live file, so every receipt this project has"
    note "taken records its predecessor as (none recorded) — a chain link that is"
    note "documented, unenforced, and silently empty (D0196)."
    pause "Enter for the diff (q quits the pager)..."
    diff -u scripts/custodian.sh "$PROPOSALS_M3/custodian.sh" | page
    if confirm "Install this custodian?"; then
        cp "$PROPOSALS_M3/custodian.sh" scripts/custodian.sh
        regen_manifest_row scripts/custodian.sh
        note "running it — every guard must FAIL its poison, for its own marker."
        note ""
        note "TWO failures are EXPECTED here and neither is a defect. This custodian"
        note "checks governance/custody.sha256 and its signature; you have just changed a"
        note "file the custody set covers (this one), and the signature is taken in step"
        note "7. Neither can come sooner — the set hashes THIS file, so regenerating or"
        note "signing before installing would attest to the custodian you are replacing."
        note "So the run below must be green EXCEPT for the stale custody hashes and the"
        note "absent custody signature. Step 7 fixes both and re-runs this as a gate that"
        note "tolerates neither; anything else failing here stops the sitting now."
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
        note "declined — the close-tag rule and the custody-set check stay unenforced"
    fi
fi

stop_after 6

# ---------------------------------------------------------------- 7. the custody set
say "Step 7 — sign the custody set (D0061: what MANIFEST.sha256 cannot be)"
note "The manifest is builder-maintained and grows at every law freeze under the standing"
note "delegation, so signing IT would put your key in the path of every milestone's"
note "Session A. The custody set is the stable subset — the guards, the trust root, the"
note "poison corpus — and signing it costs one signature per sitting."
note ""
note "COST, so you accept it knowingly: after this, ANY edit to a listed path turns the"
note "gate red until the next sitting re-signs. That is the intended property for guards."
if ! grep -q 'path: governance/custody.sha256' governance/tier-c.yaml; then
    if confirm "Declare custody.sha256's signature REQUIRED (not merely verified-if-present)?"; then
        python3 - <<'PY'
import pathlib
p = pathlib.Path("governance/tier-c.yaml")
src = p.read_text()
anchor = """  - path: governance/policy.yaml
    namespace: tannen-policy
    signer: owner@tannen
"""
addition = """  - path: governance/custody.sha256
    namespace: tannen-custody
    signer: owner@tannen
"""
assert src.count(anchor) == 1
p.write_text(src.replace(anchor, anchor + addition))
PY
        regen_manifest_row governance/tier-c.yaml
        git --no-pager diff governance/tier-c.yaml
    fi
fi
"$PY" -I -P scripts/gen_custody.py || die "custody generation failed"
if confirm "Review the custody set before signing it?"; then
    page governance/custody.sha256
fi
verify_owner governance/custody.sha256 tannen-custody \
    || sign_owner governance/custody.sha256 tannen-custody

note "the custodian again, now that the signature it requires exists — THIS is the run"
note "that validates step 6's patch, and nothing after it should be attempted if it is red"
bash scripts/custodian.sh --check-only \
    || die "custodian RED with the custody set signed — hand back to the builder; sign nothing further"

stop_after 7

# ---------------------------------------------------------------- 8. resolve the queue
say "Step 8 — the records this sitting resolves"
note "Every Tier-C record still recorded blocked-on-owner is a question this sitting was"
note "convened to answer. Accepting one is the affirmative act; leaving it blocked is"
note "also an answer, and it queues to the next sitting without stopping any work."
queue=(); mapfile -t queue < <(ls -1 decisions/*.yaml | sort)   # array first: see sign_tier_c_records
for rec in "${queue[@]}"; do
    [ "$(sed -n 's/^tier: *//p' "$rec" | head -1)" = "C" ] || continue
    grep -q '^status: blocked-on-owner$' "$rec" || continue
    printf '\n'
    rec_id=$(sed -n 's/^id: *//p' "$rec" | head -1)
    # The head -40 that used to stand here cut five of the eight queued records mid-
    # sentence with no marker, D0115 (the external-bytes door) worst of all: its display
    # ended at "Publishing tannen publishes all of it" and the next thing on screen was
    # the signing prompt. Everything below — the ruling on the renavon excerpt, the
    # recommended mechanism, the reversibility clause, the bindings — was never shown.
    # A signature over bytes the signer was not shown is not consent. Page it whole.
    note "$rec_id — $(wc -l < "$rec") lines, shown in full"
    page "$rec"
    # What a yes here does NOT do. Step 8 flips one status line and writes one .sig; no
    # step of this driver applies what a record proposes, except where named below.
    # MEASURED 2026-09-08: the queue is exactly these four. Every other Tier-C record in
    # decisions/ is already accepted. The entries below are written against what THIS
    # driver does; if you declined a step, the line naming it is no longer true and a yes
    # here signs a record this sitting did not execute.
    case "$rec_id" in
        D0154) note "APPLIED-BY: partly, and the split matters. Item 1 (the oracle-shadow-model" ;
               note "            poison line + the derived completeness pass) and item 7 (the" ;
               note "            check_laws fixture) land at steps 5 and 6 of this sitting;" ;
               note "            item 2's receipt exit-status clause lands at step 6 too." ;
               note "            Item 6 (required_tags + m3-laws-freeze) was CLOSED already," ;
               note "            at the publication sitting — governance/tag-roles.yaml:47." ;
               note "            Item 9 (the stale '712 tests') is fixed in this driver's own" ;
               note "            prose, which is not a sitting act. Items 3, 4, 5 and 8 are" ;
               note "            deferred by D0171 ruling (4) — see the note at step 6 about" ;
               note "            hunks 3 and 4, which exceed that deferral." ;;
        D0171) note "APPLIED-BY: ruling (3) is ALREADY APPLIED — D0198 derived _ALWAYS_REPLAYS" ;
               note "            from behaviour instead of remembering it, in a builder" ;
               note "            session, and the guard was watched failing first." ;
               note "            RULING (2)'s PREMISE IS FALSE. It accepts order-insensitive" ;
               note "            derivation_id as harmless because operand order is 'a caller" ;
               note "            error the type system should catch'. RT-M3-03 measured" ;
               note "            otherwise: anti_join's two operand orders are both legal," ;
               note "            mean different things, and share one step_id. D0174 flags" ;
               note "            this as urgent BECAUSE D0171 is unsigned — amending a" ;
               note "            record costs nothing now and costs a supersession after." ;
               note "            AMEND THE PREMISE BEFORE SIGNING, or sign knowing you are" ;
               note "            signing a rationale the red team falsified." ;;
        D0176) note "APPLIED-BY: nothing here, and nothing needs to be — every act it" ;
               note "            authorises was executed at the publication sitting on" ;
               note "            2026-09-07. It already carries a signature that VERIFIES;" ;
               note "            what it never got is the status flip. A yes below rewrites" ;
               note "            one line and RE-SIGNS over the new bytes, which is correct:" ;
               note "            the old signature attests to bytes that said blocked." ;;
        D0195) note "APPLIED-BY: item (2) only, at step 4f of this sitting — ci.yml's header" ;
               note "            saying the file has never run and that a remote is an" ;
               note "            unopened door. Item (3), policy.yaml's in_repo_mechanics" ;
               note "            clause permitting pushes to a PRIVATE origin while this" ;
               note "            origin is public, is applied at step 3b. Item (1), the" ;
               note "            parked cross-repo spec, is a RULING with no artifact in" ;
               note "            this repo: a yes decides where it lives, and nothing in" ;
               note "            this sitting moves a byte of it." ;;
        *)     note "APPLIED-BY: NOTHING in this sitting. A yes authorises future work only," ;
               note "            and every artifact it needs is frozen or custody-set" ;;
    esac
    # Accepting and signing are ONE act, and it rolls back. Since D0064 a Tier-C record
    # that says accepted without a signature reddens the gate, so flipping the status
    # first and prompting for the key second would leave a declined signature — or a
    # mistyped passphrase — with the repo in a state no guard permits.
    if confirm "Accept and SIGN $rec_id (resolved by this sitting)?"; then
        sed -i 's/^status: blocked-on-owner$/status: accepted/' "$rec"
        rm -f "$rec.sig"
        if ssh-keygen -Y sign -f "$KEYREF" -n tannen-decision "$rec" >/dev/null; then
            note "accepted and signed: $rec.sig (namespace tannen-decision)"
        else
            sed -i 's/^status: accepted$/status: blocked-on-owner/' "$rec"
            note "signature failed — $rec_id left blocked; nothing changed"
        fi
    else
        note "left blocked — it will appear in the next digest's owner queue"
    fi
done
sign_tier_c_records

stop_after 8

# ---------------------------------------------------------------- 8b. D0138 item 1
say "Step 8b — a test node whose name asserts the opposite of what it does (D0138 item 1)"
OLD_NODE=test_a_survivors_witness_can_give_an_unwitnessed_row_a_bag_image
NEW_NODE=test_the_alarm_is_closed_an_unwitnessed_row_cannot_be_constructed
if ! grep -q "def $OLD_NODE" tests/test_provenance_homomorphism.py; then
    note "already renamed — skipped"
else
    note "$OLD_NODE was THE ALARM: it fed anti_join a (2, 0_Why) left row and asserted the"
    note "absence witness handed a row with no bag image an image of n copies. D0110 made"
    note "that input unconstructible, so D0137 INVERTED the node in place — it now builds"
    note "the same scenario and asserts the refusal. The name is the last thing still"
    note "saying the old claim, and the docstring has been carrying the truth since."
    note ""
    note "WHY IT WAITED FOR YOU. D0110 is Tier C and owner-signed, and the signature is"
    note "over the record's WHOLE BYTES (D0063 ruling 2). Retargeting its binding"
    note "invalidates the signature, and a Tier-C record whose signature does not verify is"
    note "a red guard — so the rename and the re-signature are ONE act or neither. D0137"
    note "records this being discovered the direct way: the retarget was written, verify"
    note "returned 'incorrect signature', and the file was restored."
    note ""
    note "THREE RECORDS BIND THIS NODE, not one. D0138 named D0110; D0137 and D0138 bind it"
    note "too, and both are Tier A and unsigned, so those two retarget freely under D0045."
    note "All three move together below or the sitting leaves a binding that does not"
    note "collect. Verified by grep on 2026-09-01, not taken from D0138's own list."
    note ""
    note "AND ONE COST D0138 DID NOT ANTICIPATE — decide knowing it. docs/specs/m2.md:121"
    note "names this node in prose, and that file is FROZEN (manifested at m2-laws-freeze)."
    note "Frozen files are not edited outside a supersession (D0106 ruling 2), so after the"
    note "rename the M2 spec cites a node that no longer exists. No guard notices: nothing"
    note "checks spec prose against live node names — which is D0138 ITEM 2's shape, one"
    note "file over. The sentence is narrative about what Session B was going to do, so it"
    note "reads as history rather than as a wrong instruction. If you would rather not"
    note "strand it, decline here: the name is a cosmetic defect and the docstring already"
    note "carries the truth. Declining costs nothing but D0138 item 1 staying open."
    if python3 - <<'PY'
import pathlib, sys

OLD = "test_a_survivors_witness_can_give_an_unwitnessed_row_a_bag_image"
NEW = "test_the_alarm_is_closed_an_unwitnessed_row_cannot_be_constructed"

# The test file: the def, and the module docstring's reference to it (line ~35). Prose
# INSIDE a decision's `decision:` field is history and is never touched (D0045) — only
# `bindings` move, which is why the records below are edited by target line, not swept.
test = pathlib.Path("tests/test_provenance_homomorphism.py")
tsrc = test.read_text(encoding="utf-8")
if tsrc.count(f"def {OLD}") != 1:
    sys.exit(f"tests/test_provenance_homomorphism.py does not define {OLD} exactly once — apply by hand")

records = {
    "decisions/0110-nonzero-implies-witnessed-at-construction.yaml": 1,
    "decisions/0137-the-d0110-alarm-was-read-and-what-replaced-it.yaml": 1,
    "decisions/0138-two-more-items-for-the-m2-boundary-sitting.yaml": 1,
}
pending = {}
for rel, expected in records.items():
    p = pathlib.Path(rel)
    src = p.read_text(encoding="utf-8")
    # Only lines that are a binding TARGET. A `target:` line is the present tense; every
    # other mention of the name is the record's history and stays as written.
    lines = src.splitlines(keepends=True)
    hits = [i for i, ln in enumerate(lines)
            if ln.lstrip().startswith("target:") and OLD in ln]
    if len(hits) != expected:
        sys.exit(f"{rel}: expected {expected} binding target naming the node, found {len(hits)} — apply by hand")
    for i in hits:
        lines[i] = lines[i].replace(OLD, NEW)
    pending[p] = "".join(lines)

test.write_text(tsrc.replace(OLD, NEW), encoding="utf-8")
for p, text in pending.items():
    p.write_text(text, encoding="utf-8")
PY
    then
        git --no-pager diff tests/test_provenance_homomorphism.py decisions/
        note ""
        note "D0110's signature no longer verifies — that is this step working, not broken."
        if confirm "Keep the rename and re-sign D0110 now?"; then
            sign_owner decisions/0110-nonzero-implies-witnessed-at-construction.yaml tannen-decision
            if verify_owner decisions/0110-nonzero-implies-witnessed-at-construction.yaml tannen-decision; then
                note "D0110 verifies again against its new bytes. D0137 and D0138 are Tier A"
                note "and unsigned; nothing to re-sign there."
            else
                die "D0110 still does not verify after re-signing — do NOT continue. Restore
  with 'git checkout -- tests/test_provenance_homomorphism.py decisions/' and rerun this
  step; a signed Tier-C record that does not verify is a red gate at step 9."
            fi
        else
            git checkout -- tests/test_provenance_homomorphism.py decisions/
            note "reverted — all four files. The node keeps the name that lies and the"
            note "docstring keeps carrying the truth; D0138 item 1 stays open."
        fi
    else
        note "the edit did not apply cleanly (message above) — nothing was changed."
    fi
fi

stop_after 8b

# ---------------------------------------------------------------- 9. gate + receipt
say "Step 9 — regenerate, verify, and take the attention receipt"
"$PY" -I -P scripts/gen_projections.py || die "projection generation failed"
waiting "the full gate again, now over everything this sitting changed: $(verify_eta)"
if [ "$FAST" = 1 ]; then
    skipping_gate "make verify at step 9 — the custodian still runs, and it writes the receipt"
    bash scripts/custodian.sh --check-only || die "custody floor red at step 9"
else
    make verify || die "verify red — stop here and hand back to the builder; sign no tag over a red gate"
fi
note "full custodian run — writes and signs receipts/$(date +%F).md"
bash scripts/custodian.sh || die "custodian red — no receipt was signed"
make digest
if [ -n "$(git status --porcelain)" ]; then
    git status --short
    # RT-M2-06 D2: commit_with_hook_retry returns the SECOND attempt's status and nothing
    # used to read it. With no `set -e`, a hook that stays red fell through to step 10 and
    # tagged anyway.
    if confirm "Commit the sitting so far?"; then
        commit_with_hook_retry "$MILESTONE boundary sitting: the custodian's seven hunks, the check_laws fixture, the push clause, ci.yml's header, custody set, receipt" \
            || die "the commit failed twice — fix the hook before tagging; $MILESTONE-close must attest a commit that CONTAINS this sitting"
    fi
fi

stop_after 9

# ---------------------------------------------------------------- 10. the close tag
say "Step 10 — sign $MILESTONE-close, LAST"
if git rev-parse -q --verify "refs/tags/$MILESTONE-close" >/dev/null; then
    note "$MILESTONE-close already exists — skipped"
else
    # RT-M2-06 D2. A tag points at a COMMIT; step 9's commit was optional and unchecked, so
    # declining it (or a hook that stayed red) left this step signing the PRE-SITTING head.
    # `git tag -s` and `verify-tag` both succeed on it — nothing compares HEAD to the tree —
    # and the message below quotes `sha256sum` of DELEGATIONS.md and governance/custody.sha256
    # read from the WORKING TREE, so the tag would attest hashes that are not in the commit it
    # names. That is precisely the D0051 property those two lines exist to provide, falsified
    # by the artifact meant to carry it. This is the project's FIRST owner-signed close tag.
    [ -z "$(git status --porcelain)" ] || die "the tree is not clean, so $MILESTONE-close would attest a commit that does not contain this sitting's work — and would quote working-tree hashes absent from it (D0051). Commit step 9 first, then re-run."

    note "This is the tag D0049 says only you may mint: the builder already signs the"
    note "*-laws-freeze tags that START the consent clock, so the close that anchors your"
    note "presence stays yours. The rule that says so is now installed and poisoned."
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
        cat DELEGATIONS.md
    } > "$msg"
    page "$msg"
    if confirm "Sign $MILESTONE-close with this message?"; then
        git -c gpg.format=ssh -c user.signingkey="$KEYREF" \
            tag -s "$MILESTONE-close" -F "$msg" || die "tag signing failed"
        git -c gpg.format=ssh -c gpg.ssh.allowedSignersFile="$PWD/allowed_signers" \
            verify-tag "$MILESTONE-close" || die "$MILESTONE-close does not verify"
    fi
    rm -f "$msg"
fi

stop_after 10

# ---------------------------------------------------------------- 11. required tags
say "Step 11 — the tags this milestone minted join the required set, and the custody set is re-signed"
# D0095: required_tags always lags by construction — a boundary tag is minted by the same
# session that cannot then add it to the frozen, custody-set file that names it required.
# AT THIS BOUNDARY THE LAG IS ONE, NOT TWO, and that is a change from every previous
# sitting. m3-laws-freeze was already added to required_tags at the publication sitting of
# 2026-09-07 (governance/tag-roles.yaml:47 — MEASURED 2026-09-08, and D0154 item 6 is
# therefore CLOSED, though the M3 proposals README still lists it as pending). So the loop
# below finds exactly one tag missing: $MILESTONE-close, minted moments ago at step 10.
#
# The M2 driver's line here said "the lag is now exactly two ... neither m2 one", which was
# true when written and is the fourth generation of the same sentence to go stale. The loop
# does not depend on it — MISSING_TAGS is derived, not listed — and that is the point: the
# prose can rot without the mechanism rotting with it. Both tags are still added in the
# SAME motion when both are missing, so a boundary that mints two does not repeat D0095's
# lag at the next one.
#
# The loop below is generic over $MILESTONE and needs no per-milestone edit — but that is
# exactly why the argument matters. Run without one it defaults to this copy's MILESTONE,
# and a rehearsal or a sitting driven at the WRONG milestone finds both tags already
# present, skips the step whole, and prints nothing that looks wrong.
MISSING_TAGS=()
for suffix in laws-freeze close; do
    tag="$MILESTONE-$suffix"
    if git rev-parse -q --verify "refs/tags/$tag" >/dev/null \
       && ! grep -q "  - $tag\$" governance/tag-roles.yaml; then
        MISSING_TAGS+=("$tag")
    fi
done
if [ "${#MISSING_TAGS[@]}" -gt 0 ]; then
    note "A tag that exists but is not required can be deleted in silence (RT-15)."
    note "Missing from required_tags: ${MISSING_TAGS[*]}"
    if confirm "Add ${MISSING_TAGS[*]} to tag-roles.yaml required_tags?"; then
        python3 - "${MISSING_TAGS[@]}" <<'PY'
import pathlib, sys
tags = sys.argv[1:]
p = pathlib.Path("governance/tag-roles.yaml")
src = p.read_text()
anchor = "required_tags:\n"
assert src.count(anchor) == 1
end = src.index(anchor) + len(anchor)
addition = "".join(f"  - {t}\n" for t in tags)
p.write_text(src[:end] + addition + src[end:])
PY
        regen_manifest_row governance/tag-roles.yaml
        git --no-pager diff governance/tag-roles.yaml
        "$PY" -I -P scripts/gen_custody.py
        rm -f governance/custody.sha256.sig
        sign_owner governance/custody.sha256 tannen-custody
    fi
fi
# THE PROJECTION IS STALE HERE, AND UNTIL RT-M2-05 LANDED NOTHING COULD SAY SO. DECISIONS.md
# was last generated at the top of step 9 — before step 9's custodian wrote receipts/<today>.md
# and before step 10 minted $MILESTONE-close. BOTH of the projection's clock-dependent inputs
# arrived after it: the attention-receipt verdict names the latest receipt AND the first
# boundary tag on or after it (_gov.py:303), so the file still asserts the PREVIOUS boundary's
# freshness while this run computes this one's. Step 4g's check is what notices, and it
# noticed here first: the M2 rehearsal's final gate failed on exactly this line, with the
# sitting otherwise complete — receipt taken, close tag minted and verifying, custodian green
# (D0147). Before that check existed the staleness was simply carried into the closing commit,
# which is what RT-M2-05 found in the tree M1 left behind.
#
# REGENERATED HERE BECAUSE THERE IS NO EARLIER POINT WHERE BOTH INPUTS EXIST. Step 9's own
# regeneration cannot see either; moving it after step 9's custodian would still miss the tag.
# Neither DECISIONS.md nor CONCEPTS.md is in MANIFEST.sha256 or the custody set, so this
# disturbs no seal and no signature — checked, not assumed — and the commit below picks it up.
"$PY" -I -P scripts/gen_projections.py || die "projection generation failed"
waiting "the last full gate, with the close tag in the required set: $(verify_eta)"
if [ "$FAST" = 1 ]; then
    skipping_gate "make verify at step 11 — the custodian still runs"
    bash scripts/custodian.sh --check-only || die "custody floor red at the close"
else
    make verify || die "verify red at the close — hand back to the builder"
fi
if [ -n "$(git status --porcelain)" ]; then
    commit_with_hook_retry "$MILESTONE close: required tags and custody set re-signed"
fi

stop_after 11

say "The sitting is closed"
note "Signed this sitting: the Tier-C records, governance/policy.yaml,"
note "governance/custody.sha256, the attention receipt, and $MILESTONE-close."
note ""
note "The receipt clock is now RUNNING: $MILESTONE-close is a boundary tag dated today,"
note "so Tier-B silence-as-consent lapses seven days from it unless a fresh receipt"
note "lands. That is the design — a stopped clock was the anomaly."
note ""
note "Builder follow-ups (Tier A, no signature): upgrade the bindings this sitting made"
note "enforceable, add the new fixtures to tests/test_governance_scripts.py, and open"
note "${NEXT_MILESTONE^^} Session A in a fresh session, in a new worktree."
