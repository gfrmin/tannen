#!/usr/bin/env bash
# Build the tag-roles-derived poison fixture. RUN AT THE BOUNDARY SITTING, never shipped
# pre-built: a bundle is opaque, and an opaque artifact the owner did not watch being made
# is one taken on trust (conferral ruling 6 — the same rule custodian-tag-signer/ follows).
#
# WHAT IT PROVES (D0205). required_tags is DERIVED from docs/specs/*.md: brief-freeze once
# the owner key is enrolled, <m>-laws-freeze for every milestone with a spec, <m>-close for
# every milestone whose successor has a spec. This tree carries specs m0..m4 and a bundle
# carrying EVERY tag that rule derives EXCEPT m3-close, each signed by the principal its
# class requires. So the guard has exactly one thing to say — `required tag missing:
# m3-close` — and a guard that still read a hand-written list would say nothing at all,
# because a list that lags one boundary does not contain m3-close.
#
# NEITHER REAL KEY IS USED. Two throwaway ed25519 keys are minted in a temp dir, their
# public halves enrolled in this fixture's own allowed_signers as owner@tannen and
# builder@tannen, and the private halves deleted on exit. The fixture must VERIFY — what
# has to fail is the derived requirement, not a signature or a principal.
#
# The tag list is derived from this directory's own docs/specs/, the way the guard derives
# it, so the only name written down here is the one deliberately left out.
#
# Idempotent: every run replaces allowed_signers, governance/tag-roles.yaml and repo.bundle.
# Writes nothing outside this directory except its own temp dir.
#
# Usage:  bash make-fixture.sh
set -euo pipefail
# A hook exports GIT_DIR, and GIT_DIR beats `git -C` — without this the tags below would be
# minted in whatever repository invoked the script.
unset GIT_DIR GIT_INDEX_FILE GIT_WORK_TREE GIT_OBJECT_DIRECTORY GIT_COMMON_DIR

OMIT="m3-close"   # the one derived tag the bundle must not carry

here="$(cd "$(dirname "$0")" && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

command -v ssh-keygen >/dev/null || { echo "ssh-keygen not on PATH" >&2; exit 1; }
ssh-keygen -q -t ed25519 -N '' -C owner@tannen   -f "$tmp/owner"
ssh-keygen -q -t ed25519 -N '' -C builder@tannen -f "$tmp/builder"
{
    printf 'owner@tannen %s\n'   "$(cut -d' ' -f1,2 "$tmp/owner.pub")"
    printf 'builder@tannen %s\n' "$(cut -d' ' -f1,2 "$tmp/builder.pub")"
} > "$here/allowed_signers"

# The milestones, read off the specs exactly as the guard reads them: `m<digits>.md` only.
nums=()
for spec in "$here"/docs/specs/m*.md; do
    stem="$(basename "$spec" .md)"
    case "${stem#m}" in ''|*[!0-9]*) continue ;; esac
    nums+=("${stem#m}")
done
[ "${#nums[@]}" -gt 0 ] || { echo "no docs/specs/m<N>.md under $here" >&2; exit 1; }
mapfile -t nums < <(printf '%s\n' "${nums[@]}" | sort -n)
has_spec() { local n; for n in "${nums[@]}"; do [ "$n" = "$1" ] && return 0; done; return 1; }

repo="$tmp/repo"
git init -q -b master "$repo"
git -C "$repo" config user.name  "poison fixture"
git -C "$repo" config user.email "fixture@invalid"
git -C "$repo" config gpg.format ssh
git -C "$repo" config commit.gpgsign false
printf 'poison fixture: every derived required tag except %s\n' "$OMIT" > "$repo/README"
git -C "$repo" add README
git -C "$repo" commit -q -m "poison fixture root"

tag_as() {   # <owner|builder> <tag>
    [ "$2" = "$OMIT" ] && return 0
    git -C "$repo" -c user.signingkey="$tmp/$1" \
        tag -s "$2" -m "$2 (poison fixture: tag-roles-derived)"
}
tag_as owner brief-freeze
for n in "${nums[@]}"; do
    tag_as builder "m$n-laws-freeze"
    has_spec $((n + 1)) && tag_as owner "m$n-close"
done

# The trust-root pin must name THIS bundle's brief-freeze, or the fixture would also fail
# "trust root re-issued" — a second reason, which is the thing a poison fixture must not have.
object="$(git -C "$repo" rev-parse refs/tags/brief-freeze)"
cat > "$here/governance/tag-roles.yaml" <<YAML
# Poison fixture signer-role table (tag-roles-derived). Written by make-fixture.sh at the
# sitting: the trust-root pin is the brief-freeze object of the bundle generated beside it.
version: 1
trust_root:
  tag: brief-freeze
  object: "$object"
  signer: owner
roles:
  - {pattern: brief-freeze, signer: owner}
  - {pattern: "*-laws-freeze", signer: builder}
  - {pattern: "*-close", signer: owner}
  - {pattern: "amendment-*", signer: owner}
  - {pattern: "receipt-*", signer: owner}
# Derived, never enumerated (D0205). Empty, as the real table is.
required_tags: []
unknown: refuse
YAML

rm -f "$here/repo.bundle"
git -C "$repo" bundle create -q "$here/repo.bundle" --all
echo "wrote $here/repo.bundle ($(git -C "$repo" tag | wc -l) tags; omitted: $OMIT)"
echo "expect exactly one violation: 'required tag missing: $OMIT'"
