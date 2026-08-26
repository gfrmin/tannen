# The receipt clock cannot start on the day it is set

**Status: drafted, not binding. Needs the owner's key** — `scripts/_gov.py` is in the
custody set (`governance/tier-c.yaml` `custody.set`), so a builder editing it turns the
gate red until `governance/custody.sha256` is re-signed. **D0073 rescheduled this from the
M1 boundary sitting to the M1 laws freeze**, applied by the owner, on the reasoning that
the laws freeze is itself a milestone boundary and the defect is live in the meantime.
Neither `scripts/_gov.py`, `governance/custody.sha256` nor `tests/test_governance_scripts.py`
is in `MANIFEST.sha256`, so the frozen-path guard is not involved at any step — only the
custody signature is.

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

`tests/test_governance_scripts.py` (not a frozen path and not in the custody set, so this
half can land any time — but landing it before the patch would leave the gate red, so land
them together):

```python
def test_same_day_boundary_starts_the_receipt_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    """A boundary minted the SAME DAY as the receipt must start the seven-day clock.

    The sitting takes the receipt and mints the close tag minutes apart (docs/SITTING.md),
    so if a same-day boundary does not count then no close tag ever does, and Tier-B
    silence-as-consent never suspends (BRIEF §9.1, D0071).

    The boundary set is substituted rather than read from refs/tags, and that substitution
    IS the test. BOUNDARY_TAG_RE matches `.+-laws-freeze`, so this repo accumulates
    boundaries dated after the latest receipt as a matter of routine; against the live tag
    set the unpatched `>` reaches the same verdict by a different route, and the assertion
    goes quiet without ever failing. Exactly one boundary, on the receipt's own day, is the
    only arrangement that tells `>` and `>=` apart.
    """
    import datetime as dt
    import sys
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import _gov

    rdate = max(dt.date.fromisoformat(p.stem) for p in (REPO_ROOT / "receipts").glob("*.md"))
    long_after = rdate + dt.timedelta(days=30)

    monkeypatch.setattr(_gov, "boundary_tag_dates", lambda root: [rdate])
    fresh, detail = _gov.receipt_state(REPO_ROOT, long_after)
    assert not fresh, f"a same-day boundary did not start the clock: {detail}"

    # The half the patch must NOT change: a boundary strictly BEFORE the receipt is one
    # the receipt already answers for, so it does not start a clock against it.
    monkeypatch.setattr(_gov, "boundary_tag_dates",
                        lambda root: [rdate - dt.timedelta(days=1)])
    fresh, detail = _gov.receipt_state(REPO_ROOT, long_after)
    assert fresh, f"an earlier boundary wrongly started the clock: {detail}"
```

Verified to discriminate, 2026-08-26, by loading the current `scripts/_gov.py` and a
`>=`-patched copy side by side against this repository's real receipts:

```
current (>)    same-day boundary -> (True,  'fresh (no milestone boundary since)')   FAIL
patched (>=)   same-day boundary -> (False, 'stale: boundary 2026-08-25 + 7 days elapsed')
current (>)    earlier boundary  -> (True,  ...)   patched (>=) earlier boundary -> (True, ...)
```

### Why the first draft of this test had to be replaced

The version drafted on 2026-08-25 called `receipt_state(REPO_ROOT, today + 30d)` against
the live tag set and asserted `not fresh`. That was sound on the day it was written, when
every boundary tag was dated on or before the receipt. It stops being sound the moment
`m1-laws-freeze` exists: the tag is itself a boundary (`BOUNDARY_TAG_RE` matches
`.+-laws-freeze`), it is dated 2026-08-26, and `2026-08-26 > 2026-08-25` is true under the
*unpatched* comparison — so the receipt goes stale on 2026-09-02 with or without the fix
and the assertion passes either way. A regression test that borrows its condition from
mutable repository state stops testing the regression as soon as that state moves; this is
the same defect D0091 found in the ratchet tests, which staged their breach against the
live unenforced count and went quiet when it reached zero.

## What applying it does to the current state

With the patch, the 2026-08-25 receipt is fresh until **2026-09-01** (`m0-close` + 7 days).
The three open Tier-B veto clocks (D0006, D0014, D0020) all close **2026-08-31**, inside
that window, so applying this costs nothing today: no record moves from consented to
blocked. The first real effect is that M1's Tier-B decisions need a receipt within a week
of the M1 laws freeze — which is the design.

Restated for 2026-08-26, since the numbers moved by one day and the direction is worth
being exact about. Once `m1-laws-freeze` exists the clock starts either way, because that
tag is a boundary dated after the receipt; what the patch changes is *which* boundary it
starts from. `later[0]` becomes `m0-close` (2026-08-25) instead of `m1-laws-freeze`
(2026-08-26), so the receipt goes stale on **2026-09-01** rather than 2026-09-02. The
patch tightens the window by a day and, far more importantly, keeps the *next* sitting's
close tag from being invisible in the same way this one was.
