# CI runs red on every boundary tag push (D0252)

**Drafted, not installed.** `.github/workflows/ci.yml` is frozen (a MANIFEST.sha256 row),
custody-set (`governance/custody.sha256`) and named in `governance/tier-c.yaml`, so only the owner
applies `ci.yml.patch`, at a sitting, with the manifest row and custody set regenerated and
re-signed.

## What happens

`on: push` also fires when a tag is pushed. For that event, `actions/checkout@v4` first fetches
every tag correctly (the log shows `[new tag] m4-close`), then re-fetches the triggering one as
`git fetch --no-tags … +<commit sha>:refs/tags/m4-close`, logged as `t [tag update]`. That replaces
the owner-signed ANNOTATED tag with a LIGHTWEIGHT ref to the same commit. `check_tag_signers`
then correctly refuses it: `tag does not verify against allowed_signers: m4-close`. Through the
four records bound to `tests/test_tag_signers.py` (D0050, D0054, D0058, D0062), `check_decisions`
fails and `make verify` goes red.

The branch run on the same commit is green, because a branch push does not rewrite any tag.

## Runs affected

| Tag | Commit | Run | Result |
|---|---|---|---|
| `m3-close` | e33adf8 | 34481481487 | failure (the same four, plus D0063/D0177) |
| `m4-laws-freeze` | f491665 | 34599516034 | failure (the same four) |
| `m4-close` | 9cff0b7 | 34930012977 | failure (the same four) |

Master CI on 9cff0b7 (run 34930012800) passed.

## Watched

In a scratch clone of the repository, checked out at `m4-close`:

1. With the real annotated tag, `tests/test_tag_signers.py` gives 18 passed.
2. Reproducing checkout's refetch (`+9cff0b7…:refs/tags/m4-close`) makes `git cat-file -t m4-close`
   report `commit`. `check_tag_signers` then fails with exactly CI's violation, and the test file
   fails.
3. After `git fetch --force --tags origin` (the patch's step), the tag is annotated again. The
   test file gives 18 passed, and `check_tag_signers` reports OK over 11 tags.

## The fix

One step after checkout: `git fetch --force --tags origin`. `--force` is required, because
without it git refuses to replace the existing (wrong) local tag. It changes nothing on a branch
push, where every tag already matches.
