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
The prep session adds the door record, `decisions/0268-the-m5-gate-door-record-answering-d0257-and-d0265-drafted-for-signature.yaml`
(D0268 — the shape L5.8 reads, watched accepting it signed and refusing it unsigned).

Also by reference, drafted by the M4 session and folded in here 2026-09-17:
`../2026-09-17-inbound-dependency-amendment/` (`brief.patch`, `claude-md.patch`) — the owner's
asymmetric ruling on cross-repo imports (outbound stays banned; inbound opens by pinned release
only), landed as additive BRIEF §1.1 plus one CLAUDE.md clause, both custody-set, and filed as
`decisions/0269-a-sibling-repo-may-depend-on-tannen-at-a-pinned-release-tannen-imports-none-of-theirs.yaml`
(D0269, `links` naming D0268 since both sign at this sitting).
`../2026-09-17-inbound-dependency-amendment/contributing-notice.patch` is unfrozen and applied by
the builder after the sitting (see "Right after the sitting"), same as the rest of that list.

From a green CI on `m5`, with the owner key loaded once (`ssh-add ~/.ssh/tannen_owner`, D0185),
the sitting is this chain — rehearsed twice end to end in a scratch clone under an ephemeral
owner key (item 3 below; origin pointed at a disposable bare repo, never the real remote), and
corrected here from what the rehearsals found. The one real defect (first rehearsal):
`governance/custody.sha256.sig` already exists (signed at the last sitting), and
`ssh-keygen -Y sign` over an existing `.sig` prompts `Overwrite (y/n)?` on a terminal that has
nothing to answer with — measured hanging (and, worse, failing non-zero when stdin is closed)
rather than signing. The decision records carry no prior `.sig`, so only this one line needed the
`rm -f` first. The second rehearsal folded in the inbound-dependency amendment and confirmed its
`claude-md.patch` must apply *before* this directory's own `claude-md.patch` — the two touch
disjoint hunks of the file (the amendment's is the "Hard rules" bullet near the top; this
directory's are the "Decisions"/"Verification"/"Session discipline" headings further down), so
either order patches cleanly by itself, but composing both onto the same working tree in one
chain only succeeds amendment-first (checked directly: amendment-then-prep composes with a
three-line hunk offset and no conflict; the reverse was not needed once the working order was
found and is not asserted here). Everything else in both chains ran clean: 91 custody rows plus
the two amendment rows (BRIEF.md, CLAUDE.md's now-doubled diff), the four status flips,
`custodian.sh` green in ~10s including the full poison matrix, and a clean receipt:

```sh
P=docs/proposals/2026-09-16-m5-gate-sitting-prep \
&& A=docs/proposals/2026-09-17-inbound-dependency-amendment \
&& DOOR=decisions/0268-the-m5-gate-door-record-answering-d0257-and-d0265-drafted-for-signature.yaml \
&& AMEND=decisions/0269-a-sibling-repo-may-depend-on-tannen-at-a-pinned-release-tannen-imports-none-of-theirs.yaml \
&& git apply "$P/tier-c-custody-set.patch" \
&& git apply "$A/brief.patch" \
&& git apply "$A/claude-md.patch" \
&& git apply "$P/claude-md.patch" \
&& git apply docs/proposals/2026-09-15-ci-tag-event-checkout/ci.yml.patch \
&& for f in governance/tier-c.yaml CLAUDE.md .github/workflows/ci.yml BRIEF.md; do \
     grep -v "  $f\$" MANIFEST.sha256 > MANIFEST.tmp && sha256sum "$f" >> MANIFEST.tmp && mv MANIFEST.tmp MANIFEST.sha256; done \
&& .venv/bin/python -I -P scripts/gen_custody.py \
&& rm -f governance/custody.sha256.sig \
&& ssh-keygen -Y sign -f ~/.ssh/tannen_owner -n tannen-custody governance/custody.sha256 \
&& sed -i 's/^status: blocked-on-owner$/status: accepted/' decisions/0267-*.yaml "$DOOR" "$AMEND" \
&& ssh-keygen -Y sign -f ~/.ssh/tannen_owner -n tannen-decision decisions/0267-*.yaml \
&& ssh-keygen -Y sign -f ~/.ssh/tannen_owner -n tannen-decision "$DOOR" \
&& ssh-keygen -Y sign -f ~/.ssh/tannen_owner -n tannen-decision "$AMEND" \
&& bash scripts/custodian.sh \
&& make projections && .venv/bin/python -I -P scripts/gen_roadmap.py \
&& git add -A && git commit -m "M5 gate sitting: the door opened, the custody set is the trust root, D0252 and D0269 applied" \
&& git push origin m5
```

Then read every run the push starts. The custodian's bare run must print the receipt as signed
(D0177: run it `--check-only` first if in doubt); `ssh-add -d` afterwards. Seven key touches.
(`scripts/custodian.sh`'s own bare-mode receipt signature is a separate, eighth touch the
script makes internally — `ssh-add` makes it silent for the owner exactly as D0185 says; a
future rehearsal under an ephemeral key needs `TANNEN_OWNER_KEY=<ephemeral private key>`
exported too, the script's own documented override, or that one step prompts for the real
key's passphrase instead of using the rehearsal key — found rehearsing this correction.)

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

Item 2 lands; `../2026-09-17-inbound-dependency-amendment/contributing-notice.patch` applies
(unfrozen, no signature needed — D0269 already authorised it); D0253's `check_manifest.py`
current-envelope fix and the pre-budget lock fold; D0251's confirm fix into
`scripts/boundary_sitting.sh`; the `.dogfood/` wiring in `conftest.py` or `Makefile`, inert when
`.dogfood/` is absent (CI stays 10 skipped); D0257 and D0265 marked `superseded` by the door
record; D0251–D0253 flipped with enforced bindings; RT-M4-02 closed in the ledger (L5.2, D0260).
Then B2, in a fresh session.

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
