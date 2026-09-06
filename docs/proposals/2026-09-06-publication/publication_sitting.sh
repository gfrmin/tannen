#!/usr/bin/env bash
# publication_sitting.sh — interactive driver for the PUBLICATION sitting.
# OWNER-RUN, on the owner's machine, with the owner key's passphrase available.
#
# Builder-drafted and staged under docs/proposals/ (D0181). It is NOT in scripts/ and NOT
# in the custody set: installing it is a `git mv` plus a custody row, and that is the
# owner's act, like every other sitting driver (BRIEF §9.1).
#
# WHY THIS EXISTS. Every previous sitting had an executable driver — opening_sitting.sh
# (246 lines), boundary_sitting.sh (1,950) — and a rehearsal harness in front of it. This
# sitting had an eleven-step prose runbook. D0068's lesson is blunt: three consecutive
# attempts at the M0->M1 sitting stopped on defects a single end-to-end run would have
# found in seconds (a step gated on a later step's output; a manifest row naming a file no
# commit contained, D0065; $EDITOR invoked as a command name, D0066). Each one spent the
# owner's attention, the scarce resource this governance layer exists to conserve. This
# sitting rewrites 77 commits and re-signs the trust root. It is the least forgiving one
# yet and it was the only one without a driver.
#
# WHAT IT WILL DO TO YOUR KEY: up to 12 touches — 8 tag signatures, the rewrite
# attestation, custody.sha256, policy.yaml, and D0176.
#
# WHAT IT WILL NEVER DO: run `git filter-repo` anywhere but a fresh disposable clone;
# touch the bare repository at ~/git/tannen or any of its worktrees; force-push; or delete
# a tag before the replacement is confirmed signable. The rewrite happens in $WORK and is
# adopted by an explicit, separately-confirmed step.
#
#   publication_sitting.sh              # the sitting
#   publication_sitting.sh --dry-run    # every step narrated, nothing signed or written
#
set -uo pipefail
cd "$(dirname "$0")/../../.."          # docs/proposals/<pkg>/ -> repo root
ROOT="$PWD"

DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1

OWNER_KEY="${TANNEN_OWNER_KEY:-$HOME/.ssh/tannen_owner}"
BUILDER_KEY="${TANNEN_BUILDER_KEY:-$HOME/.ssh/tannen_builder}"
PKG="docs/proposals/2026-09-06-publication"
TODAY="$(date +%Y-%m-%d)"

say()  { printf '\n\033[1m== %s\033[0m\n' "$*"; }
note() { printf '   %s\n' "$*"; }
warn() { printf '   \033[33m! %s\033[0m\n' "$*"; }
die()  { printf '\npublication: STOP — %s\n' "$*" >&2; exit 1; }
confirm() { [ "$DRY" = 1 ] && { note "[dry-run] would ask: $1"; return 0; }
            local a; read -rp "   $1 [y/N] " a; [[ "${a:-}" == [yY]* ]]; }
run() { [ "$DRY" = 1 ] && { note "[dry-run] $*"; return 0; }; "$@"; }

# The eight signed tags, with their signer class. Derived nowhere: tag-roles.yaml owns
# this mapping, so read it rather than restating it (CLAUDE.md: no guard, and no driver,
# may depend on a hand-maintained enumeration).
owner_tags()   { grep -oP '^\s*-\s*\K\S+' governance/tag-roles.yaml | grep -E 'brief-freeze|-close$' | sort -u; }
builder_tags() { git tag | grep -E -- '-laws-freeze$' | sort -u; }

say "Precondition — the gate must be green BEFORE anything is signed"
note "This is the state the first receipt attests to. A red gate here means builder work,"
note "not a sitting."
if confirm "Run 'make verify' now (recommended; ~20 min)?"; then
    run make verify || die "verify is red — fixing it is builder work; sign nothing"
fi
PRE_HEAD="$(git rev-parse HEAD)"
note "pre-rewrite HEAD: $PRE_HEAD"

# ---------------------------------------------------------------- step 0
say "Step 0 — apply patch 04 FIRST (D0177)"
note "custodian.sh:283-285 ignores ssh-keygen's exit status: on a failed signature it"
note "prints 'attention receipt written and author-signed', leaves an UNSIGNED receipt in"
note "receipts/, and exits 0. Step 1 is the step that corrupts. Observed live 2026-09-06."
note "scripts/custodian.sh is author-key territory, so this is your edit, shown as a diff."
if [ "$DRY" = 0 ] && confirm "Open $PKG/patches/04-custodian-receipt-signing.md now?"; then
    "${PAGER:-less}" "$PKG/patches/04-custodian-receipt-signing.md"
fi
confirm "patch 04 applied to scripts/custodian.sh?" \
    || die "do not proceed to step 1 with the receipt bug live"
run bash scripts/custodian.sh --check-only \
    || die "custodian red after patch 04 — investigate before signing"

# ---------------------------------------------------------------- step 1
say "Step 1 — fresh attention receipt at the PRE-REWRITE head"
note "The last un-rewritten state, attested before it stops existing."
if [ -f "receipts/$TODAY.md" ] && [ -f "receipts/$TODAY.md.sig" ]; then
    note "receipts/$TODAY.md already present and signed — skipping"
else
    run bash scripts/custodian.sh || die "custodian failed; receipt not taken"
    [ "$DRY" = 1 ] || [ -f "receipts/$TODAY.md.sig" ] \
        || die "no receipts/$TODAY.md.sig — patch 04 is not applied, or signing failed"
fi

# ---------------------------------------------------------------- step 2
say "Step 2 — the custody-set patches and the owner edits"
note "01  check_concepts.py   mechanism (a): absent snapshot = pin-only citation, counted"
note "02  check_receipts.py   resolve a recorded HEAD through a signed rewrite attestation"
note "05  check_concepts.py   brief_row fidelity (D0180) — the field no guard reads"
note "06  check_decisions.py  retires_bindings + schema (D0181) — REQUIRED FOR STEP 5"
note "03  policy.yaml         publishing: this-repo-public; expected_citation_pins: 12"
note "    tag-roles.yaml      m3-laws-freeze into required_tags (trust_root.object: step 6)"
warn "06 is a PREREQUISITE, not an improvement. Step 5 deletes snapshots; owner-signed,"
warn "immutable D0115 binds to one by path; binding_violation resolves file bindings by"
warn "bare existence. Without 06 the gate at step 9 cannot go green and D0045 forbids the"
warn "obvious fix. The gate is ALREADY red on this — D0181 quotes the expected three."
note "After applying 06, add its retires_bindings entry to D0181 (it could not carry its"
note "own: the schema is additionalProperties:false until the patch lands)."
note "To confirm the count yourself — but note it runs a pytest per binding, ~25 min:"
note "  .venv/bin/python scripts/check_decisions.py 2>&1 | grep -c 'binding does not resolve'"
confirm "All five applied (01, 02, 03, 05, 06)?" || die "stopped at your request"

say "Step 2b — execute D0180's withdrawal, NOW that patch 06 unblocks it"
note "Until patch 06 lands this is uncommittable in either direction (D0181): withdrawing"
note "the citation reddens check_concepts' orphan check, deleting the file reddens"
note "check_decisions' binding to owner-signed immutable D0115, and both are always_run"
note "pre-commit hooks. Measured and reverted on 2026-09-06; this is where it lands."
note "  1. remove the fourth sibling's 'source' entry from"
note "     concepts/provenance-ref-grammar.yaml   (keep brief_row VERBATIM — D0180)"
note "  2. git rm concepts/snapshots/provenance-ref-grammar/renavon-adr-002.md"
note "     (bytes preserved at ~/git/tannen/.reference/snapshots/)"
note "  3. add patch 05's brief_row_divergence declaration to that record"
note "  4. add patch 06's retires_bindings entry to D0181"
note "probe before and after: .venv/bin/python $PKG/probes/brief_row_fidelity.py"
note "  expect 8/8 -> 7/8 after (1) -> 8/8 once (3) declares the divergence"
warn "ONLY NOW set expected_citation_pins, and RE-MEASURE rather than trusting patch 03:"
note "    grep -rh '      path: concepts/snapshots/' concepts/*.yaml | sort -u | wc -l"
[ "$DRY" = 1 ] || note "    -> $(grep -rh '      path: concepts/snapshots/' concepts/*.yaml | sort -u | wc -l) right now (12 once the withdrawal lands)"
confirm "Withdrawal executed, divergence declared, pin count measured and set?" \
    || die "stopped at your request"

# ---------------------------------------------------------------- step 3
say "Step 3 — the root files a public repository needs"
for f in LICENSE NOTICE README.md CONTRIBUTING.md; do
    src="$PKG/${f}.draft"
    [ -f "$src" ] || { warn "no draft for $f"; continue; }
    if [ -f "$f" ]; then note "$f already present — skipping"; else
        note "install $f from ${src}"
        run cp "$src" "$f"
    fi
done
warn "A licence file at the root IS the grant. Apache-2.0 by your ruling of 2026-09-06."

# ---------------------------------------------------------------- step 4
say "Step 4 — poison fixtures (author-key territory: tests/poison/)"
note "a) $PKG/fixture-candidates/ candidate 1 — check-concepts policy (needs patch 01)"
note "b) $PKG/fixture-candidates/ candidate 2 — check-concepts-brief-row (needs patch 05)"
note "c) docs/redteam/fixture-candidates/oracle-shadow-spoofed/ — guard patch ALREADY"
note "   landed (D0179), so this one is install-ready with no patch first."
note "Each install = git mv + a MANIFEST.sha256 row per file + a poison() line in"
note "custodian.sh + a row in tests/poison/README.md."
confirm "Fixtures installed (or deliberately deferred)?" || die "stopped at your request"
run bash scripts/custodian.sh --check-only \
    || die "custodian red after fixture install — a fixture whose guard tooth does not"

# ---------------------------------------------------------------- step 5
say "Step 5 — delete the sibling snapshots, commit, then rewrite ON A CLONE"
note "concepts/snapshots/semiring-relations/ is tannen's OWN brief excerpt: it stays, and"
note "it is what keeps check_concepts.py's byte-verifying path non-vacuous in public."
SNAP_DIRS=$(find concepts/snapshots -mindepth 1 -maxdepth 1 -type d ! -name semiring-relations -printf '%f\n' | sort)
note "to excise from history:"; printf '     %s\n' $SNAP_DIRS
if [ -n "$(git ls-files concepts/snapshots | grep -v semiring-relations)" ]; then
    confirm "Delete them from the tracked tree and commit?" || die "stopped at your request"
    for d in $SNAP_DIRS; do run git rm -rq "concepts/snapshots/$d"; done
    run git add -A && run git commit -m "Publication: remove vendored sibling snapshots from the tree"
else
    note "already absent from the tracked tree — the history rewrite still needs them"
fi

if [ "$DRY" = 1 ]; then
    WORK="${TANNEN_REWRITE_WORK:-<a fresh mktemp -d, created at run time>}"
else
    WORK="${TANNEN_REWRITE_WORK:-$(mktemp -d /var/tmp/tannen-rewrite.XXXXXX)}"
fi
say "Step 5b — the rewrite, in $WORK"
warn "NEVER in place. ~/git/tannen is BARE with four live worktrees; filter-repo in a"
warn "worktree corrupts every sibling checkout."
command -v git-filter-repo >/dev/null 2>&1 || [ -x "$HOME/.local/bin/git-filter-repo" ] \
    || die "git-filter-repo not found"
FR="$(command -v git-filter-repo || echo "$HOME/.local/bin/git-filter-repo")"
if [ ! -d "$WORK/.git" ]; then
    run git clone --no-local --quiet "$ROOT" "$WORK" || die "clone failed"
fi
BEFORE=$( [ "$DRY" = 1 ] && echo 0 || git -C "$WORK" rev-list --all --count )
note "commits in the clone before: $BEFORE"
PATHS=(); for d in $SNAP_DIRS; do PATHS+=(--path "concepts/snapshots/$d"); done
note "git filter-repo --invert-paths ${PATHS[*]}"
confirm "Run the rewrite now?" || die "stopped at your request"
run env -C "$WORK" "$FR" --invert-paths "${PATHS[@]}" || die "filter-repo failed"
if [ "$DRY" = 0 ]; then
    AFTER=$(git -C "$WORK" rev-list --all --count)
    MAP="$WORK/.git/filter-repo/commit-map"
    [ -f "$MAP" ] || die "no commit-map — cannot write the rewrite attestation"
    note "commits after: $AFTER (before: $BEFORE)"
    [ "$AFTER" = "$BEFORE" ] || warn "commit count CHANGED — expected equal; investigate"
    # The dropped-commit marker is 40 zeros in the NEW field, not the old one. Spelled
    # exactly as rehearse_rewrite.sh step 6 spells it: an earlier draft of this driver
    # anchored '^0\{40\} ' and would have reported every rewrite clean.
    pairs=$(grep -c '^[0-9a-f]\{40\} [0-9a-f]\{40\}$' "$MAP")
    dropped=$(grep -c '^[0-9a-f]\{40\} 0\{40\}$' "$MAP")
    note "commit-map: $(wc -l < "$MAP") lines, $pairs well-formed pairs, $dropped dropped-to-nothing"
    [ "$dropped" = 0 ] || die "commit-map has $dropped dropped-to-nothing entries: commits were LOST"
    [ "$pairs" = "$BEFORE" ] || warn "pairs ($pairs) != commits before ($BEFORE) — the map is incomplete"
    note "verify nothing borrowed survives:"
    if git -C "$WORK" log --all -p -- concepts/snapshots \
         | grep -qiE 'pkm|proplang|life-agent|renavon'; then
        die "sibling content still reachable in the rewritten history"
    fi
    note "   clean"
fi

# ---------------------------------------------------------------- step 6
say "Step 6 — re-create all 8 tags at their ORIGINAL tagger dates"
warn "Every tag's object hash changed, so every signature is broken — including"
warn "brief-freeze, whose tag-object hash is the trust root pinned in tag-roles.yaml."
note "GIT_COMMITTER_DATE preserves the tagger date, so bless_epoch and D0036's"
note "delegation-precedes-signature ordering are undisturbed. Re-signing with a fresh"
note "date would silently reorder them."
note "owner-signed:   $(owner_tags | tr '\n' ' ')"
note "builder-signed: $(builder_tags | tr '\n' ' ')"
if [ "$DRY" = 0 ]; then
    # The new commit for a tag is looked up in the COMMIT-MAP, never by resolving the old
    # sha inside $WORK: after the rewrite the old sha does not exist there, so
    # `git -C $WORK rev-list -1 <old>` fails and yields the empty string. An earlier draft
    # of this driver did exactly that and would have offered an empty target for all eight
    # tags — found by running the dry run, not by reading it.
    for t in $(git tag); do
        old_obj=$(git rev-parse "$t")
        old_cmt=$(git rev-list -1 "$t^{commit}")
        date=$(git for-each-ref "refs/tags/$t" --format='%(taggerdate:iso-strict)')
        git tag -l --format='%(contents)' "$t" > "$WORK/.tagmsg-$t"
        new_cmt=$(awk -v o="$old_cmt" '$1==o {print $2}' "$MAP")
        [ -n "$new_cmt" ] || die "$t: commit $old_cmt not in the commit-map — cannot re-tag"
        printf '   %-16s %s\n' "$t" "$date"
        printf '     old tag object %s  commit %s -> %s\n' "${old_obj:0:12}" "${old_cmt:0:12}" "${new_cmt:0:12}"
        printf '     GIT_COMMITTER_DATE="%s" git tag -s -F .tagmsg-%s -u <key> %s %s\n' \
            "$date" "$t" "$t" "$new_cmt"
    done
    warn "Tag re-creation is left to the keyboard on purpose: each one is a key touch and"
    warn "the message must be the original. Per tag, in $WORK:"
    note '  GIT_COMMITTER_DATE="<taggerdate>" git tag -s -F .tagmsg-<tag> -u <key> <tag> <new-commit>'
    note "then: git tag -v <tag>  and confirm the tagger date is unchanged."
fi
confirm "All 8 tags re-created and verifying, dates unchanged?" || die "stopped at your request"
note "NOW read off the new brief-freeze tag object and finish tag-roles.yaml:"
note "  git -C $WORK rev-parse brief-freeze   ->  trust_root.object"

# ---------------------------------------------------------------- step 7
say "Step 7 — the rewrite attestation (no receipt is ever re-signed)"
note "The five existing receipts stay BYTE-IDENTICAL. Editing an owner-signed attestation"
note "of a past moment to carry a new SHA is fabricating history, which is the thing the"
note "chain exists to prevent. Instead: one new attestation carrying the map, and patch 02"
note "teaches check_receipts.py to resolve a dead recorded HEAD through it."
note "Write receipts/REWRITE-$TODAY.md with the COMPLETE commit-map — all pairs, not just"
note "the five receipt HEADs. The guard only needs five; an auditor needs all of them."
note "  sed 's/^/  - /; s/ / -> /' $WORK/.git/filter-repo/commit-map"
note "Sign it under the DISTINCT namespace tannen-rewrite:"
note "  ssh-keygen -Y sign -f $OWNER_KEY -n tannen-rewrite receipts/REWRITE-$TODAY.md"
confirm "Attestation written and signed under namespace tannen-rewrite?" \
    || die "stopped at your request"

# ---------------------------------------------------------------- steps 8-10
say "Step 8 — custody"
note "  .venv/bin/python scripts/gen_custody.py"
note "  ssh-keygen -Y sign -f $OWNER_KEY -n tannen-custody governance/custody.sha256"
note "  ssh-keygen -Y sign -f $OWNER_KEY -n tannen-policy  governance/policy.yaml"
confirm "custody.sha256 and policy.yaml regenerated and signed?" || die "stopped at your request"

say "Step 9 — the full gate, on the REWRITTEN history"
note "This is the first time any of it has run against rewritten objects."
if confirm "Run 'make verify' and the custodian in $WORK now?"; then
    run env -C "$WORK" make verify || die "verify red on the rewritten history"
    run env -C "$WORK" bash scripts/custodian.sh --check-only || die "custody floor red"
fi

say "Step 10 — sign D0176, the publication record"
note "  ssh-keygen -Y sign -f $OWNER_KEY -n tannen-decision \\"
note "    decisions/0176-publication-*.yaml"
warn "D0176 is status: blocked-on-owner. D0045 makes its fields immutable, so the flip to"
warn "accepted is a NEW record, not an edit — write it before signing if that is the shape"
warn "you want, and sign both."
confirm "D0176 signed?" || die "stopped at your request"

# ---------------------------------------------------------------- publish
say "Publish — and only now"
note "  gh repo create gfrmin/tannen --public --disable-wiki --source $WORK --remote origin"
note "  git -C $WORK push -u origin master        # FIRST, so master becomes the default"
note "  git -C $WORK push origin --all && git -C $WORK push origin --tags"
note "  gh repo view gfrmin/tannen --json defaultBranchRef"
warn "If GitHub created main: gh repo edit --default-branch master"
warn "                        git push origin --delete main"
note "Then watch CI's first-ever run — fetch-depth: 0 is load-bearing and untested in anger."
note "Then the real acceptance test, the first time this gate has run on any machine but"
note "this one:"
note "  git clone https://github.com/gfrmin/tannen /var/tmp/pubcheck && cd /var/tmp/pubcheck && make verify"

say "The sitting is closed"
note "workdir kept at $WORK — remove it once the push is confirmed"
