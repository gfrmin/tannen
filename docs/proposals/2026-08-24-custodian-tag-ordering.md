# Proposal: custodian tag-ordering guard (owner-applied; Tier-C door 5)

**Status:** queued for the opening sitting (decision D0036). `scripts/custodian.sh`
is trust-root, so only the owner applies this — the builder drafts and must not touch it.

## The rule being enforced

DELEGATIONS.md, "Founding ratification": **delegation precedes signature.** The
custodian is to accept no builder-signed tag created before the blessing of the
delegation it invokes (`brief-freeze`), save the tags enumerated by hash in that
section. Today that enumeration is exactly one tag: `m0-laws-freeze`
(tag object `531bb8fe9bf070eff2f47fda2dfb3b8b135a7dc6`). Retroactive blessing stays a
founding-moment oddity, not a pattern the builder can learn to rely on.

## The patch

In `scripts/custodian.sh`, replace check 3 (the `# 3. Signed tags:` loop) with:

```sh
# 3. Signed tags: every tag must verify against allowed_signers; and no
#    builder-signed tag may predate the blessing of the delegation it invokes
#    (DELEGATIONS.md "Founding ratification": delegation precedes signature).
#    FOUNDING_TAGS enumerates the only exceptions, by tag-object hash.
FOUNDING_TAGS="531bb8fe9bf070eff2f47fda2dfb3b8b135a7dc6"   # m0-laws-freeze (D0032/D0035)
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
```

Then regenerate the custodian's manifest row (author-key territory, same recipe as
OPENING step 1 uses for `allowed_signers`):

```sh
grep -v '  scripts/custodian.sh$' MANIFEST.sha256 > MANIFEST.tmp \
  && sha256sum scripts/custodian.sh >> MANIFEST.tmp && mv MANIFEST.tmp MANIFEST.sha256
```

Verify by running `bash scripts/custodian.sh --check-only` — all green — and once by
negative control: `git -c gpg.format=ssh -c user.signingkey=<builder key> tag -s
poison-order-probe` on a **throwaway clone** with the tagger date forced into the past
(`GIT_COMMITTER_DATE="2026-01-01T00:00:00" git ... tag -s ...`), confirm the custodian
goes red on it, then delete the clone.

## Honest limits (read before applying)

- **Before `brief-freeze` exists the check is vacuous** (`bless_epoch` empty). That is
  correct: pre-blessing, everything is contingent anyway and the stale-receipt pause
  already holds work at the boundary.
- **`taggerdate` is written by the tagger**, so a malicious builder could backdate a
  tag. This guard enforces the ordering *discipline* against drift and accident; the
  residual (deliberate forgery) is covered by the enumeration being closed, by the
  owner seeing every `tag verifies:` line at each custodian run, and by red-team at
  boundaries — not by this check.
- **Poison-fixture gap:** this check reads live git state, so the file-tree fixtures
  under `tests/poison/` cannot trip it. Options: (a) at a later sitting, add a small
  bare-repo fixture with a backdated builder tag and a stub `brief-freeze`
  (`tests/poison/` is author-key territory, so this is owner work); (b) until then,
  the gap is recorded here and falls to the boundary red-team. Recommendation: (b)
  now — keep this sitting to its four steps plus this one patch — with (a) queued as
  a red-team finding for the M0-close sitting.
