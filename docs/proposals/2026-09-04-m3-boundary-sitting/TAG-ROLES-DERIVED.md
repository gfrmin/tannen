<!-- Builder draft under owner ruling (2) of 2026-09-09 (D0201), on the audit's recommendation
     (D0202). NOTHING HERE IS INSTALLED. Both targets are frozen AND custody-set, so this lands
     under the owner's key at a sitting. -->

# `required_tags`, derived — and step 11 deleted

D0202's one substantive recommendation, drafted so it can be installed at the M3 sitting rather
than waiting a boundary. It is D0095 half (2), whose own record says it "is applied by NOTHING,
which is why step 11 of every sitting still adds that boundary's tags by hand."

## The defect

`governance/tag-roles.yaml:46-54` is a hand-maintained enumeration, read at
`scripts/check_tag_signers.py:151`. It lags by exactly one milestone at every boundary: today it
lists `m3-laws-freeze` but not `m3-close`, and the only thing that ever fixes that is a human
remembering, at step 11, under the owner's key. That is the enumeration class D0171 ruling (3)
made a standing rule against.

## The rule

```
brief-freeze                 always required
<m>-laws-freeze   required   <=>  docs/specs/<m>.md exists
<m>-close         required   <=>  docs/specs/<m+1>.md exists
```

The close rule reads: **a milestone whose successor has a spec must have been closed**, because a
successor's Session A cannot happen before the predecessor's boundary sitting. That is BRIEF §8's
own ordering, not a new constraint.

## The positive control: it reproduces today's list exactly

Derived from the four spec files present, against the eight hand-written entries:

| Derived | Hand-maintained today |
|---|---|
| `m0-laws-freeze`, `m1-laws-freeze`, `m2-laws-freeze`, `m3-laws-freeze` | same four |
| `m0-close`, `m1-close`, `m2-close` | same three |
| `brief-freeze` | same |

**Eight for eight, no drift** — so the rule is not merely plausible, it is the rule the list was
already trying to express. And it self-extends: when `docs/specs/m4.md` lands at M4 Session A,
`m3-close` becomes required automatically. That is the lag, closed by construction.

## Why it cannot be gamed circularly

The obvious wrong derivation is "require the tags that exist", which is vacuous — the whole point
of `required_tags` is to detect a **deleted** tag, so the source must not be the tag set. This
derivation reads `docs/specs/*.md`, and **every one of those files is frozen in
`MANIFEST.sha256`** (`:2`, `:45`, `:66`, `:76`). So:

- **Delete a spec to shed a requirement** → `check_manifest` fails first, on a missing frozen
  path. Fails safe, and fails in a different guard, so one edit cannot silence both.
- **Add a fake `docs/specs/m9.md` to require a tag that cannot exist** → `check_tag_signers`
  fails loudly on a missing required tag. The derivation errs toward requiring *more*, never
  fewer, which is the correct direction for a floor.
- **Shallow clone / export without tags** → unchanged behaviour: every derived tag is missing and
  every one is reported, exactly as RT-15 intends.

## The change

**`governance/tag-roles.yaml`** — `required_tags` is deleted and replaced by a marker, so a
future editor cannot re-add a hand list without the guard noticing:

```yaml
# required_tags is DERIVED, never enumerated — see scripts/check_tag_signers.py.
# A hand-written list here lags by exactly one milestone at every boundary, which is
# what step 11 of every prior sitting existed to patch (D0095 half 2, D0171 ruling 3).
# The key is retained and MUST stay empty; a non-empty value is refused, so re-adding
# an enumeration is a red gate rather than a silent regression.
required_tags: []
```

**`scripts/check_tag_signers.py`** — replace the `table.get("required_tags")` read at `:151`:

```python
    declared = table.get("required_tags") or []
    if declared:
        fail.add(
            "required_tags is enumerated in tag-roles.yaml, and it is derived — a hand "
            "list lags one milestone at every boundary (D0095 half 2, D0171 ruling 3). "
            f"Remove these and let the rule derive them: {', '.join(declared)}"
        )
    for required in derive_required_tags(root):
        if required not in tags:
            fail.add(
                f"required tag missing: {required} — the tag set is part of the custody "
                "floor, not an optional decoration (RT-15). A shallow clone or an export "
                "that arrives without tags is indistinguishable from one where they were "
                "deleted, so both are refused here."
            )
```

with, beside it:

```python
def derive_required_tags(root):
    """The tags a tree must carry, DERIVED from the frozen specs rather than enumerated.

    `brief-freeze` always; `<m>-laws-freeze` for every milestone with a spec; `<m>-close`
    for every milestone whose SUCCESSOR has a spec, since a successor's Session A cannot
    precede its predecessor's boundary sitting (BRIEF 8).

    The source is `docs/specs/*.md`, every one of which is frozen in MANIFEST.sha256 — so
    deleting one to shed a requirement reddens check_manifest first, in a different guard.
    Deriving from the TAG SET would be vacuous: detecting a deleted tag is the whole job.
    """
    specs = {p.stem for p in (root / "docs" / "specs").glob("m*.md")}
    nums = sorted(int(s[1:]) for s in specs if s[1:].isdigit())
    required = {"brief-freeze"}
    required |= {f"m{n}-laws-freeze" for n in nums}
    required |= {f"m{n}-close" for n in nums if (n + 1) in nums}
    return sorted(required)
```

## The poison fixture, and watching it fail first

`tests/poison/tag-roles-derived/` — a tree carrying `docs/specs/m0.md` … `docs/specs/m4.md` and
tags for everything **except `m3-close`**. The guard must FAIL, and for its own reason: the
message must name `m3-close`, not merely be non-zero. One fixture, one reason.

Watched failing first, in this order — the discipline CONTRIBUTING.md states as "a test that has
never been watched failing is not yet a test", and the discipline D0199 exists because it was
skipped:

1. **Negative control**: run the guard against the fixture *before* installing the derivation.
   It must PASS — the hand list does not contain `m3-close`, so nothing is missing. That passing
   run is the defect, demonstrated.
2. Install the derivation. Re-run: it must now FAIL naming `m3-close`.
3. **Positive control**: run against the real tree. It must be green, and green because the
   derived set equals the eight tags that exist — assert the derived set explicitly, so a rule
   that derived *nothing* could not also look green. This is D0199's lesson exactly: the guard
   that reports "fails its poison as required" over a fixture testing a tautology.
4. **Anti-regression**: a second fixture, or the same one with `required_tags: [m0-close]`
   restored, must FAIL on the enumeration-refusal branch.

## What it buys, and what it costs

Deleting step 11 removes, from every future sitting: one `make verify` leg, one round of
pre-commit hooks, one commit, and **the second of the two owner custody signatures**. Measured
against the M3 rehearsal that is ~30 minutes and one signature moment per boundary, permanently —
~100 minutes to ~55-65, five owner signature moments to four.

The cost is honest: this edits a custody-set guard, and D0199 is the standing lesson that a guard
nobody has watched failing is a silent floor failure. It must land **with** its fixture, and
`tests/poison/` is BRIEF §9.1 author-key territory — so both halves are the owner's, at the same
sitting, in that order.

## Order at the sitting

Install the fixture (step 5, author-key territory) → install the guard and the `tag-roles.yaml`
marker → run the custodian and watch the new `poison` line bite → re-sign the custody set (both
files are custody-set members, so their hashes move). **Step 11 is then deleted from the M4
driver, not this one** — this sitting still needs it, because `m3-close` does not exist until
step 10 mints it and the derivation does not require it until `docs/specs/m4.md` exists.
