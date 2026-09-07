#!/usr/bin/env bash
# publication_sitting.sh — interactive driver for the PUBLICATION sitting.
# OWNER-RUN, on the owner's machine, with the owner key's passphrase available.
#
# Builder-drafted and staged under docs/proposals/ (D0182, D0183). It is NOT in scripts/
# and NOT in the custody set: installing it is a `git mv` plus a custody row, and that is
# the owner's act, like every other sitting driver (BRIEF §9.1). Run it from here:
#
#   docs/proposals/2026-09-06-publication/publication_sitting.sh              # the sitting
#   docs/proposals/2026-09-06-publication/publication_sitting.sh --dry-run    # narrated only
#
# WHY THIS EXISTS. Every previous sitting had an executable driver and a rehearsal harness
# in front of it; this one had an eleven-step prose runbook (D0182). D0068's lesson is
# blunt: three consecutive attempts at the M0->M1 sitting stopped on defects a single
# end-to-end run would have found in seconds. This sitting rewrites EVERY commit in the
# history — 84 of them at the last rehearsal, and one more for each commit made between
# now and the sitting — and re-signs the trust root. It is the least forgiving one yet.
#
# IT PERFORMS THE SITTING; IT DOES NOT NARRATE IT. The first draft left eight tag
# signatures, the attestation, custody and D0176 "to the keyboard on purpose". That is
# exactly what a rehearsal cannot exercise and exactly what D0065/D0066 were. Every step
# below runs under `confirm`, with the keys taken from the environment the way
# scripts/boundary_sitting.sh takes them (TANNEN_OWNER_KEY, TANNEN_BUILDER_KEY), so
# rehearse_publication.sh can run the whole thing against a disposable clone with a
# throwaway owner key before you run it once with the real one.
#
# WHAT IT WILL DO TO YOUR KEY: 10 owner touches — custody.sha256 and policy.yaml (step G),
# the attention receipt (1), the four owner tags (6), the rewrite attestation (7),
# custody.sha256 again (8), and D0176 (10). Plus 4 builder-key touches for the *-laws-freeze
# tags, which is why TANNEN_BUILDER_KEY must also be readable here.
#
# WHAT IT WILL NEVER DO: run `git filter-repo` anywhere but a fresh disposable clone;
# force-push; delete a tag before the replacement is signed and verified; or touch
# ~/git/tannen's history — the rewrite happens in $WORK, which is what gets published.
# The bare repo and its four worktrees keep the un-rewritten history; adopting the rewritten
# one locally is a separate decision this driver deliberately does not make.
#
# REHEARSAL KNOBS (never a sitting outcome; the harness reads exit status and artifacts):
#   TANNEN_SITTING_STOP_AFTER=<step>   stop (exit 3) after that step
#   TANNEN_SITTING_FAST=1              skip the two 45-minute gates and the ~20-minute commit
#                                      hooks — a mechanics-only run of every step in ~10 min,
#                                      for finding defects in steps 5-9 before paying 3 hours
#
# ORDER, and why it is not the README's original numbering. The full gate runs AFTER the
# patches and BEFORE the rewrite (step G): a patch that breaks a governance test must
# surface while everything is still reversible, not at step 9 with the history already
# rewritten. The receipt (step 1) is taken after the custody set is re-signed, because the
# custodian that writes it checks the custody floor first and refuses a drifted one.
#
set -uo pipefail
cd "$(dirname "$0")/../../.."          # docs/proposals/<pkg>/ -> repo root
ROOT="$PWD"
PY="$ROOT/.venv/bin/python"

DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1
FAST="${TANNEN_SITTING_FAST:-0}"

OWNER_KEY="${TANNEN_OWNER_KEY:-$HOME/.ssh/tannen_owner}"
BUILDER_KEY="${TANNEN_BUILDER_KEY:-$HOME/.ssh/tannen_builder}"
PKG="docs/proposals/2026-09-06-publication"

say()  { printf '\n\033[1m== %s\033[0m\n' "$*"
         [ -n "${STEPS:-}" ] && printf '%s\n' "$*" >> "$STEPS"; return 0; }
note() { printf '   %s\n' "$*"; }
warn() { printf '   \033[33m! %s\033[0m\n' "$*"; }
# A [waiting] line arms the rehearsal harness's silence tolerance for the rest of the step
# (rehearse_publication.sh, D0069): anything slower than ~25 s says so first.
waiting() { printf '   [waiting] %s\n' "$*"; }
die()  { printf '\npublication: STOP — %s\n' "$*" >&2
         # An abort is `exit 1` with no trap, so this is the only place that can say what
         # the run leaves behind. The two regimes were measured, not reasoned (D0184): the
         # answer differs either side of the sitting's first commit.
         if [ -n "${STEPS:-}" ] && [ -s "$STEPS" ]; then
             printf 'reached: step %s   (every step this run announced: %s)\n' \
                 "$(awk '/^Step /{l=$2} END{print l}' "$STEPS")" "$STEPS" >&2
             if grep -q '^Step A' "$STEPS"; then
                 printf 'The sitting had already committed (step A): the tree is clean and the custody\nfloor is green. There is nothing to undo — this is a coherent place to stop.\n' >&2
             else
                 printf 'The sitting had NOT committed yet: patches are applied in the WORKING TREE and the\ncustody floor is RED until they are signed at step G. Undo with:\n    git checkout -- . && git clean -fd\n' >&2
             fi
             [ -n "${WORK:-}" ] && [ -d "${WORK:-}/.git" ] \
                 && printf 'The rewrite happened only in the disposable clone at %s — rm -rf it.\n' "$WORK" >&2
         fi
         exit 1; }
confirm() { [ "$DRY" = 1 ] && { note "[dry-run] would ask: $1"; return 0; }
            local a; read -rp "   $1 [y/N] " a; [[ "${a:-}" == [yY]* ]]; }
run() { [ "$DRY" = 1 ] && { note "[dry-run] $*"; return 0; }; "$@"; }
# Rehearsal knob, never a sitting outcome: stop (exit 3) after the named step so a partial
# run can be inspected in minutes instead of hours. A partial run cannot read as green —
# the harness checks the exit status and everything the later steps leave behind.
stop_after() { [ "${TANNEN_SITTING_STOP_AFTER:-}" = "$1" ] || return 0
               warn "stopping after step $1 (TANNEN_SITTING_STOP_AFTER) — a rehearsal knob"; exit 3; }

# ---------------------------------------------------------------- helpers
[ -x "$PY" ] || die "no interpreter at $PY — run 'uv sync --frozen' first"
[ "$DRY" = 1 ] || [ -f "$OWNER_KEY" ]   || die "no owner key at $OWNER_KEY (set TANNEN_OWNER_KEY)"
[ "$DRY" = 1 ] || [ -f "$BUILDER_KEY" ] || die "no builder key at $BUILDER_KEY (set TANNEN_BUILDER_KEY)"

# The eight signed tags, with their signer class. Derived nowhere: tag-roles.yaml owns this
# mapping, so read it rather than restating it (CLAUDE.md: no guard, and no driver, may
# depend on a hand-maintained enumeration).
owner_tags()   { grep -oP '^\s*-\s*\K\S+' governance/tag-roles.yaml | grep -E 'brief-freeze|-close$' | sort -u; }
builder_tags() { git tag | grep -E -- '-laws-freeze$' | sort -u; }

manifest_refresh() {   # <dir> <path> — a frozen file's row after an owner edit (author-key)
    ( cd "$1" && grep -v "  $2\$" MANIFEST.sha256 > MANIFEST.tmp \
        && sha256sum "$2" >> MANIFEST.tmp && mv MANIFEST.tmp MANIFEST.sha256 )
}
manifest_refresh_if_listed() {   # <dir> <path> — only files that HAVE a row (never enlarge the set)
    if ( cd "$1" && grep -q "  $2\$" MANIFEST.sha256 ); then run manifest_refresh "$1" "$2"; fi
}
add_manifest_rows() {   # <dir> — every file under it (sealed dirs carry a row each), staged
    local f
    while IFS= read -r f; do
        run git add -- "$f"
        grep -q "  $f\$" MANIFEST.sha256 || run bash -c "sha256sum '$f' >> MANIFEST.sha256"
    done < <(find "$1" -type f ! -path '*/__pycache__/*' | sort)
}
sign_owner() {   # <dir> <file> <namespace>
    [ "$DRY" = 1 ] && { note "[dry-run] ssh-keygen -Y sign -n $3 $2"; return 0; }
    ( cd "$1" && rm -f "$2.sig" && ssh-keygen -Y sign -f "$OWNER_KEY" -n "$3" "$2" >/dev/null \
        && ssh-keygen -Y verify -f allowed_signers -I owner@tannen -n "$3" -s "$2.sig" < "$2" >/dev/null ) \
        || die "signing $2 under $3 failed (or does not verify against allowed_signers)"
}
commit_here() {   # <dir> <message> — projections first; hooks armed (~20 min for check-decisions)
    local dir="$1" msg="$2"
    run env -C "$dir" "$dir/.venv/bin/python" -I -P scripts/gen_projections.py >/dev/null \
        || die "gen_projections failed in $dir"
    run git -C "$dir" add -A
    local hook=()
    if [ "$FAST" = 1 ]; then
        warn "TANNEN_SITTING_FAST: committing with --no-verify (hooks skipped) — rehearsal only"
        hook=(--no-verify)
    else
        waiting "pre-commit hooks in $dir (check-decisions runs a pytest per binding: ~20 min)"
    fi
    if ! run git -C "$dir" commit -q "${hook[@]}" -m "$msg"; then
        # regen-projections may have rewritten a file on the first try; stage and retry once
        run git -C "$dir" add -A && run git -C "$dir" commit -q "${hook[@]}" -m "$msg" \
            || die "commit failed in $dir: $msg"
    fi
    note "committed: $(git -C "$dir" rev-parse --short HEAD 2>/dev/null) $msg"
}
ff_master() {   # <dir> — move master to HEAD if it exists and is behind. NOTHING ELSE.
    # Called on the OWNER'S REAL REPOSITORY at step 5 as well as on the rewrite clone, so it
    # must never create, check out or delete a branch: an earlier spelling of the
    # publish-shape fix below lived in here, and in the real repo it would have switched the
    # m3 worktree to master and then `branch -D m3`. The rehearsal cannot catch that — its
    # clone of a worktree has no master, so it takes the harmless path (D0186).
    local d="$1"
    [ "$(git -C "$d" rev-parse --abbrev-ref HEAD)" = master ] && {
        note "$d is on master; commits land on it directly"; return 0; }
    if git -C "$d" rev-parse -q --verify master >/dev/null 2>&1; then
        if git -C "$d" merge-base --is-ancestor master HEAD; then
            run git -C "$d" branch -f master HEAD && note "master fast-forwarded to HEAD in $d"
        else
            warn "master in $d is not an ancestor of HEAD — NOT moved; publish would push the wrong branch"
        fi
    else
        note "no local master in $d (a clone of a worktree has only its checked-out branch)"
    fi
}
publish_shape() {   # <dir> — THE REWRITE CLONE ONLY: exactly one branch, and it is master.
    # D0186, found by inspecting a kept rewrite clone rather than by reading. The driver
    # clones $PWD, which is a WORKTREE, so the clone carries only that worktree's branch —
    # and git-filter-repo DROPS the remote-tracking refs rather than converting them. The
    # rewritten clone therefore had one branch, `m3`, and no master at all, while the publish
    # narration said `push -u origin master`: that fails with `src refspec master does not
    # match any`, and the natural recovery — pushing the milestone branch — makes `m3` the
    # public default. Never call this on the repository you are sitting in.
    local d="$1" cur
    cur=$(git -C "$d" rev-parse --abbrev-ref HEAD)
    if ! git -C "$d" rev-parse -q --verify master >/dev/null 2>&1; then
        run git -C "$d" branch master HEAD \
            && note "master CREATED at HEAD in $d (the clone carried only '$cur')"
    elif [ "$(git -C "$d" rev-parse master)" != "$(git -C "$d" rev-parse HEAD)" ]; then
        # A fresh rewrite clone has no master, so this branch is unreachable where the driver
        # calls it — but checking out a STALE master would silently roll the tree back past
        # the sitting's own commit, and a footgun that cannot fire today is still a footgun.
        git -C "$d" merge-base --is-ancestor master HEAD \
            || die "master in $d is not an ancestor of HEAD — refusing to publish from it"
        run git -C "$d" branch -f master HEAD && note "master fast-forwarded to HEAD in $d"
    fi
    [ "$cur" = master ] || run git -C "$d" checkout -q master || die "could not switch $d to master"
    if [ "$cur" != master ] && git -C "$d" rev-parse -q --verify "$cur" >/dev/null 2>&1; then
        run git -C "$d" branch -D "$cur" >/dev/null \
            && note "removed '$cur' from $d — the published repository carries ONE branch, master"
        note "Nothing is lost: every milestone branch is an ancestor of master and every"
        note "milestone is marked by a signed tag. Keep it instead by deleting that line."
    fi
}
# Owner edits as data, not keystrokes. Each editlet is idempotent and asserts its anchor.
edit() {   # <name> <dir> <python source on stdin>
    local name="$1" dir="$2"
    if [ "$DRY" = 1 ]; then note "[dry-run] editlet $name"; cat >/dev/null; return 0; fi
    ( cd "$dir" && "$PY" - ) || die "editlet $name failed"
}
measure_pins() { grep -rh '      path: concepts/snapshots/' concepts/*.yaml | sort -u | wc -l; }
set_pins() {   # <n> — governance/policy.yaml#concept_registry.expected_citation_pins
    edit "set_pins($1)" . <<PY
import re, pathlib
p = pathlib.Path("governance/policy.yaml"); s = p.read_text()
block = """
# Citation pins the concept registry must account for (D0115 mechanism (a), D0176).
# NOT derived from concepts/ — see scripts/check_concepts.py. Raise or lower this only
# when a concept record's \`sources\` list actually changes, and re-sign.
concept_registry:
  expected_citation_pins: $1
"""
if "concept_registry:" not in s:
    s = s.rstrip("\n") + "\n" + block
else:
    s, n = re.subn(r"(expected_citation_pins:\s*)\d+", r"\g<1>$1", s); assert n == 1
p.write_text(s); print("   policy.yaml: expected_citation_pins = $1")
PY
}

TODAY_START="$(date +%Y-%m-%d)"
# Everything the driver writes for its own use lives HERE, never inside either repository:
# an untracked file in the rewrite clone makes filter-repo refuse ("not a fresh clone"),
# and anything left there afterwards is swept into the published commit by `git add -A`.
# Both were found by the fast rehearsal.
SCRATCH="${TANNEN_SITTING_SCRATCH:-$( [ "$DRY" = 1 ] && echo "<scratch dir>" \
           || mktemp -d "${TMPDIR:-/var/tmp}/tannen-sitting.XXXXXX")}"
[ "$DRY" = 1 ] || mkdir -p "$SCRATCH"
# The breadcrumb: one line per step, appended as it is announced. A `die` is exit 1 with
# no trap, so after an abort THIS is what says how far the sitting got — to you at the
# keyboard, and to rehearse_publication.sh, which must not learn the driver's state by
# parsing the driver's prose (BRIEF §2: one implementation, not two).
STEPS=""
if [ "$DRY" != 1 ]; then STEPS="$SCRATCH/steps"; : > "$STEPS"; fi
note "publication sitting, $TODAY_START, at $ROOT$( [ "$DRY" = 1 ] && printf ' (DRY RUN)')"
note "scratch, and its steps file recording how far this run got: $SCRATCH"

# ---------------------------------------------------------------- P
# ---------------------------------------------------------------- the passphrase path
# MEASURED, not assumed (D0185), with a throwaway passphrase-protected key: `ssh-keygen -Y
# sign -f <encrypted key>` prints `Enter passphrase for "…":` on the terminal EVERY time —
# ten times for the owner key alone, spread across ninety-five minutes. With the key in
# ssh-agent the IDENTICAL invocation signs silently, because ssh-keygen finds it there; `-f`
# keeps pointing at the private path and nothing in this driver changes. So this reports
# which of the two you are about to do; it does not alter how anything is signed.
# Neither probe prompts: `-lf` reads the public half out of the private file without
# decrypting it, and `-y -P ''` fails fast on an encrypted key.
key_encrypted() { ! ssh-keygen -y -P '' -f "$1" >/dev/null 2>&1; }
agent_holds()   { local fp; fp=$(ssh-keygen -lf "$1" 2>/dev/null | awk '{print $2}')
                  [ -n "$fp" ] && ssh-add -l 2>/dev/null | grep -qF "$fp"; }
key_report() {   # <label> <keyfile> <how many signatures this sitting makes with it>
    if   ! key_encrypted "$2"; then note "$1 key: no passphrase — $3 signature(s), no prompts"
    elif agent_holds "$2";     then note "$1 key: passphrase-protected, held by ssh-agent — $3 signature(s), no prompts"
    else warn "$1 key is passphrase-protected and NOT in ssh-agent: expect $3 SEPARATE prompts."
         warn "  ssh-add $2"
         warn "  once, IN THIS TERMINAL, makes all $3 silent. Do not use 'ssh-add -t': ~95 min."
    fi
}
# Reported in --dry-run too: the probes never sign, never prompt and never read a
# passphrase, and a preview of the sitting is exactly where this belongs.
say "Keys — which passphrase path this sitting takes"
note "Read from THIS process's SSH_AUTH_SOCK, so it is also the same-terminal check:"
note "a key added in another window, or an agent socket from a different login, shows"
note "here as 'not in ssh-agent' — which is exactly what the sitting would experience."
for _k in "owner:$OWNER_KEY:10" "builder:$BUILDER_KEY:4"; do
    _lbl=${_k%%:*}; _rest=${_k#*:}; _path=${_rest%:*}; _n=${_rest##*:}
    if [ -f "$_path" ]; then key_report "$_lbl" "$_path" "$_n"
    else note "$_lbl key: not present at $_path (dry run, or set TANNEN_$(printf '%s' "$_lbl" | tr a-z A-Z)_KEY)"
    fi
done

say "Precondition — the custody floor is green BEFORE anything is signed"
note "This is the state the first receipt attests to. A red floor here means builder work,"
note "not a sitting. The 45-minute gate runs at step G, AFTER the patches — on this tree."
run bash scripts/custodian.sh --check-only || die "custody floor red — builder work; sign nothing"
if [ "$DRY" = 0 ] && ! .venv/bin/tannen laws report >/dev/null 2>&1; then
    warn "evidence store not fresh here (a fresh clone has none) — step G's make verify regenerates it"
fi
[ -z "$(git status --porcelain)" ] || warn "working tree not clean — a sitting starts from a committed repo; whatever is here rides into commit A"
PRE_HEAD="$(git rev-parse HEAD)"
note "pre-rewrite HEAD: $PRE_HEAD"
stop_after P

# ---------------------------------------------------------------- 0
say "Step 0 — patch 04 FIRST (D0177): the custodian says 'author-signed' when signing failed"
note "custodian.sh ignores ssh-keygen's exit status: on a failed signature it prints"
note "'attention receipt written and author-signed', leaves an UNSIGNED receipt behind and"
note "exits 0. Step 1 is the step that corrupts. scripts/custodian.sh is author-key"
note "territory, so this is your edit, applied here under your confirmation."
if grep -q 'receipt signing FAILED' scripts/custodian.sh; then
    note "already applied"
else
    confirm "Apply $PKG/patches/04 to scripts/custodian.sh?" || die "do not proceed to step 1 with the receipt bug live"
    run git apply "$PKG/patches/04-custodian-receipt-signing.patch" || die "patch 04 did not apply"
fi
note "Patch 07 (same file, same reason for being yours): the custodian carried its OWN copy"
note "of the receipt-chain check, so patch 02 taught the guard about rewrite attestations"
note "and the custodian went on rejecting them. It now delegates to scripts/check_receipts.py"
note "the way it already delegates to check_tag_signers.py — one implementation, not two."
if grep -q 'scripts/check_receipts.py || bad' scripts/custodian.sh; then
    note "already applied"
else
    confirm "Apply $PKG/patches/07 to scripts/custodian.sh?" || die "the custodian would reject the attestation at step 9"
    run git apply "$PKG/patches/07-custodian-delegates-receipt-chain.patch" || die "patch 07 did not apply"
fi
run manifest_refresh . scripts/custodian.sh
stop_after 0

# ---------------------------------------------------------------- 2
say "Step 2 — the custody-set guard patches, and the owner edits from patch 03"
note "01  check_concepts.py    mechanism (a): absent snapshot = pin-only citation, counted"
note "02  check_receipts.py    resolve a recorded HEAD through a signed rewrite attestation"
note "05  check_concepts.py    brief_row fidelity (D0180) — the field no guard read"
note "06  check_decisions.py   retires_bindings (D0181) — REQUIRED for step 5"
note "03  policy.yaml          external_surface.publishing; concept_registry (measured);"
note "                         licence_defaults -> Apache-2.0 (D0176 ruling 2)"
note "    tag-roles.yaml       m3-laws-freeze joins required_tags (trust_root: step 6)"
warn "06 is a PREREQUISITE, not an improvement: step 5 deletes snapshots, owner-signed"
warn "immutable D0115 binds to one by path, and without 06 the gate at step 9 cannot go"
warn "green. Four of these patches touch MANIFEST-frozen files (custodian.sh, both schemas,"
warn "tag-roles.yaml): each row is refreshed here, or the first commit is refused."
confirm "Apply patches 01, 02, 05, 06 and the patch-03 edits now?" || die "stopped at your request"
for p in 01-check-concepts-degraded-pins 02-check-receipts-rewrite-map \
         05-check-concepts-brief-row-fidelity 06-check-decisions-retired-bindings; do
    patch="$PKG/patches/$p.patch"
    if git apply --check "$patch" >/dev/null 2>&1; then
        run git apply "$patch" || die "$p did not apply"; note "applied  $p"
    elif git apply --reverse --check "$patch" >/dev/null 2>&1; then
        note "already  $p"
    else
        die "$p neither applies nor is already applied — the tree drifted from the package"
    fi
done
run manifest_refresh . governance/schemas/concept-record.schema.json
run manifest_refresh . governance/schemas/decision-record.schema.json
edit "policy_licence" . <<'PY'
import pathlib
p = pathlib.Path("governance/policy.yaml"); s = p.read_text()
old = ("# Licence defaults (per the proplang precedent). NOTE: a licence default is not a\n"
       "# publication decision \u2014 any byte leaving the repo boundary remains Tier-C door 2.\n"
       "licence_defaults:\n"
       "  code: MIT\n"
       "  docs: CC-BY-SA-4.0\n")
new = ("# The licence, settled at the publication sitting. D0176 ruling (2), owner, 2026-09-06:\n"
       "# Apache-2.0 whole, superseding the MIT/CC-BY-SA-4.0 split these keys used to carry.\n"
       "# LICENSE and NOTICE at the root are the grant; these keys are still a default and\n"
       "# still not a publication decision \u2014 every byte leaving the boundary is Tier-C door 2.\n"
       "# No guard reads either key; the owner signature over this file is what makes it hold.\n"
       "licence_defaults:\n"
       "  code: Apache-2.0\n"
       "  docs: Apache-2.0\n")
if "code: Apache-2.0" in s:
    print("   policy.yaml: licence_defaults already Apache-2.0")
else:
    assert s.count(old) == 1, "licence_defaults anchor not found"
    p.write_text(s.replace(old, new)); print("   policy.yaml: licence_defaults = Apache-2.0 (D0176 ruling 2)")
PY
edit "policy_publishing" . <<'PY'
import pathlib
p = pathlib.Path("governance/policy.yaml"); s = p.read_text()
old = "external_surface:\n  publishing: forbidden\n"
new = ("external_surface:\n"
       "  # D0115 (owner-signed) and D0176: this repository is published at\n"
       "  # github.com/gfrmin/tannen and developed in public. `publishing` names THIS repository\n"
       "  # only — every other byte-leaving act stays a Tier-C door.\n"
       "  publishing: this-repo-public\n")
if "publishing: this-repo-public" in s:
    print("   policy.yaml: publishing already this-repo-public")
else:
    assert s.count(old) == 1, "external_surface.publishing anchor not found"
    p.write_text(s.replace(old, new)); print("   policy.yaml: external_surface.publishing = this-repo-public")
PY
set_pins "$(measure_pins)"
edit "tagroles_required" . <<'PY'
import pathlib
p = pathlib.Path("governance/tag-roles.yaml"); s = p.read_text()
if "  - m3-laws-freeze\n" in s:
    print("   tag-roles.yaml: m3-laws-freeze already required")
else:
    assert s.count("required_tags:\n") == 1
    p.write_text(s.replace("required_tags:\n", "required_tags:\n  - m3-laws-freeze\n"))
    print("   tag-roles.yaml: m3-laws-freeze joins required_tags (D0095, the third recurrence)")
PY
run manifest_refresh . governance/tag-roles.yaml
stop_after 2

# ---------------------------------------------------------------- 2b
say "Step 2b — D0180's withdrawal, now that patch 06 can carry the retirement"
note "Until patch 06 this was uncommittable in either direction (D0181). Here it is four"
note "edits and one measurement: the fourth sibling's source entry leaves the record, its"
note "snapshot leaves the tree, the divergence is DECLARED (patch 05 reads it), D0181"
note "retires D0115's binding (patch 06 reads it), and the pin count is re-measured."
confirm "Execute the withdrawal?" || die "stopped at your request"
edit "withdraw_source" . <<'PY'
import pathlib
p = pathlib.Path("concepts/provenance-ref-grammar.yaml"); s = p.read_text()
anchor = "  - repo: https://github.com/renavondata/"
if anchor not in s:
    print("   provenance-ref-grammar.yaml: fourth sibling's source entry already absent")
else:
    start = s.index(anchor); end = s.index("conformance:")
    assert start < end
    p.write_text(s[:start] + s[end:]); print("   provenance-ref-grammar.yaml: fourth sibling's source entry removed")
PY
if git ls-files --error-unmatch concepts/snapshots/provenance-ref-grammar/renavon-adr-002.md >/dev/null 2>&1; then
    run git rm -q concepts/snapshots/provenance-ref-grammar/renavon-adr-002.md
    note "snapshot removed from the tree (bytes preserved at ~/git/tannen/.reference/snapshots/)"
else
    note "snapshot already absent from the tree"
fi
edit "declare_divergence" . <<'PY'
import pathlib
p = pathlib.Path("concepts/provenance-ref-grammar.yaml"); s = p.read_text()
if "brief_row_divergence:" in s:
    print("   provenance-ref-grammar.yaml: divergence already declared")
else:
    s = s.rstrip("\n") + """
brief_row_divergence:
  omits: [renavon]
  reason: >-
    Withdrawn ahead of publication (owner ruling 2026-09-06, D0180) so the public registry
    carries no internal document path, ADR heading or private commit SHA of that
    repository. brief_row stays a verbatim quote of frozen BRIEF §2, which still names it.
  decision: D0180
"""
    p.write_text(s); print("   provenance-ref-grammar.yaml: brief_row_divergence declared (D0180)")
PY
edit "d0181_retirement" . <<'PY'
import pathlib
p = next(pathlib.Path("decisions").glob("0181-*.yaml")); s = p.read_text()
if "retires_bindings:" in s:
    print(f"   {p.name}: retirement already carried")
else:
    s = s.rstrip("\n") + """
retires_bindings:
  - record: D0115
    target: concepts/snapshots/provenance-ref-grammar/renavon-adr-002.md
    reason: >-
      Deleted by owner ruling of 2026-09-06 (D0180). The binding was documentary — it named
      where the blocker lived, and the blocker is what was removed.
"""
    p.write_text(s); print(f"   {p.name}: retires D0115's binding to the deleted snapshot")
PY
PINS="$(measure_pins)"
note "citation pins now measured at $PINS (13 before the withdrawal; 12 expected)"
set_pins "$PINS"
if [ "$DRY" = 0 ]; then
    "$PY" -I -P "$PKG/probes/brief_row_fidelity.py" | grep -E '^tooth' | sed 's/^/   /'
    "$PY" -I -P "$PKG/probes/brief_row_fidelity.py" | grep -q 'tooth 2 (owner set matches sources\[\].repo): 8/8 ok' \
        || die "brief_row fidelity is not 8/8 after the declaration — see the probe's table"
fi
stop_after 2b

# ---------------------------------------------------------------- 3
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
note "governance/policy.yaml was reconciled to match at step 2 (licence_defaults, both"
note "keys) and is signed with the rest of that file at step G. No guard reads either"
note "key: the agreement between them is held by your signature, not by a check."
stop_after 3

# ---------------------------------------------------------------- 4
say "Step 4 — poison fixtures (author-key territory: tests/poison/)"
note "a) check-concepts/governance/policy.yaml  — REQUIRED with patch 01, or that fixture"
note "   fails for two reasons instead of the one it names (fixture candidate 1)"
note "b) check-concepts-brief-row/               — patch 05's tooth (candidate 2)"
note "c) check-decisions-retired-enforced/       — patch 06's refusal (candidate 3)"
note "d) oracle-shadow-spoofed/                  — RT-M3-04; its guard patch landed (D0179)"
note "Each install = the files + a MANIFEST.sha256 row per file (sealed directory) + a"
note "poison() line in custodian.sh + a row in tests/poison/README.md + the pytest mirror."
confirm "Install all four?" || die "stopped at your request"
for c in check-concepts check-concepts-brief-row check-decisions-retired-enforced; do
    run cp -rn "$PKG/fixture-candidates/$c" tests/poison/
    add_manifest_rows "tests/poison/$c"
done
if [ -d docs/redteam/fixture-candidates/oracle-shadow-spoofed ] && [ ! -d tests/poison/oracle-shadow-spoofed ]; then
    run mkdir -p tests/poison/oracle-shadow-spoofed
    for f in README.md bootstrap_shadow_spoofed.py _delta_model.py; do
        run git mv "docs/redteam/fixture-candidates/oracle-shadow-spoofed/$f" "tests/poison/oracle-shadow-spoofed/$f"
    done
    note "the guard patch stays where it was filed (docs/redteam/…, already landed as D0179)"
fi
add_manifest_rows tests/poison/oracle-shadow-spoofed
# D0179 binds to the candidate README at its staging path. A binding follows the artifact
# it names (D0045: bindings are present-tense; D0141's were updated the same way when
# oracle-shadow-model was installed at the M2 sitting). Found by the partial rehearsal —
# the first draft moved the file and left D0179 dangling, the shape D0181 is about.
edit "d0179_binding_follows_move" . <<'PY'
import pathlib
p = next(pathlib.Path("decisions").glob("0179-*.yaml")); s = p.read_text()
old = "    target: docs/redteam/fixture-candidates/oracle-shadow-spoofed/README.md\n"
new = "    target: tests/poison/oracle-shadow-spoofed/README.md\n"
if new in s:
    print(f"   {p.name}: binding already follows the installed fixture")
else:
    assert s.count(old) == 1, "D0179 binding to the staged README not found"
    p.write_text(s.replace(old, new)); print(f"   {p.name}: binding target follows the fixture into tests/poison/")
PY
edit "custodian_poison_lines" . <<'PY'
import pathlib
p = pathlib.Path("scripts/custodian.sh"); s = p.read_text()
if "The publication sitting adds four fixtures" in s:
    print("   custodian.sh: poison lines already present")
else:
    anchor = 'if [ "$FAIL" -ne 0 ]; then\n    bad "custody floor violated"'
    assert s.count(anchor) == 1
    lines = '''# The publication sitting adds four fixtures (D0183; docs/proposals/2026-09-06-publication/
# fixture-candidates/README.md): patch 05's brief_row teeth, patch 06's refusal to retire an
# enforced binding, and RT-M3-04's spoofed oracle shadow, whose marker is the guard's OWN
# tooth text — "answers with different code" — because the fixture README's "RT-M3-04"
# never appears in the guard's output (found by wiring it, not by reading it). Candidate 1
# (check-concepts/governance/policy.yaml) is a file, not a line: it narrows an existing
# fixture back to one reason.
poison check_concepts_brief_row "brief_row" \\
    "$PY" -I -P scripts/check_concepts.py --root tests/poison/check-concepts-brief-row
poison check_decisions_retired_enforced "only a documentary binding may be retired" \\
    env -u TANNEN_CHECK_DECISIONS_NESTED PYTHONDONTWRITEBYTECODE=1 \\
    "$PY" -I -P scripts/check_decisions.py --root tests/poison/check-decisions-retired-enforced
poison oracle-shadow-spoofed "answers with different code" \\
    env -u TANNEN_CHECK_DECISIONS_NESTED PYTHONPATH=tests/poison/oracle-shadow-spoofed \\
    "$PY" -B -m pytest -p bootstrap_shadow_spoofed tests/laws/m3/test_l3_differential.py -q

'''
    p.write_text(s.replace(anchor, lines + anchor)); print("   custodian.sh: three poison() lines added")
PY
run manifest_refresh . scripts/custodian.sh
edit "pytest_mirror" . <<'PY'
import pathlib
p = pathlib.Path("tests/test_governance_scripts.py"); s = p.read_text()
if "check_concepts_brief_row" in s:
    print("   test_governance_scripts.py: rows already present")
else:
    anchor = '''     "unexplained skip"),
]
'''
    assert s.count(anchor) == 1
    rows = '''     "unexplained skip"),
    # Installed at the publication sitting (D0183) beside the guard patches they prove:
    # patch 05 (brief_row read at last, D0180) and patch 06 (retires_bindings, D0181).
    ("check_concepts_brief_row",
     ["scripts/check_concepts.py", "--root", "tests/poison/check-concepts-brief-row"],
     "brief_row"),
    ("check_decisions_retired_enforced",
     ["scripts/check_decisions.py", "--root", "tests/poison/check-decisions-retired-enforced"],
     "only a documentary binding may be retired"),
]
'''
    s = s.replace(anchor, rows)
    s = s.rstrip("\\n") + '''


def test_oracle_shadow_spoofed_fails_its_poison() -> None:
    """RT-M3-04 (D0179): the same guard, sharpened. A decoy that sets `__file__` to the
    frozen path passed the M2-era identity test outright — `check_differential` answered
    1,400 times by a stub while 544 law tests passed. The guard now compares the CODE a
    module answers with against a fresh load of the frozen file, and this fixture
    (tests/poison/oracle-shadow-spoofed/, installed at the publication sitting) keeps the
    spoofed half of the corpus, which `oracle-shadow-model/` cannot reach.

    Same deviations from POISON as its two siblings, for the same reasons: no `-I -P`, `-B`,
    a pytest run rather than --root, the venv interpreter at a literal path. The marker is
    the guard's own tooth text — the fixture README's "RT-M3-04" never appears in the output.
    """
    env = {k: v for k, v in os.environ.items() if k != "TANNEN_CHECK_DECISIONS_NESTED"}
    env["PYTHONPATH"] = str(REPO_ROOT / "tests" / "poison" / "oracle-shadow-spoofed")
    result = run(
        [str(REPO_ROOT / ".venv" / "bin" / "python"), "-B", "-m", "pytest",
         "-p", "bootstrap_shadow_spoofed", "tests/laws/m3/test_l3_differential.py", "-q"],
        env=env,
    )
    combined = result.stdout + result.stderr
    assert result.returncode != 0, (
        f"oracle-shadow-spoofed PASSED its poison — weakened:\\n{combined}"
    )
    assert "answers with different code" in combined, combined
    assert "shadowed" in combined, combined
'''
    p.write_text(s); print("   test_governance_scripts.py: two POISON rows and the spoofed test added")
PY
edit "poison_readme_rows" . <<PY
import pathlib
p = pathlib.Path("tests/poison/README.md"); s = p.read_text()
if "check-concepts-brief-row/" in s and s.count("| \`check-concepts-brief-row/\` |"):
    print("   tests/poison/README.md: rows already present")
else:
    s = s.rstrip("\n") + """

## Added at the publication sitting ($TODAY_START)

Three fixtures and one file, each the poison for a guard patch that landed at the same
sitting (D0183; \`docs/proposals/2026-09-06-publication/fixture-candidates/README.md\`).
\`check-concepts/governance/policy.yaml\` is the file: after patch 01 that fixture failed for
two reasons, and the policy narrows it back to the one it names.

| Fixture | Guard | Intended violation | Marker |
|---|---|---|---|
| \`check-concepts-brief-row/\` | \`scripts/check_concepts.py\`, tooth 2 of patch 05 (D0180) | a record whose \`brief_row\` quotes a row naming two owners while \`sources\` cites one, with no \`brief_row_divergence\` — against its own one-row constitution excerpt | \`brief_row\` |
| \`check-decisions-retired-enforced/\` | \`scripts/check_decisions.py\`, patch 06 (D0181) | an accepted record retiring another's \`enforced\` file binding, which must be refused | \`only a documentary binding may be retired\` |
| \`oracle-shadow-spoofed/\` | \`src/tannen/laws/plugin.py\`'s oracle-shadow check as sharpened by RT-M3-04 (D0179) | a decoy \`_delta_model\` that sets \`__file__\` to the frozen path — the M2-era identity test passed it outright | \`answers with different code\` (the guard's own text; the fixture README's \`RT-M3-04\` never appears in the output) |
"""
    p.write_text(s); print("   tests/poison/README.md: publication-sitting section added")
PY
manifest_refresh_if_listed . tests/poison/README.md
stop_after 4

# ---------------------------------------------------------------- G
say "Step G — custody re-signed over the patched tree, then the FULL gate before the point of no return"
note "gen_custody.py; sign custody.sha256 (tannen-custody) and policy.yaml (tannen-policy)."
note "Then the custodian, then make verify — ~45 min. Everything up to here is reversible;"
note "a red gate here is builder work on a tree you can still throw away."
confirm "Regenerate custody and sign custody.sha256 + policy.yaml? (2 key touches)" || die "stopped at your request"
run "$PY" -I -P scripts/gen_projections.py >/dev/null || die "gen_projections failed"
run "$PY" -I -P scripts/gen_custody.py || die "gen_custody failed"
sign_owner . governance/custody.sha256 tannen-custody
sign_owner . governance/policy.yaml tannen-policy
run bash scripts/custodian.sh --check-only || die "custodian red after the patches — the sitting cannot continue until it is green"
if [ "$FAST" = 1 ]; then
    warn "TANNEN_SITTING_FAST: skipping make verify on the patched tree — rehearsal only"
elif confirm "Run 'make verify' now on the patched tree (~45 min; recommended, and the receipt attests to it)?"; then
    waiting "make verify: pytest (~20 min) then check_decisions (~20 min) — the gate before the rewrite"
    run make verify || die "verify is red on the patched tree — fix it before the rewrite, not after"
fi
stop_after G

# ---------------------------------------------------------------- 1
say "Step 1 — fresh attention receipt at the PRE-REWRITE head"
note "The last un-rewritten state, attested before it stops existing (HEAD $PRE_HEAD)."
RECEIPT_DAY="$(date +%Y-%m-%d)"   # read NOW, not at start: step G may have crossed midnight
if [ -f "receipts/$RECEIPT_DAY.md" ] && [ -f "receipts/$RECEIPT_DAY.md.sig" ]; then
    note "receipts/$RECEIPT_DAY.md already present and signed — skipping"
else
    run env TANNEN_OWNER_KEY="$OWNER_KEY" bash scripts/custodian.sh || die "custodian failed; receipt not taken"
    [ "$DRY" = 1 ] || [ -f "receipts/$RECEIPT_DAY.md.sig" ] \
        || die "no receipts/$RECEIPT_DAY.md.sig — patch 04 is not applied, or signing failed"
fi
stop_after 1

# ---------------------------------------------------------------- A
say "Step A — commit the pre-rewrite sitting"
commit_here . "Publication sitting: guard patches, the fourth sibling's citation withdrawn, root files, poison fixtures, receipt"
stop_after A

# ---------------------------------------------------------------- 5
say "Step 5 — the rewrite, ON A CLONE: the sibling snapshots leave every commit, HEAD included"
note "concepts/snapshots/semiring-relations/ is tannen's OWN brief excerpt: it stays, and"
note "it is what keeps check_concepts.py's byte-verifying path non-vacuous in public."
note "There is deliberately NO deletion commit first. A commit that only deletes these"
note "paths becomes EMPTY under --invert-paths, filter-repo prunes it, and the commit-map"
note "then reports a dropped commit — the fast rehearsal watched exactly that. The rewrite"
note "IS the deletion. This tree keeps its bytes (the authorised-clone configuration patch"
note "01 makes legal: N by bytes here, N by pin in public); the clone loses them."
SNAP_DIRS=$(find concepts/snapshots -mindepth 1 -maxdepth 1 -type d ! -name semiring-relations -printf '%f\n' | sort)
note "to excise from history:"; printf '     %s\n' $SNAP_DIRS
ff_master .

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
    waiting "git clone --no-local (copies every object)"
    run git clone --no-local --quiet "$ROOT" "$WORK" || die "clone failed"
fi
BEFORE=$( [ "$DRY" = 1 ] && echo 0 || git -C "$WORK" rev-list --all --count )
note "commits in the clone before: $BEFORE"
PATHS=(); for d in $SNAP_DIRS; do PATHS+=(--path "concepts/snapshots/$d"); done
note "git filter-repo --invert-paths ${PATHS[*]}"
# The withdrawal at 2b took the fourth sibling's section title, pinned commit and content
# hash out of the TREE; they stay in every past version of the record and of CONCEPTS.md,
# and the published history is what gets published (D0176's own finding, one level down —
# measured by the rehearsal: 2 commits of each). So the rewrite scrubs exactly those three
# strings from history too, read off the pre-rewrite record at run time so that neither
# this driver nor the harness has to carry them. The repository slug and document path are
# NOT scrubbed: owner-signed immutable D0115 and D0176 name them at HEAD, by design.
SCRUB="$SCRATCH/scrub-expressions"
if [ "$DRY" = 0 ]; then
    git show "$PRE_HEAD:concepts/provenance-ref-grammar.yaml" > "$SCRATCH/pre-record.yaml"
    "$PY" - "$SCRUB" "$SCRATCH/pre-record.yaml" <<'PY'
import sys, yaml
with open(sys.argv[2], encoding="utf-8") as fh:
    record = yaml.safe_load(fh)
withdrawn = [s for s in record["sources"] if "renavon" in s["repo"].lower()]
assert len(withdrawn) == 1, f"expected one withdrawn source at PRE_HEAD, found {len(withdrawn)}"
src = withdrawn[0]
needles = [src["section"], src["commit"], src["snapshot"]["sha256"]]
with open(sys.argv[1], "w", encoding="utf-8") as fh:
    for n in needles:
        fh.write(f"{n}==>[withdrawn: D0180]\n")
print(f"   scrub expressions: {len(needles)} (section title, pinned commit, content hash)")
PY
    [ $? -eq 0 ] || die "could not derive the scrub expressions from $PRE_HEAD"
fi
confirm "Run the rewrite now (paths excised, three strings scrubbed from history)?" || die "stopped at your request"
waiting "git filter-repo over every commit"
run env -C "$WORK" "$FR" --invert-paths "${PATHS[@]}" --replace-text "$SCRUB" || die "filter-repo failed"
MAP="$WORK/.git/filter-repo/commit-map"
if [ "$DRY" = 0 ]; then
    AFTER=$(git -C "$WORK" rev-list --all --count)
    [ -f "$MAP" ] || die "no commit-map — cannot write the rewrite attestation"
    note "commits after: $AFTER (before: $BEFORE)"
    [ "$AFTER" = "$BEFORE" ] || warn "commit count CHANGED — expected equal; investigate"
    # The dropped-commit marker is 40 zeros in the NEW field, not the old one (D0182).
    pairs=$(grep -c '^[0-9a-f]\{40\} [0-9a-f]\{40\}$' "$MAP")
    dropped=$(grep -c '^[0-9a-f]\{40\} 0\{40\}$' "$MAP")
    note "commit-map: $(wc -l < "$MAP") lines, $pairs well-formed pairs, $dropped dropped-to-nothing"
    [ "$dropped" = 0 ] || die "commit-map has $dropped dropped-to-nothing entries: commits were LOST"
    [ "$pairs" = "$BEFORE" ] || warn "pairs ($pairs) != commits before ($BEFORE) — the map is incomplete"
    note "verify nothing borrowed survives:"
    if git -C "$WORK" log --all --name-only --format= -- concepts/snapshots \
         | grep -v '^concepts/snapshots/semiring-relations/' | grep -q .; then
        die "sibling snapshot paths still reachable in the rewritten history"
    fi
    note "   clean"
fi
stop_after 5

# ---------------------------------------------------------------- 5c
say "Step 5c — the rewritten clone gets a venv, hooks and a master branch"
note "A bare git clone has no .venv and no hooks: gen_custody (8), the commits (C) and"
note "make verify (9) all run in $WORK and need them. The first draft forgot this."
waiting "uv sync --frozen in $WORK"
run env -C "$WORK" uv sync --frozen --quiet || die "uv sync failed in $WORK"
run env -C "$WORK" "$WORK/.venv/bin/pre-commit" install --install-hooks >/dev/null || die "pre-commit install failed in $WORK"
run git -C "$WORK" config gpg.format ssh
publish_shape "$WORK"
stop_after 5c

# ---------------------------------------------------------------- 6
say "Step 6 — re-create all 8 tags at their ORIGINAL tagger dates, in $WORK"
warn "Every tag's object hash changed, so every signature is broken — including"
warn "brief-freeze, whose tag-object hash is the trust root pinned in tag-roles.yaml."
note "GIT_COMMITTER_DATE preserves the tagger date, so bless_epoch and D0036's"
note "delegation-precedes-signature ordering are undisturbed. Each message is the original"
note "with its OLD signature block stripped — re-signing %(contents) whole would bury a"
note "stale signature inside the new message (found by the rehearsal, not by reading)."
OWNER_TAGS="$(owner_tags)"; BUILDER_TAGS="$(builder_tags)"
note "owner-signed:   $(printf '%s ' $OWNER_TAGS)"
note "builder-signed: $(printf '%s ' $BUILDER_TAGS)"
confirm "Re-create all 8 tags now? (4 owner + 4 builder key touches)" || die "stopped at your request"
TAGMAP="$SCRATCH/tagmap"; : > "$TAGMAP" 2>/dev/null || true
for t in $(git tag); do
    old_obj=$(git rev-parse "$t")
    old_cmt=$(git rev-list -1 "$t^{commit}")
    date=$(git for-each-ref "refs/tags/$t" --format='%(taggerdate:iso-strict)')
    if printf '%s\n' $OWNER_TAGS | grep -qx "$t"; then key="$OWNER_KEY"; who=owner
    elif printf '%s\n' $BUILDER_TAGS | grep -qx "$t"; then key="$BUILDER_KEY"; who=builder
    else die "$t is in neither signer class — tag-roles.yaml does not classify it"; fi
    if [ "$DRY" = 1 ]; then
        printf '   %-16s %s  %s\n' "$t" "$date" "$who"; continue
    fi
    # The new commit is looked up in the COMMIT-MAP, never by resolving the old sha inside
    # $WORK: after the rewrite the old sha does not exist there (D0182).
    new_cmt=$(awk -v o="$old_cmt" '$1==o {print $2}' "$MAP")
    [ -n "$new_cmt" ] || die "$t: commit $old_cmt not in the commit-map — cannot re-tag"
    msg="$SCRATCH/tagmsg-$t"
    git tag -l --format='%(contents)' "$t" | sed '/-----BEGIN SSH SIGNATURE-----/,$d' > "$msg"
    git -C "$WORK" tag -d "$t" >/dev/null
    GIT_COMMITTER_DATE="$date" git -C "$WORK" -c gpg.format=ssh -c user.signingkey="$key" \
        tag -s -F "$msg" "$t" "$new_cmt" || die "$t: signing failed"
    git -C "$WORK" -c gpg.format=ssh -c gpg.ssh.allowedSignersFile="$WORK/allowed_signers" \
        verify-tag "$t" >/dev/null 2>&1 || die "$t: re-signed but does NOT verify against allowed_signers"
    new_date=$(git -C "$WORK" for-each-ref "refs/tags/$t" --format='%(taggerdate:iso-strict)')
    [ "$new_date" = "$date" ] || die "$t: tagger date moved ($date -> $new_date) — bless_epoch would shift"
    new_obj="$(git -C "$WORK" rev-parse "$t")"
    printf '   %-16s %s  %-7s %s -> %s  verified, date unchanged\n' "$t" "$date" "$who" "${old_obj:0:12}" "${new_obj:0:12}"
    printf '%s %s %s %s %s\n' "$t" "$old_obj" "$new_obj" "$old_cmt" "$new_cmt" >> "$TAGMAP"
    rm -f "$msg"
done
if [ "$DRY" = 0 ]; then
    NEW_ROOT_OBJ="$(git -C "$WORK" rev-parse brief-freeze)"
    note "new brief-freeze tag object: $NEW_ROOT_OBJ -> trust_root.object"
    edit "trust_root_repin" "$WORK" <<PY
import re, pathlib
p = pathlib.Path("governance/tag-roles.yaml"); s = p.read_text()
s2, n = re.subn(r"(trust_root:\n  tag: brief-freeze\n  object: )[0-9a-f]{40}", r"\g<1>$NEW_ROOT_OBJ", s)
assert n == 1, "trust_root block not found"
p.write_text(s2); print("   tag-roles.yaml: trust_root.object repinned")
PY
    run manifest_refresh "$WORK" governance/tag-roles.yaml
    # The founding ratification enumerates m0-laws-freeze BY TAG OBJECT — in the custodian
    # (FOUNDING_TAGS, mechanically) and in DELEGATIONS.md (by prose, the text the trust root
    # blessed). Re-creating the tag changes that object, so both must follow it or the
    # custodian reports "builder tag predates its delegation's blessing and is not
    # enumerated" on the rewritten history — found by the fast rehearsal. The attestation
    # written at step 7 carries the old->new map for every tag, and is what both point at.
    read -r _t M0_OLD_OBJ M0_NEW_OBJ M0_OLD_CMT M0_NEW_CMT < <(grep '^m0-laws-freeze ' "$TAGMAP")
    edit "founding_tags_follow" "$WORK" <<PY
import pathlib, re
p = pathlib.Path("scripts/custodian.sh"); s = p.read_text()
old = 'FOUNDING_TAGS="$M0_OLD_OBJ"'
new = 'FOUNDING_TAGS="$M0_NEW_OBJ"   # m0-laws-freeze re-created at the publication rewrite of $TODAY_START (receipts/REWRITE-*.md); was $M0_OLD_OBJ'
if new.split("   #")[0] in s:
    print("   custodian.sh: FOUNDING_TAGS already follows the re-created tag")
else:
    assert s.count(old) == 1, "FOUNDING_TAGS with the pre-rewrite object not found"
    p.write_text(s.replace(old, new)); print("   custodian.sh: FOUNDING_TAGS follows the re-created m0-laws-freeze")
p = pathlib.Path("DELEGATIONS.md"); s = p.read_text()
marker = "Re-created at the publication history rewrite"
if marker in s:
    print("   DELEGATIONS.md: founding ratification already amended")
else:
    anchor = "that tag retroactively — by this explicit enumeration, and it alone."
    assert s.count(anchor) == 1, "founding-ratification sentence not found"
    s = s.replace(anchor, anchor + """
\$marker of $TODAY_START
(\`receipts/REWRITE-$TODAY_START.md\`, owner-signed under \`tannen-rewrite\`): the same tag,
tagger date and message now seal commit \`$M0_NEW_CMT\` as tag object
\`$M0_NEW_OBJ\`. That attestation carries the old->new map for every tag and
every commit; this enumeration covers the re-created object by reference to it.""")
    p.write_text(s); print("   DELEGATIONS.md: founding ratification amended to name the re-created object")
PY
    run manifest_refresh "$WORK" scripts/custodian.sh
    run manifest_refresh "$WORK" DELEGATIONS.md
    run env -C "$WORK" "$WORK/.venv/bin/python" -I -P scripts/check_tag_signers.py || die "check_tag_signers red after the re-tagging"
fi
stop_after 6

# ---------------------------------------------------------------- 7
say "Step 7 — the rewrite attestation (no receipt is ever re-signed)"
note "The five existing receipts stay BYTE-IDENTICAL. Editing an owner-signed attestation"
note "of a past moment to carry a new SHA is fabricating history. Instead: one new"
note "attestation carrying the COMPLETE map, and patch 02 resolves each recorded HEAD"
note "through it. The guard needs five pairs; an auditor needs all of them."
ATT_DAY="$(date +%Y-%m-%d)"
ATT="receipts/REWRITE-$ATT_DAY.md"
confirm "Write $ATT with the complete commit-map and sign it under tannen-rewrite?" || die "stopped at your request"
if [ "$DRY" = 0 ]; then
    {
        echo "# History rewrite — $ATT_DAY"
        echo
        echo "- decision: D0176 (Tier-C door external-bytes, owner-signed D0115) — the vendored"
        echo "  sibling snapshots excised from every commit of every ref before publication"
        echo "- performed by: $PKG/publication_sitting.sh, in a fresh clone; never in place"
        echo "- pre-rewrite HEAD: $PRE_HEAD (attested by receipts/$RECEIPT_DAY.md)"
        echo "- commits: $BEFORE before, $AFTER after, $dropped dropped"
        echo "- excised: $(printf 'concepts/snapshots/%s ' $SNAP_DIRS)"
        echo "- tags re-created at their original tagger dates (name: old object -> new object,"
        echo "  old commit -> new commit); the founding ratification in DELEGATIONS.md and the"
        echo "  custodian's FOUNDING_TAGS follow m0-laws-freeze's new object by reference to this:"
        awk '{print "  - " $1 ": " $2 " -> " $3 " (" $4 " -> " $5 ")"}' "$TAGMAP"
        echo "- scrubbed from every past version of concepts/provenance-ref-grammar.yaml,"
        echo "  CONCEPTS.md and the package README (D0180): the withdrawn source's section"
        echo "  title, pinned commit and content hash, each replaced by [withdrawn: D0180]"
        echo "- map (old -> new, complete — every commit, not only the receipt HEADs):"
        awk '$1 ~ /^[0-9a-f]{40}$/ && $2 ~ /^[0-9a-f]{40}$/ {print "  - " $1 " -> " $2}' "$MAP"
    } > "$WORK/$ATT"
    note "$(grep -c ' -> ' "$WORK/$ATT") map lines written"
fi
sign_owner "$WORK" "$ATT" tannen-rewrite
stop_after 7

# ---------------------------------------------------------------- 8, 10
say "Step 8 — custody over the rewritten tree"
confirm "gen_custody.py in $WORK and sign custody.sha256? (1 key touch; policy.yaml is unchanged since G)" || die "stopped at your request"
run env -C "$WORK" "$WORK/.venv/bin/python" -I -P scripts/gen_projections.py >/dev/null || die "gen_projections failed"
run env -C "$WORK" "$WORK/.venv/bin/python" -I -P scripts/gen_custody.py || die "gen_custody failed"
sign_owner "$WORK" governance/custody.sha256 tannen-custody
stop_after 8

say "Step 10 — sign D0176, the publication record"
warn "D0176 is status: blocked-on-owner. D0045 makes its fields immutable, so the flip to"
warn "accepted is a NEW record, not an edit — write it before signing if that is the shape"
warn "you want, and sign both. This signs D0176 as it stands."
confirm "Sign decisions/0176-*.yaml under tannen-decision? (1 key touch)" || die "stopped at your request"
D0176="$(cd "$WORK" 2>/dev/null && ls decisions/0176-*.yaml 2>/dev/null || ls decisions/0176-*.yaml)"
sign_owner "$WORK" "$D0176" tannen-decision
stop_after 10

# ---------------------------------------------------------------- C
say "Step C — commit the rewritten sitting"
commit_here "$WORK" "Publication: rewrite attestation, trust root repinned, custody re-signed, D0176 signed"
ff_master "$WORK"
stop_after C

# ---------------------------------------------------------------- 9
say "Step 9 — the full gate, on the REWRITTEN history"
note "This is the first time any of it has run against rewritten objects."
if [ "$FAST" = 1 ]; then
    warn "TANNEN_SITTING_FAST: skipping make verify on the rewritten history — the custodian still runs"
    run env -C "$WORK" bash scripts/custodian.sh --check-only || die "custody floor red"
elif confirm "Run 'make verify' and the custodian in $WORK now (~45 min)?"; then
    waiting "make verify in $WORK: pytest (~20 min) then check_decisions (~20 min)"
    run env -C "$WORK" make verify || die "verify red on the rewritten history"
    run env -C "$WORK" bash scripts/custodian.sh --check-only || die "custody floor red"
fi
stop_after 9

# ---------------------------------------------------------------- publish
say "Publish — and only now"
note "  gh repo create gfrmin/tannen --public --disable-wiki --source $WORK --remote origin"
note "  git -C $WORK push -u origin master        # the only branch; becomes the default"
note "  git -C $WORK push origin --tags           # the eight re-signed tags"
note "  gh repo view gfrmin/tannen --json defaultBranchRef"
warn "If GitHub created main: gh repo edit --default-branch master"
warn "                        git push origin --delete main"
note "Then watch CI's first-ever run — fetch-depth: 0 is load-bearing and untested in anger."
note "Then the real acceptance test, the first time this gate has run on any machine but"
note "this one:"
note "  git clone https://github.com/gfrmin/tannen /var/tmp/pubcheck && cd /var/tmp/pubcheck && make verify"
warn "~/git/tannen and its worktrees still hold the UN-rewritten history (with the bytes)."
warn "Whether the bare repo adopts $WORK's history is a separate decision; nothing here made it."

say "The sitting is closed"
note "workdir kept at $WORK — remove it once the push is confirmed"
note "driver scratch (tag map, scrub expressions) at $SCRATCH — nothing in it is secret; remove at will"
if [ "$DRY" != 1 ] && agent_holds "$OWNER_KEY" 2>/dev/null; then
    warn "The owner key is still loaded in ssh-agent. Unload it now:"
    warn "  ssh-add -d $OWNER_KEY"
fi
