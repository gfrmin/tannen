<!-- Builder audit commissioned by owner ruling (1), 2026-09-09. Nothing here is enacted.
     Every change it proposes needs the owner's key at a boundary sitting. -->

# Floor-simplification audit — commissioned by owner ruling (1), 2026-09-09

**The question put:** now that the remote is public, which custody guards, receipt-chain
mechanics and history-integrity checks are made redundant by a protected remote with required
signature verification? Target: a smaller custody set and a shorter ceremony.

**The answer: none of them.** Thirty-five substitution claims were raised across seven mechanism
families and adversarially refuted one by one; **zero survived**. The custody set does not
shrink. The ceremony does — by a different route, and by about 35 minutes a boundary.

Method: seven parallel surveys (custody set, custodian guards, receipt chain, history integrity,
GitHub capability, ceremony split by consequence, constitutional constraints), each redundancy
claim then attacked by an independent reviewer instructed to default to "refuted" when uncertain,
followed by synthesis. Read-only throughout; nothing in the repository was modified.

---

# The custody floor after publication: what a protected remote can and cannot take over

## 1. THE PREMISE, CORRECTED

Three corrections before any of this is actionable.

**The remote is public but unprotected, and the commits in it are unsigned.** Measured 2026-09-09: `GET /repos/gfrmin/tannen/branches/master/protection` returns 404, `GET .../rulesets` returns `[]`, `commit.gpgsign=false`, and every commit reports `%G? = N`. "A protected remote with required signature verification" is therefore not a facility we can spend against — it is unbuilt work. The question as posed asks which guards are made redundant by something that does not exist yet. Nothing is currently made redundant by anything.

**If it were built, it would buy less than the phrase suggests.** GitHub's "Verified" badge attests that a commit or tag signature matches a key registered to a GitHub *account*. This repository's trust root is `ssh-keygen -Y verify -f allowed_signers -I <principal> -n <namespace>` against `allowed_signers:10` (`builder@tannen`) and `allowed_signers:17` (`owner@tannen`) — two deliberately distinct principals, per D0015, so that "an artifact that must be author-signed ... verifies only against `owner@tannen`, so a builder signature can never satisfy it" (`allowed_signers:3-5`). One GitHub account pushes both roles. GitHub cannot distinguish them and has no notion of the namespaces (`tannen-custody`, `tannen-policy`, `tannen-decision`, `tannen-receipt`, `tannen-rewrite`) that separate presence from authorisation. Turning on required signature verification would not verify this repo's trust root; it would verify a different one, and BRIEF.md:168-173 is the clause that forbids treating the second as the first: "Authorisation attaches to the artifact of record, never to a report about it."

There is also a structural bar on the remote entering the floor at all. `scripts/custodian.sh:18-25`, quoting D0063 ruling 3: "THE FLOOR MAY DEPEND ONLY ON TOOLS THE OS PROVIDES AND PATHS NAMED LITERALLY." `gh` is not OS-provided, needs a credential, and returns a third party's assertion. A remote may be a second observer; it may not become a term in the floor's verdict.

**The five-minutes-a-week target is not in the brief.** I searched BRIEF.md at HEAD and at `brief-freeze`, plus policy, decisions, docs and DELEGATIONS: there is no weekly minute figure anywhere in the repo. Do not cite one. The complaint about ceremony accretion has a better footing: `docs/OPENING.md:1` — "the opening-sitting checklist (owner, ~10 minutes)" — and `docs/OPENING.md:3` — "Exactly four owner steps (BRIEF §9.2; decision D0027)". Against that, the M3 driver has **26 steps, not 24** (26 `say "Step ..."` headers in `docs/proposals/2026-09-04-m3-boundary-sitting/boundary_sitting.sh`, from :356 to :2592), 51 `confirm` sites of which roughly 21 fire, and ~100 minutes. That is an order of magnitude over the only owner-time figure the repo ever wrote down. Note also that BRIEF.md:174 caps sitting *frequency* ("milestone boundaries only"), not duration, so no clause is literally breached — the argument has to run through `governance/policy.yaml:48-49`, "deference spends owner attention, which is the one resource the autonomy protocol exists to conserve."

## 2. WHAT THE REMOTE CAN GENUINELY TAKE OVER

**Nothing. Zero of thirty-five substitution claims survived refutation.** That is the honest headline and I am not going to soften it.

What the remote does do is add a second observer without removing a first. Three places where that is real, each *additive*:

- **Durability of pushed refs.** A tag ruleset on the eight freeze/close tags makes a pushed tag hard to delete or repoint. Location: remote-side, no in-repo artifact. Degree: adds detection of remote-side tampering; removes nothing, because `governance/tag-roles.yaml:16-19` (the trust-root object pin) and `:47-55` (`required_tags`) answer *local* tag deletion, which the remote never sees. Local residue: all of `scripts/check_tag_signers.py`.
- **A second executor of the same gate.** `.github/workflows/ci.yml:29` already runs `make verify` with `fetch-depth: 0`. Degree: a green run on a machine the builder does not control is a better witness than a local run — *conditional on* the hash pin at `MANIFEST.sha256:109` and `governance/custody.sha256`, because Actions loads the workflow from the commit being pushed, so without the pin the commit under observation supplies its own observer. Local residue: the manifest row, the custody row, and the owner signature over `custody.sha256`. Also: `[skip ci]` in a commit message silently skips the run, and with no required status checks nothing notices.
- **An off-machine copy of what was pushed.** Degree: makes a post-hoc rewrite of *published* history noisy. Local residue: the receipt chain, because nothing in `scripts/` or the `Makefile` pushes (`grep -rn 'git push' scripts/ Makefile` returns nothing) — the boundary driver has no push step, so every signature is taken on a tree the remote has not yet seen.

Degree, summarised: **defence in depth, not substitution.** Every one of these strengthens the case for keeping the remote and enabling protection. None of them is an argument for deleting a local guard.

## 3. WHAT MUST STAY LOCAL, AND WHY

Six families of attack survive any remote configuration. Each is a reason a specific local mechanism stays.

**(a) The unpushed window is where the ceremony lives.** The sitting signs the custody set (`boundary_sitting.sh:2295`), the receipt (`:2523`) and `m3-close` (`:2549`) against the local working tree, and pushes nothing. A rewrite performed before the push — `git commit --amend` across a receipt boundary, a rebase of the four commits `m3` currently carries above `origin/master` — is invisible to a remote that has not received the prior state. `scripts/check_receipts.py:180` (pairwise ancestry) and `:193` (last receipt's HEAD must be an ancestor of current HEAD) are the only detectors, and they run offline before the network is involved.

**(b) Local ref deletion is not a remote event.** `git tag -d brief-freeze` pushes nothing. Locally it empties `bless_epoch` (`scripts/custodian.sh:81-83`), switching off delegation-precedes-signature (`:92-99`) for every tag created afterwards, and it drops the tag from `BOUNDARY_TAG_RE` (`scripts/_gov.py:25`) so `receipt_state` (`scripts/_gov.py:268`) returns fresh for ever and `effective_status` (`:309-315`) converts every lapsed Tier-B veto to "accepted (veto lapsed)". Tag protection on GitHub is untouched and never consulted; no guard fetches origin. Only `required_tags` and the trust-root pin refuse it. The same end state arrives with no attacker at all: `git clone --depth 1` of the public repo has zero tags.

**(c) A tree-content attack is a legal fast-forward.** Force-push protection constrains how refs move, not what a tree contains. One ordinary commit can delete `Makefile:44` (`bash scripts/custodian.sh --check-only` — the only path by which the custodian runs), or rewrite `.github/workflows/ci.yml` so the job still named `verify` runs `true`, or strip hooks from `.pre-commit-config.yaml`. Every proposed remote rule is satisfied. What refuses it is `sha256sum -c governance/custody.sha256` (`scripts/custodian.sh:52-60`) plus the owner signature over that file, and `MANIFEST.sha256:109`/`:124`. Removing a custody row removes exactly that difference.

**(d) The topic-branch launder.** Work happens on `m3` by design — CLAUDE.md mandates one worktree and one branch per milestone. `m3` strictly extends `origin/master`. Rewrite inside the 26 post-tag commits on `m3`, force-push `m3` (unprotected), then merge to master: master only grows, so append-only is satisfied and nothing is rejected. Protecting `m3` requires enumerating every future milestone branch — the hand-maintained enumeration D0171 ruling 3 forbids. `check_receipts.py:193` is the only thing that fails.

**(e) A trust-root re-issue can carry a genuinely valid signature.** With the owner key in ssh-agent (D0185 measured `~/.ssh/tannen_owner` as passphrase-protected, and the sitting unlocks it), `git tag -d brief-freeze` and a backdated `git tag -s` produces a tag that `git verify-tag` accepts, whose class role is correct, whose existence satisfies `required_tags`, and whose date becomes the new `bless_epoch`. Signature verification cannot catch it because the signature is real; the role table cannot catch it because owner *is* the right role. Only the object-hash comparison at `governance/tag-roles.yaml:16-19`, enforced at `scripts/check_tag_signers.py:94-98`, does — and it does so offline, in every clone, for ever.

**(f) Offline third-party verification is the point of publishing.** D0176 published the repo so a stranger can verify it. A clone contains no protection state, no push history and no audit log; protection settings are unverifiable from the artifact at any time, past or present. Everything a third party can check is in-tree: `allowed_signers`, the eight tag signatures, `governance/custody.sha256.sig`, the six receipts and `receipts/REWRITE-2026-09-07.md.sig`. Every guard removed on the strength of a remote control is a guard that stranger loses entirely.

And the self-bypass: the GitHub admin credential is in this machine's keyring; a ruleset can be deleted, a force-push performed, and the ruleset recreated byte-identically, with no personal-account audit-log API to record it. The receipt chain still catches that, because `receipts/2026-09-07.md:3` pins pre-rewrite HEAD `3f8634b9...` and only an owner-signed `REWRITE-*.md` map can make the chain verify again. A control that the party it constrains can switch off is not a trust root.

## 4. THE SMALLER CUSTODY SET

**The honest answer is that none can go.** The set today is 26 patterns resolving to 75 paths (`wc -l governance/custody.sha256` = 75; the patterns are `governance/tier-c.yaml` `custody.set`). The proposed diff:

```
  (no removals)
+ scripts/rehearse_sitting.sh
```

Why each candidate for removal fails:

- The nine `scripts/check_*.py` / `_gov.py` / `gen_*.py` members are the guards themselves; each is the sole detector of at least one attack in §3.
- `Makefile`, `.pre-commit-config.yaml`, `.github/workflows/ci.yml`, `conftest.py` are the *reachability* of those guards — attack (c) and RT-03 are exactly the case where the guard is intact and unreachable.
- `allowed_signers`, `scripts/custodian.sh`, `tests/poison/**/*` are BRIEF.md:191 door 5 by name; removal is a one-way door, not a tidy-up.
- `BRIEF.md`, `CLAUDE.md`, `DELEGATIONS.md`, `governance/{policy,tier-c,tag-roles,importlinter}.yaml`, `governance/schemas/*.json` are the *inputs* the guards read; editing a table is cheaper than editing a guard, which is why they are in.
- The weakest member is `scripts/opening_sitting.sh` — the opening happened once. But it is re-runnable, it writes trust-root files, and removing it is itself a Tier-C record plus a custody regeneration plus an owner signature. It is not worth a signature to save a hash.

The one addition is step 4k / RT-M3-06: `scripts/rehearse_sitting.sh` is the 21KB harness whose green output is D0068's precondition for the real sitting, and it is in neither the manifest nor the custody set. It already writes `owner@tannen` lines into a clone's `allowed_signers`; one `$CLONE`→`$ROOT` slip launders the trust root with every gate green. Widening is the safe direction and no guard today distinguishes widening from narrowing.

Separately, one *repair* that shrinks the ceremony without shrinking the set: `required_tags` (`governance/tag-roles.yaml:47-55`) is a hand-maintained enumeration read at `scripts/check_tag_signers.py:151`. It currently lists `m3-laws-freeze` but not `m3-close`, and D0095's own record says half (2) — replacing the enumeration with a derived rule — "is applied by NOTHING, which is why step 11 of every sitting still adds that boundary's tags by hand." Deriving it from the boundary tags the receipt and decision record already name honours the standing rule against hand-maintained enumerations, and deletes an entire ceremony step.

## 5. THE SHORTER CEREMONY

The irreducible signing ceremony — owner key, no delegation possible:

| Step | Act | Wall clock |
|---|---|---|
| 5 (`:1849`) | install poison fixtures; door-5 territory | ~5 min |
| 6 (`:2212`) | install `scripts/custodian.sh` (191-line diff, read in full) | ~15 min |
| 7 (`:2295`) | regenerate + sign `governance/custody.sha256` | ~2 min |
| 8 (`:2339`) | read and sign four Tier-C records, 600 lines | ~25 min |
| 9 (`:2523`) | full custodian run → signed receipt | included below |
| 10 (`:2549`) | `git tag -s m3-close` | ~2 min |
| 3b (`:548`), 4l (`:1764`) | owner-only by the letter (signed file; `tests/poison/` prose) | ~5 min |

That is roughly 55 minutes and it is the part that should not shrink. Step 8 in particular: 600 lines read in full is the attention the protocol exists to spend, and the `head -40` that used to stand there cut five of eight records mid-sentence.

Where the clock actually goes is not owner attention. Measured: `make verify` legs of 18m12s and 18m49s in the rehearsal clone, 33m31s on the builder's clean machine, and pre-commit rounds at ~12 minutes each. Three concrete cuts, in order of return:

1. **Land the derived `required_tags` (§4) at this sitting; delete step 11 at the next.** Step 11 (`:2592`) is one `make verify` leg, one hook round, one commit, and *the second of the two owner custody signatures*. Saves ~30 minutes and one signature per boundary, for ever.
2. **Two verify legs, not three.** Keep step 0's precondition gate (`:356`) — it is the only thing that stops the owner signing over a tree a guard already refuses, and D0200 records it catching an injected manifest failure — and keep step 9's leg before the receipt and the close tag. The middle leg exists to cover step 11's edits and goes with it.
3. **One commit round, not two,** once step 11 is gone.

Net: ~100 minutes to ~55-65, four owner signature moments (Tier-C records, custody set, receipt, close tag) instead of five, with no guard removed and no custody member dropped.

What makes the split safe is a four-part chain that already exists: D0068's rehearsal precondition (strengthened by putting the harness in custody); step 0's clean-tree `make verify` with tolerances naming only the custody drift step 7 answers; step 7's regeneration followed by an unconditional `custodian --check-only || die`; and step 10's D0051 clean-tree refusal, so the close tag can only quote hashes present in the commit it names. Builder pre-work is verified by the owner running that chain *before* the signature, not by the builder asserting it.

One thing I recommend against: moving steps 4f and 4k into builder pre-work between sittings. Doing that requires narrowing `governance/policy.yaml:62-63` (the excludes clause forbidding builder edits to frozen or signed files), which is strictly broader than BRIEF door 5 and is genuinely the release valve on offer. But the pre-commit frozen-path hook currently *prevents* those edits; after narrowing, a guard-weakening edit is live until someone notices, and a stale custody signature is detection, not prevention. The payback is four prompts and under five minutes. That trade is not worth taking.

## 6. WHAT THIS COSTS AND WHAT COULD GO WRONG

The minimum paperwork for any custody-set change is three owner signatures at a boundary sitting — the Tier-C record, `custody.sha256`, the receipt — plus a fourth if `policy.yaml` moves, plus owner-hand edits for anything in door 5. **A proposal to shorten the sitting costs a sitting.** The recommendation in §5 clears that bar only because it pays back every boundary thereafter.

On the GitHub dependency: there is no self-containment principle in BRIEF §3, and GitHub is not a constellation repo, so BRIEF.md:26 and §10 are not engaged — that reading would also condemn `ci.yml`, which §9.1 explicitly contemplates. The real constraints are narrower and firmer: the floor may not call `gh` (D0063 ruling 3); and the binding vocabulary is `file | config | pytest | manifest`, so any in-repo assertion about branch protection can only be `documentary`, which detects nothing and pushes the ratcheted unenforced count the wrong way (BRIEF.md:175). Relying on a remote control converts an enforced binding into a documentary one — the paperwork punishes the substitution even where it is sound.

Migration risk. `governance/policy.yaml:66` still excludes "pushing to any remote other than a private origin already configured here" — the act this repo now performs after every commit (D0195 item 3). Enabling rulesets is arguably inside the already-signed D0115/D0176 door, since configuring protection sends no new bytes, but aligning the policy text is an owner edit and re-signature under `tannen-policy`, and it should happen at the same sitting rather than being inferred.

Two trust-root files currently say false things and only the owner can fix them: `.github/workflows/ci.yml:6-7` ("This file has never actually run: the repo has no remote"), and the surviving TODO fragment at `allowed_signers:14-16` ("Until then no owner attestation ... can verify"). Related, and worth knowing before leaning on "touch = presence" (BRIEF.md:164): `allowed_signers:17` enrols a plain `ssh-ed25519`, not the `ed25519-sk` the brief contemplates, and D0185 measured the private half as passphrase-protected. The local irreducible act is a passphrase, not a touch.

Risk in the recommendation itself: deriving `required_tags` edits a custody-set guard, and D0199 is the standing lesson that a guard nobody has watched fail is a silent floor failure. It must land with its own poison fixture — and `tests/poison/` is door 5, owner-applied. Risk in doing nothing: BRIEF.md:182 mints fixtures at every boundary with no retirement path, and the only clause that widens anything automatically (BRIEF.md:197, graduated autonomy) is scoped to defaults on law evidence and cannot reach the custody floor. If an automatic release valve is wanted, extending that clause is the proposal — and it is a §9.2 amendment.

Finally, if any ceremony metric is added (prompts per boundary, owner minutes per sitting), BRIEF.md:176-181 forbids adding and ratcheting it in one breath: land the measurement, publish one digest carrying true values, ratchet from the next.

## 7. GOVERNANCE PAPERWORK

Four records, in this order. No record is ever hand-edited (D0045); corrections are new records.

1. **R1 — Tier A, builder, no signature.** "Where the boundary sitting's wall clock actually is": the measurement (26 steps, 51 confirm sites, ~21 firing, two 18-minute verify legs, 33m31s on the clean machine, ~12 min per hook round) and the finding that owner attention is ~55 minutes of a ~100-minute run. `risk_flags: [governance-paths]` so it surfaces in the exception-only digest (BRIEF.md:175). Bindings: none; flagged `unenforced` with the stated reason that it is a measurement.
2. **R2 — Tier A by reversibility, sitting-gated by custody.** Derive `required_tags` from the boundary tags, retiring the hand-maintained enumeration (D0095 half 2). Bindings: `file` → `scripts/check_tag_signers.py`, `pytest` → its new test, and a poison fixture under `tests/poison/` (owner-applied, door 5). Consequence recorded explicitly: step 11 of `boundary_sitting.sh` is deleted at the next boundary, along with one verify leg, one hook round and one of the two owner custody signatures.
3. **R3 — Tier C, door 5 (trust-root changes), BRIEF.md:191; `governance/tier-c.yaml:33-35`.** Add `scripts/rehearse_sitting.sh` to `custody.set`. `status: blocked-on-owner` until signed (`scripts/check_decisions.py`'s `TIER_C_UNSIGNED_OK`), then `<record>.yaml.sig` verifying as `owner@tannen` under namespace `tannen-decision` (D0063 ruling 2). `governance/tier-c.yaml` is frozen at `MANIFEST.sha256:104`, so its manifest row is refreshed in the same change.
4. **R4 — Tier A, `risk_flags: [governance-paths, public-surface]`.** The null result of this audit, on the record: publication supplies a second observer and substitutes for no local guard; the remote's trust root is account keys, not `allowed_signers` principals; the floor may not consult the remote (D0063 ruling 3); and no member of the custody set is removed. This record exists so the next session does not re-litigate it, and so a future proposal has to argue against a written finding rather than against silence.

If the remote's role is to change — enabling rulesets, or treating CI as a required check — add **R5, owner edit and re-signature of `governance/policy.yaml`** under namespace `tannen-policy`, aligning `in_repo_mechanics` with the now-public origin (D0195 item 3, D0115, D0176). It is in `required_signatures` and custody-set, though not in `MANIFEST.sha256`.

Signer for every signature above: `owner@tannen` only. DELEGATIONS.md forecloses the alternative — the builder's signature attests builder action under recorded instruction and cannot mint an owner attestation. Timing: a boundary sitting (BRIEF.md:174). Until then all four queue without blocking anything (BRIEF.md:195). Order at the sitting is the driver's existing order: step 0 gate → owner-shown diffs → step 7 custody signature → step 8 Tier-C signatures → step 9 receipt → step 10 close tag.

---

## 8. THE QUESTION THIS AUDIT DID NOT ASK: REORDERING, NOT SUBSTITUTION

Added 2026-09-10 on owner ruling (1), which accepted §1–§7 and then named the gap: the audit
refuted **substitution** — a remote guard standing in for a local one — and never considered
**reordering**, pushing before the signing window so that "no remote can witness this" becomes
a fact about the ceremony's order rather than about the ceremony. Eight claims were raised
across four angles and every one was refuted, as in the main audit. What follows is what
survived the refutations.

**(1) The framing is off by six signatures.** "Before the signing window" has no referent
inside the ceremony. The owner's key is first used at **step 3**, on `governance/policy.yaml`,
and is used again at step 3b, twice in step 4c and once in step 4h — six owner-key signature
sites before step 7's custody signature. The signing window opens minutes in. The only point
that is genuinely "before" it is step 0, and the tree at step 0 is the pre-sitting HEAD.

**(2) There is nothing to push.** The driver has exactly two commit sites, both after step 7:
step 9 and step 11. Everything steps 0–8b do — six owner signatures, step 5's poison fixtures,
step 6's custodian install, step 7's custody signature — writes **uncommitted working-tree
state**, and `git push` moves refs and the objects they reach, not a working tree. A push
inserted anywhere before step 9 carries nothing the sitting produced. This is structural, not
incidental: the artifacts are signed as byte strings the moment they are written, and the
signature precedes any commit that could carry them.

**(3) Manufacturing something to push is refused one layer earlier, by a rule the owner has
already declined to bend.** To make a pre-signing push non-empty the ceremony must add a commit
to its irreversible middle. That commit cannot be taken: `.pre-commit-config.yaml` runs
`check_manifest.py`, whose `main()` calls `check_custody` **unconditionally, before** the
`--staged` branch, and `check_custody` fails on precisely the drift the ceremony creates by
construction — the `cp`'d driver, the swapped custodian. Forcing it requires `--no-verify`,
which **D0181 refused for a real commit even under a direct owner ruling**, sequencing to a
sitting instead. The reordering therefore terminates on the repository's own standing refusal.

**(4) And if it were forced, the publication would be of a red tree.** `git add -A` would sweep
the deliberate drift into public history; `ci.yml` is `on: push:` with no branch filter and
checks out the commit, so the first thing the world would learn about the sitting is a red
verdict on its middle — while the owner is still sitting.

**(5) One variant survives structurally, and is refused on the abort path.** A push at the
seam between step 9's commit and step 10's tag needs no invented commit and no red floor: step
9 has committed, step 10's own guard has just required the tree to be clean, so that commit
contains the whole sitting. It is refused because it would be the ceremony's **first published
act**, and the two failures immediately downstream — the owner declining the close tag, or
`verify-tag` failing after `git tag -s` succeeded — would strand a never-closed sitting on
public `master`. Today no abort leaves anything beyond this machine. That property is worth
more than a witness to a tree, and it is the honest answer to the owner's question: not
impossible, priced, and the price is the abort path.

**(6) The finding that runs the other way, and it is the useful one.** §3(a) above makes an
attack family conditional on ignorance: a pre-push rewrite "is invisible to a remote **that has
not received the prior state**." Pushing the pre-sitting HEAD *before* the ceremony delivers
exactly that prior state, and so closes family (a) — the only one of the six that a remote can
close. That is not a reordering of the ceremony at all; it is ordinary builder habit performed
before it starts. **And nothing enforces it.** The driver contains no `git fetch`, no `git
push` and no reference to any remote-tracking ref; `docs/SITTING.md` does not use the words
push, origin or remote once; no guard consults a remote. It is therefore true by habit and was
**false for over twenty-seven hours on 2026-09-09**, by this repository's own reflog —
`origin/master` sat at `2bb4954` from 15:10 on 2026-09-08 until 18:55 the following day, the
window in which this audit was written and which §3(a) describes as "the four commits `m3`
currently carries above `origin/master`."

The recommendation is one comparison at step 0: the sitting refuses to start unless `origin`
already holds `HEAD`. It costs a `git ls-remote`, it makes a load-bearing property into a
checked one, and it is the only thing in this whole line of enquiry that the remote actually
buys. **It is queued, not landed.** It is an addition to the ceremony, and the owner's standing
objection of 2026-09-09 is precisely to additions that are each individually correct: "that's a
ratchet with no release." Whether a boundary sitting may depend on the network at all is the
owner's call, not the builder's — it would be the first step of the ceremony that fails when
the network does.

**(7) A live defect, found on the way.** Asking what a mid-ceremony push would strand exposed
what the ceremony already strands. `die()` branches on `git status --porcelain` alone, and the
working tree was never a complete account: a minted, owner-signed close tag lives outside it.
Four `die()` sites are downstream of `git tag -s` — `verify-tag`, and step 11's projection,
custodian and `make verify` failures, the last being much the likeliest — and step 10 has just
required the tree to be clean, so all four printed *"nothing is half-applied. This is a
coherent place to stop."* over a signed close tag. The rehearsal harness could not catch it
either: its `"$MILESTONE-close was NOT minted"` assertion sat inside the **dirty** branch. Both
are fixed (D0210): the driver asks the refs before the tree, and the harness asks the tag
question on every abort.
