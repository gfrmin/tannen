#!/usr/bin/env bash
# publish_push.sh — the steps AFTER the sitting: create the repository, push, confirm the
# default branch, watch CI's first run, and verify a fresh clone on this machine.
#
# WHY THIS IS A SCRIPT. The sitting narrates these and leaves them to the keyboard. They are
# therefore typed at minute ninety-five, after fourteen signatures, which is precisely when
# `push --all` instead of `push -u origin master` costs you a repository whose default branch
# is wrong (D0186 is that same class of mistake, found in the narration rather than in a run).
#
# THIS IS THE ONE SCRIPT IN THE PACKAGE THAT SENDS BYTES OUT. It creates a PUBLIC repository
# and pushes a history to it. That is Tier-C door `external-bytes`, opened by owner-signed
# D0115 and executed by D0176 — but the act is still yours: it requires --yes, it is never
# invoked by the driver, and --dry-run prints every command without running any of them.
#
#   publish_push.sh --work <the sitting's rewrite clone> [--slug gfrmin/tannen] --yes
#   publish_push.sh --work <dir> --dry-run
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"   # $PWD is the repo root when run from there
SLUG="${TANNEN_PUBLISH_SLUG:-gfrmin/tannen}" ; WORK="" ; YES=0 ; DRY=0
while [ $# -gt 0 ]; do
    case "$1" in
        --work) WORK="$2"; shift 2 ;;
        --slug) SLUG="$2"; shift 2 ;;
        --yes)  YES=1; shift ;;
        --dry-run) DRY=1; shift ;;
        *) echo "usage: $0 --work <dir> [--slug owner/name] (--yes | --dry-run)" >&2; exit 2 ;;
    esac
done
say()  { printf '\n\033[1m== %s\033[0m\n' "$*"; }
note() { printf '   %s\n' "$*"; }
warn() { printf '   \033[33m! %s\033[0m\n' "$*"; }
die()  { printf '\npublish: STOP — %s\n' "$*" >&2; exit 1; }
run()  { [ "$DRY" = 1 ] && { note "[dry-run] $*"; return 0; }; "$@"; }

[ -n "$WORK" ] || die "no --work: the rewrite clone the sitting left (it prints the path at the end)"
[ "$YES" = 1 ] || [ "$DRY" = 1 ] || die "refusing without --yes: this creates a PUBLIC repository at $SLUG"
git -C "$WORK" rev-parse --git-dir >/dev/null 2>&1 || die "$WORK is not a git repository"

say "What is about to become public"
note "source:      $WORK"
note "destination: https://github.com/$SLUG  (PUBLIC)"
note "commits:     $(git -C "$WORK" rev-list --count HEAD)"
note "branch:      $(git -C "$WORK" rev-parse --abbrev-ref HEAD)"
note "tags:        $(git -C "$WORK" tag | tr '\n' ' ')"

say "Refusing to publish something that is not the sitting's output"
[ -z "$(git -C "$WORK" status --porcelain)" ] || die "$WORK has uncommitted changes"
N=$(git -C "$WORK" for-each-ref --format=x refs/heads | wc -l)
# This is the guard that caught D0189: the sitting's own publish_shape left four branches,
# and refusing here cost a diagnosis instead of a public repository with the wrong shape.
[ "$N" = 1 ] || die "$WORK has $N branches; the sitting leaves exactly one, master (D0186, D0189)"
[ "$(git -C "$WORK" rev-parse --abbrev-ref HEAD)" = master ] \
    || die "$WORK is not on master; the first push decides the public default branch"
git -C "$WORK" ls-tree --name-only HEAD receipts/ | grep -q 'REWRITE-' \
    || die "no rewrite attestation in HEAD — this is not the published history the sitting made"
note "one branch, master, with a rewrite attestation in its tree"
for t in $(git -C "$WORK" tag); do
    ( cd "$WORK" && git -c gpg.format=ssh -c gpg.ssh.allowedSignersFile=allowed_signers \
        verify-tag "$t" >/dev/null 2>&1 ) || die "tag $t does not verify — do not publish this"
done
note "all $(git -C "$WORK" tag | wc -l) tags verify against allowed_signers"
gh auth status >/dev/null 2>&1 || die "gh is not authenticated"
gh repo view "$SLUG" --json name >/dev/null 2>&1 && die "$SLUG already exists"
note "$SLUG does not exist yet"

say "Creating the repository (no push yet: the FIRST push decides the default branch)"
run gh repo create "$SLUG" --public --disable-wiki --source "$WORK" --remote origin \
    || die "gh repo create failed"

say "Pushing master first, then the tags"
run git -C "$WORK" push -u origin master || die "pushing master failed"
run git -C "$WORK" push origin --tags     || die "pushing tags failed"

say "The default branch must be master, never main"
if [ "$DRY" = 0 ]; then
    DEF=$(gh repo view "$SLUG" --json defaultBranchRef --jq .defaultBranchRef.name 2>/dev/null)
    note "default branch: $DEF"
    if [ "$DEF" != master ]; then
        warn "fixing it"
        run gh repo edit "$SLUG" --default-branch master || die "could not set the default branch"
        git -C "$WORK" ls-remote --heads origin main | grep -q main \
            && run git -C "$WORK" push origin --delete main
    fi
fi

say "CI's first-ever run — fetch-depth: 0 is load-bearing and has never executed anywhere"
if [ "$DRY" = 1 ]; then note "[dry-run] gh run watch --exit-status"
else
    for _ in 1 2 3 4 5 6; do
        RID=$(gh run list --repo "$SLUG" --limit 1 --json databaseId --jq '.[0].databaseId' 2>/dev/null)
        [ -n "$RID" ] && break
        note "waiting for the workflow to appear..."; sleep 10
    done
    if [ -n "${RID:-}" ]; then
        gh run watch "$RID" --repo "$SLUG" --exit-status \
            && note "CI is green" \
            || warn "CI is RED — fix and push again. This fails forward; nothing is lost."
    else
        warn "no workflow run appeared; check https://github.com/$SLUG/actions yourself"
    fi
fi

say "The real acceptance test: this gate on a machine that is not the one that built it"
CHECK="${TMPDIR:-/var/tmp}/tannen-pubcheck-$$"
if [ "$DRY" = 1 ]; then note "[dry-run] git clone https://github.com/$SLUG $CHECK && make verify"
else
    run git clone --quiet "https://github.com/$SLUG" "$CHECK" || die "cloning the published repo failed"
    note "cloned to $CHECK; running make verify (~45 min)"
    ( cd "$CHECK" && uv sync --frozen --quiet && make verify ) \
        && note "make verify is GREEN on a fresh clone of the published repository" \
        || warn "make verify is RED on the fresh clone — read $CHECK before adopting anything"
fi

say "Then, and only then"
note "  bash $HERE/adopt_published_history.sh --from https://github.com/$SLUG --ci-green"
note "and afterwards:  ssh-add -d \${TANNEN_OWNER_KEY:-\$HOME/.ssh/tannen_owner}"
