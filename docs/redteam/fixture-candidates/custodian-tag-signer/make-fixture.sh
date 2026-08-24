#!/usr/bin/env bash
# Build the tag-signer poison fixture. RUN AT THE BOUNDARY SITTING (the builder key
# signs the poison tag; the bundle then lands in tests/poison/, which is author-key
# territory, so the owner installs it).
#
# The other poison fixtures are directories of files. This one cannot be: the violation
# is a *signed git object*. The fixture is therefore a one-file git bundle, which
# scripts/check_tag_signers.py knows how to clone (`--repo …/repo.bundle`).
#
# ONE fixture, TWO teeth — both holes the M0 red team found in the same guard:
#   * a builder-signed `*-close` tag        -> "tag signed by the wrong principal"  (D0049)
#   * a repo whose trust root is gone       -> "trust root MISSING" / "required tag
#                                              missing"                             (RT-15)
# The bundle carries the bad close tag and NO brief-freeze, so one clone exercises both.
#
# Usage:  bash make-fixture.sh [BUILDER_KEY]     (default ~/.ssh/tannen_builder)
set -euo pipefail
key="${1:-$HOME/.ssh/tannen_builder}"
here="$(cd "$(dirname "$0")" && pwd)"
repo_root="$(cd "$here/../../../.." && pwd)"
out="$here/repo.bundle"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

[ -f "$key" ] || { echo "no builder key at $key" >&2; exit 1; }

# The signer set the fixture is checked against: the REAL public halves, copied from the
# repo's own allowed_signers. The fixture must *verify* — what has to fail is the
# principal-vs-tag-class rule, not the signature. Both principals are enrolled, which is
# also what makes owner_key_enrolled() true, and hence the missing trust root a MISSING
# rather than a not-yet.
grep -E '^(builder|owner)@tannen ' "$repo_root/allowed_signers" > "$here/allowed_signers"
grep -q '^owner@tannen ' "$here/allowed_signers" || {
    echo "owner@tannen is not enrolled in $repo_root/allowed_signers" >&2; exit 1; }

cat > "$here/governance/tag-roles.yaml" <<'YAML'
# Poison fixture signer-role table. Same shape as governance/tag-roles.yaml; the
# trust-root object is a hash that exists in no repo, so the pin cannot accidentally
# match the bundle.
version: 1
trust_root:
  tag: brief-freeze
  object: "0000000000000000000000000000000000000000"
  signer: owner
roles:
  - {pattern: brief-freeze, signer: owner}
  - {pattern: "*-laws-freeze", signer: builder}
  - {pattern: "*-close", signer: owner}
  - {pattern: "amendment-*", signer: owner}
  - {pattern: "receipt-*", signer: owner}
required_tags:
  - brief-freeze
unknown: refuse
YAML

git -C "$tmp" init -q .
git -C "$tmp" config user.name  "builder"
git -C "$tmp" config user.email "builder@tannen"
git -C "$tmp" config gpg.format ssh
git -C "$tmp" config user.signingkey "$key"
printf 'poison fixture: a builder-signed milestone close tag, in a repo with no trust root\n' >"$tmp/README"
git -C "$tmp" add README
git -C "$tmp" commit -q -m "poison fixture root"
git -C "$tmp" tag -s -m "poison: builder-signed close tag (D0049)" poison-m9-close
git -C "$tmp" bundle create -q "$out" --all
echo "wrote $out"
echo
echo "both teeth, from the repo root:"
echo "  uv run python scripts/check_tag_signers.py --root $here --repo $here/repo.bundle"
echo "expect: 'trust root MISSING', 'required tag missing: brief-freeze',"
echo "        'tag signed by the wrong principal (expected owner@tannen, got builder@tannen)'"
