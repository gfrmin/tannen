#!/usr/bin/env bash
# scripts/custodian.sh — the guard of the guards (BRIEF §9.1 custody floor).
# AUTHOR-KEY TERRITORY: this file, allowed_signers, tests/poison/, and their
# MANIFEST.sha256 rows are owner-edited only (CLAUDE.md hard rules; Tier-C door
# trust-root-changes).
#
# Verifies, in order:
#   1. frozen-path hashes (MANIFEST.sha256) AND the owner-signed custody set
#      (governance/custody.sha256 — the bytes the owner vouched for, D0061);
#   2. the custody set and the CI config are themselves manifested;
#   3. every git tag verifies against allowed_signers, no builder tag predates its
#      delegation, and the right PRINCIPAL signed the right CLASS of tag (D0050);
#   4. the owner signatures that are required, not optional: policy.yaml and
#      custody.sha256. Absent is a downgrade once an owner key is enrolled (RT-04);
#   5. GUARD LIVENESS BY POISON: every guard must FAIL against its fixture under
#      tests/poison/, for the intended reason. A guard that passes poison is weakened.
#
# Modes:
#   custodian.sh --check-only   verify only (builder machine, CI). No receipt.
#   custodian.sh                full run on the OWNER's machine: verify, then write
#                               and author-sign the dated attention receipt
#                               (hardware key: touch = presence). Key path override:
#                               TANNEN_OWNER_KEY (default ~/.ssh/tannen_owner).
set -uo pipefail
cd "$(dirname "$0")/.."

FAIL=0
say() { printf 'custodian: %s\n' "$*"; }
bad() { printf 'custodian: FAIL — %s\n' "$*" >&2; FAIL=1; }

# 1. Frozen-path hashes.
if ! sha256sum --quiet -c MANIFEST.sha256 >/dev/null 2>&1; then
    bad "frozen-path hashes do not verify (sha256sum -c MANIFEST.sha256)"
else
    say "frozen-path hashes verify"
fi

# 1b. The custody set: the bytes the OWNER signed for, checked without trusting any
#     Python guard — every guard in scripts/ is itself inside this set (D0061, RT-14).
if [ -f governance/custody.sha256 ]; then
    if ! sha256sum --quiet -c governance/custody.sha256 >/dev/null 2>&1; then
        bad "custody set hashes do not verify — a file the owner signed for has changed"
    else
        say "custody set hashes verify ($(wc -l <governance/custody.sha256) path(s))"
    fi
else
    bad "governance/custody.sha256 is missing — the enumeration the manifest is not"
fi

# 2. Custody set + CI config are manifested.
manifested_ok=1
for path in scripts/custodian.sh allowed_signers .github/workflows/ci.yml \
    DELEGATIONS.md governance/tier-c.yaml governance/tag-roles.yaml \
    scripts/check_tag_signers.py \
    $(find tests/poison -type f | sort); do
    if ! grep -q "  ${path}\$" MANIFEST.sha256; then
        bad "not manifested: $path"
        manifested_ok=0
    fi
done
[ "$manifested_ok" -eq 1 ] && say "custody set and CI config are manifested"

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

# 3b. The right principal signed the right class of tag, the trust root is the object
#     it is pinned to, and the required tags exist at all (D0050/D0054; RT-15).
uv run python scripts/check_tag_signers.py || bad "tag signer roles violated"

# 4. Owner signatures that are REQUIRED once an owner key is enrolled. Verified-if-present
#    was the pre-opening state; after the sitting, an absent signature is a downgrade a
#    single `rm` could perform in silence (RT-04).
owner_enrolled=0
grep -qE '^owner@tannen[[:space:]]' allowed_signers && owner_enrolled=1
require_sig() {   # <file> <namespace>
    local file="$1" ns="$2"
    if [ -f "$file.sig" ]; then
        if ssh-keygen -Y verify -f allowed_signers -I owner@tannen -n "$ns" \
            -s "$file.sig" <"$file" >/dev/null 2>&1; then
            say "$file signature verifies (owner@tannen)"
        else
            bad "$file.sig does not verify against owner@tannen"
        fi
    elif [ "$owner_enrolled" -eq 1 ]; then
        bad "$file.sig absent but owner@tannen is enrolled — a signature was deleted (RT-04)"
    else
        say "$file unsigned (expected before the opening sitting)"
    fi
}
require_sig governance/policy.yaml   tannen-policy
require_sig governance/custody.sha256 tannen-custody

# 5. Guard liveness by poison: each guard must fail its fixture, for the right reason.
poison() {
    local name="$1" marker="$2"
    shift 2
    local out
    if out=$("$@" 2>&1); then
        bad "guard '$name' PASSED its poison fixture — the guard is weakened"
    elif ! printf '%s' "$out" | grep -q "$marker"; then
        bad "guard '$name' failed its poison for the wrong reason (marker '$marker' absent)"
    else
        say "guard '$name' fails its poison as required"
    fi
}
poison check_manifest "frozen path modified" \
    uv run python scripts/check_manifest.py --root tests/poison/check-manifest
poison check_concepts "snapshot content drifted" \
    uv run python scripts/check_concepts.py --root tests/poison/check-concepts
poison check_decisions "binding does not resolve" \
    uv run python scripts/check_decisions.py --root tests/poison/check-decisions
poison lint-imports "BROKEN" \
    env PYTHONPATH=tests/poison/lint-imports uv run lint-imports \
    --config tests/poison/lint-imports/pyproject.toml

# The fixtures added at the M0 boundary sitting. The four above prove their guard runs;
# these prove it still has the specific tooth the red team had to file off (RT-01..RT-15).
# Each guard is invoked with the hatch cleared, because an inherited environment variable
# is not authenticable and a poison run must not be silenceable by one (RT-08).
for marker in "tannen.kernel is not allowed to import os" \
              "tannen.kernel is not allowed to import datetime" \
              "tannen is not allowed to import pkm"; do
    poison lint-imports-kernel "$marker" \
        env PYTHONPATH=tests/poison/lint-imports-kernel uv run lint-imports \
        --config pyproject.toml
done
poison check_decisions_ratchet "RATCHET BREACH" \
    env -u TANNEN_CHECK_DECISIONS_NESTED \
    uv run python scripts/check_decisions.py --root tests/poison/check-decisions-ratchet
poison check_decisions_pytest "binding does not resolve" \
    env -u TANNEN_CHECK_DECISIONS_NESTED \
    uv run python scripts/check_decisions.py --root tests/poison/check-decisions-nested-hatch
poison check_decisions_tier_c "Tier-C record accepted without an owner signature" \
    env -u TANNEN_CHECK_DECISIONS_NESTED \
    uv run python scripts/check_decisions.py --root tests/poison/check-decisions-unsigned-tier-c
poison check_manifest_sealed "unmanifested file in sealed path" \
    uv run python scripts/check_manifest.py --root tests/poison/check-manifest-sealed
poison check_manifest_signature "missing owner signature" \
    uv run python scripts/check_manifest.py --root tests/poison/check-manifest-unsigned-policy
poison check_tag_signers_principal "tag signed by the wrong principal" \
    uv run python scripts/check_tag_signers.py \
    --root tests/poison/custodian-tag-signer --repo tests/poison/custodian-tag-signer/repo.bundle
poison check_tag_signers_required "required tag missing" \
    uv run python scripts/check_tag_signers.py \
    --root tests/poison/custodian-tag-signer --repo tests/poison/custodian-tag-signer/repo.bundle

if [ "$FAIL" -ne 0 ]; then
    bad "custody floor violated"
    exit 1
fi
say "custody floor intact"

# 6. Attention receipt (owner machine only; never in --check-only mode).
if [ "${1:-}" != "--check-only" ]; then
    date_str=$(date +%F)
    receipt="receipts/${date_str}.md"
    {
        echo "# Attention receipt — ${date_str}"
        echo
        echo "- HEAD: $(git rev-parse HEAD 2>/dev/null || echo '(unborn)')"
        echo "- custodian: all checks green"
        echo "- consequence: Tier-B silence-as-consent is valid from this date until"
        echo "  the next milestone boundary + 7 days (BRIEF §9.1)."
    } >"$receipt"
    ssh-keygen -Y sign -f "${TANNEN_OWNER_KEY:-$HOME/.ssh/tannen_owner}" \
        -n tannen-receipt "$receipt"
    say "attention receipt written and author-signed: $receipt (+ .sig)"
fi
