#!/usr/bin/env bash
# scripts/opening_sitting.sh — interactive driver for the opening sitting
# (docs/OPENING.md). OWNER-RUN, on the owner's machine, hardware key plugged in.
#
# Builder-drafted (decision D0037), but it signs nothing by itself: every
# signature is your key answering to your touch, and every edit to author-key
# territory (allowed_signers, scripts/custodian.sh, their MANIFEST rows) is
# shown as a diff and confirmed at the keyboard before it lands. Read this
# file end to end before running it — it drives your key.
#
# Safe to re-run: each step detects work already done and skips it.
# Expect up to 4 key touches: keygen, policy signature, brief-freeze tag,
# first receipt.
set -uo pipefail
cd "$(dirname "$0")/.."

OWNER_KEY="${TANNEN_OWNER_KEY:-$HOME/.ssh/tannen_owner}"

say()  { printf '\n\033[1m== %s\033[0m\n' "$*"; }
note() { printf '   %s\n' "$*"; }
die()  { printf '\nopening: STOP — %s\n' "$*" >&2; exit 1; }
confirm() { local a; read -rp "$1 [y/N] " a; [[ "${a:-}" == [yY]* ]]; }

regen_manifest_row() {  # author-key territory: caller confirms before calling
    local path="$1"
    grep -v "  ${path}\$" MANIFEST.sha256 > MANIFEST.tmp \
        && sha256sum "$path" >> MANIFEST.tmp \
        && mv MANIFEST.tmp MANIFEST.sha256
}

commit_with_hook_retry() {  # regen-projections may rewrite files on the first try
    local msg="$1"
    git add -A && git commit -m "$msg" && return 0
    git add -A && git commit -m "$msg"
}

say "Precondition — make verify must be green before anything is signed"
if confirm "Run 'make verify' now (recommended)?"; then
    make verify || die "verify is red — fixing it is builder work; do not sign anything"
fi

say "Step 0 — inspect the trust root from a clean clone (read-only, ~5 min)"
if confirm "Run the clean-clone inspection now?"; then
    tmp=$(mktemp -d /tmp/tannen-inspect.XXXXXX)
    git clone --quiet . "$tmp"
    note "clean clone at $tmp"
    note "opening scripts/custodian.sh — read it end to end; it is sized for this"
    read -rp "   Enter to open the pager (q quits it)..." _
    "${PAGER:-less}" "$tmp/scripts/custodian.sh"
    note "now watch every guard FAIL its poison fixture:"
    (cd "$tmp" && uv sync --frozen --quiet && bash scripts/custodian.sh --check-only) \
        || die "custodian RED on a clean clone — sign nothing; investigate"
    note "finally DELEGATIONS.md — the text your step-3 signature makes binding,"
    note "including the founding ratification of m0-laws-freeze by hash"
    read -rp "   Enter to open DELEGATIONS.md..." _
    "${PAGER:-less}" "$tmp/DELEGATIONS.md"
    rm -rf "$tmp"
    confirm "Guards all failed their poison, delegation text read — proceed?" \
        || die "stopped at your request"
fi

say "Step 1 — owner key, enrolled in allowed_signers"
if [ -f "$OWNER_KEY" ]; then
    note "key already at $OWNER_KEY — keygen skipped"
elif confirm "Generate hardware-backed ed25519-sk key (FIDO2 plugged in; touch when it blinks)?"; then
    ssh-keygen -t ed25519-sk -f "$OWNER_KEY" -C "tannen owner key" || die "keygen failed"
elif confirm "No FIDO2 key here? Fall back to plain ed25519 (weaker custody, BRIEF §9.1)?"; then
    ssh-keygen -t ed25519 -f "$OWNER_KEY" -C "tannen owner key" || die "keygen failed"
else
    die "no key, no sitting"
fi
if grep -q '^owner@tannen ' allowed_signers; then
    note "owner@tannen already enrolled — skipped"
else
    note "about to edit allowed_signers + its MANIFEST row (author-key territory — your act):"
    printf '     +owner@tannen %s\n' "$(cut -d' ' -f1,2 "$OWNER_KEY.pub")"
    confirm "Enroll this key and drop the TODO-owner placeholder?" || die "stopped before enrolment"
    printf 'owner@tannen %s\n' "$(cut -d' ' -f1,2 "$OWNER_KEY.pub")" >> allowed_signers
    sed -i '/TODO-owner/d' allowed_signers
    regen_manifest_row allowed_signers
    git --no-pager diff allowed_signers
fi

say "Step 2 — policy values, then the tannen-policy signature"
note "defaults: envelopes all zero (they stay zero until the M4 sitting regardless),"
note "spot-check K=3, MIT code / CC BY-SA docs, publishing + cross-repo PRs forbidden,"
note "network writes captured-oracles-only. Zeros are valid."
if confirm "Edit governance/policy.yaml before signing?"; then
    "${EDITOR:-nano}" governance/policy.yaml
fi
if [ -f governance/policy.yaml.sig ] && ssh-keygen -Y verify -f allowed_signers \
    -I owner@tannen -n tannen-policy -s governance/policy.yaml.sig \
    <governance/policy.yaml >/dev/null 2>&1; then
    note "existing signature still verifies — skipped"
else
    rm -f governance/policy.yaml.sig
    note "signing policy.yaml (touch when it blinks)"
    ssh-keygen -Y sign -f "$OWNER_KEY" -n tannen-policy governance/policy.yaml \
        || die "policy signature failed"
fi

say "Optional — custodian tag-ordering guard (D0036; trust-root, yours alone to apply)"
if grep -q 'FOUNDING_TAGS=' scripts/custodian.sh; then
    note "already applied — skipped"
elif confirm "Read the proposal and decide now?"; then
    "${PAGER:-less}" docs/proposals/2026-08-24-custodian-tag-ordering.md
    if confirm "Apply the proposal's patch to scripts/custodian.sh?"; then
        old_block=$(mktemp) && new_block=$(mktemp)
        cat > "$old_block" <<'OLD'
# 3. Signed tags: every tag must verify against allowed_signers.
for tag in $(git tag -l 2>/dev/null); do
    if git -c gpg.format=ssh -c gpg.ssh.allowedSignersFile="$PWD/allowed_signers" \
        verify-tag "$tag" >/dev/null 2>&1; then
        say "tag verifies: $tag"
    else
        bad "tag does not verify against allowed_signers: $tag"
    fi
done
OLD
        cat > "$new_block" <<'NEW'
# 3. Signed tags: every tag must verify against allowed_signers; and no
#    builder-signed tag may predate the blessing of the delegation it invokes
#    (DELEGATIONS.md "Founding ratification": delegation precedes signature).
#    FOUNDING_TAGS enumerates the only exceptions, by tag-object hash.
FOUNDING_TAGS="531bb8fe9bf070eff2f47fda2dfb3b8b135a7dc6"   # m0-laws-freeze (D0032/D0035)
bless_epoch=""
if git rev-parse -q --verify refs/tags/brief-freeze >/dev/null 2>&1; then
    bless_epoch=$(git for-each-ref --format='%(taggerdate:unix)' refs/tags/brief-freeze)
fi
for tag in $(git tag -l 2>/dev/null); do
    out=$(git -c gpg.format=ssh -c gpg.ssh.allowedSignersFile="$PWD/allowed_signers" \
        verify-tag "$tag" 2>&1)
    if [ $? -ne 0 ]; then
        bad "tag does not verify against allowed_signers: $tag"
        continue
    fi
    say "tag verifies: $tag"
    if [ -n "$bless_epoch" ] && printf '%s' "$out" | grep -q 'signature for builder@tannen'; then
        tag_hash=$(git rev-parse "refs/tags/$tag")
        tag_epoch=$(git for-each-ref --format='%(taggerdate:unix)' "refs/tags/$tag")
        if [ "$tag_epoch" -lt "$bless_epoch" ] \
            && ! printf '%s\n' $FOUNDING_TAGS | grep -qx "$tag_hash"; then
            bad "builder tag predates its delegation's blessing and is not enumerated: $tag"
        fi
    fi
done
NEW
        python3 - "$old_block" "$new_block" <<'PYEOF' || die "patch did not apply cleanly"
import pathlib, sys
old = pathlib.Path(sys.argv[1]).read_text()
new = pathlib.Path(sys.argv[2]).read_text()
p = pathlib.Path("scripts/custodian.sh")
src = p.read_text()
if src.count(old) != 1:
    sys.exit("expected exactly one occurrence of custodian check 3 — aborted, file untouched")
p.write_text(src.replace(old, new))
PYEOF
        rm -f "$old_block" "$new_block"
        git --no-pager diff scripts/custodian.sh
        if confirm "Diff is exactly the proposal's block — keep it?"; then
            regen_manifest_row scripts/custodian.sh
            bash scripts/custodian.sh --check-only \
                || die "custodian red after the patch — investigate before signing anything"
            sed -i 's/^status: blocked-on-owner$/status: accepted/' \
                decisions/0036-custodian-tag-ordering-guard.yaml
            note "applied; D0036 marked accepted (your application is the affirmative act)"
        else
            git checkout -- scripts/custodian.sh
            note "reverted — D0036 stays queued; a builder session can record a veto instead"
        fi
    else
        note "leaving D0036 queued; a builder session can record a veto if you decide against it"
    fi
fi

say "Step 3 — commit the sitting; sign brief-freeze with DELEGATIONS.md as the message"
if git rev-parse -q --verify refs/tags/brief-freeze >/dev/null; then
    note "brief-freeze already exists — skipped"
else
    git status --short
    confirm "Commit the above and sign brief-freeze (touch when it blinks)?" \
        || die "stopped before the freeze"
    if [ -n "$(git status --porcelain)" ]; then
        commit_with_hook_retry "opening sitting: owner key, signed policy, brief-freeze" \
            || die "commit failed — a pre-commit guard went red; investigate"
    fi
    git -c gpg.format=ssh -c user.signingkey="$OWNER_KEY" \
        tag -s brief-freeze -F DELEGATIONS.md || die "tag signing failed"
fi
git -c gpg.format=ssh -c gpg.ssh.allowedSignersFile="$PWD/allowed_signers" \
    verify-tag brief-freeze || die "brief-freeze does not verify — go no further"
note "brief-freeze verifies against allowed_signers"

say "Step 4 — first attention receipt + weekly custodian cron"
mkdir -p receipts
today=$(date +%F)
if [ -f "receipts/$today.md.sig" ]; then
    note "today's receipt already exists — custodian run skipped"
else
    note "full custodian run — verifies everything, then writes receipts/$today.md"
    note "and signs it (touch when it blinks)"
    TANNEN_OWNER_KEY="$OWNER_KEY" bash scripts/custodian.sh \
        || die "custodian red — no receipt was signed; investigate"
fi
if [ -n "$(git status --porcelain)" ]; then
    commit_with_hook_retry "first attention receipt" || die "receipt commit failed"
fi
if crontab -l 2>/dev/null | grep -qF "scripts/custodian.sh"; then
    note "custodian cron already installed — skipped"
elif confirm "Install the weekly custodian cron (Mon 09:00)?"; then
    ( crontab -l 2>/dev/null
      echo "0 9 * * 1 cd $PWD && bash scripts/custodian.sh >> \$HOME/.cache/tannen-custodian.log 2>&1"
    ) | crontab -
    note "installed — an unattended run writes no receipt (no touch): that is the design"
else
    note "skipped — without receipts, Tier-B consent suspends at the next boundary (by design)"
fi

say "Confirm — make verify && make digest"
make verify || die "verify red after the sitting — leave a note; this is builder work now"
make digest
if [ -n "$(git status --porcelain)" ]; then
    commit_with_hook_retry "post-sitting digest" || die "digest commit failed"
fi

say "The sitting is closed"
note "delegations live; m0-laws-freeze ratified by enumeration; first receipt fresh."
note "Next (builder work, fresh session in ~/git/worktrees/tannen/m0):"
note "    'Session B for M0 per CLAUDE.md.'"
