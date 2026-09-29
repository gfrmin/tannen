# The v0.5.1 sitting

**Status:** drafted by the builder. It executes the items D0276 (3) queued. Doors and signatures
in one `&&` chain, rehearsed once (D0267 ruling 3).

## What it signs and applies

1. **The version-tag role** (`tag-roles-version.patch`). `governance/tag-roles.yaml` gains
   `v[0-9]*`, signed by the owner. Its note says that a version tag attests the tree at the
   version `pyproject.toml` carries and is not a milestone gate. The note holds by
   construction: the receipt clock counts only `brief-freeze`, `*-laws-freeze` and `*-close`
   (`BOUNDARY_TAG_RE`, `scripts/_gov.py`). Today the table refuses a `v0.5.1` tag as an
   unknown class (`unknown: refuse`). `tag-roles.yaml` is frozen and custody-set, so its
   MANIFEST row is refreshed, and custody is regenerated and re-signed.
2. **The attention receipt**, taken by `scripts/custodian.sh`. The receipt has been stale since
   2026-09-26. A version tag starts no clock, so the renewed receipt stays fresh until the next
   milestone boundary plus 7 days.
3. **The README pin** (`readme.patch`). The example pin becomes `@v0.5.1`. It lands in the
   sitting's commit, so the sentence is true once it is on master.
4. **`v0.5.1`**, owner-signed, last. It points at the sitting's commit, whose `pyproject.toml`
   is 0.5.1; the builder bumped the version in the preceding commit, as 2ec9ddb did for 0.5.0.
   `tag-message.sh` refuses a dirty tree and any other version.

## The chain

Run it in `~/git/tannen` on `master`, in a real terminal, with the owner key in the agent (D0185).
There are three key touches: custody, the receipt (inside `custodian.sh`) and the tag. The push
carries the builder's draft commit as well; CI is the gate (D0267 ruling 3).

```sh
cd ~/git/tannen \
&& ssh-add ~/.ssh/tannen_owner \
&& test -z "$(git status --porcelain)" && test "$(git branch --show-current)" = master \
&& grep -qx 'version = "0.5.1"' pyproject.toml \
&& P=docs/proposals/2026-09-29-v0.5.1-sitting \
&& git apply "$P/tag-roles-version.patch" "$P/readme.patch" \
&& grep -v '  governance/tag-roles.yaml$' MANIFEST.sha256 > MANIFEST.tmp && sha256sum governance/tag-roles.yaml >> MANIFEST.tmp && mv MANIFEST.tmp MANIFEST.sha256 \
&& .venv/bin/python -I -P scripts/gen_custody.py \
&& rm -f governance/custody.sha256.sig \
&& ssh-keygen -Y sign -f ~/.ssh/tannen_owner -n tannen-custody governance/custody.sha256 \
&& .venv/bin/python -I -P scripts/check_manifest.py \
&& bash scripts/custodian.sh \
&& make projections \
&& git add -A && git commit -m "v0.5.1 sitting: the version-tag role, the README pin, the attention receipt renewed (D0276)" \
&& M=$(mktemp) && bash "$P/tag-message.sh" > "$M" \
&& git -c gpg.format=ssh -c user.signingkey="$HOME/.ssh/tannen_owner" tag -s v0.5.1 -F "$M" \
&& git -c gpg.format=ssh -c gpg.ssh.allowedSignersFile="$PWD/allowed_signers" verify-tag v0.5.1 \
&& .venv/bin/python -I -P scripts/check_tag_signers.py \
&& bash scripts/custodian.sh --check-only \
&& git push origin master v0.5.1 \
&& ssh-add -d ~/.ssh/tannen_owner
```

Then read every CI run the push starts, for `master` and for the tag.

## After it

The pitch to the first dependent is unblocked (D0276 (4)). It pins `v0.5.1`, and any PR to the
sibling goes through the `external-bytes` door.
