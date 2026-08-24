> **SUPERSEDED (2026-08-24) by `2026-08-24-custodian-signer-role-table.md`.**
> This draft patched one instance — `*-close` — of a class the custodian misses entirely:
> it never checks which principal signed which kind of tag. Empirical testing showed a
> builder-signed `amendment-*` tag, and a builder re-issue of `brief-freeze` itself, also
> pass today. Kept unchanged because decision D0049 binds to this path; the generalised
> patch is the one to apply.

# Proposal: custodian requires milestone close tags to be owner-signed (owner-applied; Tier-C door 5)

**Status:** queued for the M0→M1 boundary sitting (decision D0049).
`scripts/custodian.sh` is trust-root — author-key territory — so only the owner applies
this. The builder drafts and must not touch the file.

## The rule being enforced

D0049 (owner, 2026-08-24) decided that milestone close tags remain owner-signed and the
standing delegation is **not** extended to cover them. The reason is structural rather
than about risk in the individual act:

> The builder mints the opening tags that start the consent clocks, so the owner must
> sign the closes that anchor presence — delegating both ends would hollow out the
> receipt mechanism.

Concretely: `receipt_state()` in `scripts/_gov.py` computes attention-receipt freshness
as *the first milestone-boundary tag after the receipt, plus 7 days*. Boundary tags are
matched by `BOUNDARY_TAG_RE` = `brief-freeze | *-laws-freeze | *-close`. The builder may
mint `*-laws-freeze` tags under standing delegation, so the builder already controls when
the consent clock **starts**. If the builder could also mint `*-close`, it would control
both ends of the mechanism that measures the owner's presence — and a mechanism whose
subject controls its own measurement measures nothing.

## The gap today

The custodian verifies that *every* tag verifies against `allowed_signers`, and that no
builder-signed tag predates its delegation's blessing (D0036, applied). It does **not**
check *which principal* signed *which kind* of tag. A builder-signed `m0-close` would
therefore pass check 3 today: it verifies, and it postdates `brief-freeze`. The decision
is currently carried by DELEGATIONS.md's frozen text alone — real, since extending the
delegation means re-freezing an author-key path, but it is a prohibition no guard states.

## The patch

In `scripts/custodian.sh` check 3, inside the `for tag in $(git tag -l ...)` loop,
immediately after `say "tag verifies: $tag"`, insert:

```sh
    # Milestone close tags anchor owner presence (D0049): the builder mints the
    # opening tags that START the consent clocks, so the owner must sign the closes.
    # A close tag signed by anyone but the owner is a hollowed receipt mechanism.
    case "$tag" in
        *-close)
            if ! printf '%s' "$out" | grep -q 'signature for owner@tannen'; then
                bad "milestone close tag is not owner-signed (D0049): $tag"
            fi
            ;;
    esac
```

`$out` already holds the `git verify-tag` output for `$tag` at that point, so this costs
no extra git invocation.

## Poison fixture

Guard liveness (BRIEF §9.1) needs a fixture, and this one cannot be a directory of files
the way the other four are: the violation is a *signed git object*, so the fixture is a
throwaway repo carrying a builder-signed `*-close` tag. A draft lives at
`docs/redteam/fixture-candidates/` if the boundary red-team pass produced one; otherwise
the owner can mint it at the sitting with a builder-signed tag on a scratch clone.
Marker string: `close tag is not owner-signed`.

## Verification after applying

1. `bash scripts/custodian.sh --check-only` → still green on the real repo (no `*-close`
   tag exists yet, so the new branch is not taken).
2. Mint a builder-signed `m0-close` on a scratch clone → custodian must fail with
   `close tag is not owner-signed`.
3. Owner-sign the real `m0-close` → custodian green, and `receipt_state()` begins the
   7-day freshness clock from that tag's date.
4. Upgrade D0049's bindings to include a `manifest` binding on `scripts/custodian.sh`
   once the patch lands.

## Companion gap found while drafting this: DELEGATIONS.md is not frozen

`DELEGATIONS.md` is the document this decision rests on, and it is **not** listed in
`MANIFEST.sha256`, nor in the custodian's custody set (check 2 covers
`scripts/custodian.sh`, `allowed_signers`, `.github/workflows/ci.yml` and
`tests/poison/**` only). Its authority comes from being quoted verbatim in the
owner-signed `brief-freeze` tag message — but **no guard compares the file to the tag
message**. A builder could today append "and milestone close tags" to delegation 1 and
every check would stay green, because the blessed text lives in the tag while the read
text lives in the file, and nothing joins them.

This is the same shape as the decision above — an instruction whose enforcement is
assumed rather than mechanical — so it should be closed at the same sitting. Two ways,
in order of preference:

1. **Freeze it.** Add a `DELEGATIONS.md` row to `MANIFEST.sha256` and to the custodian's
   check-2 custody-set list. Cheapest, and it makes the file's read-only status a fact
   rather than a convention noted in a session's memory. Note the consequence and accept
   it deliberately: the owner then amends the delegation only by re-freezing, which is
   exactly the friction an amendment should carry.
2. **Join file to tag.** Have the custodian re-derive the blessed text from
   `git tag -l --format='%(contents)' brief-freeze` and diff it against `DELEGATIONS.md`.
   Stronger in principle — it checks the *right* invariant rather than a proxy — but the
   tag message is the file with its markdown headings stripped, so the comparison needs
   a normalisation step, and a normaliser is a place for a bug to hide.

Recommend (1), with (2) noted as the better invariant if the normalisation ever becomes
cheap. Either way this is trust-root work: owner-applied.

The M0-boundary red-team pass is auditing this surface independently; if it reproduces
the gap, its report at `docs/redteam/2026-08-24-m0-boundary.md` will carry the exact
reproduction and a fixture candidate.
