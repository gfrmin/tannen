#!/usr/bin/env bash
# scripts/custodian.sh — the guard of the guards (BRIEF §9.1 custody floor).
#
# THIS COPY is docs/proposals/2026-09-04-m3-boundary-sitting/custodian.sh: the live file
# plus six delimited hunks (`--- M3 DRAFT HUNK n ---`), each mapped to a D0154 queue item.
# The owner installs it at the M3 sitting's step 6, after reading the diff. It is a
# proposal: it enforces nothing until installed.
#
# REBASED onto the live file on 2026-09-08 (D0196). The 2026-09-04 draft was written
# against the pre-publication custodian, and installing it verbatim would have REVERTED
# three publication-sitting changes: FOUNDING_TAGS back to the pre-rewrite pin (breaking
# check_tag_signers against the rewritten history), the 28-line inline receipt-chain loop
# back over D0176's delegation to scripts/check_receipts.py, and the three publication
# poison invocations (check_concepts_brief_row, check_decisions_retired_enforced,
# oracle-shadow-spoofed) deleted. That last one interacts with hunk 1c: with the
# invocations gone and the fixtures still on disk, the new completeness pass would have
# reddened the floor at the sitting's step 7.
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
# --- M3 DRAFT HUNK 3 (D0154 item 4; D0146 item 2) ----------------------------
# `find` now excludes __pycache__, matching check_manifest.py:113's sealed-path rule. A
# .pyc written into tests/poison/ by an ad-hoc import made THIS check red at `make
# verify`'s last step, ~37 minutes in, while check_manifest stayed green — and the "not
# manifested" message invited a manifest row for a gitignored, interpreter-versioned
# file. The only correct response to a stray .pyc is deleting it; excluding the
# directory here makes the two guards agree about what a sealed tree contains.
manifested_ok=1
for path in scripts/custodian.sh allowed_signers .github/workflows/ci.yml \
    DELEGATIONS.md governance/tier-c.yaml governance/tag-roles.yaml \
    scripts/check_tag_signers.py \
    $(find tests/poison -type f -not -path '*/__pycache__/*' | sort); do
# --- end M3 DRAFT HUNK 3 -----------------------------------------------------
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
FOUNDING_TAGS="85d19e94e7021e8346ec81f428c2581bfa7313d3"   # m0-laws-freeze re-created at the publication rewrite of 2026-09-07 (receipts/REWRITE-*.md); was 531bb8fe9bf070eff2f47fda2dfb3b8b135a7dc6   # m0-laws-freeze (D0032/D0035)
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
#     ONE implementation, not two. scripts/check_receipts.py is custody-set and is what
#     `make verify` runs; the inline copy this line replaced drifted from it the first time
#     the guard learned something new — a rewrite attestation under its own namespace
#     (patch 02, D0176) — and the custodian then rejected the attestation as a receipt
#     with a bad signature while the guard accepted it. BRIEF §2: restatement is
#     duplication; duplication is drift. Found by rehearsing the publication sitting.
"$PY" -I -P scripts/check_receipts.py || bad "receipt chain violated (scripts/check_receipts.py)"

# 5. Guard liveness by poison: each guard must fail its fixture, for the right reason.
# --- M3 DRAFT HUNK 1a (D0154 item 1; D0152 item 6; D0095 half (2)) -----------
# poison() now RECORDS which tests/poison/ directories its invocation reaches, and the
# completeness pass at hunk 1c refuses any installed fixture no line exercises. The M2
# sitting installed oracle-shadow-model — manifest rows, custody rows, README row — and
# the custodian ran every fixture but that one while printing "custody floor intact": a
# hand-kept enumeration extended only at the moment its extender may not edit it (D0095's
# shape). The enumerated invocations stay, because they are heterogeneous for reasons each
# one's comment states; their COVERAGE becomes derived, the same move D0142 made for the
# oracle map. Had this existed on 2026-09-03 the sitting would have failed loudly.
POISON_SEEN=""
poison() {
    local name="$1" marker="$2"
    shift 2
    local fx
    for fx in $(printf '%s\n' "$@" | grep -o 'tests/poison/[A-Za-z0-9_-]*' | sort -u); do
        case " $POISON_SEEN " in
            *" $fx "*) : ;;
            *) POISON_SEEN="$POISON_SEEN $fx" ;;
        esac
    done
# --- end M3 DRAFT HUNK 1a (function body below unchanged) --------------------
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

# The publication sitting adds four fixtures (D0183; docs/proposals/2026-09-06-publication/
# fixture-candidates/README.md): patch 05's brief_row teeth, patch 06's refusal to retire an
# enforced binding, and RT-M3-04's spoofed oracle shadow, whose marker is the guard's OWN
# tooth text — "answers with different code" — because the fixture README's "RT-M3-04"
# never appears in the guard's output (found by wiring it, not by reading it). Candidate 1
# (check-concepts/governance/policy.yaml) is a file, not a line: it narrows an existing
# fixture back to one reason.
poison check_concepts_brief_row "brief_row" \
    "$PY" -I -P scripts/check_concepts.py --root tests/poison/check-concepts-brief-row
poison check_decisions_retired_enforced "only a documentary binding may be retired" \
    env -u TANNEN_CHECK_DECISIONS_NESTED PYTHONDONTWRITEBYTECODE=1 \
    "$PY" -I -P scripts/check_decisions.py --root tests/poison/check-decisions-retired-enforced
poison oracle-shadow-spoofed "answers with different code" \
    env -u TANNEN_CHECK_DECISIONS_NESTED PYTHONPATH=tests/poison/oracle-shadow-spoofed \
    "$PY" -B -m pytest -p bootstrap_shadow_spoofed tests/laws/m3/test_l3_differential.py -q

# --- M3 DRAFT HUNK 1b (D0154 item 1; D0152 item 6) ---------------------------
# The fixture the M2 boundary sitting installed and never wired: oracle-shadow-model
# (RT-M2-01, the M1->M2 pass's single CRITICAL finding). The same attack as oracle-shadow
# one milestone on — a decoy `_model` primed into sys.modules by a -p bootstrap plugin,
# ahead of frozen tests/laws/m2/test_l2_differential.py's bare `import _model as M`.
# Every deviation from poison()'s usual form is oracle-shadow's, for oracle-shadow's
# reasons: no -I -P (the attack IS PYTHONPATH; under -I the fixture's setup could never
# run), -B (the decoy imports from inside a sealed directory), the literal venv
# interpreter. No -k: D0142's widened guard aborts at collection, so there is nothing to
# select. This line is what makes the custody FLOOR run it, not just an unfrozen test.
poison oracle-shadow-model "RT-M2-01" \
    env -u TANNEN_CHECK_DECISIONS_NESTED PYTHONPATH=tests/poison/oracle-shadow-model \
    "$PY" -B -m pytest -p bootstrap_shadow_model tests/laws/m2/test_l2_differential.py -q
# --- end M3 DRAFT HUNK 1b ----------------------------------------------------

# --- M3 DRAFT HUNK 1c (D0154 item 1; D0152 item 6; the derived half) ---------
# Every directory under tests/poison/ must have been reached by some invocation above.
# This is the loop that would have caught 2026-09-03. It runs BEFORE the FAIL check below,
# so an unexercised fixture reddens the floor rather than being reported after it closes.
poison_uncovered=0
for dir in tests/poison/*/; do
    fx=${dir%/}
    case " $POISON_SEEN " in
        *" $fx "*) : ;;
        *) bad "fixture $fx is installed but NO poison invocation exercises it (D0152 item 6's shape)"
           poison_uncovered=$((poison_uncovered+1)) ;;
    esac
done
# The success line is CONDITIONAL, and that is not a detail. The first draft of this loop
# printed it unconditionally, so a run that had just reported an unexercised fixture still
# closed with "every installed fixture is exercised" — D0177's exact shape, in the guard
# written to close D0152's. Caught by running the loop against a fabricated orphan rather
# than by reading it, which is the whole argument for poison fixtures in one line.
[ "$poison_uncovered" -eq 0 ] && say "poison coverage: every installed fixture is exercised"
# --- end M3 DRAFT HUNK 1c ----------------------------------------------------

if [ "$FAIL" -ne 0 ]; then
    bad "custody floor violated"
    exit 1
fi
say "custody floor intact"

# 6. Attention receipt (owner machine only; never in --check-only mode).
if [ "${1:-}" != "--check-only" ]; then
    date_str=$(date +%F)
    receipt="receipts/${date_str}.md"
# --- M3 DRAFT HUNK 4 (D0154 item 3; D0153) -----------------------------------
# The previous receipt is now the latest one THAT IS NOT the file being written, and its
# HEAD is read from that file. Two defects, one fix. (a) The live spelling `sort | tail -1`
# picks the receipt being written on any same-day re-run, and the guard below then dropped
# the chain line entirely — silently, because check_receipts parses only `- HEAD:`.
# (b) `prev_head` is never assigned ANYWHERE in the live file: the only occurrence is the
# `${prev_head:-...}` read itself, because the loop that used to set it was deleted when
# the receipt-chain check was delegated to scripts/check_receipts.py. So every receipt
# written since renders "at (none recorded)" — receipts/2026-09-07.md shows it. The chain
# line has been decorative since, and nothing noticed.
    prev=$(ls -1 receipts/*.md 2>/dev/null | grep -vx "$receipt" | sort | tail -1)
    {
        echo "# Attention receipt — ${date_str}"
        echo
        echo "- HEAD: $(git rev-parse HEAD 2>/dev/null || echo '(unborn)')"
        if [ -n "$prev" ]; then
            prev_recorded=$(sed -n 's/^- HEAD: \([0-9a-f]\{7,40\}\)$/\1/p' "$prev" | head -1)
            echo "- previous receipt: $(basename "$prev" .md) at ${prev_recorded:-(none recorded)}"
        fi
# --- end M3 DRAFT HUNK 4 -----------------------------------------------------
        echo "- custodian: all checks green"
        echo "- consequence: Tier-B silence-as-consent is valid from this date until"
        echo "  the next milestone boundary + 7 days (BRIEF §9.1)."
        echo "- chain: the HEAD above extends the previous receipt's HEAD. Each receipt is"
        echo "  an owner-signed witness that the history up to that point was not rewritten"
        echo "  afterwards (D0063 ruling 4); scripts/check_receipts.py verifies the chain."
    } >"$receipt"
    if ssh-keygen -Y sign -f "${TANNEN_OWNER_KEY:-$HOME/.ssh/tannen_owner}" \
           -n tannen-receipt "$receipt"; then
        say "attention receipt written and author-signed: $receipt (+ .sig)"
    else
# --- M3 DRAFT HUNK 2 (D0154 item 2's third clause; D0152 item 3) -------------
        # An unsigned receipt is worse than no receipt: it attests to nothing while
        # looking like an attestation, and check_receipts would then redden every later
        # run for a file this step should never have left behind. Two additions to the
        # live spelling, which D0177 already brought this far. The `.sig` goes too: a
        # stale signature over a removed file outlives the thing it signed. And the exit
        # is non-zero, because a half-written receipt left behind is exactly what step 0
        # of the sitting driver reads as a RESUMED sitting and skips its gate for
        # (D0148 item 5) — so this must stop the run, not merely colour it.
        rm -f "$receipt" "$receipt.sig"
        bad "receipt signing FAILED (locked agent? declined touch?) — $receipt removed; re-run to retry"
        exit 1
# --- end M3 DRAFT HUNK 2 -----------------------------------------------------
    fi
fi
