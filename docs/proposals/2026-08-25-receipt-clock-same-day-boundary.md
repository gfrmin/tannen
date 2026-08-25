# The receipt clock cannot start on the day it is set

**Status: drafted, not binding. Needs the owner's key** — `scripts/_gov.py` is in the
custody set (`governance/tier-c.yaml` `custody.set`), so a builder editing it turns the
gate red until a sitting re-signs `governance/custody.sha256`. Apply this at the M1
boundary sitting, in the step that installs guard patches.

## The defect

`docs/SITTING.md` states the order and its reason:

> **Takes an attention receipt and mints the close tag** — in that order, so the receipt's
> consent clock starts running against a boundary tag rather than stopping.

It does not. `scripts/_gov.py::receipt_state` compares at day granularity with a strict
inequality:

```python
later = [d for d in boundary_tag_dates(root) if d > rdate]
if not later:
    return True, f"receipt {latest.name} fresh (no milestone boundary since)"
```

`rdate` comes from the receipt's filename (`receipts/2026-08-25.md`), and
`boundary_tag_dates` returns tagger *dates*. A sitting takes the receipt and mints the
close tag minutes apart, so both are the same day and `d > rdate` is false. The boundary
the sitting deliberately placed *after* the receipt does not start the clock — and since
every close tag is minted at the sitting that takes the receipt, no close tag ever will.

Reproduced against this repository on 2026-08-25, with `receipts/2026-08-25.md` present
and `m0-close` tagged 2026-08-25 12:57:38 +0800:

```
$ .venv/bin/python -c "import sys,datetime as dt; sys.path.insert(0,'scripts'); import _gov; \
    from pathlib import Path; print(_gov.receipt_state(Path('.'), dt.date(2026,9,4)))"
(True, 'receipt 2026-08-25.md fresh (no milestone boundary since)')
```

Ten days after the boundary, the receipt still reads FRESH. The consequence is the one
BRIEF §9.1 is built to prevent: **Tier-B silence-as-consent never suspends**, because the
condition that suspends it cannot be reached.

## The patch

```diff
--- a/scripts/_gov.py
+++ b/scripts/_gov.py
-    later = [d for d in boundary_tag_dates(root) if d > rdate]
+    # A boundary minted the same day as the receipt counts. The sitting takes the receipt
+    # and mints the close tag minutes apart (docs/SITTING.md), so a strict `>` at day
+    # granularity excluded every close tag this project will ever make, and the clock the
+    # ordering exists to start could never start.
+    later = [d for d in boundary_tag_dates(root) if d >= rdate]
```

A boundary dated *before* the receipt is still excluded, which is the intended reading: a
receipt taken after a boundary is a fresh attestation, not a late one.

## The test to add alongside it

`tests/test_governance_scripts.py` (not a frozen path, so this half can land any time —
but landing it before the patch would leave the gate red, so land them together):

```python
def test_same_day_boundary_starts_the_receipt_clock(tmp_path: Path) -> None:
    """A close tag minted the same day as the receipt must start the seven-day clock.

    The sitting takes the receipt and mints the tag minutes apart, so if a same-day
    boundary does not count, no boundary ever does and Tier-B silence-as-consent never
    suspends (BRIEF §9.1).
    """
    import datetime as dt
    import sys
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import _gov

    fresh, detail = _gov.receipt_state(REPO_ROOT, dt.date.today() + dt.timedelta(days=30))
    assert not fresh, f"receipt still fresh a month past the boundary: {detail}"
```

## What applying it does to the current state

With the patch, the 2026-08-25 receipt is fresh until **2026-09-01** (`m0-close` + 7 days).
The three open Tier-B veto clocks (D0006, D0014, D0020) all close **2026-08-31**, inside
that window, so applying this costs nothing today: no record moves from consented to
blocked. The first real effect is that M1's Tier-B decisions need a receipt within a week
of the M1 laws freeze — which is the design.
