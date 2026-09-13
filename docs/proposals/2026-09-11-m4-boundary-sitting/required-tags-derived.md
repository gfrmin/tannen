# Proposal: `required_tags` derived — installed at the M4 sitting (D0205, D0229 item 4)

**Status:** drafted for the M4 boundary sitting's step 4, with its poison fixture at step 5 and
its custodian line in step 6's draft. Nothing here is installed. `scripts/check_tag_signers.py`
and `governance/tag-roles.yaml` are frozen **and** custody-set, and
`tests/poison/custodian-tag-signer/` is author-key territory.

The rule, the eight-for-eight positive control it had at M3, and the argument for why deriving
from frozen specs is not circular are all in
`docs/proposals/2026-09-04-m3-boundary-sitting/TAG-ROLES-DERIVED.md`. They are not restated
here. This file records what changed since that draft and what was watched failing.

## Artifacts

| File | What |
|---|---|
| `required-tags-derived.patch` | `git apply`-able against HEAD `5762439`: `scripts/check_tag_signers.py`, `governance/tag-roles.yaml`, `tests/test_tag_signers.py`, and `tests/poison/custodian-tag-signer/{governance/tag-roles.yaml,make-fixture.sh}` |
| `docs/redteam/fixture-candidates/tag-roles-derived/` | The fixture: specs `m0`…`m4`, a placeholder table, `make-fixture.sh`, and `README.md` |

## What changed versus the M3 draft

1. **`brief-freeze` is required only once the owner key is enrolled.** The draft said "always".
   That contradicts `check_trust_root`, which deliberately tolerates an absent trust root before
   the opening sitting. It also turned `test_missing_trust_root_is_tolerated_before_the_opening_sitting`
   red. The condition is now the same `opened` that function uses. The spec-derived tags carry
   no such condition.
2. **The guard prints the derived set** (`required (derived from docs/specs): …`). A rule that
   derived nothing would otherwise look exactly as green as one that derived everything.
3. **The installed tag-signer fixture moves too.** Its table carried `required_tags: [brief-freeze]`,
   which the refusal branch would reject — a second failure reason added to a fixture that must
   keep its original ones. It becomes `required_tags: []`, and so does the heredoc in its
   `make-fixture.sh` that would re-create the list. The derivation still requires `brief-freeze`
   there, because the fixture enrols an owner key, so the tooth is unchanged.
4. **The fixture is generated, not shipped.** It uses fixture-local throwaway keys rather than
   the builder's key, and derives its tag list from its own specs. The only name written in the
   script is the omitted `m3-close`.
5. **Tests.** The two enumeration tests now require tags through specs. Four tests are new:
   successor-spec requires the predecessor's close; an enumerated list is refused even when
   every tag it names exists; `m1-corrections.md` is not a milestone; and every real spec yields
   its laws-freeze tag, with every derived tag present.

## Watched failing (2026-09-13, in a disposable clone of `5762439`)

| # | Run | Verdict |
|---|---|---|
| 1 | **Negative control** — the SHIPPED guard against the generated fixture | **PASS**, rc 0, 9 tags. `m3-close` is absent and nothing notices: the defect, demonstrated |
| 2 | The patched guard against the same fixture | **FAIL, 1 violation**: `required tag missing: m3-close` and nothing else |
| 3 | **Positive control** — the patched guard on the real tree | **OK**, 10 tags. Derived set = `brief-freeze`, `m0..m4-laws-freeze`, `m0..m3-close` — **10, equal to `git tag` exactly**. The hand list holds **9**; the tenth is `m4-laws-freeze`, which is RT-M4-06's lag, closed |
| 4 | Anti-regression — `required_tags: [m0-close]` restored in a fixture copy | **FAIL** on `required_tags is enumerated … m0-close` |
| 5 | `custodian-tag-signer/` under the patched guard | Same three violations as before (trust root MISSING, `required tag missing: brief-freeze`, wrong principal). Both custodian markers are present |
| — | `make-fixture.sh` run twice | Idempotent; each run regenerates |
| — | `tests/test_tag_signers.py` + the two `check_tag_signers` POISON rows | 20 passed |
| — | `git apply --check` on a fresh HEAD clone | OK |

## At the sitting

- **Step 4.** `git apply` the patch, then regenerate the manifest rows for
  `governance/tag-roles.yaml`, `scripts/check_tag_signers.py` and
  `tests/poison/custodian-tag-signer/governance/tag-roles.yaml` (also `make-fixture.sh`, if it
  carries a row).
  - Decline: `git checkout --` all five files.
- **Step 5.** `git mv` the candidate, run `bash tests/poison/tag-roles-derived/make-fixture.sh`,
  **then** `add_manifest_rows`. The script writes `repo.bundle`, `allowed_signers` and the
  table, so rows taken before it runs leave unmanifested files in a sealed directory.
- **Step 6.** The custodian draft carries:
  ```
  poison check_tag_signers_derived "required tag missing: m3-close" \
      "$PY" -I -P scripts/check_tag_signers.py \
      --root tests/poison/tag-roles-derived --repo tests/poison/tag-roles-derived/repo.bundle
  ```
  The marker names the tag. `custodian-tag-signer/` already prints `required tag missing:
  brief-freeze`, so the bare message class would not test this fixture.
- **Follow-on.** `tests/test_governance_scripts.py` needs the matching POISON row in the same
  step the fixture installs, or its completeness pass goes red.
- **Consequence.** Step 11's `required_tags` edit disappears for good: under the derivation,
  `m4-close` becomes required when `docs/specs/m5.md` lands at M5 Session A.
