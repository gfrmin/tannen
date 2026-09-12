# Proposal: check_manifest compares ceilings against the CURRENT milestone's envelope

**Status:** queued for the M4 boundary sitting, and a precondition to the first nonzero
envelope. Owner ruling of 2026-09-12, recorded as decision D0240 item (3); the defect is
D0229 item (5), filed at M4 Session A precisely so it would not be discovered mid-ceremony.

`scripts/check_manifest.py` is in `governance/tier-c.yaml`'s `custody.set`. **This was
measured, not assumed:** appending a single comment line to the file turns the gate red with

```
check_manifest: FAIL (1 violation(s))
  - custody drift: scripts/check_manifest.py changed since the custody file was written.
    Any owner signature over it no longer covers these bytes ...
```

and reverting restores `check_manifest: OK`. So this is an owner-applied edit plus a
re-signature, not builder work — as D0229 item (5) already said of both its sides. The
ruling called it builder work; that is the one part of the ruling this draft corrects.

## The defect this closes

`governance/policy.yaml` has always said a ceiling may never exceed the **current**
milestone's envelope. The guard compares against the **maximum over all of them**:

```python
envelopes = (load_yaml(root / policy_rel) or {}).get("budget_envelopes", {})
max_envelope = max(envelopes.values(), default=0)
```

Inert while every envelope is zero — `max({0,0,0,0,0,0}) == 0` — and live the moment the M4
budget sitting raises one, which is the sitting this would bite. Raise M5's envelope to fund
a later milestone and every earlier milestone's ceilings are authorised to M5's number.

## The patch

Add a helper beside the other module-level functions in `scripts/check_manifest.py`:

```python
def current_milestone(root: Path) -> str | None:
    """The milestone this repository is in, DERIVED from MANIFEST.sha256's own rows.

    Never written down: a hand-maintained "current milestone" constant lags by exactly one
    boundary, which is the shape D0095 argued about `required_tags`, D0142 about the oracle
    map and D0169 about the milestone list (D0171 ruling (3), D0211). A milestone is frozen
    when its spec and its law files both carry manifest rows; the highest such is the one in
    flight. `m<digits>` only — docs/specs/ also holds forward-correction files such as
    m3-corrections.md, and a looser match silently invents a milestone (gen_roadmap.py:241).
    """
    manifest = parse_manifest(root / "MANIFEST.sha256")
    is_milestone = lambda name: name.startswith("m") and name[1:].isdigit()  # noqa: E731
    specs = {p.split("/")[-1][:-3] for p in manifest
             if p.startswith("docs/specs/") and p.endswith(".md")}
    laws = {p.split("/")[2] for p in manifest if p.startswith("tests/laws/")}
    frozen = {m for m in specs & laws if is_milestone(m)}
    return f"M{max(int(m[1:]) for m in frozen)}" if frozen else None
```

Then replace the comparison inside `check_tier_c_consistency` (currently the
`elif budget_rel and (root / budget_rel).exists():` branch) with:

```python
    elif budget_rel and (root / budget_rel).exists():
        # BRIEF §9.2: operational SpendGuard ceilings may never exceed what the
        # owner-signed policy envelopes authorise (Tier-C door: spend-envelopes) — the
        # CURRENT milestone's envelope, which is what policy.yaml has always said and what
        # this comparison did not do. Taking the maximum over all milestones meant a raised
        # LATER envelope silently authorised every earlier milestone's ceilings
        # (D0229 item (5); owner ruling D0240 item (3)).
        envelopes = (load_yaml(root / policy_rel) or {}).get("budget_envelopes", {})
        ceilings = (load_yaml(root / budget_rel) or {}).get("ceilings", {})
        current = current_milestone(root)
        if current is None:
            fail.add(
                "no milestone has both a frozen spec row and frozen law rows in "
                "MANIFEST.sha256, so there is no current envelope to compare ceilings "
                "against — a comparison with no basis admits everything"
            )
        elif current not in envelopes:
            fail.add(
                f"policy.yaml names no budget envelope for {current}, the current "
                f"milestone — a missing envelope authorises nothing, and falling back to "
                f"the other milestones' values would authorise the largest of them"
            )
        else:
            for name, value in sorted(ceilings.items()):
                if value > envelopes[current]:
                    fail.add(
                        f"budget.yaml ceiling {name}={value} exceeds {current}'s policy.yaml "
                        f"budget envelope ({envelopes[current]}) — Tier-C door spend-envelopes"
                    )
```

**Note the control flow.** The original branch falls through to the import-linter contract
checks below it; this replacement uses `if/elif/else` and adds no `return`, so those checks
still run. An early return here would silently stop enforcing the `forbidden_imports`
single-source rule — D0016's guard — which is a worse bug than the one being fixed.

## Watched failing, 2026-09-12, before this draft was written

A guard nobody has watched fail is not yet a guard (CONTRIBUTING.md), and a patch whose
behaviour was only reasoned about is not evidence. Both decision rules — the shipped one and
the replacement — were run over scratch envelope/ceiling pairs, with **no** change to the
real `budget.yaml` or `policy.yaml`. Verdicts as measured:

| # | Scenario | Shipped rule | Patched rule |
|---|---|---|---|
| a | `M5: 1000`, current milestone at `0`, ceilings `total=500 fetch=500` | **PASS — the defect** | FAIL: `fetch=500 exceeds M4 envelope (0)`, `total=500 exceeds M4 envelope (0)` |
| b | current milestone at `1000`, same ceilings | PASS | PASS |
| c | the current milestone's key deleted | **PASS — silently compares against the others** | FAIL: `policy.yaml names no envelope for M4` |
| d | the real tree, untouched | PASS | PASS |

Row (a) is the bug: a raised *later* envelope authorising ceilings under an earlier
milestone. Row (b) is the control that matters — a rule that fired in both directions would
be no better than the one it replaces. Row (c) is the branch that did not exist before.

Row (d) is the positive control on the derivation itself: `current_milestone` reads **M4**
off the real `MANIFEST.sha256`, so the helper is not merely returning `None` and taking the
quiet path. On the real tree the patch changes nothing today — every envelope is zero, so
`max(...) == envelopes[current] == 0`, and every ceiling is zero. That is the point: it is
applied while it is inert, so the sitting that raises an envelope is not also the sitting
that first exercises the guard.

## Verification, after the owner applies it

```
.venv/bin/python -I -P scripts/check_manifest.py   # still OK on the real tree
.venv/bin/python -I -P scripts/gen_custody.py      # custody.sha256 covers the new bytes
bash scripts/custodian.sh --check-only             # after the owner re-signs custody.sha256
uv run pytest tests/test_governance_scripts.py -q  # the guard's own suite
```
