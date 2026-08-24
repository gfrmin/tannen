#!/usr/bin/env bash
# scripts/custodian.sh — the guard of the guards (BRIEF §9.1 custody floor).
# AUTHOR-KEY TERRITORY: this file, allowed_signers, tests/poison/, and their
# MANIFEST.sha256 rows are owner-edited only (CLAUDE.md hard rules; Tier-C door
# trust-root-changes).
#
# Verifies, in order:
#   1. frozen-path hashes (MANIFEST.sha256);
#   2. the custody set and the CI config are themselves manifested;
#   3. every git tag verifies against allowed_signers;
#   4. the policy signature (governance/policy.yaml.sig), once it exists;
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

# 2. Custody set + CI config are manifested.
manifested_ok=1
for path in scripts/custodian.sh allowed_signers .github/workflows/ci.yml \
    $(find tests/poison -type f | sort); do
    if ! grep -q "  ${path}\$" MANIFEST.sha256; then
        bad "not manifested: $path"
        manifested_ok=0
    fi
done
[ "$manifested_ok" -eq 1 ] && say "custody set and CI config are manifested"

# 3. Signed tags: every tag must verify against allowed_signers.
for tag in $(git tag -l 2>/dev/null); do
    if git -c gpg.format=ssh -c gpg.ssh.allowedSignersFile="$PWD/allowed_signers" \
        verify-tag "$tag" >/dev/null 2>&1; then
        say "tag verifies: $tag"
    else
        bad "tag does not verify against allowed_signers: $tag"
    fi
done

# 4. Policy signature (owner signs at the opening sitting; verified once present).
if [ -f governance/policy.yaml.sig ]; then
    if ssh-keygen -Y verify -f allowed_signers -I owner@tannen -n tannen-policy \
        -s governance/policy.yaml.sig <governance/policy.yaml >/dev/null 2>&1; then
        say "policy.yaml signature verifies (owner@tannen)"
    else
        bad "governance/policy.yaml.sig does not verify against owner@tannen"
    fi
else
    say "policy.yaml unsigned (expected before the opening sitting)"
fi

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
