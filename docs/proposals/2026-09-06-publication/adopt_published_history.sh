#!/usr/bin/env bash
# adopt_published_history.sh — point the LOCAL repository at the published, rewritten history.
#
# WHEN. After `publication_sitting.sh` has run, after the push, and after CI has gone green on
# GitHub. Not before: adopting a history that CI rejects is the one version of this that is
# genuinely awkward to undo. The script refuses to run without --ci-green, which is you
# asserting you looked.
#
# WHY IT IS NOT `git fetch && git reset --hard origin/master`. The published repository carries
# ONE branch, master, and eight tags — it has no m0/m1/m2/m3 refs at all, because the rewrite
# clone was a clone of a worktree and git-filter-repo drops remote-tracking refs (D0186). Every
# local branch must therefore be RESOLVED THROUGH THE COMMIT MAP in the rewrite attestation,
# which is exactly what that owner-signed artifact exists for (D0176). A branch whose tip is not
# in the map is not in the published history, and this script stops rather than guessing.
#
# WHAT IT NEVER DOES: touch the stash (shared across worktrees), delete anything not backed up
# first, or run while any worktree has uncommitted work. Every pre-adoption ref is copied under
# refs/backup/pre-publication-<date>/ BEFORE anything moves, so the old history stays reachable
# and `git log refs/backup/...` resolves every pre-publication SHA in all 186 decision records.
#
#   adopt_published_history.sh --from <url|path> --ci-green [--repo <bare>] [--dry-run]
#
set -euo pipefail

SRC="" ; CI_GREEN=0 ; DRY=0 ; REPO=""
while [ $# -gt 0 ]; do
    case "$1" in
        --from)     SRC="$2"; shift 2 ;;
        --repo)     REPO="$2"; shift 2 ;;
        --ci-green) CI_GREEN=1; shift ;;
        --dry-run)  DRY=1; shift ;;
        *) echo "usage: $0 --from <url|path> --ci-green [--repo <bare>] [--dry-run]" >&2; exit 2 ;;
    esac
done

say()  { printf '\n\033[1m== %s\033[0m\n' "$*"; }
note() { printf '   %s\n' "$*"; }
warn() { printf '   \033[33m! %s\033[0m\n' "$*"; }
die()  { printf '\nadopt: STOP — %s\n' "$*" >&2; exit 1; }
run()  { [ "$DRY" = 1 ] && { note "[dry-run] $*"; return 0; }; "$@"; }

[ -n "$SRC" ] || die "no source: --from <url of the published repo, or a path to the rewrite clone>"
[ "$CI_GREEN" = 1 ] || die "refusing without --ci-green: push first, watch CI's first run, then come back"
REPO="${REPO:-$(git rev-parse --git-common-dir 2>/dev/null)}"
REPO="$(cd "$REPO" && pwd)"
git -C "$REPO" rev-parse --git-dir >/dev/null 2>&1 || die "not a git repository: $REPO"
TODAY="$(date +%Y-%m-%d)"
BACKUP="refs/backup/pre-publication-$TODAY"
NS="refs/publication-incoming"

say "The repository, and every worktree on it"
note "repository: $REPO"
# `git worktree list` includes the BARE repository itself. It has no working tree, so
# `status` fails there and `|| true` would report it as clean, and the branch-moving loop
# below would then try to `git reset --hard` inside it. Filter it out by asking.
WORKTREES=()
while IFS= read -r line; do
    case "$line" in worktree\ *) w="${line#worktree }"
        [ "$(git -C "$w" rev-parse --is-bare-repository 2>/dev/null)" = true ] && continue
        WORKTREES+=("$w") ;;
    esac
done < <(git -C "$REPO" worktree list --porcelain)
[ "${#WORKTREES[@]}" -gt 0 ] || note "no non-bare worktrees; every branch moves by ref"
for w in "${WORKTREES[@]}"; do
    b=$(git -C "$w" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '<detached>')
    st=$(git -C "$w" status --porcelain 2>/dev/null || true)
    if [ -n "$st" ]; then
        printf '%s\n' "$st" | sed 's/^/     /' | head -10
        die "worktree $w is not clean. Adoption resets it; commit or discard first."
    fi
    note "clean: $w  (on $b)"
done
# The stash stack is shared across worktrees and this script must not be the thing that
# silently invalidates someone else's entry. Report, never touch.
if [ -n "${WORKTREES[0]:-}" ] && s=$(git -C "${WORKTREES[0]}" stash list 2>/dev/null) && [ -n "$s" ]; then
    warn "the shared stash stack is not empty; nothing here touches it, but entries were made"
    warn "against the OLD history and will apply to the new one only by luck:"
    printf '%s\n' "$s" | sed 's/^/     /'
fi

say "Fetching the published history into $NS (nothing local moves yet)"
run git -C "$REPO" fetch --quiet "$SRC" \
    "+refs/heads/master:$NS/master" "+refs/tags/*:$NS/tags/*" || die "fetch from $SRC failed"
NEW_HEAD=$(git -C "$REPO" rev-parse "$NS/master" 2>/dev/null) || die "no master in $SRC"
note "published master: $NEW_HEAD"
note "published tags:   $(git -C "$REPO" for-each-ref --format='%(refname:strip=3)' "$NS/tags" | tr '\n' ' ')"

say "The rewrite attestation, and its signature"
ATT=$(git -C "$REPO" ls-tree --name-only "$NS/master" receipts/ | grep 'REWRITE-' | head -1) \
    || die "no receipts/REWRITE-*.md in the published history — this is not a rewritten publication"
note "attestation: $ATT"
TMP=$(mktemp -d "${TMPDIR:-/var/tmp}/tannen-adopt.XXXXXX")
trap 'rm -rf "$TMP"' EXIT
git -C "$REPO" show "$NS/master:$ATT"          > "$TMP/att"      || die "cannot read $ATT"
git -C "$REPO" show "$NS/master:$ATT.sig"      > "$TMP/att.sig"  || die "cannot read $ATT.sig"
git -C "$REPO" show "$NS/master:allowed_signers" > "$TMP/signers" || die "cannot read allowed_signers"
ssh-keygen -Y verify -f "$TMP/signers" -I owner@tannen -n tannen-rewrite -s "$TMP/att.sig" < "$TMP/att" \
    || die "the attestation does NOT verify under tannen-rewrite — do not adopt this history"
note "attestation verifies under tannen-rewrite for owner@tannen"

# old -> new, one pair per line, exactly as the driver wrote it.
grep -oP '^\s*-\s*\K[0-9a-f]{40} -> [0-9a-f]{40}' "$TMP/att" | tr -d ' ' | sed 's/->/ /' > "$TMP/map"
MAPPED=$(wc -l < "$TMP/map")
[ "$MAPPED" -gt 0 ] || die "the attestation carries no old -> new pairs"
note "$MAPPED commits in the map"
remap() { awk -v k="$1" '$1==k {print $2; found=1} END{exit !found}' "$TMP/map"; }

say "Resolving every local ref (still nothing moved)"
# TWO RULES, and the difference matters — the rehearsal found it by running the guards on the
# result rather than by checking that the refs moved. A HISTORICAL branch (m0, m1, m2) marks
# a point in the past, so it resolves THROUGH THE MAP to the same point in the rewritten
# history. The WORKING branch does not: the sitting itself makes two commits — the pre-rewrite
# commit A and the post-rewrite commit C — that exist only in the published history and have
# no pre-publication counterpart to map from. Remapping master lands it two commits before the
# publication: no rewrite attestation in the tree, an unpatched check_receipts, the old trust
# root still pinned in tag-roles.yaml — while the tags are the re-signed ones. All three
# guards go red, and the repository looks broken when it is merely at the wrong commit.
# So master, and any branch that was sitting on master's tip, takes the PUBLISHED head.
OLD_MASTER=$(git -C "$REPO" rev-parse -q --verify master 2>/dev/null || true)
# D0190 — the rule above assumes master IS the sitting's commit A. That stopped being true the
# moment a commit landed after the sitting, and D0189's own commit did exactly that, the same
# morning. Taking the published head then DISCARDS every post-sitting commit from master. The
# backup refs below would still hold them, so nothing is destroyed — but master would come out
# short and nothing would say so, which is the silent half of a data loss. Any commit on master
# the published map does not know is post-sitting work: stop, and let it be replayed.
if [ -n "$OLD_MASTER" ]; then
    AFTER=""
    while read -r c; do
        remap "$c" >/dev/null 2>&1 || AFTER="$AFTER $c"
    done < <(git -C "$REPO" rev-list master --not "$NEW_HEAD")
    if [ -n "$AFTER" ]; then
        note "on master, but not in the published history:"
        for c in $AFTER; do note "   $(git -C "$REPO" log -1 --format='%h %s' "$c")"; done
        set -- $AFTER
        die "master carries $# commit(s) made AFTER the sitting, which adoption would drop.
Replay them onto the published head, PUSH, and only then re-run this script — a cherry-pick
gets a NEW sha that is no more in the map than the original was, so replaying alone does not
satisfy this guard; being in the published history is what does (D0192):
    git -C $REPO branch post-publication $NEW_HEAD
    git -C $REPO checkout post-publication
    git -C $REPO cherry-pick $(set -- $AFTER; echo "$*" | tr ' ' '\n' | tac | tr '\n' ' ')
    git -C $REPO branch -f master post-publication
    git -C $REPO push origin master
(each cherry-pick pays the pre-commit hooks). The published repository is unaffected either
way; this script has moved nothing yet."
    fi
fi
declare -A NEWTIP
for b in $(git -C "$REPO" for-each-ref --format='%(refname:strip=2)' refs/heads); do
    old=$(git -C "$REPO" rev-parse "$b")
    if [ "$b" = master ] || { [ -n "$OLD_MASTER" ] && [ "$old" = "$OLD_MASTER" ]; }; then
        NEWTIP["$b"]="$NEW_HEAD"
        note "$(printf '%-8s' "$b") ${old:0:8} -> ${NEW_HEAD:0:8}  (the published head; it carries the sitting's own commits)"
    elif new=$(remap "$old"); then
        NEWTIP["$b"]="$new"; note "$(printf '%-8s' "$b") ${old:0:8} -> ${new:0:8}  (through the map)"
    else
        die "branch $b (${old:0:8}) is NOT in the published history's map. Adoption would orphan it."
    fi
done

say "Backing up every existing ref under $BACKUP"
while read -r sha ref; do
    run git -C "$REPO" update-ref "$BACKUP/${ref#refs/}" "$sha"
done < <(git -C "$REPO" for-each-ref --format='%(objectname) %(refname)' refs/heads refs/tags)
note "$(git -C "$REPO" for-each-ref --format=x "$BACKUP" 2>/dev/null | wc -l) refs backed up"
note "the pre-publication history stays reachable: git log $BACKUP/heads/master"

say "Moving the branches"
for b in "${!NEWTIP[@]}"; do
    wt=""
    for w in "${WORKTREES[@]}"; do
        [ "$(git -C "$w" rev-parse --abbrev-ref HEAD 2>/dev/null || true)" = "$b" ] && { wt="$w"; break; }
    done
    if [ -n "$wt" ]; then
        # `git branch -f` REFUSES a branch checked out in a worktree, so move it from inside
        # the worktree, which moves the ref and the working tree together.
        run git -C "$wt" reset --hard --quiet "${NEWTIP[$b]}" || die "reset failed in $wt"
        note "$b: worktree $wt reset to ${NEWTIP[$b]:0:8}"
    else
        run git -C "$REPO" branch -f "$b" "${NEWTIP[$b]}" || die "could not move $b"
        note "$b: moved to ${NEWTIP[$b]:0:8}"
    fi
done

say "Replacing the tags with the re-signed ones"
for t in $(git -C "$REPO" for-each-ref --format='%(refname:strip=3)' "$NS/tags"); do
    run git -C "$REPO" update-ref "refs/tags/$t" "$(git -C "$REPO" rev-parse "$NS/tags/$t")"
    note "tag $t replaced"
done

say "Cleaning up the incoming namespace"
while read -r _ ref; do run git -C "$REPO" update-ref -d "$ref"; done \
    < <(git -C "$REPO" for-each-ref --format='%(objectname) %(refname)' "$NS")

say "Verifying the adopted repository"
V="${WORKTREES[0]:-}"
if [ "$DRY" = 1 ]; then note "[dry-run] would run the guards in $V"
elif [ -n "$V" ] && [ -x "$V/.venv/bin/python" ]; then
    ( cd "$V" && git -c gpg.format=ssh -c gpg.ssh.allowedSignersFile=allowed_signers \
        verify-tag brief-freeze >/dev/null 2>&1 ) || die "brief-freeze does not verify after adoption"
    note "brief-freeze verifies"
    ( cd "$V" && .venv/bin/python -I -P scripts/check_receipts.py ) || die "check_receipts red after adoption"
    ( cd "$V" && .venv/bin/python -I -P scripts/check_tag_signers.py ) || die "check_tag_signers red after adoption"
    ( cd "$V" && bash scripts/custodian.sh --check-only ) || die "custodian red after adoption"
else
    warn "no venv found in $V — run 'make verify' there yourself before trusting this"
fi

say "Adopted"
note "Every pre-publication ref is still reachable under $BACKUP."
note "To undo: git -C $REPO for-each-ref $BACKUP, then reset each branch/worktree back."
note "Once you are sure, months from now, the backup refs can be deleted — not before."
