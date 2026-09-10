# M3 boundary sitting — the owner's agenda

Generated from `boundary_sitting.sh`, sha256 `00c66cf…` — the bytes the clearance run of 2026-09-10 cleared.

**26 steps. 20 prompts state a cost for declining, 31 do not.** A prompt with no `else` arm simply skips its action — usually a printout, but NOT always: step 0's `make verify` has no else arm and declining it skips the precondition gate. Not every site fires — several sit inside conditionals, so the number you meet depends on repo state.

**Step 8 will ask you 7 times**, once per Tier-C record still blocked-on-owner — derived from `decisions/` just now, not copied from a previous run: D0154, D0171, D0176, D0195, D0201, D0207, D0212.

**12 steps do something consequential**, and only these:

- **Step 0** — uses your key
- **Step 1** — uses your key
- **Step 3** — uses your key
- **Step 3b** — uses your key
- **Step 4c** — uses your key
- **Step 4h** — uses your key
- **Step 7** — uses your key
- **Step 8** — uses your key
- **Step 8b** — uses your key
- **Step 9** — signs the receipt, writes a commit
- **Step 10** — mints the close tag
- **Step 11** — uses your key, writes a commit

Everything else edits files you can revert. Every prompt is decline-and-continue except step 10's: decline there and the sitting stops without a close tag.

---

## Step 0 — boundary sitting, $MILESTONE. Precondition: a green gate and a read queue  ⚠ uses your key

- *no stated consequence* — Show what is already changed? — **n** skips the action (**y** runs `git status --short | page`).
- *no stated consequence* — Run 'make verify' now (recommended — nothing should be signed over a red gate)? — **n** skips the action.
- *no stated consequence* — Show the digest's owner queue (what this sitting is for)? — **n** skips the action (**y** runs `latest_digest=$(ls -1 digest/*.md 2>/dev/null | tail -1)`).
- *no stated consequence* — ssh-add $OWNER_KEY now? — **n** skips the action (**y** runs `ssh-add "$OWNER_KEY" && KEYREF="$OWNER_KEY.pub"`).

**Sign $id? (BRIEF §9.2: Tier C is affirmative signature only, never silence)**

Answering **n**:

> left unsigned — the Tier-C guard will report it until it is signed or
> its status is changed to rejected/blocked-on-owner


## Step 1 — Tier-C records already recorded accepted (a safety net; usually empty)  ⚠ uses your key

No prompt — the driver acts or skips on its own.

## Step 2 — the guard that makes step 1 mean something (builder work)

No prompt — the driver acts or skips on its own.

## Step 3 — policy.yaml: in-repo mechanics are Tier A  ⚠ uses your key

*Resolves: D0048, D0053*

- *no stated consequence* — Read the proposal first? — **n** skips the action (**y** runs `page docs/proposals/2026-08-24-policy-in-repo-mechanics.md`).

**Keep this clause?**

Answering **n**:

> reverted — D0048 and D0053 stay documentary


## Step 3b — policy.yaml excludes the push this repository now makes daily  ⚠ uses your key

*Resolves: D0195 item 3*

- *no stated consequence* — Take SHAPE B — delete both push clauses (external_surface speaks alone)? — **n** skips the action (**y** runs `SHAPE=B`).
- *no stated consequence* — Take SHAPE A instead — widen both clauses to name the published origin? — **n** skips the action (**y** runs `SHAPE=A`).

**Keep this amendment and re-sign policy.yaml?**

Answering **n**:

> reverted — the clause still excludes the push this repo makes daily,
> and D0195 item (3) stays open for the next sitting.


## Step 4 — binding strength as a schema field

*Resolves: D0052; frozen path*

- *no stated consequence* — Read the proposal? — **n** skips the action (**y** runs `page docs/proposals/2026-08-24-binding-strength-grade.md`).
- *no stated consequence* — Apply $PROPOSALS/apply_binding_strength.py? — **n** skips the action (**y** runs `"$PY" -I -P "$PROPOSALS/apply_binding_strength.py" || die "applier fai`).

**Diff is what the proposal describes — keep it?**

Answering **n**:

> reverted


## Step 4b — the two frozen files the sitting amends

- *no stated consequence* — Regenerate BRIEF.md's MANIFEST row now (author-key territory)? — **n** skips the action (**y** runs `regen_manifest_row BRIEF.md`).
- *no stated consequence* — Read the drafted amendment? — **n** skips the action (**y** runs `page "$PROPOSALS/brief-9.1-amendment.md"`).
- *no stated consequence* — Open BRIEF.md now? — **n** skips the action (**y** runs `edit BRIEF.md || note "editor exited non-zero — the diff below is the `).

**Keep this edit?**

Answering **n**: reverts the edit, leaves the item open.

- *no stated consequence* — Install this ci.yml? — **n** skips the action (**y** runs `cp "$PROPOSALS/ci.yml" .github/workflows/ci.yml`).

## Step 4c — D0070's two drafted binding upgrades, on D0049 and D0063  ⚠ uses your key

*Resolves: D0105 item 3*

- *no stated consequence* — Fix D0049's swallowed binding and add manifest:scripts/custodian.sh? — **n** skips the action (**y** runs `python3 - <<'PY'`).

**Keep this edit and re-sign D0049?**

Answering **n**:

> reverted — D0049 keeps its corrupted binding and stale-looking signature

- *no stated consequence* — Add manifest:BRIEF.md to D0063? — **n** skips the action (**y** runs `python3 - <<'PY'`).

**Keep this edit and re-sign D0063?**

Answering **n**:

> reverted — D0063 keeps its documentary-only binding


## Step 4d — CLAUDE.md tells every session to run a command that checks nothing

*Resolves: D0108*


**Keep BOTH edits?**

Answering **n**:

> reverted — both files. CLAUDE.md keeps the line that checks nothing, and
> D0111 keeps tolerating it; leave D0108 blocked at step 8 to match.


## Step 4e — the supersession registry's real hinge is conftest.py, not laws.yaml

*Resolves: D0131 item 3, as RT-M2-02 corrects it*


**Add conftest.py and scripts/check_laws.py to the custody set?**

Answering **n**:

> reverted — the registry's pointer stays builder-editable and RT-M2-02
> stays open. Say so in the receipt; a declined finding is a decision.


## Step 4f — check_laws.py reaches the gate only through the file an attacker edits

*Resolves: D0131 item 4, D0152 item 2*


**Wire check_laws.py into the gate (whichever of the three edits were outstanding)?**

Answering **n**:

> reverted — all three, including any that were already applied before this
> step ran. Re-run the sitting to be offered them again: the guard above now
> reads the whole set, so a partial state is offered rather than skipped.


## Step 4g — DECISIONS.md asserts the receipt is FRESH from a hash that cannot see the clock

*Resolves: RT-M2-05*


**Make DECISIONS.md's date-dependent claims checkable?**

Answering **n**:

> reverted — DECISIONS.md keeps asserting a freshness no guard can check.
> Both files revert together; the fixture is only correct beside the guard.


## Step 4h — three signed Tier-C records now say something false in the present tense  ⚠ uses your key

*Resolves: D0123, D0131 item 7*


**Keep $rec_id's upgrade and re-sign it?**

Answering **n**:

> reverted — $rec_id keeps a binding whose detail is false in the present tense.


## Step 4i — a guard checks that a record is well-formed, never that it says what its author meant

*Resolves: D0131 item 8 = D0106 item 1*


**Land bindings_count — schema field, the check AND its test, together?**

Answering **n**:

> reverted — all three. D0106 item 1 stays open; note it in the receipt.


## Step 4j — a verdict is one bit, and there is nowhere in an evidence record to put the rest

*Resolves: D0131 item 2 = D0117*


**Land \`examined\` — schema, build_record AND the plugin, together?**

Answering **n**:

> reverted — all three. D0117 stays accepted and unappliable; the evidence
> record keeps saying only whether a law passed.


## Step 4k — the rehearsal that vouches for a custody-set script is vouched for by nothing

*Resolves: RT-M3-06*


**Add scripts/rehearse_sitting.sh to the custody set?**

Answering **n**:

> declined — RT-M3-06 stays open, and the rehearsal keeps vouching for a
> custody-set script without being one.


## Step 4l — an installed fixture whose README still says it is not installed

*Resolves: D0152 item 5*


**Correct the fixture's README (frozen + custody-set; regenerates its manifest row)?**

Answering **n**:

> reverted — D0152 item 5 stays open, and the fixture keeps saying it is
> staged somewhere it is not.


## Step 5 — install the red-team poison fixtures (author-key territory)

- *no stated consequence* — Generate it now (uses the builder key to sign the poison tag)? — **n** skips the action (**y** runs `&& bash "$CANDIDATES/custodian-tag-signer/make-fixture.sh"`).
- *no stated consequence* — Install $fixture into tests/poison/? — **n** skips the action (**y** runs `git mv "$CANDIDATES/$fixture" "tests/poison/$fixture" || die "git mv f`).
- *no stated consequence* — Add the new fixtures to the tests/poison/README.md table? — **n** skips the action (**y** runs `cat "$PROPOSALS/poison-readme-rows.md" >> tests/poison/README.md`).
- *no stated consequence* — Add oracle-shadow (RT-M1-01) to the tests/poison/README.md table? — **n** skips the action (**y** runs `cat "$PROPOSALS_M1/poison-readme-rows.md" >> tests/poison/README.md`).
- *no stated consequence* — Add oracle-shadow-model (RT-M2-01) to the tests/poison/README.md table? — **n** skips the action (**y** runs `cat "$PROPOSALS_M2/poison-readme-rows.md" >> tests/poison/README.md`).
- *no stated consequence* — Add check-laws-dropped-successor (D0154 item 7) to the tests/poison/README.md table? — **n** skips the action (**y** runs `cat "$PROPOSALS_M3/poison-readme-rows.md" >> tests/poison/README.md`).
- *no stated consequence* — Retarget D0141's binding to the installed tests/poison/ path? — **n** skips the action (**y** runs `python3 - <<'PY' || die "retarget_d0141: the binding is not the expect`).
- *no stated consequence* — Retarget D0199's binding to the installed tests/poison/ path? — **n** skips the action (**y** runs `python3 - <<'PY' || die "retarget_d0199: the binding is not the expect`).

## Step 5b — land RT-M1-05: the guard patch and its fixture, together

*Resolves: D0103, D0105 item 2*

- *no stated consequence* — Read the patch first? — **n** skips the action (**y** runs `page "$CANDIDATES/check-decisions-file-skip/rt-m1-05-check-decisions.p`).

**Apply it (scripts/check_decisions.py, tests/test_governance_scripts.py)?**

Answering **n**:

> declined — the fixture below only installs once the patch is applied, so it
> is skipped too this pass

- *no stated consequence* — Install the check-decisions-file-skip fixture (RT-M1-05)? — **n** skips the action (**y** runs `mkdir -p tests/poison/check-decisions-file-skip`).
- *no stated consequence* — Add check-decisions-file-skip (RT-M1-05) to tests/poison/README.md? — **n** skips the action (**y** runs `cat "$PROPOSALS_M1/poison-readme-row-file-skip.md" >> tests/poison/REA`).

## Step 6 — the custodian itself (trust root; yours alone to apply)


**Install this custodian?**

Answering **n**:

> declined — the close-tag rule and the custody-set check stay unenforced


## Step 7 — sign the custody set  ⚠ uses your key

*Resolves: D0061: what MANIFEST.sha256 cannot be*

- *no stated consequence* — Declare custody.sha256's signature REQUIRED (not merely verified-if-present)? — **n** skips the action (**y** runs `python3 - <<'PY'`).
- *no stated consequence* — Review the custody set before signing it? — **n** skips the action (**y** runs `page governance/custody.sha256`).

## Step 8 — the records this sitting resolves  ⚠ uses your key


**Accept and SIGN $rec_id (resolved by this sitting)?**

Answering **n**:

> left blocked — it will appear in the next digest's owner queue


## Step 8b — a test node whose name asserts the opposite of what it does  ⚠ uses your key

*Resolves: D0138 item 1*


**Keep the rename and re-sign D0110 now?**

Answering **n**:

> reverted — all four files. The node keeps the name that lies and the
> docstring keeps carrying the truth; D0138 item 1 stays open.


## Step 9 — regenerate, verify, and take the attention receipt  ⚠ signs the receipt, writes a commit

- *no stated consequence* — Commit the sitting so far? — **n** skips the action (**y** runs `commit_with_hook_retry "$MILESTONE boundary sitting: the custodian's s`).

## Step 10 — sign $MILESTONE-close, LAST  ⚠ mints the close tag

- *no stated consequence* — Sign $MILESTONE-close with this message? — **n** skips the action (**y** runs `git -c gpg.format=ssh -c user.signingkey="$KEYREF" \`).

## Step 11 — the tags this milestone minted join the required set, and the custody set is re-signed  ⚠ uses your key, writes a commit

- *no stated consequence* — Add ${MISSING_TAGS[*]} to tag-roles.yaml required_tags? — **n** skips the action (**y** runs `python3 - "${MISSING_TAGS[@]}" <<'PY'`).

