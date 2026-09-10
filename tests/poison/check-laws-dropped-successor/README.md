# `check-laws-dropped-successor` — the guard that can retire a frozen law had no fixture

**D0154 item (7)**, and one of the three items D0171 ruling (4) keeps IN the M3 sitting.

`scripts/check_laws.py` is in the custody set (`governance/tier-c.yaml`), and it is the
**only** custody-set guard with neither a fixture under `tests/poison/` nor a `poison`
line in `scripts/custodian.sh` — verified: `grep check_laws scripts/custodian.sh` is
empty in the live file. So BRIEF §9.1's guard-liveness-by-poison discipline does not
cover the guard that decides whether a retired law still carries its claim forward.

**What is missing is not the test.** The behaviour is already covered by
`tests/test_law_validation.py::test_check_laws_refuses_a_supersession_whose_successor_no_law_defines`,
which builds a tree with successor `L9.404` and asserts a non-zero exit. That file is
**unfrozen and uncustodied** — an ordinary file any builder may edit, delete or weaken,
with no signature over its bytes. What is missing is the CUSTODY FLOOR exercising it.
Every other custody-set guard is watched failing by `custodian.sh` on every run, under
the owner's signature; this one is not. RT-M3-02 names the same shape one layer down:
"pinned by one unsealed test and by no frozen law".

## What the tree is

A miniature repository, passed to the guard with `--root`, exactly as the
`check-decisions-*` and `check-concepts-*` fixtures are:

| Path | Why it is here |
|---|---|
| `governance/laws.yaml` | The defect: a `superseded` entry naming successor `L9.99`, which no law file in the tree defines. D0106 ruling 2's rule — a law found wrong is superseded FORWARD — with nothing carrying it forward. |
| `tests/laws/m1/test_l1_poison.py` | Defines `test_l1_7_a_law_that_was_retired`, the node the registry retires. Without it the tree would fail on "is not a law node" instead, and the marker would not mean what it says. Parsed with `ast`, never executed. |
| `decisions/0001-poison-the-record-that-retired-l1-7.yaml` | Carries `id: D0001` so the entry's `record` field resolves. Without it the tree fails for TWO reasons and the marker stops distinguishing them. |

There is deliberately **no `MANIFEST.sha256`**, so no law file counts as frozen and
`check_declarations` requires nothing. One fixture, one reason.

## Verified, not asserted

```
$ .venv/bin/python -I -P scripts/check_laws.py --root <this tree>
check_laws: FAIL (1 violation(s))
  - governance/laws.yaml: tests/laws/m1/test_l1_poison.py::test_l1_7_a_law_that_was_retired
    names successor L9.99, which no law file defines — a claim retired with nothing
    carrying it forward is a claim dropped (D0106)
exit=1
```

And the **positive control**, which is what says the refusal is about the successor and
not about the tree being odd — with `successor: "L1.7"`, a law this tree does define:

```
check_laws: OK — 0 frozen law file(s) declare their validation, 0 exempt …;
1 superseded/pending node(s) name a live successor
exit=0
```

## Installing it (the owner, at the sitting)

1. `git mv docs/redteam/fixture-candidates/check-laws-dropped-successor tests/poison/`
2. A row per file in `MANIFEST.sha256`.
3. A row in `tests/poison/README.md`'s table.
4. The `poison` line — already drafted, as **HUNK 5** of this sitting's `custodian.sh`:

```sh
poison check_laws "which no law file defines" \
    "$PY" -I -P scripts/check_laws.py --root tests/poison/check-laws-dropped-successor
```

Step 5 installs fixtures and step 6 installs the custodian, so that ordering is already
right. Until step 5 runs, the drafted line refuses — and says so accurately rather than
claiming the guard is weakened; see the note on hunk 1a.
