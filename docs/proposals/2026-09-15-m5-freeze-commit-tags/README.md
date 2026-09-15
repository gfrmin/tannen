# A laws-freeze tag cannot precede the commit it seals (D0254)

**Drafted, not installed.** `scripts/check_tag_signers.py` is frozen (a MANIFEST.sha256 row) and
custody-set, so only the owner applies `check_tag_signers.patch`, with its manifest row and the
custody set regenerated and the custody set re-signed. `test_tag_signers.patch` touches an unfrozen
builder test, but it must land in the same act: its new deferral test fails against the unpatched
guard.

## What happens

The M4 sitting installed D0205's derivation: `<m>-laws-freeze` is required for every
`docs/specs/<m>.md` **on disk**. The check-decisions pre-commit hook runs `tests/test_tag_signers.py`
(bound by D0050, D0054, D0058, D0062), and its two real-repo nodes run that rule. So M5 Session A's
freeze commit, which adds `docs/specs/m5.md`, needs `m5-laws-freeze` before the commit that tag
seals can exist. M5 is the first Session A since the derivation landed.

No split of the commit avoids it. `tests/laws/m5/` without the spec fails D0241's bound node
`tests/test_laws_runner.py::test_discovery_matches_the_frozen_spec_table`; the spec without the
laws fails the same node; `--no-verify` is refused by standing rule.

## The fix: one deferral

`<m>-laws-freeze` is not yet owed for a spec that is on disk but **absent from the root's own
HEAD**, and only when the root is a git work tree with a HEAD. It is owed the moment the spec is
committed. Nothing else is deferred:

- a tree with no `.git` (an export) keeps the strict rule;
- CI checks out committed trees, so every spec there is in HEAD;
- the close rule is unchanged (a successor's spec on disk still requires the predecessor's close);
- a committed spec whose tag was deleted is refused exactly as before (RT-15).

It reads the **root's** HEAD, not the `--repo` bundle's. Reading the bundle would disarm
`tests/poison/tag-roles-derived`, whose bundle carries tags and no specs.

## Watched, in a scratch clone of master at e03b4ac

| Case | Guard | Expected | Seen |
|---|---|---|---|
| placeholder `docs/specs/m5.md` on disk | unpatched | both real-repo nodes fail, `m5-laws-freeze` missing | 2 failed |
| no placeholder | unpatched | `tests/test_tag_signers.py` green | 18 passed |
| new tests | unpatched | the deferral test fails | 1 failed, 19 passed |
| full test file | patched | green | 20 passed |
| real tree | patched | OK | OK, 11 tags |
| `m5.md` staged, not committed | patched | OK; `m4-close` now required and present | OK; real-repo nodes 2 passed |
| `m5.md` committed, no tag | patched | refused naming `m5-laws-freeze` | refused; 2 failed |
| `m4-laws-freeze` deleted | patched | refused | `required tag missing: m4-laws-freeze` |
| poison `tag-roles-derived` | patched | exactly `required tag missing: m3-close` | exactly that, 1 violation |
| poison `custodian-tag-signer` | patched | wrong principal and missing `brief-freeze` | both present |

The patched guard's sha256 is `f812a00516a5fbaf9ee4aa492c0607a452abe1ff806837cba14a336ef37884c5`.

`test_a_committed_spec_owes_its_laws_freeze_again` passes against both guards. It is a
no-weakening control (the deferral must end at the commit), not a demonstration of the fix.

## Owner steps

In `~/git/tannen` on master, with the owner key loaded in ssh-agent. One chain, so a broken step
stops the rest:

```
git apply docs/proposals/2026-09-15-m5-freeze-commit-tags/check_tag_signers.patch && git apply docs/proposals/2026-09-15-m5-freeze-commit-tags/test_tag_signers.patch && test "$(sha256sum scripts/check_tag_signers.py | cut -d' ' -f1)" = f812a00516a5fbaf9ee4aa492c0607a452abe1ff806837cba14a336ef37884c5 && grep -v '  scripts/check_tag_signers.py$' MANIFEST.sha256 > MANIFEST.tmp && sha256sum scripts/check_tag_signers.py >> MANIFEST.tmp && mv MANIFEST.tmp MANIFEST.sha256 && .venv/bin/python -I -P scripts/gen_custody.py && rm -f governance/custody.sha256.sig && ssh-keygen -Y sign -f "$OWNER_KEY" -n tannen-custody governance/custody.sha256 && .venv/bin/python -I -P scripts/check_manifest.py && .venv/bin/python -I -P scripts/check_tag_signers.py && TANNEN_NO_EVIDENCE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_tag_signers.py
```

Set `OWNER_KEY` to the owner key file first (the path the sitting driver's `KEYREF` uses).
`ssh-keygen -Y sign` writes `governance/custody.sha256.sig` beside the file, so the old signature
is removed immediately before it. Then commit and push master. The builder fast-forwards `m5` onto
it and makes the freeze commit.
