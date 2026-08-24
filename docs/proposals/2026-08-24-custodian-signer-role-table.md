# Proposal: custodian signer-role table for tags (owner-applied; Tier-C door 5)

**Status:** queued for the M0→M1 boundary sitting (decision D0050).
**Supersedes** `2026-08-24-custodian-close-tag-signer.md`, which patched one instance of
the class this patch closes. `scripts/custodian.sh` is trust-root — author-key territory
— so only the owner applies it. The builder drafts and must not touch the file.

## What was actually wrong

D0049 was drafted as a nine-line `*-close` special case. That was too narrow. The real
defect is that **the custodian never checks which principal signed which kind of tag**.
It verifies that a tag verifies against `allowed_signers`, and that a builder-signed tag
does not predate its delegation's blessing (D0036). Both principals are enrolled in
`allowed_signers`, so any tag signed by either satisfies both checks.

Three experiments, run in a throwaway clone at
`/tmp/.../scratchpad/tagtest*` (deleted; reproduce with the recipe below):

| # | Act | Custodian verdict |
|---|---|---|
| 1 | Builder-signed `m0-close` | `tag verifies: m0-close` → **custody floor intact, exit 0** |
| 2 | Builder-signed `amendment-2026-09-01` | `tag verifies: amendment-…` → **custody floor intact, exit 0** |
| 3 | `git tag -d brief-freeze` then re-issue it **builder-signed** | `tag verifies: brief-freeze` → **custody floor intact, exit 0** |

Experiment 3 is the serious one. `brief-freeze` is the trust root: it is the owner's
founding signature, its message carries the blessed delegation text verbatim, and its
date is `bless_epoch` — the reference point for "delegation precedes signature". Nothing
pins its tag-object hash, so a builder can delete it and re-issue it under its own key,
with its own delegation text in the message, and the custodian prints **`custody floor
intact`**.

Ordering matters and is worth stating exactly, because a partial test would have missed
it. If the trust root is replaced *after* other builder tags exist, the custodian does
fail — but for an unrelated reason: re-issuing `brief-freeze` moves `bless_epoch` to now,
so the pre-existing builder tags suddenly predate their blessing and trip the D0036
check. That is an accident, not a defence. Replace the trust root **first**, before
minting anything else, and there is nothing left to trip:

```
$ git tag -d brief-freeze && git tag -s brief-freeze -m "Re-issued by the builder"
$ bash scripts/custodian.sh --check-only
custodian: tag verifies: brief-freeze
...
custodian: custody floor intact      # exit 0
```

Observed signer before: `owner@tannen`, tag object `c219e638…`. After: `builder@tannen`,
tag object `34779f82…`. No check noticed.

This compounds with the companion finding that `DELEGATIONS.md` is not frozen: a builder
could rewrite the delegation *and* re-bless it with a signature of its own, end to end,
with every guard green. Neither hole is reachable by accident — both take deliberate
acts — but a custody floor that only stops accidents is not a custody floor.

## The patch

In `scripts/custodian.sh`, extend check 3. Above the tag loop:

```sh
# Tag classes and their authorised signing principal (D0050). A tag's NAME declares
# what kind of authority it claims; this table says who may make that claim.
#   brief-freeze   owner    trust root: founding signature, blessed delegation text,
#                           and bless_epoch for the delegation-precedes-signature rule
#   *-laws-freeze  builder  standing delegation 1 (DELEGATIONS.md)
#   *-close        owner    milestone close; anchors the receipt clock (D0049)
#   amendment-*    owner    constitution amendments (Tier-C door 4)
#   receipt-*      owner    reserved
# An UNKNOWN tag class is refused rather than waved through: otherwise the next hole
# is simply a tag kind this table never heard of.
tag_signer_role() {
    case "$1" in
        brief-freeze)  echo owner   ;;
        *-laws-freeze) echo builder ;;
        *-close)       echo owner   ;;
        amendment-*)   echo owner   ;;
        receipt-*)     echo owner   ;;
        *)             echo unknown ;;
    esac
}

# The trust root is pinned by tag-object hash: re-issuing brief-freeze under any key
# is the one act that would otherwise redefine every other check in this file.
TRUST_ROOT_TAG="c219e63819beb4052b326e47b9cbd5d208779cda"   # brief-freeze, owner@tannen
if git rev-parse -q --verify refs/tags/brief-freeze >/dev/null 2>&1; then
    if [ "$(git rev-parse refs/tags/brief-freeze)" != "$TRUST_ROOT_TAG" ]; then
        bad "trust root re-issued: brief-freeze is not tag object $TRUST_ROOT_TAG"
    fi
fi
```

and inside the loop, immediately after `say "tag verifies: $tag"`:

```sh
    role=$(tag_signer_role "$tag")
    if [ "$role" = "unknown" ]; then
        bad "tag class not in the signer-role table — add it deliberately or rename: $tag"
    elif ! printf '%s' "$out" | grep -q "signature for ${role}@tannen"; then
        bad "tag signed by the wrong principal (expected ${role}@tannen): $tag"
    fi
```

`$out` already holds this tag's `git verify-tag` output, so no extra git invocation.

## What this does not fix, stated plainly

The pin above lives in `scripts/custodian.sh`, which is frozen by a `MANIFEST.sha256`
row — and `MANIFEST.sha256` is not itself signed, nor listed in itself. A builder that
edits a frozen file *and* updates its manifest row in the same commit leaves
`sha256sum -c` satisfied. So the pin raises the cost of re-issuing the trust root without
making it impossible, and this proposal should not be read as claiming otherwise.

The structural fix, once the table above makes `brief-freeze` un-reissuable by the
builder, is that the owner-signed trust root becomes a genuine anchor for the custody
set's own bytes: the custodian can compare `scripts/custodian.sh`, `allowed_signers`,
`tests/poison/**` and `DELEGATIONS.md` against **the tree of the most recent
owner-signed boundary tag**, with legitimate later additions (law-freeze manifest rows)
enumerated as blessed. That closes the loop the pin only narrows. It is a larger change
and wants its own sitting; recorded here so the gap is not mistaken for closed. The
M0-boundary red-team pass is auditing this surface independently and its report may
sharpen the shape.

## Reproduction recipe

```sh
git clone /home/g/git/tannen /tmp/tagtest && cd /tmp/tagtest
git config gpg.format ssh
git config user.signingkey ~/.ssh/tannen_builder
git config user.email builder@tannen
git tag -s m0-close -m "test"          # or: git tag -d brief-freeze; git tag -s brief-freeze -m "test"
bash scripts/custodian.sh --check-only; echo "exit $?"
```

## Poison fixtures

Both experiments must become fixtures, or this patch is a guard whose liveness is
untested — the exact failure mode `tests/poison/` exists to prevent. Unlike the four
existing fixtures, the violation here is a *signed git object* rather than a file tree,
so each fixture is a small **bare repository** committed under `tests/poison/`, carrying
the offending tag. Drafts and the builder script that generates them are staged with the
red-team candidates under `docs/redteam/fixture-candidates/`; the corpus is author-key
territory, so the owner installs them.

Markers: `tag signed by the wrong principal` and `trust root re-issued`.

## Order of operations at the sitting

Load-bearing, and worth following exactly:

1. Apply this patch and the `MANIFEST.sha256` additions **first**, and re-sign whatever
   the changes require.
2. Install the poison fixtures and confirm `custodian.sh --check-only` fails each one for
   its marker.
3. **Then** sign `m0-close`.

So the first owner-signed close tag this project ever mints is validated by the very rule
that requires closes to be owner-signed, in the same custodian run that proves the rule
bites. A guard should be born having already caught something real.

## Verification after applying

1. `bash scripts/custodian.sh --check-only` → green on the real repo; `brief-freeze` maps
   to `owner`, `m0-laws-freeze` to `builder`, both match.
2. Builder-signed `m0-close` in a scratch clone → `tag signed by the wrong principal (expected owner@tannen)`.
3. Re-issued `brief-freeze` in a scratch clone → `trust root re-issued`.
4. A tag named `random-thing` → `tag class not in the signer-role table`.
5. Upgrade D0050's binding to a `manifest` binding on `scripts/custodian.sh`.
