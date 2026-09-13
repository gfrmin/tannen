# Binding upgrades at the M4 sitting: D0214's nine, and this sitting's own queue

Two helpers, both run by the driver with the owner at the keyboard. The driver shows the diff,
then re-signs a Tier-C record or flips a Tier-A one. Neither helper signs anything.

| Helper | Driver step | What it edits |
|---|---|---|
| `upgrade_binding.py <id>` | 8b | D0214's nine upgrades, on five records that are **already owner-signed**, so each edit is followed by a re-signature |
| `queue_upgrades.py <id>` | 8, before accept/sign | Bindings on **this sitting's queue** records, each gated on a detector that its artifact landed earlier in the sitting. This is D0214's recommendation: upgrade in the same breath as the status flip, before the signature. |

Both helpers replace exact text, never sweep: only `bindings` and `bindings_count` move, and
`decision:` prose is history (D0045). Every after-text below was measured against the tree on
2026-09-13 rather than copied from D0214.

## D0214's own claims, measured

Two of D0214's nine claims are not true as written. The after-text corrects them rather than
repeating them.

- **Item (1)** says `governance/laws.yaml` joined `custody.set` at the M2 sitting. **It did not.**
  `governance/tier-c.yaml` lists `scripts/check_laws.py` (:131) and `conftest.py` (:116), and no
  `governance/laws.yaml`. The M2 driver's step 4e added conftest.py in its place, because RT-M2-02
  showed the pointer, not the data, is what an attack edits (D0141).
- **Item (8)** says `required_tags` "is now complete". **On 2026-09-13 it lacked `m4-laws-freeze`**
  (RT-M4-06, D0229 item 4). The upgrade claims the trust-root repin and `m3-laws-freeze`, and
  states that completeness is NOT claimed.

The tag-roles.yaml details (D0131, D0154, D0176) are phrased to stay true whichever way step 4
goes: "whether it is held by the hand enumeration or by the derivation D0205 put in its place".

## `upgrade_binding.py` — D0214's nine

| # | Record | Binding before | Binding after | Tree precondition (refuses without it) | Measured |
|---|---|---|---|---|---|
| 1 | D0131 | `file` governance/tier-c.yaml, documentary | `manifest`, enforced | tier-c.yaml lists `scripts/check_laws.py` and `conftest.py` | tier-c.yaml has a MANIFEST row matching its bytes; check_laws.py is in `make verify` |
| 2 | D0131 | `file` governance/tag-roles.yaml, documentary | `manifest`, enforced | — | m1-/m2-laws-freeze are in `required_tags`; MANIFEST row current |
| 3 | D0154 | `file` scripts/custodian.sh, documentary | `manifest`, enforced | — | The hunks are present: `poison check_laws` (:330), the NOT INSTALLED refusal (:190), the completeness line (:352), the __pycache__ exclusion (:89), the previous-receipt line (:382), `rm -f "$receipt" "$receipt.sig"` + `exit 1` (:405-407); MANIFEST row current |
| 4 | D0154 | `file` scripts/boundary_sitting.sh, documentary | `file`, enforced (custody-set, no MANIFEST row) | the driver carries `flock -n 9` **and** `PROPOSALS_M4=` | The detail describes the M4 driver (lock kept, receipt behind the confirm, fixed M3 steps retired as no-ops), so it refuses over any other driver. Watched refusing on an unmodified clone. |
| 5 | D0154 | `file` governance/tag-roles.yaml, documentary | `manifest`, enforced | — | m3-laws-freeze and m3-close are in `required_tags` |
| 6 | D0154 | *(new)* | `pytest` `tests/test_governance_scripts.py::test_every_installed_fixture_is_exercised_by_this_suite`, enforced; **bindings_count 4 → 5** | the test is defined | `--collect-only`: 1 collected; run: 1 passed, not skipped |
| 7 | D0171 | `file` scripts/custodian.sh, documentary | `manifest`, enforced | custodian carries `poison check_laws "which no law file defines"` | as row 3 |
| 8 | D0176 | `file` governance/tag-roles.yaml, documentary | `manifest`, enforced | `object: d60b792f…` present | trust root repinned; m3-laws-freeze present; m4-laws-freeze absent (so completeness is NOT claimed) |
| 9 | D0195 | `file` .github/workflows/ci.yml, documentary | `manifest`, enforced | ci.yml carries `THIS FILE NOW RUNS` | header replaced (:12); MANIFEST row current |

`bindings_count` changes only on D0154 (4 → 5). D0131 and D0176 carry no count; D0171 (5) and
D0195 (3) are unchanged.

**The tag-roles.yaml binding appears in both tables, and that is safe.** D0229 item (4)'s binding
on `governance/tag-roles.yaml` (row 4 of the D0229 group below) is a separate record, so there is
no collision.

## `queue_upgrades.py` — this sitting's queue

Detectors read code and config, never comments. `code_has` skips `#`-led lines, and a comment-only
`# id: regen-roadmap` was watched **not** firing. **The detector strings are contracts with the
sibling drafts; the driver and the patches must produce them.**

| Record | Binding | After | Detector (all must hold) |
|---|---|---|---|
| D0214 | `file` scripts/boundary_sitting.sh | enforced | the driver calls `queue_upgrades.py` **and** `upgrade_binding.py` on non-comment lines |
| D0215 | `file` scripts/check_decisions.py | enforced | `gen_projections.py` no longer contains `f"Attention receipt: **{` (the digest's `f"- Attention receipt:` is a different spelling and stays); `check_decisions.py` no longer contains `attention-receipt line is not what today computes`; `check_decisions.py` has a **non-comment line containing `D0215`** (the refusal of a verdict line) |
| D0215 | `file` scripts/boundary_sitting.sh | **retargeted** to `docs/proposals/2026-09-04-m3-boundary-sitting/boundary_sitting.sh`, still documentary | M4 driver installed (`PROPOSALS_M4=`). :2664 and :2746-2760 were measured still true in the M3 copy; the installed M4 driver would falsify them. |
| D0238 | `file` governance/policy.yaml | enforced | policy.yaml contains `WHAT SPENDGUARD DOES AND DOES NOT DO` (the drafted sentence's own heading) |
| D0240 | `file` governance/policy.yaml (item 1) | enforced | as D0238 |
| D0240 | `file` scripts/check_manifest.py (item 3) | enforced | `def current_milestone(` |
| D0242 | *(new)* `file` scripts/check_manifest.py | enforced; **bindings_count 3 → 4** | `def unmet_spend_preconditions(` |
| D0244 | `file` scripts/check_manifest.py | enforced | both `def unmet_spend_preconditions(` and `def current_milestone(` |
| D0217 | `file` .pre-commit-config.yaml (item 1) | enforced | non-comment `id: regen-roadmap` |
| D0217 | `file` Makefile (item 2) | enforced | non-comment `scripts/gen_roadmap.py` |
| D0217 | `file` scripts/boundary_sitting.sh (item 3) | enforced | M4 driver installed; driver still greps `^status: blocked-on-owner$`; driver does **not** contain the M3 step-8 prefilter `[ "$(sed -n 's/^tier: *//p' "$rec" \| head -1)" = "C" ] \|\| continue` verbatim |
| D0229 | DELEGATIONS.md (item 1) | `file`→`manifest`, enforced | DELEGATIONS.md exists and contains no `$marker` |
| D0229 | governance/importlinter.toml (item 2) | `file`→`manifest`, enforced | `id = "shell-no-subprocess"` **and** `scripts/check_doorway.py` exists |
| D0229 | tests/poison/README.md (item 3) | `file`→`manifest`, enforced | a directory `tests/poison/*disarm*` with a README row `` | `<name>/` | ``; the detail names the directory found |
| D0229 | governance/tag-roles.yaml (item 4) | `file`→`manifest`, enforced — **two texts**: "derivation installed" or "m4-laws-freeze enumerated (lesser half)" | `def derive_required_tags(` in check_tag_signers.py, else a `  - m4-laws-freeze` line in tag-roles.yaml |
| D0229 | scripts/check_manifest.py (item 5) | enforced (`file`) | `def current_milestone(` |
| D0241 | — | nothing | the clamp and successor law are M5 Session A's |

Not moved, deliberately:
- **D0214:** the D0213 citation and the check_decisions.py rule citation (:73, :384-390) stay
  documentary, since the guard enforces the signature, not the upgrade.
- **D0215:** the `_gov.py` citation stays documentary, because the remedy does not edit `_gov.py`.
- **D0238/D0240/D0242:** the frozen L4.4 `manifest` bindings and D0240's `src/tannen/cli.py`
  (deferred clamp) stay as they are.
- **D0242:** `governance/laws.yaml` (owed by M5) stays documentary.
- **D0241 and D0244:** the draft citations stay documentary.

## Verified, in a disposable clone (never the real tree)

**`upgrade_binding.py`**
- All five records edited. Every edited record validated against
  `governance/schemas/decision-record.schema.json`, with `bindings_count == len(bindings)`, every
  file/manifest target existing, and every manifest target holding a MANIFEST row.
- The new pytest node collects and passes.
- A second run gives "already upgraded" for all five (exit 1).
- D0154 refuses on a tree without the M4 driver and leaves the clone untouched.

**`queue_upgrades.py`**
- Unmodified clone: all nine report "nothing landed" and nothing is edited.
- One landed artifact (the regen-roadmap hook): only D0217 item (1) fires; the second run reports
  "already upgraded".
- Lock marker alone: D0242 fires with its count bump, and D0244 (which needs both markers) does not.
- Decline branch: `m4-laws-freeze` enumerated gives D0229's "lesser half" text.
- A hand-edited pre-state exits 1.
- **Every artifact simulated as landed:** all 16 upgrades fire, every record validates, and a
  second run reports "already upgraded" for each.
