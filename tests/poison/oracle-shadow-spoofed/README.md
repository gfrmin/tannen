# `oracle-shadow-spoofed/` — **needs patch** — the shadow guard authenticates a module by what it says about itself

**Guard:** `src/tannen/laws/plugin.py`'s `LawEvidencePlugin.pytest_collection_modifyitems`
(`_oracle_shadow_problem`), **as widened by RT-M3-04**. Against the shipped check this fixture
does not bite — that is the finding — which is why it is staged here and not in `tests/poison/`.

**Intended violation:** a decoy `_delta_model.py`, faithfully re-exporting the frozen M3 model
(`tests/laws/m3/_delta_model.py`), primed into `sys.modules['_delta_model']` by a `-p`-loaded
bootstrap plugin before `tests/laws/m3/test_l3_differential.py` is collected — **and setting
`__file__` to the frozen file's path**. The shipped guard's whole identity test is

```python
actual_file = getattr(module, "__file__", None)
actual = Path(actual_file).resolve() if actual_file else None
if actual == frozen[0]:
    continue                       # plugin.py:96-99
```

`__file__` is a plain attribute. A module that sets it to the frozen path is, to this check,
the frozen module.

**Why it is needed.** `tests/poison/oracle-shadow-model/` (installed at the M2 sitting) covers
the NAIVE shadow — a decoy honest about where it lives — and the shipped guard catches that one
(verified 2026-09-05: it exits non-zero). So once D0154 item 1 wires `oracle-shadow-model` into
`scripts/custodian.sh`, the custody floor will report this guard exercised and live **while the
bypass that actually reaches the kill criterion goes untested**. BRIEF §9.1's rule is that a
guard which passes its poison is weakened; the sharper case is a guard whose poison corpus tests
only the half it already catches.

**Measured, against the shipped guard** (2026-09-05, sandbox copy; the real tree was never
poisoned):

```
check_differential called on the DECOY stub × 1400
544 passed, 1 xfailed in 648.74s                       # tests/laws — all four milestones
tannen evidence: 52 record(s) written to evidence
check_manifest: OK — frozen paths intact; seals unbroken; custody set current; …
L3.12   ok      pass     hypothesis-derandomize    sha256:94c965b3c7575288…
OK — 52 law(s) carry fresh passing evidence.
```

`check_differential` is BRIEF §6's differential kill criterion and frozen L3.12's entire body.
It was answered 1,400 times by `lambda *a, **k: None`, and the last line above is the
completion criterion CLAUDE.md names for an implementation session.

**Marker:** `RT-M3-04`

**Command that must exit non-zero** (against the patched check, run from the repo root):

```sh
env PYTHONPATH=docs/redteam/fixture-candidates/oracle-shadow-spoofed \
    uv run pytest -p bootstrap_shadow_spoofed tests/laws/m3/test_l3_differential.py -q
```

**Verified 2026-09-05**, both directions, in sandbox copies — with one caveat that cost this
pass a wrong measurement and will cost the next one too. A copied worktree's `.venv` carries
`site-packages/_editable_impl_tannen.pth`, which holds the **absolute path of the original
tree**, so a copy of this repo silently imports the original's `tannen` and any edit under the
copy's `src/` does nothing. Every row below was run with `PYTHONPATH=$PWD/src` prepended and
`tannen.laws.plugin.__file__` checked first. Copied `__pycache__` compounds it cosmetically:
`.pyc` files carry the original tree's `co_filename`, so tracebacks name the real repo even when
the copy's source is what ran.

| against | expected | measured |
|---|---|---|
| shipped guard | passes — reproduces the hole | `exit=0`, `14 passed in 16.91s` |
| patched guard | exits non-zero, naming the substitution | `exit=1`, `answers with different code for ['check_differential']` |
| patched guard, decoy declares `__all__ = []` | still exits non-zero | `exit=1`, same one name |
| clean tree + patch | unchanged | `151 passed` (`tests/laws/m2 tests/laws/m3`); existing `oracle-shadow/` and `oracle-shadow-model/` fixtures both still bite |
| `git apply --check` on a pristine `3528996` | applies | clean |

## The patch: `rt-m3-04-plugin-code-identity.patch`

Compares the **code the module answers with** against a fresh load of the frozen file, function
by function, instead of asking the module where it came from. Three spellings were tried and the
first two were falsified by measurement rather than by review:

1. **`co_filename` per public callable** — rejected. The real model has two functions whose
   `co_filename` is `<string>` (hypothesis builds `stream_tables` and `two_worlds` by `exec`),
   so the check has false positives on the honest module.
2. **`sha256(co_code + repr(co_consts) + repr(co_names))`** — rejected. `repr` of a nested code
   object carries its memory address, so two independent loads of the same file disagreed on
   **ten of sixteen** functions.
3. **Recursive digest over `co_code`, `co_names` and `co_consts`, descending into nested code
   objects** — kept. Two independent loads of the frozen file are identical; the decoy is caught
   on exactly the one function it substituted.

A third defect was then found in the surviving patch, by attacking it: it read the
export list as `module.__all__ or dir(module)` — from the module **under test**, which a decoy
controls. `__all__ = []` fingerprinted nothing and passed. The shipped spelling reads the export
list off the frozen reference only and looks up each name on the module under test; the evasion
then exits non-zero. The fixture sets `__all__` deliberately so the corpus keeps that case.

**What it does not close.** This is defence in depth, not a fix for the naming hazard. A decoy
that `compile()`s its stub from the frozen file's own source text and patches behaviour through
a closure or a mutable default would still need to change *some* code object, so this check has
real teeth — but the actual fix remains the one RT-M1-01 named at M1 and RT-M2-01 repeated at
M2: **a package-qualified import in the frozen law file**, which needs the owner's key because
the law files are frozen. That is now three boundaries of the same recommendation.

**Install cost.** The reference load runs once per frozen oracle per pytest session (five
oracles at M3). Measured as noise against a 26–31s `tests/laws/m3` run.
