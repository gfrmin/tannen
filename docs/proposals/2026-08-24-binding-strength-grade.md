# Proposal: binding strength as a schema field (owner-applied; frozen path)

**Status:** queued for the M0→M1 boundary sitting (decision D0052).
`governance/schemas/decision-record.schema.json` is frozen (`MANIFEST.sha256` row 4), so
the builder cannot apply this. The report-side changes in `scripts/` are not frozen but
are useless without the schema half, so both are drafted here and land together.

## The problem

A binding either *prevents or detects* a violation, or it merely *records that someone
meant to*. `check_decisions` cannot tell the difference: it resolves a binding and
reports the record as enforced. Two examples written today, both green, both honest, and
not remotely equivalent in strength:

- **D0051** binds `manifest: DELEGATIONS.md`. The file is now in `MANIFEST.sha256`, so an
  edit fails `sha256sum -c`, fails `check_manifest`, and is rejected by the pre-commit
  frozen-paths hook. Violating the decision is mechanically hard.
- **D0048** binds `file: docs/proposals/2026-08-24-policy-in-repo-mechanics.md`. The file
  exists. That is the whole check. It proves the remedy was drafted; it detects no
  violation of anything, because the clause it proposes is not yet in force.

Both currently count identically toward "2 unenforced (with reasons)". The distinction
was written as prose inside D0048's binding `detail` — which works exactly once, for a
reader who happens to open that record. Prose in a `detail` field is not a projection and
cannot be counted, so the digest cannot show the owner how much of the enforcement
surface is real.

This matters most at precisely this moment: the boundary sitting's whole purpose is to
convert a batch of documentary bindings into enforced ones, and there is currently no
number that measures whether that happened.

## The patch — schema half

In `governance/schemas/decision-record.schema.json`, inside
`properties.bindings.items.properties`, add:

```json
"strength": {
  "enum": ["enforced", "documentary"],
  "description": "enforced: the target mechanically prevents or detects violation of this decision (a frozen path, a passing test, a consumed config key, a guard). documentary: the target records the intent — a drafted patch awaiting owner application, a prose rule no guard states — and detects nothing. Absent is read as 'enforced', so existing records keep their meaning; new records state it."
}
```

`additionalProperties: false` is already set on the binding object, which is why this
cannot be adopted incrementally by writing the field first and patching the schema later.

## The patch — report half

In `scripts/_gov.py`, alongside `ratchet_metrics`:

```python
def binding_strengths(records: list[dict]) -> tuple[int, int]:
    """(enforced, documentary) binding counts. Absent strength reads as enforced, so
    pre-D0052 records are unchanged by this metric — see the sequencing note below."""
    enforced = documentary = 0
    for record in records:
        for binding in record["bindings"]:
            if binding.get("strength", "enforced") == "documentary":
                documentary += 1
            else:
                enforced += 1
    return enforced, documentary
```

In `scripts/check_decisions.py`'s summary line, report the split; in
`scripts/gen_projections.py`, add a digest line under the ratchet section:

```
- Bindings: **N enforced**, **M documentary** (M awaiting owner application)
```

## Sequencing hazard — read before applying

Do **not** simply add `documentary` to the ratchet's `<!-- metrics: -->` comment on the
day the schema lands. Until the schema allows the field, every record counts as
`documentary=0`; a digest generated in that state establishes a **zero baseline**, and
the first honestly-marked documentary binding after it would register as a ratchet
breach. The ratchet would then be punishing accurate self-reporting, which inverts it.

Apply in this order:

1. Land the schema field and the report half; mark the existing bindings honestly
   (D0048, D0050, D0052, D0053 are documentary today; D0051 is enforced).
2. Generate the digest **with the corrected numbers**. That digest is the first
   baseline for `documentary`.
3. Only then add `documentary` to `check_ratchet`'s enforced comparisons.

The same hazard is generic to every new ratcheted metric: a metric must be *true* for one
digest before it is *enforced* from the next. Worth stating in BRIEF §9.1 if the pattern
recurs — flagged, not proposed, since §9.1 is owner text.

## Verification after applying

1. `uv run python scripts/check_decisions.py` → summary reports the enforced/documentary
   split; all records still valid.
2. `uv run pytest` → green (`tests/test_governance_ratchet.py` unaffected until step 3).
3. `make digest` → the digest shows the split, and the count of documentary bindings
   falls as each proposal in this batch is applied.
