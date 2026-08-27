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
# THE FLOOR MAY DEPEND ONLY ON TOOLS THE OS PROVIDES AND PATHS NAMED LITERALLY
# (conferral ruling 3, decision D0063). Checks 1-4 use sha256sum, ssh-keygen, git and
# grep — nothing this repo installs. Where a Python guard is unavoidable it is the venv
# interpreter at a literal path in isolated mode (-I ignores PYTHONPATH, PYTHONHOME and
# user site-packages; -P stops any directory being prepended to sys.path), never `uv run`
# and never a console entry point, because both resolve through metadata the builder
# writes. The custody set covers a guard's code; this covers its resolution, and
# resolution is enforcement. What remains outside both: site-packages itself.
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
PY="$PWD/.venv/bin/python"
[ -x "$PY" ] || { printf 'custodian: FAIL — no interpreter at %s\n' "$PY" >&2; exit 1; }
LINT=(-I -c 'import sys; from importlinter.cli import lint_imports_command; sys.exit(lint_imports_command())')
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
"$PY" -I -P scripts/check_tag_signers.py || bad "tag signer roles violated"

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

# 4b. THE RECEIPT CHAIN (conferral ruling 4, D0063). Every check in this file runs on a
#     working tree the builder controls; none of them constrains what happened before a
#     commit existed. The receipts are the one artifact the builder cannot forge, so they
#     are made into a witness: each receipt records the HEAD it was taken at, and each
#     HEAD must be an ancestor of the next. Rewriting history between two owner-signed
#     attestations then stops being invisible. This is also the justification for a remote
#     when one is eventually added (Tier C): an unrewritable witness, not a backup.
prev_head=""; prev_name=""
for receipt in $(ls -1 receipts/*.md 2>/dev/null | sort); do
    if [ ! -f "$receipt.sig" ]; then
        [ "$owner_enrolled" -eq 1 ] && bad "unsigned attention receipt: $receipt"
        continue
    fi
    ssh-keygen -Y verify -f allowed_signers -I owner@tannen -n tannen-receipt \
        -s "$receipt.sig" <"$receipt" >/dev/null 2>&1 \
        || bad "receipt signature does not verify: $receipt"
    head=$(sed -n 's/^- HEAD: \([0-9a-f]\{7,40\}\)$/\1/p' "$receipt" | head -1)
    [ -n "$head" ] || continue
    if ! git cat-file -e "${head}^{commit}" 2>/dev/null; then
        bad "receipt $receipt records HEAD $head, which is no longer a commit here"
        continue
    fi
    if [ -n "$prev_head" ] && ! git merge-base --is-ancestor "$prev_head" "$head" 2>/dev/null; then
        bad "receipt chain broken: $prev_name recorded $prev_head, not an ancestor of $head"
    fi
    prev_head="$head"; prev_name="$receipt"
done
if [ -n "$prev_head" ]; then
    if git merge-base --is-ancestor "$prev_head" HEAD 2>/dev/null; then
        say "receipt chain verifies to HEAD"
    else
        bad "receipt chain broken at the tip: $prev_name recorded $prev_head, not an ancestor of HEAD"
    fi
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
    "$PY" -I -P scripts/check_manifest.py --root tests/poison/check-manifest
poison check_concepts "snapshot content drifted" \
    "$PY" -I -P scripts/check_concepts.py --root tests/poison/check-concepts
poison check_decisions "binding does not resolve" \
    "$PY" -I -P scripts/check_decisions.py --root tests/poison/check-decisions
# The shadowing fixtures used to arrive via PYTHONPATH, which -I now ignores — and which
# was the same inherited-environment channel RT-08 exploited. `env -C` puts the poison
# tree on sys.path as the working directory instead: no variable, one literal path.
poison lint-imports "BROKEN" \
    env -C tests/poison/lint-imports "$PY" "${LINT[@]}" --no-cache --config pyproject.toml

# The fixtures added at the M0 boundary sitting. The four above prove their guard runs;
# these prove it still has the specific tooth the red team had to file off (RT-01..RT-15).
# Each guard is invoked with the hatch cleared, because an inherited environment variable
# is not authenticable and a poison run must not be silenceable by one (RT-08).
for marker in "tannen.kernel is not allowed to import os" \
              "tannen.kernel is not allowed to import datetime" \
              "tannen is not allowed to import pkm"; do
    poison lint-imports-kernel "$marker" \
        env -C tests/poison/lint-imports-kernel "$PY" "${LINT[@]}" --no-cache \
        --config "$PWD/governance/importlinter.toml"
done
poison check_decisions_ratchet "RATCHET BREACH" \
    env -u TANNEN_CHECK_DECISIONS_NESTED \
    "$PY" -I -P scripts/check_decisions.py --root tests/poison/check-decisions-ratchet
poison check_decisions_pytest "binding does not resolve" \
    env -u TANNEN_CHECK_DECISIONS_NESTED \
    "$PY" -I -P scripts/check_decisions.py --root tests/poison/check-decisions-nested-hatch
poison check_decisions_tier_c "Tier-C record accepted without an owner signature" \
    env -u TANNEN_CHECK_DECISIONS_NESTED \
    "$PY" -I -P scripts/check_decisions.py --root tests/poison/check-decisions-unsigned-tier-c
poison check_manifest_sealed "unmanifested file in sealed path" \
    "$PY" -I -P scripts/check_manifest.py --root tests/poison/check-manifest-sealed
poison check_manifest_signature "missing owner signature" \
    "$PY" -I -P scripts/check_manifest.py --root tests/poison/check-manifest-unsigned-policy
poison check_tag_signers_principal "tag signed by the wrong principal" \
    "$PY" -I -P scripts/check_tag_signers.py \
    --root tests/poison/custodian-tag-signer --repo tests/poison/custodian-tag-signer/repo.bundle
poison check_tag_signers_required "required tag missing" \
    "$PY" -I -P scripts/check_tag_signers.py \
    --root tests/poison/custodian-tag-signer --repo tests/poison/custodian-tag-signer/repo.bundle

# The M1 boundary sitting adds one fixture: oracle-shadow (RT-M1-01,
# docs/redteam/2026-08-26-m1-boundary.md). Deliberately WITHOUT -I -P, unlike every guard
# above: the attack this proves the defence against is a module reaching sys.modules
# through PYTHONPATH before the frozen file's bare `import _fragment as F` does, and -I
# ignores PYTHONPATH entirely (RT-08's own closed channel) — under -I this fixture's own
# setup could never run, isolated mode would silently make it untestable rather than
# green. The interpreter is still the literal venv path, never `uv run` (RT-02, ruling 3);
# only the isolation flag is absent, and only for this one line, and only because the
# fixture's job requires the very channel -I exists to close.
# -B (PYTHONDONTWRITEBYTECODE): importing _fragment.py and bootstrap_shadow.py from
# INSIDE tests/poison/oracle-shadow — a sealed directory where every file needs a
# manifest row — would otherwise write __pycache__/*.pyc there on the first run,
# unmanifested. The same hazard --no-cache already closes for lint-imports (D0063
# rationale: "running import-linter with a poison fixture as the working directory
# writes a cache INSIDE a sealed directory, breaking the seal"); -B is pytest's
# equivalent for the interpreter's own bytecode cache, which --no-cache does not reach.
# Found by rehearsing this fixture inside its OWN eventual tests/poison/ location, not
# by reading it: docs/redteam/fixture-candidates/oracle-shadow/ is unsealed, so nothing
# there surfaced it.
poison oracle-shadow "RT-M1-01" \
    env -u TANNEN_CHECK_DECISIONS_NESTED PYTHONPATH=tests/poison/oracle-shadow \
    "$PY" -B -m pytest -p bootstrap_shadow tests/laws/m1/test_l1_duckdb.py \
    -k test_l1_16_the_catalogue_covers_every_operator_of_the_fragment -q

# A second M1 fixture: check-decisions-file-skip (RT-M1-05), lands together with the
# guard patch it proves (this sitting's step 5b), never before it — see D0105 item 2.
# check_decisions.py itself spawns pytest as a SUBPROCESS (run_pytest: `sys.executable -m
# pytest ...`), so -B on THIS outer interpreter does not reach it: -B sets
# sys.dont_write_bytecode on the process it is given to, and subprocess.run starts a new
# one. PYTHONDONTWRITEBYTECODE=1 is an environment variable, which run_pytest's
# `env={**os.environ, ...}` DOES forward to the child — confirmed live (2026-08-27): the
# outer-process -B flag left __pycache__ behind under tests/poison/, unmanifested and
# sealed the same way oracle-shadow's did; the env var closes it because it survives the
# fork where the flag does not.
poison check_decisions_file_skip "unexplained skip" \
    env -u TANNEN_CHECK_DECISIONS_NESTED PYTHONDONTWRITEBYTECODE=1 \
    "$PY" -I -P scripts/check_decisions.py --root tests/poison/check-decisions-file-skip

if [ "$FAIL" -ne 0 ]; then
    bad "custody floor violated"
    exit 1
fi
say "custody floor intact"

# 6. Attention receipt (owner machine only; never in --check-only mode).
if [ "${1:-}" != "--check-only" ]; then
    date_str=$(date +%F)
    receipt="receipts/${date_str}.md"
    prev=$(ls -1 receipts/*.md 2>/dev/null | sort | tail -1)
    {
        echo "# Attention receipt — ${date_str}"
        echo
        echo "- HEAD: $(git rev-parse HEAD 2>/dev/null || echo '(unborn)')"
        if [ -n "$prev" ] && [ "$prev" != "$receipt" ]; then
            echo "- previous receipt: $(basename "$prev" .md) at ${prev_head:-(none recorded)}"
        fi
        echo "- custodian: all checks green"
        echo "- consequence: Tier-B silence-as-consent is valid from this date until"
        echo "  the next milestone boundary + 7 days (BRIEF §9.1)."
        echo "- chain: the HEAD above extends the previous receipt's HEAD. Each receipt is"
        echo "  an owner-signed witness that the history up to that point was not rewritten"
        echo "  afterwards (D0063 ruling 4); scripts/check_receipts.py verifies the chain."
    } >"$receipt"
    ssh-keygen -Y sign -f "${TANNEN_OWNER_KEY:-$HOME/.ssh/tannen_owner}" \
        -n tannen-receipt "$receipt"
    say "attention receipt written and author-signed: $receipt (+ .sig)"
fi
