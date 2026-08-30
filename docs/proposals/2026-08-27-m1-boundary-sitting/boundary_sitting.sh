#!/usr/bin/env bash
# scripts/boundary_sitting.sh — interactive driver for a MILESTONE BOUNDARY sitting
# (docs/SITTING.md; the M0→M1 queue was D0060, this M1→M2 queue is D0105). OWNER-RUN,
# owner key present.
#
# THIS COPY is docs/proposals/2026-08-27-m1-boundary-sitting/boundary_sitting.sh, tuned
# for the M1 boundary (D0104's red-team findings, D0095's required_tags lag). Per
# CLAUDE.md's build protocol, the original scripts/boundary_sitting.sh is never edited in
# place outside a sitting — the owner copies THIS FILE over it before running (step 0 of
# D0105's queue), the same way step 6 below replaces scripts/custodian.sh. That copy is
# itself expected custody drift, tolerated in unexpected_failures() below by name.
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
cd "$(dirname "$0")/.."

MILESTONE="${1:-m1}"
OWNER_KEY="${TANNEN_OWNER_KEY:-$HOME/.ssh/tannen_owner}"
# PROPOSALS still names the M0→M1 sitting's own directory: steps 3/4/4b/6 below compare
# against artifacts drafted there, and every one of those comparisons is already-applied
# (a no-op skip) as of this milestone — nothing there needed a second draft. PROPOSALS_M1
# is this sitting's own directory, used only where this milestone adds something new
# (the oracle-shadow poison row, the custodian.sh diff carrying its poison line).
PROPOSALS="docs/proposals/2026-08-25-boundary-sitting"
PROPOSALS_M1="docs/proposals/2026-08-27-m1-boundary-sitting"
CANDIDATES="docs/redteam/fixture-candidates"
KEYREF="$OWNER_KEY"          # what ssh-keygen -Y sign is pointed at (key file, or .pub
                             # when the private half is loaded into an agent)
# The venv interpreter at a literal path, in isolated mode — the same spelling the Makefile
# uses and for the same reason (RT-02, conferral ruling 3, D0063). `uv run` would resolve
# through pyproject.toml and uv.lock, which are builder-controlled; a script that drives the
# owner's key should not take its interpreter from the party it is checking on.
PY="$PWD/.venv/bin/python"
# How long the gate takes, measured not guessed. M0's "a minute" (2026-08-25, 174 tests) is
# stale: M1 added eight semirings, the executor and the layer lattice, and the batched
# pytest check_decisions.py runs to resolve bindings now carries the full 537-test suite.
# Measured this session, under shared-machine load, at 14-20 minutes; a quiet machine may
# be faster, but "a minute" would read as hung long before the gate finishes.
VERIFY_ETA="15-20 minutes (M1's suite is much larger than M0's; a quiet machine may be faster)"

say()  { printf '\n\033[1m== %s\033[0m\n' "$*"; }
note() { printf '   %s\n' "$*"; }
# A step about to be quiet for more than a moment says so FIRST, and says it with this
# helper rather than an ordinary note, so scripts/rehearse_sitting.sh can check the rule
# mechanically: in a rehearsal transcript, every silence longer than 25 seconds must have
# one of these lines directly above it. An owner watching a still terminal cannot tell
# waiting from hung — at the M0 sitting they could not, and killed the driver twice at its
# own first question (D0069). Stating the expected duration is the whole fix; the harness
# exists to keep it stated as the driver grows.
waiting() { printf '   [waiting] %s\n' "$*"; }
die()  { printf '\nsitting: STOP — %s\n' "$*" >&2; exit 1; }
confirm() { local a; read -rp "$1 [y/N] " a; [[ "${a:-}" == [yY]* ]]; }
pause() { read -rp "   $1" _; }
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
    git add -A && git commit -m "$1" && return 0
    git add -A && git commit -m "$1"
}

# ---------------------------------------------------------------- 0. preconditions
say "Boundary sitting — $MILESTONE. Precondition: a green gate and a read queue"
[ -x "$PY" ] || die "no interpreter at $PY — run 'uv sync --frozen' first"
[ -f "$OWNER_KEY" ] || die "no owner key at $OWNER_KEY (set TANNEN_OWNER_KEY)"
grep -q '^owner@tannen ' allowed_signers || die "owner@tannen is not enrolled in allowed_signers"
if confirm "Run 'make verify' now (recommended — nothing should be signed over a red gate)?"; then
    # Capturing output and DISPLAYING it are two different acts, and `$( )` only does the
    # first. The gate takes the better part of a minute — 174 tests, ten law suites and a
    # batched pytest run inside check_decisions — and this printed nothing at all until it
    # was over, so the sitting read as hung at its own first question (owner, 2026-08-25;
    # killed twice before it ever reached step 1). A driver that spends the owner's
    # attention owes them a visible reason to keep waiting. tee does both jobs: the run
    # streams to the terminal, and the log is what unexpected_failures reads afterwards.
    # PIPESTATUS must be read on the very NEXT line — any command in between, an
    # assignment included, replaces it.
    waiting "the full gate: about $VERIFY_ETA. It streams below; nothing to do but watch."
    verify_log=$(mktemp -t tannen-verify.XXXXXX)
    make verify 2>&1 | tee "$verify_log"
    verify_rc=${PIPESTATUS[0]}
    verify_out=$(cat "$verify_log"); rm -f "$verify_log"
    if [ "$verify_rc" -ne 0 ]; then
        unexpected=$(unexpected_failures "$verify_out")
        [ -z "$unexpected" ] || die "verify is red — fixing it is builder work; sign nothing yet:
$unexpected"
        note "green except the custody set, which is this sitting's step 7 — continuing"
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

# ---------------------------------------------------------------- 2. builder handoff
say "Step 2 — the guard that makes step 1 mean something (builder work)"
if grep -q "affirmative signature only" scripts/check_decisions.py; then
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

# ---------------------------------------------------------------- 4b. frozen text
say "Step 4b — the two frozen files the sitting amends"
if grep -q 'Metric calibration' BRIEF.md; then
    note "BRIEF §9.1 amendment already applied — skipped"
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

# ---------------------------------------------------------------- 5. poison fixtures
say "Step 5 — install the red-team poison fixtures (author-key territory)"
note "Eight fixtures. Seven are the M0→M1 corpus, already installed by that sitting (this"
note "loop skips them). The eighth, oracle-shadow (RT-M1-01), is new: drafted under"
note "$CANDIDATES and verified to fail src/tannen/laws/plugin.py's oracle-shadow check for"
note "the intended reason. check-decisions-file-skip (RT-M1-05) is deliberately NOT in"
note "this list — its guard fix is not committed yet (D0103); installing that fixture"
note "before the fix lands would leave the custodian permanently red against the shipped"
note "guard, which step 5's own marking convention exists to prevent. It joins this list"
note "at the sitting where the RT-M1-05 patch (docs/redteam/fixture-candidates/check-decisions-file-skip/rt-m1-05-check-decisions.patch)"
note "is actually applied — see D0105's queue, item after the custody re-signature."
note "Installing one is a git mv, a manifest row per file, and a poison line in the"
note "custodian — the custodian replacement in step 6 already carries every line, so the"
note "fixtures must land first or it will fail on missing paths."
FIXTURES="lint-imports-kernel check-decisions-ratchet check-decisions-nested-hatch
          check-manifest-sealed check-manifest-unsigned-policy
          check-decisions-unsigned-tier-c custodian-tag-signer
          oracle-shadow"
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
if ! grep -q 'lint-imports-kernel' tests/poison/README.md; then
    if confirm "Add the new fixtures to the tests/poison/README.md table?"; then
        cat "$PROPOSALS/poison-readme-rows.md" >> tests/poison/README.md
        regen_manifest_row tests/poison/README.md
        git --no-pager diff tests/poison/README.md
    fi
fi
if [ -d tests/poison/oracle-shadow ] && ! grep -q 'oracle-shadow' tests/poison/README.md; then
    if confirm "Add oracle-shadow (RT-M1-01) to the tests/poison/README.md table?"; then
        cat "$PROPOSALS_M1/poison-readme-rows.md" >> tests/poison/README.md
        regen_manifest_row tests/poison/README.md
        git --no-pager diff tests/poison/README.md
    fi
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
waiting "checking the decision bindings still resolve — up to a minute; it runs pytest"
broken=$("$PY" -I -P scripts/check_decisions.py 2>&1 \
    | grep -E 'binding does not resolve — (target does not exist|not listed in MANIFEST)' || true)
[ -z "$broken" ] || die "a decision binding stopped resolving when the fixtures moved:
$broken
  Retarget it to the installed tests/poison/ path — builder work, no signature involved.
  Nothing has been signed; the fixtures stay installed and step 5 will skip them next run."

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
if [ -d tests/poison/check-decisions-file-skip ] && ! grep -q 'check-decisions-file-skip' tests/poison/README.md; then
    if confirm "Add check-decisions-file-skip (RT-M1-05) to tests/poison/README.md?"; then
        cat "$PROPOSALS_M1/poison-readme-row-file-skip.md" >> tests/poison/README.md
        regen_manifest_row tests/poison/README.md
        git --no-pager diff tests/poison/README.md
    fi
fi

# ---------------------------------------------------------------- 6. the custodian
say "Step 6 — the custodian itself (trust root; yours alone to apply)"
# $PROPOSALS_M1/custodian.sh, not $PROPOSALS/custodian.sh: the M0→M1 draft is already
# installed (that comparison would read "already applied" and never offer the one line
# this milestone adds). This sitting's own draft is the LIVE custodian.sh plus one new
# poison line for oracle-shadow (RT-M1-01) — the diff below should show only that.
if diff -q scripts/custodian.sh "$PROPOSALS_M1/custodian.sh" >/dev/null; then
    note "already applied — skipped"
else
    note "Read the whole diff. This file is the guard of the guards; the poison corpus"
    note "keeps it honest, and every line you accept here is a line you are vouching for."
    pause "Enter for the diff (q quits the pager)..."
    diff -u scripts/custodian.sh "$PROPOSALS_M1/custodian.sh" | page
    if confirm "Install this custodian?"; then
        cp "$PROPOSALS_M1/custodian.sh" scripts/custodian.sh
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
    case "$rec_id" in
        D0061) note "APPLIED-BY: already built and owner-signed; accepting ratifies executed work" ;;
        D0095) note "APPLIED-BY: item 1 lands at step 11. Item 2 — the half this record calls" ;
               note "            the one that matters more — is applied by NOTHING" ;;
        D0108) note "APPLIED-BY: step 4d, earlier in this sitting. If you declined it there," ;
               note "            the fix did not land and a yes here signs an untrue record" ;;
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

# ---------------------------------------------------------------- 9. gate + receipt
say "Step 9 — regenerate, verify, and take the attention receipt"
"$PY" -I -P scripts/gen_projections.py || die "projection generation failed"
waiting "the full gate again, now over everything this sitting changed: about $VERIFY_ETA"
make verify || die "verify red — stop here and hand back to the builder; sign no tag over a red gate"
note "full custodian run — writes and signs receipts/$(date +%F).md"
bash scripts/custodian.sh || die "custodian red — no receipt was signed"
make digest
if [ -n "$(git status --porcelain)" ]; then
    git status --short
    confirm "Commit the sitting so far?" && commit_with_hook_retry "$MILESTONE boundary sitting: custody set, tag-signer rule, poison fixtures, receipt"
fi

# ---------------------------------------------------------------- 10. the close tag
say "Step 10 — sign $MILESTONE-close, LAST"
if git rev-parse -q --verify "refs/tags/$MILESTONE-close" >/dev/null; then
    note "$MILESTONE-close already exists — skipped"
else
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

say "Step 11 — the tags this milestone minted join the required set, and the custody set is re-signed"
# D0095: required_tags always lags by construction — a boundary tag is minted by the same
# session that cannot then add it to the frozen, custody-set file that names it required.
# $MILESTONE-laws-freeze was minted at M1 Session A's freeze commit and has been missing
# from required_tags ever since (filed D0095, blocked-on-owner); $MILESTONE-close is
# minted moments ago, at step 10, above. Both are added here, in the SAME motion, so this
# boundary does not repeat D0095's own lag at the next one — exactly its recommendation.
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
waiting "the last full gate, with the close tag in the required set: about $VERIFY_ETA"
make verify || die "verify red at the close — hand back to the builder"
if [ -n "$(git status --porcelain)" ]; then
    commit_with_hook_retry "$MILESTONE close: required tags and custody set re-signed"
fi

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
note "M1 Session A in a fresh session."
