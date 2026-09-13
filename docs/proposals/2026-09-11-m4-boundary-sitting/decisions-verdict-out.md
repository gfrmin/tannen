# Proposal: DECISIONS.md stops storing a verdict that moves with the clock and the tag set (D0215)

**Status:** queued for the M4 boundary sitting, driver step 4b. The patch is
`decisions-verdict-out.patch` in this directory. It touches three custody-set scripts
(`scripts/_gov.py`, `scripts/check_decisions.py`, `scripts/gen_projections.py`), so it is
owner-applied and covered by step 7's custody re-signature. It also carries one edited test
and one new test file, neither of them custody-set. None of the five files has a
`MANIFEST.sha256` row.

## The defect

D0215, measured on three close tags: `m1-close`, `m2-close` and `m3-close` each point at a
commit whose `DECISIONS.md` carries `Attention receipt: **FRESH** — receipt <date>.md fresh
(no milestone boundary since)`.

`check_decisions` compares that line with what the current run computes. The computation
reads `git tag -l` and today's date, and no commit contains either. So the instant a sitting
mints its close tag, the commit the tag names turns red, permanently. CI run 34481481487 on
`e33adf8` is the recorded instance.

The same holds for the `Status (effective)` column: a provisional Tier-B record's row reads
`accepted (veto lapsed)` or `BLOCKED` depending on the date and on receipt freshness, and the
guard compared it with the day.

D0215's recommendation is adopted as written, and its four rejected remedies are not
re-argued here:
- DECISIONS.md carries only what its commit contains.
- The verdict is rendered where a dated artifact can carry it honestly (`digest/<date>.md`).
- `check_decisions` goes on computing and reporting the verdict, and stops asserting that a
  tracked file agrees with it.

## The design

- **`_gov.receipt_line(root)`** returns the line DECISIONS.md carries:
  ``Latest attention receipt: `receipts/<date>.md` — signature file present.``
  (or `— NO signature file beside it.`, or `none in this tree.`).
  - Both facts are files in the tree.
  - The signature is not verified here; verification stays in `receipt_state`, at run time.
  - It uses the same date parse as `receipt_state`, so `REWRITE-<date>.md` is not taken for a
    receipt (D0183).
- **`_gov.STORED_VERDICT_RE`** matches a stored verdict in either spelling a projection has
  used (`Attention receipt: **FRESH**`, and the digest's bulleted form). It is anchored at the
  line start, because record titles quoted in DECISIONS.md legitimately mention the words:
  D0215's own title does.
- **`gen_decisions`** changes as follows:
  - It renders `receipt_line` instead of the verdict.
  - The status column is `Status (recorded)`.
  - The intro says where the date-dependent computation now lives.
  - `today` is accepted and ignored, so the call site keeps one signature.
- **`gen_digest` is unchanged.** The digest still renders the verdict line and every
  effective status. It is dated, and nothing recompares it (RT-07 is a separate, standing
  finding).
- **`check_decisions`** still computes the verdict and prints it (`attention receipt: …`), and
  still prints every Tier-B veto clock with its effective status. The RT-M2-05 comparison is
  replaced by two checks:
  - DECISIONS.md must contain no stored verdict. This keeps RT-M2-05's failure — a tracked
    file asserting FRESH after the receipt went stale — impossible, by removing the claim
    rather than checking it harder.
  - DECISIONS.md must contain exactly `receipt_line(root)`.
- **Sharing `receipt_line` between generator and guard is deliberate,** as with `input_hash`.
  Its output is a pure function of files in the commit, so the comparison is a freshness
  check. D0141's objection to a shared renderer was about a clock verdict whose correctness
  the guard had to judge, and none is left in this file.

**The input hash is NOT widened to cover `receipts/`.** The receipt line is compared directly
against the tree, which is strictly stronger than a header hash: a hash in a header cannot
see an edit to the body, the point `ROADMAP.md` §8 item 5 makes. Widening as well would
report one stale projection twice, under two messages.

**Tests move with it.**
- `tests/test_tier_c_signatures.py`: the `run()` helper wrote the verdict line from
  `receipt_state` at a fixed date. It now writes `receipt_line`.
- `tests/test_decisions_projection.py` (new):
  - The D0215 control. Render; move the date past a Tier-B veto; mint `m9-close`; assert not
    one byte moved, and that the Tier-B row shows the recorded status.
  - The detector fires on both spellings and not on a quoted title.
  - A stored verdict is refused, with its positive control.
  - The guard still prints the verdict and the veto clock.
  - A receipt line that disagrees with the tree is refused.
  - A `REWRITE-*.md` attestation is ignored.

## What applying it does to the tree, in order

1. **Immediately after `git apply`,** `check_decisions` is RED with two violations: *stores an
   attention-receipt verdict*, and *receipt line does not match*. The input-hash header does
   NOT move, because no decision record changed, so only the new checks can see that
   `DECISIONS.md` must be regenerated. That is the check doing its job, and it means **the
   driver runs `gen_projections.py` in the same step**, not at step 9.
2. After regeneration it is green. `CONCEPTS.md` is byte-identical; `DECISIONS.md` changes
   in 11 lines (header paragraph, receipt line, column name, three Tier-B rows).
3. **Step 9 must regenerate AFTER the receipt is written,** or the committed receipt line names
   the previous receipt and the pre-commit `check-decisions` hook refuses the commit.

## Watched failing, 2026-09-13, in a scratch clone — never the real tree

The control reproduces D0215's shape:
1. Enrol a throwaway `owner@tannen` key in the clone.
2. Write and sign `receipts/2026-09-13.md` and regenerate projections, so the line reads
   "fresh (no milestone boundary since)".
3. Commit.
4. Mint a boundary-shaped tag `m9-close` on that same commit. `BOUNDARY_TAG_RE` matches
   `.+-close`, and `boundary_tag_dates` reads its creator date, 2026-09-13.

Runs used `TANNEN_CHECK_DECISIONS_NESTED=1`, **RT-08's hatch**, which skips pytest-binding
resolution. That is acceptable here only because the property under test is the projection
comparison, which the hatch does not touch.

| # | Guard | Tree | Verdict |
|---|---|---|---|
| a | shipped | fresh projection, no new tag | OK |
| b | shipped | **same commit**, `m9-close` minted | **FAIL — "attention-receipt line is not what today computes ('… fresh until 2026-09-20 (boundary 2026-09-13 + 7d)')". D0215, reproduced.** |
| c | patched | patch applied, projection not yet regenerated | FAIL — *stores a verdict* + *receipt line does not match* |
| d | patched | regenerated and committed, no new tag | OK |
| e | patched | **same commit**, `m9-close` minted | **OK**, while printing `attention receipt: FRESH — … fresh until 2026-09-20` |
| f | patched | same commit, `--today 2026-12-31` | **OK**, while printing `attention receipt: STALE — … 7 days elapsed` |
| g | patched | row (e)'s tree with the old verdict line hand-restored | FAIL — both checks name it |

Rows (b) and (e) are the decisive pair: one commit, one tag, and opposite verdicts from the
shipped and patched guards. Row (f) shows that the clock half is gone as well as the tag half.
Row (g) is the control against a remedy that merely stopped looking.

Also run in the clone:
- `git apply --check` of the patch on a fresh clone of HEAD `5762439`: clean.
- `pytest tests/test_decisions_projection.py tests/test_tier_c_signatures.py
  tests/test_roadmap.py tests/test_receipt_chain.py`: 36 passed.
- `tests/test_governance_scripts.py -k "receipt or projection or …"`: 3 passed.

## Verification, after the owner applies it

```
.venv/bin/python -I -P scripts/gen_projections.py     # DECISIONS.md loses its verdict line
.venv/bin/python -I -P scripts/check_decisions.py     # green; still PRINTS the verdict
uv run pytest tests/test_decisions_projection.py tests/test_tier_c_signatures.py -q
.venv/bin/python -I -P scripts/gen_custody.py         # three custody rows move; step 7 re-signs
```

## What it does not do

- **It does not repair the three existing close tags.** Their commits are immutable and still
  carry the old line. Checking them out and running the SHIPPED guard stays red. Running the
  guard from any commit after this lands is green on them only if that guard is used, which
  it is not: a checkout runs its own scripts.
- **The digest is still not header-verified** (RT-07, unchanged).
- **Nothing changes about who is told a receipt is stale.** The run prints it and the digest
  renders it. BRIEF §9.1's consequence — Tier-B consent suspended — is computed exactly as
  before.
