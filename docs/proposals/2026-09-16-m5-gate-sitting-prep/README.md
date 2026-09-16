# M5 gate sitting — the agenda, and the prep brief

One owner sitting, no driver, no dates. It opens the M5 gate and applies the four rulings of
2026-09-16 (D0267). A builder prep session drafts what it signs; the sitting is one command chain,
rehearsed once with an ephemeral key before the owner runs it. The receipt is renewed by the
sitting whenever it happens — a stale one blocks only Tier-B silence-consent (D0267).

## State

M5 Session B1 closed at `924ef46` (D0263, D0264, D0265). D0266 dropped the duplicate
check_decisions run from the pytest step, so `make verify` and CI each lose ~15 minutes. D0267
records the rulings and waits for this sitting's signature. Work stays in the `m5` worktree.

## The gate

`governance/tier-c.yaml` `renavon-first-contact` is unopened. **Read nothing from the Renavon
monorepo, `.reference/` included** — not to measure it, not to survey exports, not "just to
check". If you think you need a Renavon byte to make progress, you are in B2 and you stop.

## What the sitting signs (owner)

In this directory: `tier-c-custody-set.patch` (D0267 ruling 1; `custody.sha256.preview` is the
regenerated set it produces, 91 rows, 16 of them outside `tests/poison/`), `claude-md.patch`
(rulings 2 and 3 reach the manual), and by reference
`../2026-09-15-ci-tag-event-checkout/ci.yml.patch` (D0252, so tag-event runs stop being red).
The prep session adds the door record (`decisions/<door>.yaml`, the shape L5.8 reads).

From a green CI on `m5`, with the owner key loaded once (`ssh-add ~/.ssh/tannen_owner`, D0185),
the sitting is this chain — the prep session rehearses it and corrects it here before you run it:

```sh
P=docs/proposals/2026-09-16-m5-gate-sitting-prep \
&& git apply "$P/tier-c-custody-set.patch" \
&& git apply "$P/claude-md.patch" \
&& git apply docs/proposals/2026-09-15-ci-tag-event-checkout/ci.yml.patch \
&& for f in governance/tier-c.yaml CLAUDE.md .github/workflows/ci.yml; do \
     grep -v "  $f\$" MANIFEST.sha256 > MANIFEST.tmp && sha256sum "$f" >> MANIFEST.tmp && mv MANIFEST.tmp MANIFEST.sha256; done \
&& .venv/bin/python -I -P scripts/gen_custody.py \
&& ssh-keygen -Y sign -f ~/.ssh/tannen_owner -n tannen-custody governance/custody.sha256 \
&& sed -i 's/^status: blocked-on-owner$/status: accepted/' decisions/0267-*.yaml decisions/<door>.yaml \
&& ssh-keygen -Y sign -f ~/.ssh/tannen_owner -n tannen-decision decisions/0267-*.yaml \
&& ssh-keygen -Y sign -f ~/.ssh/tannen_owner -n tannen-decision decisions/<door>.yaml \
&& bash scripts/custodian.sh \
&& make projections && .venv/bin/python -I -P scripts/gen_roadmap.py \
&& git add -A && git commit -m "M5 gate sitting: the door opened, the custody set is the trust root, D0252 applied" \
&& git push origin m5
```

Then read every run the push starts. The custodian's bare run must print the receipt as signed
(D0177: run it `--check-only` first if in doubt); `ssh-add -d` afterwards. Six key touches.

## What the prep session produces (builder, fresh session)

Read first: `docs/specs/m5.md` §0.2, §2, §3, §8; D0255–D0257, D0261–D0267;
`tests/laws/m5/test_l5_authorisation.py` (the judge of the door record);
`tests/laws/m5/test_l5_replay.py` (the fresh-interpreter law that constrains the wiring).

1. **The door record**, in exactly the shape L5.8 accepts: a file under `decisions/`, `tier: C`,
   `status: blocked-on-owner` (the chain flips it), `links` naming the door id **read from**
   `governance/tier-c.yaml`, answering D0257's asks (1)–(5) and D0265 as fields the record STATES.
   D0265 is policy-answerable: `governance/policy.yaml#external_surface` defaults to nothing
   leaving, so the vertical lives in `.dogfood/` (gitignored) and is importable through
   environment wiring; publishing its name, code, measurement or analyses is a later door-2
   record, never this one's act. Watch L5.8 accept it signed and refuse it unsigned, in a scratch
   repository COPY under an ephemeral owner key (B1's method, D0264). The real `allowed_signers`
   is never touched.
2. **The commit-time guard, drafted and watched** (lands as a normal commit right after the
   sitting releases `scripts/check_decisions.py`, `Makefile` and `.pre-commit-config.yaml`):
   `check_decisions.py --collect-only` resolves pytest bindings by collection for the hook;
   `--pytest-report FILE` resolves them from the gate's own `pytest --junitxml` run; the default
   keeps running pytest, so all six `tests/poison/check-decisions*` fixtures and every custodian
   call are untouched. Watch: each fixture still bites under the new script; a planted failing
   bound node passes `--collect-only` and fails `--pytest-report`; the hook entry and the
   `Makefile` order (pytest, then the guard) drafted beside them. Expected: commits ~3 min, CI
   ~12 min.
3. **Rehearse the chain above once**, in a scratch clone with an ephemeral owner key appended to
   its copy of `allowed_signers` (FAST: no full `make verify` inside). Correct the chain in this
   README from what the rehearsal finds; do not add steps.
4. **The measurement recipe**: the steps that take `measurement/1` over the candidate sources ON
   the owner's machine AFTER the signature and write `.dogfood/measurement.json`. It must not run
   here. L5.4 then selects the vertical and nobody chooses it.
5. **The vertical's cross-repo guard** (unfrozen): the vertical imports nothing from the
   constellation, the forbidden list DERIVED from `governance/importlinter.toml`'s `no-cross-repo`
   contract (D0211; D0171 ruling (3)); skips cleanly with no corpus; watched FAILING on a planted
   `import renavon` before it is trusted green.

Facts the prep relies on (measured in B1, 2026-09-16): L5.10 spawns a fresh interpreter that
inherits ENV, not `sys.path` — a conftest `sys.path.insert` makes the parent pass and the child
fail; `PYTHONPATH=<root>/.dogfood` makes both pass. `lint-imports`' `no-cross-repo` contract has
`source_modules = ["tannen"]`, so a vertical outside `src/tannen/` is invisible to it — item 5.

## Right after the sitting (builder, normal commits)

Item 2 lands; D0253's `check_manifest.py` current-envelope fix and the pre-budget lock fold;
D0251's confirm fix into `scripts/boundary_sitting.sh`; the `.dogfood/` wiring in `conftest.py`
or `Makefile`, inert when `.dogfood/` is absent (CI stays 10 skipped); D0257 and D0265 marked
`superseded` by the door record; D0251–D0253 flipped with enforced bindings; RT-M4-02 closed in
the ledger (L5.2, D0260). Then B2, in a fresh session.

## Hard constraints

Nothing spends; every ceiling stays zero. No network from any test. Frozen paths are read-only;
custody-set files are drafted as patches until the sitting releases them. Never `--no-verify`;
never set `TANNEN_CHECK_DECISIONS_NESTED`. Carry `TANNEN_NO_EVIDENCE=1` on ad-hoc pytest. Run
`make projections && .venv/bin/python -I -P scripts/gen_roadmap.py` before `git add`. Until item
2 lands a commit is ~18 min of hooks: run it setsid-detached into a log, never two at once, never
edit the tree while it runs. CI is the gate; no local `make verify` unless before a merge or a
sitting. Scrub absolute paths from tracked files.

## Done

The door record watched both ways; every `check-decisions*` fixture watched biting under the
drafted guard; the chain rehearsed green once and corrected here; CI green on the push.

**Do not open the gate. Do not start B2.**
