#!/usr/bin/env bash
# scripts/rehearse_sitting.sh — run scripts/boundary_sitting.sh end to end, with no human
# and without the owner's key, against a disposable clone of this repo.
#
# WHY THIS EXISTS. The boundary driver runs once per milestone, interactively, on the one
# occasion the owner's key is out from behind its passphrase — and until 2026-08-25 it had
# only ever been READ, never executed. Three consecutive attempts at the M0→M1 sitting
# stopped on defects that a single end-to-end run would have found in seconds: a step
# gated on a later step's output, a manifest row naming a file no commit contained
# (D0065), and $EDITOR invoked as though it were a command name (D0066). Every one of them
# spent the owner's attention, which is the scarce resource this entire governance layer
# exists to conserve (BRIEF §9.2). A script that drives the owner's key deserves what
# every law in this repo already gets: a run against a fixture before it runs for real.
#
# WHAT A GREEN RUN PROVES: step order, shell quoting, the gates, idempotence, and that the
# sitting arrives at a green `make verify` with every artifact signed, tagged and committed.
#
# WHAT IT CANNOT PROVE: custody. The clone enrols a THROWAWAY owner key, because the real
# key is passphrase-protected and unattended signing is exactly what that passphrase
# exists to prevent. The signatures a rehearsal produces are structurally correct and
# attest to nothing. Read a green run as "the mechanism works", never as "the sitting
# happened".
#
# NOTHING HERE TOUCHES THE REAL REPO. Its only access is `git clone` and a read-only
# `git diff`; every mutation happens inside a temporary directory, which is printed at the
# end and removed unless --keep.
#
#   scripts/rehearse_sitting.sh                     # HEAD + uncommitted work: what the
#                                                   # owner is about to run. Must be green.
#   scripts/rehearse_sitting.sh --from head         # the sitting from a pristine repo. A
#                                                   # deeper test, and it legitimately
#                                                   # surfaces defects the working tree has
#                                                   # already fixed — read its failures
#                                                   # against HEAD, not against your tree.
#   scripts/rehearse_sitting.sh --answers n --keep  # the decline-everything path
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"

MODE=worktree ANSWER=y KEEP=0 MILESTONE=m0
while [ $# -gt 0 ]; do
    case "$1" in
        --from)      MODE="$2"; shift 2 ;;
        --answers)   ANSWER="$2"; shift 2 ;;
        --milestone) MILESTONE="$2"; shift 2 ;;
        --keep)      KEEP=1; shift ;;
        *) echo "usage: $0 [--from head|worktree] [--answers y|n] [--milestone m0] [--keep]" >&2
           exit 2 ;;
    esac
done
case "$MODE" in head|worktree) ;; *) echo "--from must be head or worktree" >&2; exit 2 ;; esac

say()  { printf '\n\033[1m-- %s\033[0m\n' "$*"; }
note() { printf '   %s\n' "$*"; }

WORK=$(mktemp -d "${TMPDIR:-/tmp}/tannen-rehearsal-XXXXXX")
CLONE="$WORK/repo"
LOG="$WORK/transcript.txt"
STAMPED="$WORK/transcript.stamped"   # same lines, each prefixed with elapsed seconds
SILENCE_LIMIT=25                     # seconds the driver may be quiet without saying so
cleanup() { [ "$KEEP" = 1 ] || rm -rf "$WORK"; }
trap cleanup EXIT

say "Building a disposable clone at $CLONE (mode: $MODE)"
git clone --quiet --no-hardlinks "$ROOT" "$CLONE"
git -C "$CLONE" config user.name  "rehearsal"
git -C "$CLONE" config user.email "rehearsal@invalid"
git -C "$CLONE" config commit.gpgsign false
git -C "$CLONE" config tag.gpgsign false
note "cloned $(git -C "$CLONE" rev-parse --short HEAD) with $(git -C "$CLONE" tag | wc -l) tag(s)"

if [ "$MODE" = worktree ]; then
    # The owner's real re-run starts from an uncommitted tree, so the resume path is only
    # rehearsed if the rehearsal starts from one too. --binary carries the tag-signer
    # bundle; --exclude-standard keeps .venv and other ignored noise out.
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

# The artifact under test is the driver as it stands NOW. Cloning HEAD alone rehearses
# whatever driver was last committed, which on 2026-08-25 meant faithfully reproducing the
# defect the working tree had already fixed — a green run would then have meant nothing and
# a red one would have pointed at the wrong file. Everything else in head mode stays at
# HEAD, which is the point: a sitting that starts from a committed repo.
# TANNEN_REHEARSE_DRIVER overlays some OTHER driver instead — which is how this harness
# gets tested against its own history. `git show <sha>:scripts/boundary_sitting.sh > old.sh`
# and point it here, and a check that claims to catch a past defect can be watched catching
# it. A guard should be born having already caught something real (docs/SITTING.md), and
# that applies to the harness as much as to the floor it rehearses.
DRIVER="${TANNEN_REHEARSE_DRIVER:-$ROOT/scripts/boundary_sitting.sh}"
[ -f "$DRIVER" ] || { echo "no driver at $DRIVER" >&2; exit 1; }
cp -a "$DRIVER" "$CLONE/scripts/boundary_sitting.sh"
if [ -n "${TANNEN_REHEARSE_DRIVER:-}" ]; then
    note "driver under test: $DRIVER (OVERRIDDEN — not the working tree)"
elif git -C "$ROOT" diff --quiet HEAD -- scripts/boundary_sitting.sh; then
    note "driver under test: scripts/boundary_sitting.sh, unmodified since HEAD"
else
    note "driver under test: scripts/boundary_sitting.sh from the WORKING TREE (differs from HEAD)"
fi


say "Minting a throwaway owner key (the real one is passphrase-protected, by design)"
KEY="$WORK/rehearsal_owner"
ssh-keygen -q -t ed25519 -N '' -C rehearsal-owner@invalid -f "$KEY"
# APPENDED, never substituted: the real owner and builder public halves must stay enrolled
# or brief-freeze and m0-laws-freeze stop verifying and the custodian is red before the
# driver has done anything. Two principals may share a name in allowed_signers; verify
# succeeds if any line for that principal matches.
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
# allowed_signers is an INPUT to the DECISIONS.md freshness hash as well as a custody-set
# member, so enrolling the throwaway key restales the projection. A fixture that starts
# inconsistent produces failures that belong to the fixture, and they are indistinguishable
# from the driver's own until someone traces them — which cost a full rehearsal cycle.
( cd "$CLONE" && .venv/bin/python -I -P scripts/gen_projections.py >/dev/null )
if [ "$MODE" = head ]; then
    # A sitting starts from a committed repo; the fixture's own edits must not masquerade
    # as sitting work. In worktree mode they ride along with the uncommitted tree instead,
    # which is what the owner will actually be looking at.
    ( cd "$CLONE" && git add -A && git commit -q -m "rehearsal fixture: enrol a throwaway owner key" )
fi
# pre-commit is a project dependency, not a system one — it lives in the venv, and the
# commit steps are only rehearsed honestly with the frozen-path and projection hooks armed.
if ( cd "$CLONE" && .venv/bin/pre-commit install --install-hooks >/dev/null 2>&1 ); then
    note "pre-commit hooks armed in the clone"
else
    note "WARNING: pre-commit hooks NOT installed — the commit steps run unguarded, so a"
    note "hook failure at the real sitting would not show up here. Fix before trusting a pass."
fi

say "Writing the editor stand-in for step 4b"
# Step 4b hands BRIEF.md to $EDITOR because it is owner text. A rehearsal needs a
# non-interactive editor that makes the real change, so this applies the drafted blocks
# exactly as the proposal specifies: after the two named bullets, additive only. It is
# also a usable EDITOR for the real sitting, for an owner who would rather review a diff
# than retype two paragraphs.
cat > "$WORK/apply-brief-amendment" <<'SHIM'
#!/usr/bin/env bash
set -euo pipefail
target="${1:?no file}"
draft="docs/proposals/2026-08-25-boundary-sitting/brief-9.1-amendment.md"
[ -f "$draft" ] || { echo "no amendment draft at $draft" >&2; exit 1; }
python3 - "$target" "$draft" <<'PY'
import re, sys
target, draft = sys.argv[1], sys.argv[2]
blocks = re.findall(r"```markdown\n(.*?)```", open(draft).read(), re.S)
if len(blocks) != 2:
    sys.exit(f"expected 2 fenced blocks in the draft, found {len(blocks)}")
after = ["- **Exception-only digest.**", "- **Attention receipts.**"]
lines = open(target).read().splitlines(keepends=True)
for anchor, block in zip(after, blocks):
    hits = [i for i, l in enumerate(lines) if l.startswith(anchor)]
    if len(hits) != 1:
        sys.exit(f"anchor {anchor!r} appears {len(hits)} times in {target}")
    lines.insert(hits[0] + 1, block if block.endswith("\n") else block + "\n")
open(target, "w").writelines(lines)
PY
SHIM
chmod +x "$WORK/apply-brief-amendment"

say "Running the driver — $(printf '%s' "$ANSWER") to every prompt, transcript at $LOG"
# Answers come from a FILE, not from `yes |`: a pipe that outlives the driver dies of
# SIGPIPE, and under pipefail that becomes the pipeline's status. The obvious spelling of
# the file — `yes "$ANSWER" | head -n 2000` — has the same defect one step earlier, and
# took out the first rehearsal run before the driver started. No pipe, no signal.
awk -v a="$ANSWER" 'BEGIN { for (i = 0; i < 2000; i++) print a }' > "$WORK/answers"
# Every line is also written with the second it arrived, because WHEN the driver spoke is
# a fact about the sitting and the plain transcript cannot hold it. `$( )` around a
# minutes-long command produces a perfect transcript and a terminal that shows nothing at
# all until it ends — the two are indistinguishable afterwards, and only the timing tells
# them apart (D0069).
stamp() {   # stdin -> stdout unchanged; a copy with elapsed seconds to $1
    local line start=$SECONDS
    : > "$1"
    while IFS= read -r line || [ -n "$line" ]; do
        printf '%d\t%s\n' "$((SECONDS - start))" "$line" >> "$1"
        printf '%s\n' "$line"
    done
}
set +e
( cd "$CLONE" && env \
    SSH_AUTH_SOCK= \
    TANNEN_OWNER_KEY="$KEY" \
    EDITOR="$WORK/apply-brief-amendment" \
    PAGER=cat \
    TERM=dumb \
    bash scripts/boundary_sitting.sh "$MILESTONE" ) < "$WORK/answers" 2>&1 \
    | stamp "$STAMPED" > "$LOG"
DRIVER_RC=${PIPESTATUS[0]}   # the NEXT line after the pipeline, always: an assignment
set -e                       # in between would replace PIPESTATUS with its own status
note "driver exited $DRIVER_RC after $(wc -l < "$LOG") lines"

# ------------------------------------------------------------------ verdict
# Each check is what a green sitting MUST leave behind, phrased so that a failure names
# the thing that is missing rather than the check that noticed.
say "Verdict"
FAILED=0
check() {  # <description> <command...>
    local desc="$1"; shift
    if "$@" >/dev/null 2>&1; then printf '   \033[32mok\033[0m   %s\n' "$desc"
    else printf '   \033[31mFAIL\033[0m %s\n' "$desc"; FAILED=$((FAILED + 1)); fi
}
in_clone() { ( cd "$CLONE" && "$@" ); }
# `!` is a shell keyword, not a command, so it cannot be passed as the first word of "$@" —
# `check "…" ! grep …` execs a program literally named `!` and reports a failure that is
# only ever the check's own. Negation needs a function.
absent() { ! grep -q "$1" "$2"; }
# Gaps between consecutive output lines, minus the ones the driver announced. A waiting()
# line ARMS tolerance for the rest of its step and the next step header disarms it, rather
# than covering only the gap immediately below it: a slow command that streams — the gate
# does — puts its own output between the announcement and its quiet stretches, and pytest
# alone goes ~20s between progress lines. The unit being announced is the step, not the
# pause. So the rule is: after a step header, the driver may not go quiet for longer than
# the limit until it has said that it is about to.
silences() {
    awk -v limit="$SILENCE_LIMIT" '
        {
            t = $0 + 0
            line = substr($0, index($0, "\t") + 1)
            # The gap being judged is the one BEFORE this line, so it is judged against
            # the state as of the previous line — arm and disarm after the check, or a
            # long silence ending in the announcement excuses itself.
            if (NR > 1 && !armed && t - pt > limit)
                printf "%3ds of silence after: %s\n", t - pt, pl
            if (line ~ /== /)          armed = 0
            if (line ~ /\[waiting\]/) armed = 1
            pt = t; pl = line
        }' "$1"
}
speaks_up() { [ -z "$(silences "$1")" ]; }

check "the driver ran to completion (exit 0)"            test "$DRIVER_RC" -eq 0
check "no step aborted the sitting"                      absent 'sitting: STOP' "$LOG"
check "no silence over ${SILENCE_LIMIT}s went unannounced"     speaks_up "$STAMPED"
if [ "$ANSWER" = y ]; then
    check "$MILESTONE-close exists"                      in_clone git rev-parse -q --verify "refs/tags/$MILESTONE-close"
    check "$MILESTONE-close verifies as owner@tannen"    in_clone git -c gpg.format=ssh \
              -c gpg.ssh.allowedSignersFile="$CLONE/allowed_signers" verify-tag "$MILESTONE-close"
    check "the custody set is signed"                    test -f "$CLONE/governance/custody.sha256.sig"
    check "this sitting took a fresh attention receipt" test -f "$CLONE/receipts/$(date +%F).md"
    check "and signed it"                                test -f "$CLONE/receipts/$(date +%F).md.sig"
    check "the custodian is green with no tolerances"    in_clone bash scripts/custodian.sh --check-only
    check "the gate is green end to end"                 in_clone make verify
    check "nothing was left uncommitted"                 test -z "$(in_clone git status --porcelain)"
    check "no Tier-C door is left unsigned"              in_clone bash -c \
              '.venv/bin/python -I -P scripts/check_decisions.py | grep -q "0 queued"'
fi

# Failures the driver PRINTED but did not stop on are the interesting ones: a sitting that
# reports FAIL and carries on is worse than one that stops. Tolerance is bounded by
# POSITION, not by pattern alone: before step 7 the custody set is unsigned by
# construction, so the custodian's complaints about it — and make's summary line for them —
# are the sitting's agenda. From step 7 onward the signature exists and there is no
# tolerance at all, so the same text there is a defect.
if ! speaks_up "$STAMPED"; then
    say "Silences the owner would read as a hang"
    silences "$STAMPED"
    note "announce each with waiting() in the driver, or fix whatever made it slow"
fi

say "Unexpected failure lines in the transcript (empty is the goal)"
awk '
  /== Step 7/ { strict = 1 }
  /fails its poison as required/ { next }
  # The driver SHOWS the owner unified diffs of the custodian and of ci.yml, and those
  # diffs contain the guard source that prints the FAIL lines. Source code being displayed
  # is not a failure. Diff bodies carry a prefix; program output does not.
  # (No apostrophes in this comment: the whole awk program is single-quoted in the shell.)
  /^[+-]/ { next }
  /^ .*(printf|echo|bad\(\))/ { next }
  /sitting: STOP|: FAIL|FAILED|Traceback|command not found|No such file|Error [0-9]/ {
      if (strict || $0 !~ /custody set hashes do not verify|custody\.sha256\.sig absent|custody floor violated|make: \*\*\* \[Makefile/)
          printf "%d:%s\n", NR, $0
  }' "$LOG" | head -30

say "Transcript: $LOG (timed copy: $STAMPED)"
[ "$KEEP" = 1 ] && note "clone kept at $CLONE" || note "(--keep to inspect the clone)"
if [ "$FAILED" -eq 0 ]; then
    printf '\n\033[32mrehearsal: the sitting completes\033[0m — mechanics only; the real key signs nothing here\n'
else
    printf '\n\033[31mrehearsal: %d check(s) failed\033[0m — fix the driver before the owner runs it\n' "$FAILED"
fi
exit "$FAILED"
