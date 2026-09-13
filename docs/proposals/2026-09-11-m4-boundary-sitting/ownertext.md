# Owner-text patches for the M4 sitting — what each does, and what was measured

Five `git apply`-able patches, drafted 2026-09-13. Each one:
- applies to HEAD `5762439` on its own, and all five stack cleanly;
- excludes `MANIFEST.sha256` and `governance/custody.sha256`, because those rows are the driver's
  job (`regen_manifest_row`, then step 7's `gen_custody.py`).

Every measurement below was taken in a disposable clone. No real-tree file was touched.

## 1. `policy-envelope-sentence.patch` — D0240 item (1)

- **Changes:** `governance/policy.yaml`'s comment block above `budget_envelopes:`, exactly as
  `policy-envelope-sentence.md` specifies. Nothing else, and `budget_envelopes` still parses to
  six zeros.
- **Result:** patched sha256 `37bbc99b53b2…`.
- **D0243 open set after this patch alone:** `{clamp, current-envelope, successor-law}`, so
  `policy-sentence` leaves the set.
- **On decline:** `git checkout -- governance/policy.yaml governance/policy.yaml.sig`.
- **Manifest rows:** none (custody-set and signature-required, not manifested). Re-sign
  `tannen-policy`.

## 2. `check-manifest-current-envelope.patch` — D0240 (3) + D0242 (3), folded by D0244 (1)

- **Changes:** both changes from `check-manifest-current-envelope.md`, verbatim.
- **One deviation:** the doc says to add `import ast`, and the helper also names `Iterable`, which
  `check_manifest.py` never imported. The patch adds `from collections.abc import Iterable`.
  (Under `from __future__ import annotations` the missing name would not have raised, but it
  would still be a dangling name.)
- **Result:** patched sha256 `417a264feaa8…`. On the real tree the only violation is the expected
  custody drift. `current_milestone` reads `M4`, and the lock reports both M5 owings open.

Rows a–i, re-run against the shipped rule and the patched file:

| Row | Shipped | Patched |
|---|---|---|
| a (`M5:1000`, ceilings 500) | PASS | FAIL: lock ×2 + `fetch`/`total` exceed M4 (0) |
| b (`M4:1000`, ceilings 500) | PASS | **FAIL: lock ×2.** The doc's "b PASS" predates the lock fold. |
| b′ (row b with both owings landed) | — | PASS |
| b″ (`M4:100`, owings landed) | — | FAIL: comparison only |
| c (M4 key deleted) | PASS | FAIL: no envelope for M4 |
| d, e (real tree) | PASS | PASS (lock disarmed) |
| f (envelope nonzero) | PASS | FAIL: lock ×2 |
| g (ceiling nonzero) | FAIL | FAIL: lock ×2 + comparison |
| h (both owings landed) | PASS | PASS |
| i (flag only in a docstring) | PASS | FAIL: clamp only |

- **D0243 open sets:** this patch alone gives `{clamp, policy-sentence, successor-law}`; patches
  1+2 give `{clamp, successor-law}`. The strict node
  `test_each_d0240_precondition_is_open_today_and_the_gate_names_it` goes red, as D0244 item (3)
  intends, and the sitting rewrites its expected set in the same step.
- **On decline:** `git checkout -- scripts/check_manifest.py`.
- **Manifest rows:** none (custody-set only).
- **Not verified:** stacking with `check-manifest-shell-contract.patch`, which edits the same file.

## 3. `roadmap-wiring.patch` — D0217 items (1)(2)

- **Changes:** a `regen-roadmap` hook after `regen-projections` in `.pre-commit-config.yaml`, and
  `gen_roadmap.py` added to `make projections`.
- **Defect this exposes, and fixes in the same patch:** `tests/test_roadmap.py`'s perturbation for
  `.pre-commit-config.yaml` only *appended* a mention of `gen_roadmap.py`. Once the hook exists,
  that append changes nothing, and
  `test_every_declared_input_reaches_the_body[.pre-commit-config.yaml]` goes red. The patch turns
  the perturbation into a toggle and corrects T1's failure message, which would otherwise say
  "Nothing regenerates it automatically".
- **Control:** the toggle also passes against HEAD's hook-less config (9/9).
- **ROADMAP.md must be regenerated in the same step.** Its intro sentence becomes "A pre-commit
  hook regenerates this file, so a stale copy cannot be committed.", and the Sources row for
  `.pre-commit-config.yaml` changes.
- **Tests:** with the patch applied and ROADMAP.md regenerated, `test_operating_manual.py` +
  `test_roadmap.py` give 31 passed.
- **Stacking:** applies cleanly after `doorway-guard.patch`, which also edits the Makefile.
- **On decline:** `git checkout -- .pre-commit-config.yaml Makefile tests/test_roadmap.py ROADMAP.md`.
- **Manifest rows:** none.

## 4. `delegations-marker.patch` — D0229 item (1)

- **Changes:** `DELEGATIONS.md:42` `$marker of 2026-09-07` becomes `Re-created at the publication
  history rewrite of 2026-09-07`. That is the value of `marker` in `publication_sitting.sh:832`;
  line 839 wrote a literal `\$marker` inside a plain string.
- **Safe to edit (measured).** No guard hashes or quotes DELEGATIONS.md's content.
  - `custodian.sh` only checks that it has a manifest row, and `check_manifest` checks its frozen
    hash and custody row.
  - Close-tag messages quote its sha256 when minted, and nothing re-verifies that quote.
  - After the edit and a regenerated row: `check_tag_signers` OK (10 tags), `check_receipts` OK,
    and `check_manifest` shows only custody drift.
  - `custodian --check-only` shows all 21 poison lines as required and full coverage. The only
    failures are "custody set hashes do not verify" and "custody floor violated", the two lines
    step 0 already tolerates.
- **Consequence:** `m4-close`'s message will quote the corrected hash.
- **On decline:** `git checkout -- DELEGATIONS.md MANIFEST.sha256`.
- **Manifest rows:** `DELEGATIONS.md`.

## 5. `poison-readme-corrections.patch` — D0229 item (3b)

- **Changes:**
  - `tests/poison/oracle-shadow-spoofed/README.md`: the "What it does not close" paragraph.
  - `tests/poison/README.md`: the "It defends against one exploitation…" sentences.
  - Both texts are verbatim from M3 `SUPERSESSIONS.md:171-198`, and both anchors still match the
    live files.
  - `_delta_model.py`'s header citation `frozen L3.12` becomes `frozen L3.16`.
- **Beyond `SUPERSESSIONS.md`'s named sites, flagged for your review:** the same mis-citation at
  `oracle-shadow-spoofed/README.md:42` is corrected too. Line 38 is a dated transcript row and is
  left alone.
- **Left stale:**
  - The decoy header's "Staged here and not in tests/poison/" (lines 13-16).
  - The replacement's "pinning it here too is queued", which goes stale if `oracle-shadow-cross-file`
    installs at this sitting.
  - The M1 README text's "keep naming the SUPERSEDED files", which is verbatim from the draft even
    though `test_l1_duckdb.py` has not been superseded.
- **Verdict unchanged:** the `oracle-shadow-spoofed` poison invocation still exits 1 with "answers
  with different code" after the edit, and `test_oracle_shadow_spoofed_fails_its_poison` passes.
  With the three manifest rows regenerated, `check_manifest` shows exactly three custody-drift
  lines.
- **On decline:** `git checkout -- tests/poison/README.md tests/poison/oracle-shadow-spoofed/ MANIFEST.sha256`.
- **Manifest rows:** `tests/poison/README.md`, `tests/poison/oracle-shadow-spoofed/README.md`,
  `tests/poison/oracle-shadow-spoofed/_delta_model.py`.
