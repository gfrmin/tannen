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
#   scripts/rehearse_sitting.sh --abort-at 12       # accept everything up to prompt 12,
#                                                   # then decline ONE — the path an owner
#                                                   # most wants rehearsed and the one this
#                                                   # harness could not express until M3.
#   TANNEN_SITTING_FAST=1 scripts/rehearse_sitting.sh --abort-at 12
#                                                   # the same, in about ten minutes: the
#                                                   # driver skips the three long gates and
#                                                   # the commit hooks, and says so on every
#                                                   # line it skips.
#
# WHY --abort-at, AND WHY IT IS NOT --answers n. `--answers n` declines the FIRST prompt, so
# the run stops before it has done anything and every step after it is unexercised. The
# failure an owner actually fears is the other one: something looks wrong in the irreversible
# middle, they answer n, and the sitting has to leave the repository in a state they can
# reason about. Until this flag existed that path had never once been executed — for either
# driver — and when the publication harness finally ran it, it found that the answer differs
# either side of the sitting's first commit (D0184). Two regimes, and the driver now says
# which one it is in.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"

# THE MILESTONE IN FLIGHT IS DERIVED, NOT DEFAULTED. This was `MILESTONE=m0`, and because
# m0-close has existed since the first sitting, every unargumented rehearsal ever run took
# D0120's refusal branch or — before D0120 — silently skipped steps 10 and 11 while the
# verdict printed green off a tag the clone was cloned with. A default that names a finished
# milestone is a default that is always wrong.
#
# The milestone in flight is the one whose laws are frozen and whose close tag is not yet
# minted, and git already knows both facts. Derived rather than enumerated, per D0171 ruling
# (3): no guard may depend on a hand-maintained enumeration. If none matches — every
# milestone closed — the derivation yields empty and the run stops rather than guessing.
milestone_in_flight() {
    local t n
    for t in $(git tag -l 'm*-laws-freeze' | sort -V -r); do
        n="${t%-laws-freeze}"
        git rev-parse -q --verify "refs/tags/$n-close" >/dev/null 2>&1 || { printf '%s' "$n"; return 0; }
    done
    return 1
}
MODE=worktree ANSWER=y KEEP=0 MILESTONE="" ALLOW_PREEXISTING_CLOSE=0 ABORT_AT=0
ABORT_STEP="${TANNEN_ABORT_STEP:-}"
while [ $# -gt 0 ]; do
    case "$1" in
        --from)      MODE="$2"; shift 2 ;;
        --answers)   ANSWER="$2"; shift 2 ;;
        --milestone) MILESTONE="$2"; shift 2 ;;
        --abort-at)  ABORT_AT="$2"; shift 2 ;;
        --abort-step) ABORT_STEP="$2"; shift 2 ;;
        --keep)      KEEP=1; shift ;;
        --allow-preexisting-close) ALLOW_PREEXISTING_CLOSE=1; shift ;;
        *) echo "usage: $0 [--from head|worktree] [--answers y|n] [--milestone mN]" >&2
           echo "          [--abort-at N [--abort-step ID]] [--keep] [--allow-preexisting-close]" >&2
           exit 2 ;;
    esac
done
case "$MODE" in head|worktree) ;; *) echo "--from must be head or worktree" >&2; exit 2 ;; esac
case "$ABORT_AT" in ''|*[!0-9]*) echo "--abort-at takes a prompt index (1-based)" >&2; exit 2 ;; esac
if [ -z "$MILESTONE" ]; then
    MILESTONE=$(milestone_in_flight) || {
        echo "every milestone with a laws-freeze tag also has a close tag, so there is" >&2
        echo "nothing in flight to rehearse. Pass --milestone explicitly if you mean to." >&2
        exit 2; }
fi
# --abort-at asserts WHERE it expects to land, and the verdict checks the assertion. The
# harness deliberately does not compute the step from the prompt index: several confirms are
# inside conditionals, so the mapping depends on repo state, and a harness that derived it
# would be a second copy of the driver's control flow living out here (BRIEF §2). State the
# expectation, let the run refute it.
if [ "$ABORT_AT" -gt 0 ] && [ -z "$ABORT_STEP" ]; then
    echo "--abort-at also needs --abort-step ID (or TANNEN_ABORT_STEP): the step you expect" >&2
    echo "prompt #$ABORT_AT to fall in. The verdict checks it, which is the whole point —" >&2
    echo "a run that lands somewhere else has told you something." >&2
    exit 2
fi

say()  { printf '\n\033[1m-- %s\033[0m\n' "$*"; }
note() { printf '   %s\n' "$*"; }

WORK=$(mktemp -d "${TMPDIR:-/tmp}/tannen-rehearsal-XXXXXX")
CLONE="$WORK/repo"
LOG="$WORK/transcript.txt"
STAMPED="$WORK/transcript.stamped"   # same lines, each prefixed with elapsed seconds
SITTING="$WORK/sitting"              # the driver's $TANNEN_SITTING_SCRATCH
STEPFILE="$SITTING/steps"            # ...and the breadcrumb it appends a step to
PROMPTFILE="$SITTING/prompts"        # ...and "<prompt index> <step>", one line per prompt
mkdir -p "$SITTING"
SILENCE_LIMIT=25                     # seconds the driver may be quiet without saying so

# ISOLATION, AS A POSITIVE CONTROL RATHER THAN A PROMISE. The header above says nothing here
# touches the real repo; until M3 nothing checked it, and "the driver never writes under
# $ROOT" was a claim of exactly the kind this project refuses everywhere else. Record the
# real repository's state BEFORE the driver runs and compare after.
#
# Tracked changes come from `status --porcelain --untracked-files=no`; untracked ones from a
# separate `ls-files --others --exclude-standard`, so .venv and other ignored noise never
# enter. The allowlist exists because a builder legitimately drafts under docs/, decisions/
# and digest/ while a two-hour run is going, and their edits are not the driver's — it is
# scoped to where THIS repo's builder writes, not copied from elsewhere. The trailing
# `|| true` keeps grep's empty-match exit 1 from killing the function under set -e.
ROOT_HEAD_BEFORE=$(git -C "$ROOT" rev-parse HEAD)
root_state() { git -C "$ROOT" status --porcelain --untracked-files=no
               git -C "$ROOT" ls-files --others --exclude-standard \
                   | grep -vE '^(docs|decisions|digest)/' || true; }
ROOT_STATUS_BEFORE=$(root_state)
# A bare FAIL on the isolation check reads as "the driver wrote into your repository", which
# is alarming and usually wrong — the common cause is the operator editing the tree in another
# window during the run. Name the difference rather than leaving it to be guessed.
root_state_diff() {
    local now; now=$(root_state)
    [ "$ROOT_STATUS_BEFORE" = "$now" ] && return 0
    note "what differs (before -> after). If you edited the tree while this ran, it is you:"
    diff <(printf '%s\n' "$ROOT_STATUS_BEFORE") <(printf '%s\n' "$now") | sed 's/^/     /' | head -20
    note "the driver never writes under $ROOT; HEAD is checked separately and above."
}
# Which step a run reached is the DRIVER's fact, so the driver states it: say() appends every
# header it prints to $TANNEN_SITTING_SCRATCH/steps and these read it. Scraping the
# transcript for header text would be a second copy of the driver's step vocabulary living
# out here — BRIEF §2's duplication-is-drift — and when the publication harness tried that,
# the pattern was wrong, grep matched nothing, and under `set -euo pipefail` the failing
# substitution killed the harness mid-verdict instead of failing one check (D0184). Hence
# `|| true` at every bare substitution below.
last_step()    { awk '/^Step /{last=$2} END{print last}' "$STEPFILE" 2>/dev/null; }
reached_step() { awk -v s="$1" '$1=="Step" && $2==s {f=1} END{exit !f}' "$STEPFILE" 2>/dev/null; }
cleanup() { [ "$KEEP" = 1 ] || rm -rf "$WORK"; }
trap cleanup EXIT

say "Building a disposable clone at $CLONE (mode: $MODE)"
git clone --quiet --no-hardlinks "$ROOT" "$CLONE"
git -C "$CLONE" config user.name  "rehearsal"
git -C "$CLONE" config user.email "rehearsal@invalid"
git -C "$CLONE" config commit.gpgsign false
git -C "$CLONE" config tag.gpgsign false
note "cloned $(git -C "$CLONE" rev-parse --short HEAD) with $(git -C "$CLONE" tag | wc -l) tag(s)"

# D0120: whether this run can exercise steps 10 and 11 at all is decided HERE, before two
# hours of gate, not in the verdict. If $MILESTONE-close is already in the clone, step 10's
# own guard prints "already exists — skipped" and never mints the owner-only close tag; and
# if the milestone's tags are already in required_tags, step 11's MISSING_TAGS is empty and
# the step that edits a frozen, custody-set file, re-manifests it, regenerates the custody
# set and takes a SECOND owner signature is skipped whole. The default MILESTONE=m0 made
# both true for every rehearsal ever run, while the verdict below still printed
# "$MILESTONE-close exists" green — off the tag the clone was cloned with. A post-condition
# whose answer does not depend on the run is not a post-condition.
CLOSE_TAG_PREEXISTED=0
git -C "$CLONE" rev-parse -q --verify "refs/tags/$MILESTONE-close" >/dev/null \
    && CLOSE_TAG_PREEXISTED=1
if [ "$CLOSE_TAG_PREEXISTED" = 1 ]; then
    note "$MILESTONE-close is ALREADY in the clone — steps 10 and 11 will skip, and this"
    note "run cannot say anything about them. Did you mean --milestone <the one in flight>?"
    [ "$ALLOW_PREEXISTING_CLOSE" = 1 ] || {
        echo "refusing to rehearse $MILESTONE: its close tag already exists in the clone," >&2
        echo "so steps 10 and 11 cannot run (pass --allow-preexisting-close to rehearse" >&2
        echo "steps 0-9 only, and read the verdict knowing 10-11 were not exercised)." >&2
        exit 1
    }
fi

# The receipt a sitting takes is named for the day the CUSTODIAN runs, and the verdict
# below used to look for `receipts/$(date +%F).md` — a SECOND, later reading of the same
# clock. An accept-path rehearsal runs about two hours, so the two readings disagree
# whenever a run crosses midnight, and the verdict then reports a receipt that was written
# and signed as missing. Observed 2026-09-02: the receipt was `2026-09-01.md`, taken at
# 23:23, and both receipt checks printed FAIL against a clone that had done nothing wrong.
# Snapshot what the clone already had and let the verdict ask what this run ADDED — the
# same shape as CLOSE_TAG_PREEXISTED above, and for the same reason.
RECEIPTS_BEFORE=" $(cd "$CLONE" && ls receipts/ 2>/dev/null | tr '\n' ' ')"

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
# The cp itself is DELIBERATELY DEFERRED to after the custody set is regenerated and
# re-signed below. See the comment there — the order is the whole point.
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
# gen_custody.py just rewrote custody.sha256's bytes (allowed_signers' own hash moved),
# but the REAL repo's custody.sha256.sig — carried over untouched by the clone — is a
# signature over the OLD bytes. Left as-is, check_manifest reports "signature does not
# verify for governance/custody.sha256 against owner@tannen" at the driver's own step 0,
# before it has done anything: not a defect in the driver under test, but the fixture
# starting from a state check_manifest correctly calls invalid. Re-sign with the
# throwaway key, the same key everything else in this rehearsal signs with, so the
# fixture's own setup does not manufacture a failure indistinguishable from a real one.
( cd "$CLONE" && rm -f governance/custody.sha256.sig
  ssh-keygen -Y sign -f "$KEY" -n tannen-custody governance/custody.sha256 >/dev/null )

# NOW copy the driver under test in — AFTER the custody set has been generated and signed
# over the driver the clone came with, never before.
#
# The owner's real sequence is `cp <proposal>/boundary_sitting.sh scripts/` and then run it,
# against a custody set the owner signed at the LAST sitting, over the PREVIOUS milestone's
# driver. scripts/boundary_sitting.sh is a custody-set member (governance/tier-c.yaml), so
# that cp is custody drift, the gate is red from the owner's very first command, and step 0
# survives only because unexpected_failures() tolerates that one drift BY NAME until step 7
# re-signs.
#
# Copying before gen_custody.py — which is what this harness did until 2026-09-02 — makes
# the clone's custody set cover the NEW driver, so there is no drift, so step 0's gate is
# green and the tolerance branch never executes. Six rehearsals passed without once running
# it: `grep -c "green except the custody set"` over all four kept transcripts returns 0.
# The branch that carries the owner's first command was the one branch never rehearsed.
#
# Deferring the cp to here reproduces the owner's actual starting state in BOTH modes. In
# head mode the fixture commit below still picks it up, so the tree is clean and RESUMED=0
# is unaffected; in worktree mode it rides along uncommitted, as it already did. (D0150)
cp -a "$DRIVER" "$CLONE/scripts/boundary_sitting.sh"
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

if [ "$ABORT_AT" -gt 0 ]; then
    say "Running the driver — y to every prompt except #$ABORT_AT (expected: step $ABORT_STEP)"
else
    say "Running the driver — $(printf '%s' "$ANSWER") to every prompt, transcript at $LOG"
fi
# Answers come from a FILE, not from `yes |`: a pipe that outlives the driver dies of
# SIGPIPE, and under pipefail that becomes the pipeline's status. The obvious spelling of
# the file — `yes "$ANSWER" | head -n 2000` — has the same defect one step earlier, and
# took out the first rehearsal run before the driver started. No pipe, no signal.
# 1-BASED, and it has to be: index 0 would name no prompt. With ABORT_AT=0 — the default —
# no i ever equals it, so the same line still produces the uniform answers file.
# bash prints a `read -p` prompt only when stdin is a terminal, so nothing marks the prompts
# in the transcript; the verdict identifies where the abort landed from the driver's own
# breadcrumb, not by counting prompts in prose.
if [ "$ABORT_AT" -gt 0 ]; then
    awk -v n="$ABORT_AT" 'BEGIN { for (i = 1; i <= 2000; i++) print (i == n ? "n" : "y") }' > "$WORK/answers"
else
    awk -v a="$ANSWER" 'BEGIN { for (i = 0; i < 2000; i++) print a }' > "$WORK/answers"
fi
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
# TANNEN_SITTING_FAST is NOT set here: it is inherited from the caller's environment if the
# operator set it, and a fast run must be the operator's explicit choice, never a default the
# harness quietly supplies. The driver prints a [TANNEN_SITTING_FAST] line for every gate it
# skips, and the verdict below counts them, so a fast run cannot be mistaken for a full one.
( cd "$CLONE" && env \
    SSH_AUTH_SOCK= \
    TANNEN_OWNER_KEY="$KEY" \
    TANNEN_SITTING_SCRATCH="$SITTING" \
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
present() { grep -q "$1" "$2"; }
equal()   { [ "$1" = "$2" ]; }
# A sitting that STOPS is not a sitting that failed — this driver's confirms are all
# decline-and-continue, so the only way a decline stops it is step 10 refusing to tag over
# the dirty tree step 9's declined commit left (D0051, RT-M2-06 D2). Both decline paths
# assert the same post-conditions, so they share one implementation.
stopped_cleanly() {
    check "it said so, rather than dying silently"     present 'sitting: STOP' "$LOG"
    check "and said WHERE it stopped"                  present '^reached: step ' "$LOG"
    check "it exited 1, not some other status"         test "$DRIVER_RC" -eq 1
    check "no silence over ${SILENCE_LIMIT}s went unannounced" speaks_up "$STAMPED"
    # THE TAG QUESTION IS NOT THE TREE QUESTION, and nesting it inside the dirty branch made
    # it unaskable in the one case where it matters. Four of the driver's die() sites sit
    # downstream of `git tag -s`, over a tree step 10 has just required to be clean — step
    # 11's final `make verify` going red at the close is the likeliest — so on all four the
    # tree branch says "clean" and the tag check never runs. Ask the refs first, every abort.
    if in_clone git rev-parse -q --verify "refs/tags/$MILESTONE-close" >/dev/null 2>&1; then
        note "  it stopped with $MILESTONE-close ALREADY MINTED — an owner signature stands"
        check "the driver said the close tag is minted"      present "$MILESTONE-close IS MINTED" "$LOG"
        check "and did not call that nothing half-applied"   absent 'nothing is half-applied' "$LOG"
    else
        # Deliberately a note, not a check: the branch condition just established this, so a
        # green line here would assert what the `if` decided. That is the shape this milestone
        # has recorded a dozen times, and it does not get to reappear in the verdict that finds it.
        note "  $MILESTONE-close was not minted, so the working tree is the whole account"
    fi
    if [ -z "$(in_clone git status --porcelain)" ]; then
        note "  it stopped AFTER committing: the tree is clean, nothing uncommitted to undo"
        check "the driver said the tree is clean"      present 'The tree is CLEAN' "$LOG"
    else
        note "  it stopped BEFORE committing: edits are in the working tree by design"
        check "the driver said the tree is dirty"      present 'The tree is DIRTY' "$LOG"
        check "and gave the undo"                      present 'git checkout -- \. && git clean -fd' "$LOG"
    fi
}
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

# Every run, whichever path: the driver must have left a breadcrumb, and it must not have
# written into the real repository. These two are the harness's own claims about itself, and
# until M3 neither was checked.
check "the driver left a step breadcrumb at all"         test -s "$STEPFILE"
# WHICH PATH STEP 0 TOOK IS A FACT ABOUT WHAT THIS RUN COVERED, and a verdict that does not
# say it lets a green run imply coverage it does not have. In --from worktree mode the
# working tree is applied as a patch, which is a tracked modification, so step 0's clause (a)
# sets RESUMED=1 and the precondition gate is SKIPPED on every worktree run ever made. Say so.
if present 'so this is a RESUMED sitting' "$LOG"; then
    note "NOTE: step 0 took the RESUMED path, so its precondition gate was NOT exercised."
    note "      Only --from head starts from a clean tree and runs it."
else
    # AND "IT RAN" IS NOT "IT MEASURED SOMETHING". Step 0's gate is announced as 35 minutes and
    # completes in zero seconds: check_manifest.py is the FIRST recipe line of the verify target,
    # the cp that installs the driver is custody drift on a custody-set member, so make stops
    # there and check_decisions, the pytest suite, the laws report and lint-imports never run
    # (D0151; docs/SITTING.md:36-38). Reporting only "the gate ran" let this harness's own author
    # read coverage into a three-line run and write it into the README twice. Measure it.
    # THE ANCHOR COVERS BOTH SPELLINGS ON PURPOSE. This scan used to key on "[waiting] the
    # full gate:", which is exactly the banner owner ruling (2) of 2026-09-10 removes from a
    # drifted step 0 — so the fix for the driver would have silently blinded the detector
    # that caught the driver, and the verdict would have gone from measuring zero seconds to
    # measuring nothing while printing the same green. Fourth detector-versus-proxy episode
    # in this milestone, and the first one caught BEFORE it shipped.
    GATE0_SECS=$(awk -F'\t' '/\[waiting\] the (full gate:|floor check only)|The gate below is the custodian alone/ && !armed { start = $1; armed = 1; next }
                              /== Step 1 / { if (armed) print $1 - start; exit }' "$STAMPED" 2>/dev/null)
    # ANCHORED, and that is not style: a bare / passed/ matched D0117's TITLE in the Tier-C
    # queue step 0 prints, and reported the empty gate as having run a suite. Third proxy-
    # matching detector in one session; caught only by running the control.
    GATE0_TESTS=$(awk '/\[waiting\] the (full gate:|floor check only)|The gate below is the custodian alone/ { armed = 1 }
                       /== Step 1 / { exit }
                       armed && /^[0-9]+ passed/ { n++ }
                       END { print n + 0 }' "$LOG")
    note "step 0 entered its precondition gate (RESUMED=0) and it ran for ${GATE0_SECS:-?}s"
    if [ "${GATE0_TESTS:-0}" -eq 0 ]; then
        note "      IT ESTABLISHED NOTHING — no pytest summary before step 1, so neither"
        note "      check_decisions, the suite, the laws report nor lint-imports ran there."
        # NAME THE MECHANISM ONLY WHERE IT WAS OBSERVED. Under FAST the step-0 gate is the
        # custodian and `make` is never invoked, so the check_manifest explanation — correct
        # for every full run — would be this note asserting a cause it did not see. That is
        # the exact error the driver line beneath it was just corrected for; a verdict that
        # repeats it about the driver would be worth nothing.
        if grep -q 'NOT RUN: make verify at step 0' "$LOG"; then
            note "      (TANNEN_SITTING_FAST: the gate was the custodian alone, so this run says"
            note "      nothing about where a real make verify would have stopped.)"
        else
            note "      make stopped at check_manifest, verify's first recipe line, where the cp"
            note "      that installed the driver shows as custody drift."
        fi
        note "      The precondition is established BEFORE the cp or not at all (D0151, D0206)."
    else
        note "      and it reached the suite, so the precondition was genuinely established here."
    fi
    # OWNER RULING (2), 2026-09-10: "the 35-minute banner must not appear on a gate that
    # cannot run", and the continuation line must claim only what it established. Both are
    # step-0 text and therefore this harness's business. The banner assertion is
    # unconditional: a rehearsal always cps the driver into the clone, so the custody drift
    # that makes the gate vacuous is present on every run this harness can make. The
    # continuation line only exists if the owner accepted the gate, so it is asserted only
    # when the driver announced it was running one.
    check "no full-gate ETA was promised for a gate the cp makes vacuous" \
        absent '\[waiting\] the full gate:' "$LOG"
    # THE GATE IS ENTERED IN TWO REGIMES AND BOTH PRINT THE CONTINUATION LINE. Gating this
    # on the drifted-banner text alone would have silently stopped asserting it the moment a
    # FAST run took the other branch — the same shape as the anchor bug two blocks up, found
    # the same way: by reading the verdict of the run that was supposed to prove the fix.
    if present '\[waiting\] the floor check only' "$LOG" || present 'NOT RUN: make verify at step 0' "$LOG"; then
        check "the gate's continuation line claims only what the run established" \
            present 'that is ALL this established' "$LOG"
    else
        note "NOTE: step 0's gate was declined or skipped, so the continuation line it prints"
        note "      was not exercised. Only an accepted, non-FAST step-0 gate reaches it."
    fi
fi
check "the real repo's HEAD is untouched"                equal "$ROOT_HEAD_BEFORE" "$(git -C "$ROOT" rev-parse HEAD)"
check "the real repo's working tree is untouched"        equal "$ROOT_STATUS_BEFORE" "$(root_state)"
root_state_diff
FAST_SKIPS=$(grep -c 'TANNEN_SITTING_FAST' "$LOG" || true)
[ "$FAST_SKIPS" -eq 0 ] || note "NOTE: $FAST_SKIPS gate(s) were SKIPPED (TANNEN_SITTING_FAST). This run says nothing about them."

# STEP 5 INSTALLS A POISON FIXTURE, so the custody floor is legitimately red until step 7
# re-signs it and DECISIONS.md is stale until step 9 regenerates: the check_decisions the
# driver runs at step 5 is EXPECTED to fail, and it reported that failure as an anomaly on
# every accept run ever made. Adding the line to the position-bounded tolerance below would
# have been the WRONG fix: it is the same line D0199 failed on in rehearsal 1, so a blanket
# skip would have hidden the only defect these rehearsals have so far caught. Name the
# transient instead, assert the block carries nothing beyond it, and let anything else through.
CD_MID_KNOWN='^  - decisions/0063-[^:]*\.yaml: binding does not resolve — pytest node fails: tests/test_governance_scripts\.py$'
CD_MID_KNOWN="$CD_MID_KNOWN"'|^  - decisions/0177-[^:]*\.yaml: binding does not resolve — pytest node fails: tests/test_governance_scripts\.py::test_check_passes_on_real_tree$'
CD_MID_KNOWN="$CD_MID_KNOWN"'|^  - DECISIONS\.md is stale'

# A TOLERANCE THAT WAS NEVER EXERCISED IS NOT EVIDENCE. Both blocks below pass trivially when
# the failure they tolerate did not occur at all — and a run that skipped the gate entirely
# then reports the same green as a run that inspected a real block and found it clean. That is
# the sixth time in this driver and its harness that a guard has measured a proxy instead of
# the state, so each one counts its input first and says which case it is in.
pre7_fails() {   # <FAIL-line regex> -> how many such lines appear before step 7
    awk -v pat="$1" '/== Step 7/ { exit } $0 ~ pat { n++ } END { print n + 0 }' "$LOG"
}
pre7_unknown() { # <FAIL-line regex> <known-detail regex> -> detail lines outside the known set
    awk -v pat="$1" '
      /== Step 7/        { exit }
      $0 ~ pat           { inblock = 1; next }
      inblock && /^  - / { print; next }
      inblock            { inblock = 0 }' "$LOG" | grep -vE "$2" || true
}

CD_MID_OK=0
if [ "$(pre7_fails '^check_decisions: FAIL')" -gt 0 ]; then
    CD_MID_EXTRA=$(pre7_unknown '^check_decisions: FAIL' "$CD_MID_KNOWN")
    [ -z "$CD_MID_EXTRA" ] && CD_MID_OK=1
    check "the pre-step-7 check_decisions failure is only the known step-5 transient" \
        test -z "$CD_MID_EXTRA"
    [ -z "$CD_MID_EXTRA" ] || printf '%s\n' "$CD_MID_EXTRA" | sed 's/^  - /     /'
else
    note "NOTE: no check_decisions failure before step 7, so that tolerance was not exercised."
fi

# STEP 0's PRECONDITION GATE RUNS check_manifest AGAINST A TREE THE HARNESS HAS JUST EDITED:
# the driver under test is copied over scripts/boundary_sitting.sh, a custody-set member, and
# is deliberately NOT re-signed — step 7 is where that happens. So the gate reports custody
# drift on exactly that path, and the driver answers "green except the custody set, which is
# this sitting's step 7 — continuing". The owner's real sequence is the same `cp`, so this is
# what a real sitting shows too. It had never been seen before 2026-09-09 because only a
# --from head run reaches this gate: everywhere else RESUMED=1 skips it. Tolerate the one
# path, and nothing else — a frozen-path violation here is a stop, not a note.
CM_PRE_KNOWN='^  - custody drift: scripts/boundary_sitting\.sh changed since the custody file was written\.'
CM_PRE_OK=0
if [ "$(pre7_fails '^check_manifest: FAIL')" -gt 0 ]; then
    CM_PRE_EXTRA=$(pre7_unknown '^check_manifest: FAIL' "$CM_PRE_KNOWN")
    [ -z "$CM_PRE_EXTRA" ] && CM_PRE_OK=1
    check "the pre-step-7 check_manifest failure is only the driver's own custody drift" \
        test -z "$CM_PRE_EXTRA"
    [ -z "$CM_PRE_EXTRA" ] || printf '%s\n' "$CM_PRE_EXTRA" | sed 's/^  - /     /'
else
    note "NOTE: step 0's gate reported no check_manifest failure, so that tolerance was not"
    note "      exercised. Only --from head reaches that gate (RESUMED=0)."
fi

if [ "$ABORT_AT" -gt 0 ]; then
    # ------------------------------------------------- the single-decline path
    # THE PUBLICATION HARNESS'S SEMANTICS DO NOT TRANSFER, and porting them unexamined would
    # have produced a verdict that failed on every run. Every confirm in publication_sitting.sh
    # is spelled `confirm "..." || die "stopped at your request"`, so one `n` is exit 1. In THIS
    # driver all 42 confirms are `if confirm; then ... else note "declined"; fi` — declining is
    # a supported answer that leaves the step un-applied and the sitting running, which is the
    # whole reason every step reverts its own edits. Measured: zero `confirm ... || die` sites.
    #
    # So `--abort-at N` here means DECLINE ONE PROMPT, and the run's exit status is a fact to
    # measure, not to assert. There is exactly one prompt that stops the sitting, and only
    # indirectly: declining step 9's commit leaves the tree dirty, and step 10 then refuses to
    # tag over it — `[ -z "$(git status --porcelain)" ] || die` — because a close tag over an
    # uncommitted sitting attests a commit that does not contain it (D0051, RT-M2-06 D2). That
    # is the most valuable single decline to rehearse, and the verdict recognises it by name.
    LAST_STEP=$(last_step || true)
    say "Verdict — ONE PROMPT DECLINED: n at prompt #$ABORT_AT"
    PROMPT_STEP=$(awk -v n="$ABORT_AT" '$1==n{print $2}' "$PROMPTFILE" 2>/dev/null || true)
    note "prompt #$ABORT_AT fell in step ${PROMPT_STEP:-<not reached>}; the run's last step was ${LAST_STEP:-<none>}"
    check "the prompt map agrees with --abort-step"       equal "$PROMPT_STEP" "$ABORT_STEP"

    if [ "$DRIVER_RC" -eq 0 ]; then
        check "no silence over ${SILENCE_LIMIT}s went unannounced" speaks_up "$STAMPED"
        note "regime: the sitting CONTINUED — this driver treats a decline as an answer, not a stop"
        check "it ran to the end"                         equal "$(awk 'END{print}' "$STEPFILE" 2>/dev/null || true)" "The sitting is closed"
        check "and printed no STOP"                       absent 'sitting: STOP' "$LOG"
        check "the declined step said so in the transcript" present 'declined' "$LOG"
    else
        note "regime: the sitting STOPPED"
        stopped_cleanly
    fi
elif [ "$ANSWER" = y ]; then
    # These three are the floor for any non-abort run and must not be lost in the branching:
    # a completed sitting exits 0, prints no STOP, and never goes quiet without saying so.
    check "the driver ran to completion (exit 0)"        test "$DRIVER_RC" -eq 0
    check "no step aborted the sitting"                  absent 'sitting: STOP' "$LOG"
    check "no silence over ${SILENCE_LIMIT}s went unannounced" speaks_up "$STAMPED"
    check "$MILESTONE-close was minted by THIS run"      test "$CLOSE_TAG_PREEXISTED" -eq 0
    check "$MILESTONE-close exists"                      in_clone git rev-parse -q --verify "refs/tags/$MILESTONE-close"
    check "$MILESTONE-close verifies as owner@tannen"    in_clone git -c gpg.format=ssh \
              -c gpg.ssh.allowedSignersFile="$CLONE/allowed_signers" verify-tag "$MILESTONE-close"
    check "the custody set is signed"                    test -f "$CLONE/governance/custody.sha256.sig"
    NEW_RECEIPT=""
    for _r in "$CLONE"/receipts/*.md; do
        [ -e "$_r" ] || continue
        case "$RECEIPTS_BEFORE" in *" $(basename "$_r") "*) continue ;; esac
        NEW_RECEIPT="$_r"; break
    done
    check "this sitting took a fresh attention receipt" test -n "$NEW_RECEIPT"
    check "and signed it"                                test -f "$NEW_RECEIPT.sig"
    check "the custodian is green with no tolerances"    in_clone bash scripts/custodian.sh --check-only
    # Under a fast run the driver skipped its own gates, so a verdict that then spends
    # forty minutes proving the gate green has thrown away the reason for running fast.
    # The cheap floor still runs, and the check says which one it was.
    if [ "${TANNEN_SITTING_FAST:-0}" = 1 ]; then
        check "the custody floor is green (make verify skipped: FAST)" \
                                                         in_clone bash scripts/custodian.sh --check-only
    else
        check "the gate is green end to end"             in_clone make verify
    fi
    check "nothing was left uncommitted"                 test -z "$(in_clone git status --porcelain)"
    # ONE RUN, TWO NAMED FACTS. This was a single check piping check_decisions into
    # `grep -q "0 queued"`, so ANY failure of that guard — a binding that stopped resolving, a
    # stale projection, a schema error — printed "FAIL no Tier-C door is left unsigned" and
    # sent the reader to decisions/ looking for an unsigned door.
    #
    # On 2026-09-09 it did precisely that. Every Tier-C door WAS signed; the real defect was
    # that D0199's binding named the fixture path step 5 had just `git mv`d away, so
    # check_decisions never reached the summary line the grep was looking for (D0200). The
    # check was right to fail and wrong about why, which is this project's most familiar
    # failure mode wearing a verdict's clothing.
    CD_LOG="$WORK/check_decisions.txt"
    note "running check_decisions in the clone — the verdict's own long leg, about 10 minutes"
    in_clone bash -c '.venv/bin/python -I -P scripts/check_decisions.py' > "$CD_LOG" 2>&1
    CD_RC=$?
    check "check_decisions is green in the sitting's own tree"   test "$CD_RC" -eq 0
    check "no Tier-C door is left queued"                        present '0 queued' "$CD_LOG"
    # Name the bindings that broke, if any: a sitting MOVES files, and a binding pointing at
    # a pre-move path is the recurring shape (D0141 at M2, D0199 at M3).
    # `|| true` IS LOAD-BEARING, and it was missing for exactly one run. Under
    # `set -euo pipefail` a grep that matches NOTHING exits 1, so this line — added to name
    # offending bindings — killed the harness on the first run that had none to name. The
    # verdict died between "no Tier-C door is left queued" and the three checks after it,
    # printing RC=1 over a run whose every check had passed. The SUCCESS case broke it, which
    # is D0184's lesson arriving by a different door on the same day it was quoted.
    grep -E 'binding does not resolve' "$CD_LOG" | head -5 | sed 's/^/     /' || true
    # The breadcrumb underwrites the green verdict too: a run that stopped early and still
    # satisfied every check above would be caught here, because only the last line of a
    # completed sitting is this one.
    check "and recorded every step through the last one" \
        equal "$(awk 'END{print}' "$STEPFILE" 2>/dev/null || true)" "The sitting is closed"
else
    # --answers n DECLINES EVERYTHING, INCLUDING STEP 9'S COMMIT, so this run cannot complete
    # and asserting that it does is a defect in the verdict, not the driver. Step 9 runs
    # gen_projections and the full custodian unconditionally — they are not confirms, and the
    # custodian WRITES AND SIGNS the receipt — so the tree is necessarily dirty by step 10,
    # where the D0051 guard correctly refuses to mint a close tag over work no commit contains.
    #
    # The harness asserted `exit 0` and `no sitting: STOP` here for every run, which was true
    # while nothing refused a dirty tree. RT-M2-06 D2 added that refusal at the M2 boundary and
    # this check was never re-examined: it has been asserting the opposite of the correct
    # outcome ever since. Measured 2026-09-09, two FAILs on a run that behaved perfectly.
    say "Verdict — EVERY prompt declined"
    note "a fully declined sitting MUST stop at step 10: step 9's receipt is written"
    note "unconditionally, so the tree is dirty and D0051 forbids tagging over it"
    stopped_cleanly
    check "it got as far as step 10 before stopping" reached_step 10
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
# On a --abort-at run the driver's own `sitting: STOP` is the EXPECTED outcome, not an
# anomaly: the verdict above has already checked that it is present, says which step it
# names, and confirms the tree state that goes with it. Left in this scan it reported the
# run's whole purpose as an unexpected failure, which is how a rehearsal teaches an operator
# to skim past this section — and this section is where the genuinely unexpected shows up.
# Both decline paths expect a STOP: --abort-at N declines one prompt, --answers n declines
# every prompt, and either way step 10's refusal is the run working. Only an accept run has
# no business printing one, and there the check above catches it.
DECLINES=0; { [ "$ABORT_AT" -gt 0 ] || [ "$ANSWER" = n ]; } && DECLINES=1
awk -v declined="$DECLINES" -v cdok="$CD_MID_OK" -v cmok="$CM_PRE_OK" '
  declined > 0 && /^sitting: STOP/ { next }
  /== Step 7/ { strict = 1 }
  cdok > 0 && strict == 0 && /^check_decisions: FAIL/ { next }
  cmok > 0 && strict == 0 && /^check_manifest: FAIL/ { next }
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

if [ -s "$PROMPTFILE" ]; then
    say "Prompt map — which prompt index fell in which step"
    note "Choose --abort-at N from THIS, not from counting confirm sites: several are inside"
    note "conditionals, so the mapping depends on repo state. N is 1-based and counts the"
    note "driver's pause() prompts as well as its confirm() ones — both read a line."
    # `have` rather than `prev != ""`, and that is not style. `prev` is assigned from $2, a
    # FIELD, so awk keeps it a "strnum": compared against the string constant "" it coerces
    # BOTH to numbers, and step 0's id is literally "0", so `0 != 0` is false and the entire
    # first group vanishes. Measured: the map printed step 3b onward and silently omitted
    # prompts 1-3, which are step 0's — so an operator picking --abort-at 2 would have found
    # no step in the map for it. A flag cannot be coerced.
    awk '{ s = $2 "" }
         s != prev { if (have) printf "     step %-5s prompts %s-%s\n", prev, start, last
                     prev = s; start = $1; have = 1 }
         { last = $1 }
         END { if (have) printf "     step %-5s prompts %s-%s\n", prev, start, last }' "$PROMPTFILE"
fi

say "Transcript: $LOG (timed copy: $STAMPED)"
[ "$KEEP" = 1 ] && note "clone kept at $CLONE" || note "(--keep to inspect the clone)"
if [ "$FAILED" -eq 0 ]; then
    printf '\n\033[32mrehearsal: the sitting completes\033[0m — mechanics only; the real key signs nothing here\n'
else
    printf '\n\033[31mrehearsal: %d check(s) failed\033[0m — fix the driver before the owner runs it\n' "$FAILED"
fi
exit "$FAILED"
