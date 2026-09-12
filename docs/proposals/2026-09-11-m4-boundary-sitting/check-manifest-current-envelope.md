# Proposal: check_manifest compares ceilings against the CURRENT milestone's envelope

**Status:** queued for the M4 boundary sitting, and a precondition to the first nonzero
envelope. Owner ruling of 2026-09-12, recorded as decision D0240 item (3); the defect is
D0229 item (5), filed at M4 Session A precisely so it would not be discovered mid-ceremony.

**This patch now carries TWO changes**, by the owner's later ruling of the same day (D0244
item (1)): the envelope comparison below, and the pre-budget lock D0242 item (3) ordered made
mechanical. The lock is folded in here rather than shipped as a third draft because this file
is already being re-signed at this sitting, so the fold costs one custody regeneration and one
signature instead of two. The two changes are therefore signed, or declined, together.

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

## The second change: the pre-budget lock (D0242 item (3), folded here by D0244 item (1))

The deferral of the CLI clamp to M5 Session A (D0241) rests on the gap being inert here — zero
envelopes, zero ceilings, no credentials. The owner's ruling: *"the argument's load-bearing
element is the absence of credentials, which is not enforced by anything — it's a property of
your machine."* So the preconditions bind the first nonzero envelope mechanically.

**Which preconditions this guard can honestly hold, and which it cannot.** Two of the four are
applied by the *same sitting* that installs this code — `policy.yaml`'s sentence
(`policy-envelope-sentence.md`) and the comparison above. A check for those here would be a
patch testing itself, green the moment it was written. So this guard holds exactly the two the
ruling names — "while `governance/laws.yaml` lacks the superseded entry retiring L4.4's third
node and the clamp is absent from `cli.py`" — both owed by M5 Session A, both open today. All
four stay pinned in `tests/test_spend_preconditions.py` (D0243), which can pin the sitting's
output precisely because it is not the sitting's output. Neither artifact is redundant.

Add `import ast` to the imports, and these beside `current_milestone`:

```python
L4_4_CLAMPED_NODE = (
    "tests/laws/m4/test_l4_modes.py::"
    "test_l4_4_tannen_run_spend_is_the_one_spelling_that_can_call"
)


def _nonzero(values: Iterable[object]) -> bool:
    """Whether anything here authorises a spend. A bool is not a budget."""
    return any(isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0
               for v in values)


def _declares_flag(source: str, flag: str) -> bool:
    """Whether `source` DECLARES `flag` as an argparse option, read off the syntax tree.

    Not a grep: a flag named in a docstring, a comment or an error message does not declare
    it, and a guard that learned another artifact's state from its prose is the defect
    D0171 ruling (3) and D0211 forbid. The shape asserted is `<x>.add_argument("<flag>", …)`.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "add_argument"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == flag
        for node in ast.walk(tree)
    )


def unmet_spend_preconditions(root: Path) -> list[str]:
    """D0240's preconditions to the first nonzero envelope that this guard can still see.

    Empty means the pre-budget sitting may proceed. The other two preconditions are applied
    by the sitting that installs this function, so testing them here would be testing this
    patch; `tests/test_spend_preconditions.py` (D0243) pins all four.
    """
    unmet = []
    laws = load_yaml(root / "governance" / "laws.yaml") or {}
    retired = {entry.get("node") for entry in (laws.get("superseded") or [])}
    if L4_4_CLAMPED_NODE not in retired:
        unmet.append(
            f"governance/laws.yaml has no superseded entry retiring {L4_4_CLAMPED_NODE} — "
            "L4.4's third node still says `tannen run --spend` may be called with a budget "
            "of its own, which is the law the clamp reverses (D0240 item (2), D0241)"
        )
    cli = root / "src" / "tannen" / "cli.py"
    source = cli.read_text(encoding="utf-8") if cli.exists() else ""
    if not _declares_flag(source, "--budget-override"):
        unmet.append(
            "src/tannen/cli.py declares no --budget-override, so `tannen run --budget` is "
            "still honoured as handed in and the shortest spelling can spend against a "
            "budget the owner never signed (D0240 item (2))"
        )
    return unmet
```

Then, inside the same `elif` branch, immediately after `envelopes` and `ceilings` are loaded
and **before** the current-milestone comparison:

```python
        # D0242 item (3): the first nonzero envelope is a one-way door, and the deferral of
        # the clamp to M5 Session A rests on this gap being inert here — zero envelopes, zero
        # ceilings, no credentials. The first two are properties of this repository, so they
        # are checked; the third is a property of a machine and cannot be. While ANY spend is
        # authorised at all, the preconditions to authorising it must already be met.
        if _nonzero(list(envelopes.values()) + list(ceilings.values())):
            for problem in unmet_spend_preconditions(root):
                fail.add(
                    "a nonzero budget envelope or ceiling is declared while a precondition "
                    f"to the first spend is open — {problem}"
                )
```

This is an addition inside the existing branch — no replacement, no early `return` — so the
current-milestone comparison below it and the import-linter contract checks after it both
still run, for the same reason the note above gives.

## Watched failing, 2026-09-12, before this section was written

Both decision rules were run over scratch trees, with **no** change to the real
`budget.yaml`, `policy.yaml`, `laws.yaml` or `cli.py`. Verdicts as measured:

| # | Scenario | Verdict |
|---|---|---|
| e | the real tree: every envelope and ceiling zero | PASS — the lock is disarmed |
| f | one envelope nonzero, neither M5 owing landed | FAIL: `superseded-entry`, `clamp` |
| g | one *ceiling* nonzero, envelopes all zero, neither owing landed | FAIL: `superseded-entry`, `clamp` |
| h | one envelope nonzero, **both** owings landed | PASS |
| i | envelope nonzero, entry landed, `--budget-override` only in a **docstring** | FAIL: `clamp` |

Row (i) is the one that earns the AST: a grep would have passed that tree, and a flag that
exists only in prose is exactly the state D0211 forbids a guard to be fooled by. Row (g) proves
the trigger arms on a ceiling and not only on an envelope. Row (h) is the control against a
lock that can never open — a guard that refuses for a reason that cannot clear is an
obstruction, not a gate.

**And the control that changes how row (e) reads.** The probe also printed the real tree's
inputs: every envelope and every ceiling is zero, and `unmet_spend_preconditions` on the real
tree returns **both** identifiers. So (e) passes because the trigger is disarmed, *not* because
the preconditions are met. Without that line, (e) would have read as a clean tree.

## Verification, after the owner applies it

```
.venv/bin/python -I -P scripts/check_manifest.py   # still OK on the real tree (row e)
.venv/bin/python -I -P scripts/gen_custody.py      # custody.sha256 covers the new bytes
bash scripts/custodian.sh --check-only             # AFTER the owner re-signs custody.sha256
uv run pytest tests/test_governance_scripts.py tests/test_spend_preconditions.py -q
```

Regenerating the custody hash does not re-sign it, and a regenerated file under a stale
signature is the alarm rather than a nuisance — the owner affirmed that reading at D0242 item
(2). The last line now also runs D0243's gate: once this patch lands, that gate's
`current-envelope` identifier leaves the open set, which is the announcement that a
precondition landed. Updating the gate is part of the sitting, by ruling (D0244 item (3)).
