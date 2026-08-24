#!/usr/bin/env bash
# Build the close-tag poison fixture. RUN BY THE OWNER, ONCE, at the boundary sitting.
#
# The other poison fixtures are directories of files. This one cannot be: the
# violation is a *signed git object* (a builder-signed `*-close` tag), so the fixture
# is a git bundle carrying a throwaway repo whose only interesting content is that
# tag. The builder cannot generate it — the red team must not create tags — and it
# needs the builder key, so the owner runs this script and commits `repo.bundle`.
#
# Usage:  bash make-fixture.sh [BUILDER_KEY]     (default ~/.ssh/tannen_builder)
set -euo pipefail
key="${1:-$HOME/.ssh/tannen_builder}"
out="$(cd "$(dirname "$0")" && pwd)/repo.bundle"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

git -C "$tmp" init -q .
git -C "$tmp" config user.name  "builder"
git -C "$tmp" config user.email "builder@tannen"
git -C "$tmp" config gpg.format ssh
git -C "$tmp" config user.signingkey "$key"
printf 'poison fixture: a builder-signed milestone close tag\n' >"$tmp/README"
git -C "$tmp" add README
git -C "$tmp" commit -q -m "poison fixture root"
# The violation: a *-close tag signed by the BUILDER key. D0049 says close tags
# anchor owner presence and stay owner-signed; the custodian does not check the
# signer's principal against the tag's kind today.
git -C "$tmp" tag -s -m "poison: builder-signed close tag (D0049)" poison-m9-close
git -C "$tmp" bundle create -q "$out" --all
echo "wrote $out"
echo "verify with: git -C \$(mktemp -d) clone -q $out repo && git -C repo tag -l"
