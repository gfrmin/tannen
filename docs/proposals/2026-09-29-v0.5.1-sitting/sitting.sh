#!/usr/bin/env bash
# The v0.5.1 sitting (D0276 (3), D0277). Run by the owner, in a real terminal, from the root of
# ~/git/tannen on master:  bash docs/proposals/2026-09-29-v0.5.1-sitting/sitting.sh
# Three key touches (custody, the receipt inside custodian.sh, the tag), silent once the key is
# in the agent (D0185). Any failing step stops the rest. TANNEN_OWNER_KEY overrides the key path,
# for rehearsal only; custodian.sh reads the same variable.
set -euo pipefail
KEY=${TANNEN_OWNER_KEY:-$HOME/.ssh/tannen_owner}
P=docs/proposals/2026-09-29-v0.5.1-sitting
step(){ echo; echo "=== sitting: $*"; }

cd "$(git rev-parse --show-toplevel)"
step "preflight: clean tree on master at version 0.5.1"
test -z "$(git status --porcelain)" || { echo "the tree is not clean" >&2; exit 1; }
test "$(git branch --show-current)" = master || { echo "not on master" >&2; exit 1; }
grep -qx 'version = "0.5.1"' pyproject.toml || { echo "pyproject.toml is not 0.5.1" >&2; exit 1; }

step "the owner key into the agent (removed again on exit)"
ssh-add "$KEY"
trap 'ssh-add -d "$KEY" >/dev/null 2>&1 || true' EXIT

step "apply the version-tag role and the README pin"
git apply "$P/tag-roles-version.patch" "$P/readme.patch"
grep -v '  governance/tag-roles.yaml$' MANIFEST.sha256 > MANIFEST.tmp
sha256sum governance/tag-roles.yaml >> MANIFEST.tmp
mv MANIFEST.tmp MANIFEST.sha256

step "regenerate and re-sign custody (key touch 1)"
.venv/bin/python -I -P scripts/gen_custody.py
rm -f governance/custody.sha256.sig
ssh-keygen -Y sign -f "$KEY" -n tannen-custody governance/custody.sha256
.venv/bin/python -I -P scripts/check_manifest.py

step "custodian and the attention receipt (key touch 2)"
TANNEN_OWNER_KEY="$KEY" bash scripts/custodian.sh

step "projections and the sitting commit (the hooks take about 12 minutes)"
make projections
git add -A
git commit -m "v0.5.1 sitting: the version-tag role, the README pin, the attention receipt renewed (D0276)"

step "sign v0.5.1 (key touch 3) and verify it"
M=$(mktemp)
bash "$P/tag-message.sh" > "$M"
git -c gpg.format=ssh -c user.signingkey="$KEY" tag -s v0.5.1 -F "$M"
git -c gpg.format=ssh -c gpg.ssh.allowedSignersFile="$PWD/allowed_signers" verify-tag v0.5.1
.venv/bin/python -I -P scripts/check_tag_signers.py
bash scripts/custodian.sh --check-only

step "push master and the tag"
git push origin master v0.5.1

step "done: now read both CI runs, for master and for v0.5.1"
