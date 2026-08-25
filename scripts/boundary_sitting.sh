#!/usr/bin/env bash
# scripts/boundary_sitting.sh — interactive driver for a MILESTONE BOUNDARY sitting
# (docs/SITTING.md; the M0→M1 queue is decision D0060). OWNER-RUN, owner key present.
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

MILESTONE="${1:-m0}"
OWNER_KEY="${TANNEN_OWNER_KEY:-$HOME/.ssh/tannen_owner}"
PROPOSALS="docs/proposals/2026-08-25-boundary-sitting"
CANDIDATES="docs/redteam/fixture-candidates"
KEYREF="$OWNER_KEY"          # what ssh-keygen -Y sign is pointed at (key file, or .pub
                             # when the private half is loaded into an agent)

say()  { printf '\n\033[1m== %s\033[0m\n' "$*"; }
note() { printf '   %s\n' "$*"; }
die()  { printf '\nsitting: STOP — %s\n' "$*" >&2; exit 1; }
confirm() { local a; read -rp "$1 [y/N] " a; [[ "${a:-}" == [yY]* ]]; }
pause() { read -rp "   $1" _; }

sign_owner() {   # <file> <namespace>   -> writes <file>.sig
    ssh-keygen -Y sign -f "$KEYREF" -n "$2" "$1" >/dev/null \
        || die "signature failed for $1 (namespace $2)"
    note "signed: $1.sig (namespace $2)"
}
verify_owner() { # <file> <namespace>   -> 0 if a valid owner signature is already there
    [ -f "$1.sig" ] && ssh-keygen -Y verify -f allowed_signers -I owner@tannen \
        -n "$2" -s "$1.sig" <"$1" >/dev/null 2>&1
}
regen_manifest_row() {   # author-key territory: caller confirms before calling
    grep -v "  $1\$" MANIFEST.sha256 > MANIFEST.tmp \
        && sha256sum "$1" >> MANIFEST.tmp && mv MANIFEST.tmp MANIFEST.sha256
}
add_manifest_rows() {    # every file under a directory (sealed dirs carry a row each)
    local dir="$1"
    while IFS= read -r f; do
        grep -q "  $f\$" MANIFEST.sha256 || sha256sum "$f" >> MANIFEST.sha256
    done < <(find "$dir" -type f | sort)
}
commit_with_hook_retry() {   # regen-projections may rewrite files on the first try
    git add -A && git commit -m "$1" && return 0
    git add -A && git commit -m "$1"
}

# ---------------------------------------------------------------- 0. preconditions
say "Boundary sitting — $MILESTONE. Precondition: a green gate and a read queue"
[ -f "$OWNER_KEY" ] || die "no owner key at $OWNER_KEY (set TANNEN_OWNER_KEY)"
grep -q '^owner@tannen ' allowed_signers || die "owner@tannen is not enrolled in allowed_signers"
if confirm "Run 'make verify' now (recommended — nothing should be signed over a red gate)?"; then
    make verify || die "verify is red — fixing it is builder work; sign nothing yet"
fi
if confirm "Show the digest's owner queue (what this sitting is for)?"; then
    latest_digest=$(ls -1 digest/*.md 2>/dev/null | tail -1)
    [ -n "$latest_digest" ] && sed -n '/## Requires owner/,/^## /p' "$latest_digest" | "${PAGER:-less}"
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
sign_tier_c_records() {
    local signed=0 rec id tier status
    while IFS= read -r rec; do
        tier=$(sed -n 's/^tier: *//p' "$rec" | head -1)
        status=$(sed -n 's/^status: *//p' "$rec" | head -1)
        id=$(sed -n 's/^id: *//p' "$rec" | head -1)
        [ "$tier" = "C" ] || continue
        case "$status" in accepted) ;; *) continue ;; esac
        verify_owner "$rec" tannen-decision && continue
        printf '\n'
        sed -n '1,/^rationale:/p' "$rec" | head -40
        note "-- $id ($rec): Tier C, status accepted, no owner signature"
        if confirm "Sign $id? (BRIEF §9.2: Tier C is affirmative signature only, never silence)"; then
            sign_owner "$rec" tannen-decision
            signed=$((signed + 1))
        else
            note "left unsigned — the Tier-C guard will report it until it is signed or"
            note "its status is changed to rejected/blocked-on-owner"
        fi
    done < <(ls -1 decisions/*.yaml | sort)
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
    "${PAGER:-less}" docs/proposals/2026-08-24-policy-in-repo-mechanics.md
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
        "${PAGER:-less}" docs/proposals/2026-08-24-binding-strength-grade.md
    fi
    if confirm "Apply $PROPOSALS/apply_binding_strength.py?"; then
        uv run python "$PROPOSALS/apply_binding_strength.py" || die "applier failed"
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
        "${PAGER:-less}" "$PROPOSALS/brief-9.1-amendment.md"
    fi
    note "BRIEF.md is owner text and frozen — apply the two blocks in your editor."
    if confirm "Open BRIEF.md now?"; then
        "${EDITOR:-nano}" BRIEF.md
        git --no-pager diff BRIEF.md
        if confirm "Keep this edit?"; then
            regen_manifest_row BRIEF.md
        else
            git checkout -- BRIEF.md
        fi
    fi
fi
if diff -q .github/workflows/ci.yml "$PROPOSALS/ci.yml" >/dev/null; then
    note "ci.yml already current — skipped"
else
    note "ci.yml is frozen, so the builder cannot add the fetch-depth the new guards need:"
    note "a shallow checkout arrives without tags, which the custody floor refuses (RT-15),"
    note "and without the history the receipt chain walks."
    diff -u .github/workflows/ci.yml "$PROPOSALS/ci.yml" | "${PAGER:-less}"
    if confirm "Install this ci.yml?"; then
        cp "$PROPOSALS/ci.yml" .github/workflows/ci.yml
        regen_manifest_row .github/workflows/ci.yml
    fi
fi

# ---------------------------------------------------------------- 5. poison fixtures
say "Step 5 — install the red-team poison fixtures (author-key territory)"
note "Seven fixtures, all drafted under $CANDIDATES and verified to fail their guard for"
note "the intended reason. Installing one is a git mv, a manifest row per file, and a"
note "poison line in the custodian — the custodian replacement in step 6 already carries"
note "every line, so the fixtures must land first or it will fail on missing paths."
FIXTURES="lint-imports-kernel check-decisions-ratchet check-decisions-nested-hatch
          check-manifest-sealed check-manifest-unsigned-policy
          check-decisions-unsigned-tier-c custodian-tag-signer"
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

# ---------------------------------------------------------------- 6. the custodian
say "Step 6 — the custodian itself (trust root; yours alone to apply)"
if diff -q scripts/custodian.sh "$PROPOSALS/custodian.sh" >/dev/null; then
    note "already applied — skipped"
else
    note "Read the whole diff. This file is the guard of the guards; the poison corpus"
    note "keeps it honest, and every line you accept here is a line you are vouching for."
    pause "Enter for the diff (q quits the pager)..."
    diff -u scripts/custodian.sh "$PROPOSALS/custodian.sh" | "${PAGER:-less}"
    if confirm "Install this custodian?"; then
        cp "$PROPOSALS/custodian.sh" scripts/custodian.sh
        regen_manifest_row scripts/custodian.sh
        note "running it — every guard must FAIL its poison, for its own marker"
        bash scripts/custodian.sh --check-only \
            || die "custodian RED after the patch — do not go further; this is the point of running it here"
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
uv run python scripts/gen_custody.py || die "custody generation failed"
if confirm "Review the custody set before signing it?"; then
    "${PAGER:-less}" governance/custody.sha256
fi
verify_owner governance/custody.sha256 tannen-custody \
    || sign_owner governance/custody.sha256 tannen-custody

# ---------------------------------------------------------------- 8. resolve the queue
say "Step 8 — the records this sitting resolves"
note "Every Tier-C record still recorded blocked-on-owner is a question this sitting was"
note "convened to answer. Accepting one is the affirmative act; leaving it blocked is"
note "also an answer, and it queues to the next sitting without stopping any work."
while IFS= read -r rec; do
    [ "$(sed -n 's/^tier: *//p' "$rec" | head -1)" = "C" ] || continue
    grep -q '^status: blocked-on-owner$' "$rec" || continue
    printf '\n'
    sed -n '1,/^rationale:/p' "$rec" | head -40
    rec_id=$(sed -n 's/^id: *//p' "$rec" | head -1)
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
done < <(ls -1 decisions/*.yaml | sort)
sign_tier_c_records

# ---------------------------------------------------------------- 9. gate + receipt
say "Step 9 — regenerate, verify, and take the attention receipt"
uv run python scripts/gen_projections.py || die "projection generation failed"
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
    "${PAGER:-less}" "$msg"
    if confirm "Sign $MILESTONE-close with this message?"; then
        git -c gpg.format=ssh -c user.signingkey="$KEYREF" \
            tag -s "$MILESTONE-close" -F "$msg" || die "tag signing failed"
        git -c gpg.format=ssh -c gpg.ssh.allowedSignersFile="$PWD/allowed_signers" \
            verify-tag "$MILESTONE-close" || die "$MILESTONE-close does not verify"
    fi
    rm -f "$msg"
fi

say "Step 11 — the close tag joins the required set, and the custody set is re-signed"
if git rev-parse -q --verify "refs/tags/$MILESTONE-close" >/dev/null \
   && ! grep -q "  - $MILESTONE-close\$" governance/tag-roles.yaml; then
    note "A tag that exists but is not required can be deleted in silence (RT-15)."
    if confirm "Add $MILESTONE-close to tag-roles.yaml required_tags?"; then
        python3 - "$MILESTONE" <<'PY'
import pathlib, sys
milestone = sys.argv[1]
p = pathlib.Path("governance/tag-roles.yaml")
src = p.read_text()
anchor = "required_tags:\n"
assert src.count(anchor) == 1
end = src.index(anchor) + len(anchor)
p.write_text(src[:end] + f"  - {milestone}-close\n" + src[end:])
PY
        regen_manifest_row governance/tag-roles.yaml
        git --no-pager diff governance/tag-roles.yaml
        uv run python scripts/gen_custody.py
        rm -f governance/custody.sha256.sig
        sign_owner governance/custody.sha256 tannen-custody
    fi
fi
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
