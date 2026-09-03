# `oracle-shadow-model/` — **needs patch** — the M2 differential oracle answers to a name, not an identity

**Guard:** `src/tannen/laws/plugin.py`'s `LawEvidencePlugin.pytest_collection_modifyitems`
(`_oracle_shadow_problem`), **as widened by RT-M2-01**. Against the shipped check this fixture
does not bite, which is why it is staged here and not in `tests/poison/`.

**Intended violation:** a decoy `_model.py`, faithfully re-exporting the real frozen M2 model
(`tests/laws/m2/_model.py`), primed into `sys.modules['_model']` by a `-p`-loaded bootstrap
plugin BEFORE `tests/laws/m2/test_l2_differential.py` is collected — so the frozen file's bare
`import _model as M` receives the decoy. Run against the **real** frozen law file, the same way
`lint-imports-kernel/` runs against the real contracts, so it goes silent exactly when the check
is neutered.

**Why it is needed:** this is the one M2 finding that reaches BRIEF §6's kill criterion directly,
without touching a frozen or manifested byte. `tests/poison/oracle-shadow/` covers `_fragment`
only — the M1 name — while M2 added `_model` and `_subject`, bare-imported across seven frozen
law files. `tests/` is not a sealed directory (`governance/tier-c.yaml:77-80` seals `tests/laws`,
`tests/poison`, `governance/schemas`), so neither decoy file needs a manifest row.

**Marker:** `RT-M2-01`

**Command that must exit non-zero** (against the widened check, run from the repo root):

```sh
env PYTHONPATH=docs/redteam/fixture-candidates/oracle-shadow-model \
    uv run pytest -p bootstrap_shadow_model tests/laws/m2/test_l2_differential.py \
    -k test_l2_9 -q
```

**Verified** (2026-09-01, against the **shipped** check — i.e. the fixture reproduces the hole):

```
$ env PYTHONPATH=docs/redteam/fixture-candidates/oracle-shadow-model TANNEN_NO_EVIDENCE=1 \
      .venv/bin/python -m pytest -p bootstrap_shadow_model \
      tests/laws/m2/test_l2_differential.py -q
34 passed in 12.86s

$ python -c "import _model; print(_model.__file__)"
…/docs/redteam/fixture-candidates/oracle-shadow-model/_model.py
re-exports check_differential: True     SHAPES count: 17
```

The decoy answers to the name, the plugin's abort never fires, and every test passes.

**And the payload, verified separately** — with `check_differential` stubbed to `return None` in
the decoy, L2.9 becomes vacuous and the whole M2 suite is still green, with the manifest clean:

```
[PROBE] marker = HOSTILE decoy: check_differential neutered
34 passed          (test_l2_differential.py — L2.9 now asserts nothing)
113 passed         (tests/laws/m2 entire)
check_manifest: OK — frozen paths intact; seals unbroken; custody set current; …
```

**Patch this fixture needs before installation** — `src/tannen/laws/plugin.py`, replacing the
single-name constants at lines 50-51:

```python
#: Oracle modules imported by bare name from frozen law files, per milestone directory.
#: A single hardcoded name was RT-M1-01's closure; M2 added two more and the closure did
#: not follow (RT-M2-01). Derive rather than enumerate where possible.
_ORACLE_MODULES = {
    "_fragment": Path("tests") / "laws" / "m1" / "_fragment.py",
    "_model":    Path("tests") / "laws" / "m2" / "_model.py",
    "_subject":  Path("tests") / "laws" / "m2" / "_subject.py",
}
```

with `_oracle_shadow_problem` iterating that mapping and aborting if any `sys.modules` entry for
those names resolves outside its frozen path. `src/tannen/laws/plugin.py` carries **no** manifest
row and is **not** custody-set, so the patch itself is builder-landable; only the fixture's
installation under `tests/poison/` is owner work.

**Known limit — this pins the DEFENCE, not a closure of the hazard.** The bare
`import _model as M` in the frozen law files is still collision-prone, and a widened check
catches only the shadow shapes reachable through those exact names. The actual fix is
package-qualified imports in the frozen files — which needs new files and manifest rows under
CLAUDE.md's do-not-edit-a-frozen-law rule. RT-M1-01 said the same thing at M1 and it was not
done; RT-M2-01 is the cost of that.

**Consider also sealing `tests/`.** Every reproduction of this finding, and of RT-M1-01 before
it, depends on `tests/` itself accepting a new file with no manifest row.
