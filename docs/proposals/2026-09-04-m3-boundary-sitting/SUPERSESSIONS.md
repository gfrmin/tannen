<!-- Builder drafting under owner ruling (3) of 2026-09-09 (D0201). NOTHING HERE IS ENACTED.
     docs/specs/m3.md and the M3 law files are frozen; this file proposes replacement text and
     the owner installs it. D0171 ruling (1) states the supersession "waits for the signature
     rather than being executed under the standing delegation." -->

# Supersessions drafted for the sitting — the two deferred Session-A items

Owner ruling (3), 2026-09-09 (D0201): draft these before M4 Session A rather than letting them
roll to a fourth consecutive boundary. "Frozen prose known to be false is precisely how D0049
happened."

**Both first drafts were refuted.** Each item was attacked by two independent reviewers — one on
correctness, one asking whether the "owner territory" claim is even true — and both returned
`sound: false` on what they were handed. Three of seven proposed falsifications in item 1 are
**not** shown false and are not carried as falsity claims; item 2's first-draft loader silenced
the very guard it exists to serve. What survives is below. The refuted material is kept visible
rather than deleted, on D0063's precedent of keeping the questions beside the answers.

---

# Builder's proposal — the two Session-A items, drafted for installation

Prepared 2026-09-09 against the repository root at `3de45cc`. Nothing was written, staged or committed inside the repo; the working tree is unchanged. Every claim marked **measured today** was re-run by me against the shipped package or against the tree copy at `.../scratchpad/repo`, not read off a record.

Both adversarial reviews returned `sound=false` on the drafts they were given. Three of the seven passages in the item-1 draft are not shown false, and the item-2 draft's loader **silences the guard it exists to serve** — reproduced below. Neither refuted version is carried forward.

---

## What is false, and what falsified it

Only passages a reviewer confirmed. `docs/specs/m3.md` is frozen and intact: `MANIFEST.sha256:76` carries `27116aec…21c3e2` and `sha256sum` of the working file matches byte for byte (checked independently).

| Location | Quoted current text | What falsified it | Evidence |
|---|---|---|---|
| `docs/specs/m3.md:335-337` (§7) | "**Every step is its own derivation**: the existing `derivation_id` over the step's descriptor and its *content-addressed inputs* — `(state_ref, ledger_ref, sorted delta refs)`." | `derivation_id` sorts the **whole** input list, not the delta refs inside a fixed triple; and on a node's first tick `state_ref` is not an input at all, so the frozen triple names three inputs where there are two. The word `sorted` also hides a live collision: a binary node's two operand orders share one `step_id`. | `src/tannen/kernel/derivation.py:32` (`content_address({"inputs": sorted(inputs), …})`); `src/tannen/incremental.py:523-524` (`inputs = list(refs) + [ledger_in] + ([state_ref] if state_ref is not None else [])`); RT-M3-03 in `decisions/0174-m3-red-team-findings.yaml:70-80`. **Measured today**: `anti_join` swapped — same `step_id`, `record=True` serves `[{'k':'x'}]` where the correct answer is `[]`, `rebuilt=False`, no exception. |
| `docs/specs/m3.md:337-338` (§7) | "One derivation, one output, holds because a step is a pure function of those inputs" | False when frozen: a step was also a function of the module-level registry, which is in none of the named inputs. True today only because of a change the sentence does not name (D0197), and still not true of a `map_rows` node's registered out-schema. | RT-M3-01 in `decisions/0174…:31`; `decisions/0197-a-delta-nodes-descriptor-now-names-the-code-it-runs-not-a-string.yaml:43-48` names this sentence as unclosed residue. `src/tannen/incremental.py:172` stores `(f, tuple(sorted(schema)))` but `:108-125` hashes only `f`; `:727-728` reads the schema back out of `MAPS` at tick time. **Measured today**: two processes registering one `map_id` with different out-schemas produce one descriptor and one `step_id`; the second is served the first's value (schema `['a']` where `('b',)` was declared), `rebuilt=False`. |
| `docs/specs/m3.md:339` (§7) | "Replaying a stream hits traces;" | `advance` **consults** the trace and by default writes none, so there is no trace row to hit. This is the owner's own ruling. | `decisions/0171-the-m3-conferral-rulings.yaml:17-23` — "§7's sentence is now FALSE AS WRITTEN … supersede the prose forward". `src/tannen/incremental.py:474` (`record: bool = False`), `:576` (`if record: traces.record(...)`), `:574` (`rebuilt = not store.has(step_ref)`), `:459` (`rebuilt` = "already in the store or the trace"). The default is forced, not chosen: `tests/laws/m3/test_l3_executor.py:111` re-records under a completed `step_id` outside its `pytest.raises`, and `src/tannen/executor.py:100-107` refuses a conflicting re-record. |
| `docs/specs/m3.md:444` (§10 law table, L3.15 row) | "a replayed stream hits traces" | The same claim as `:339`, repeated verbatim in the row a reader reaches for first. Correcting the body and leaving the table is the D0049 shape. | Same as `:339`. The row's parsed cells are safe to restate elsewhere: `tests/test_laws_runner.py:50-56` reads only `docs/specs/<milestone>.md`, so a corrected row in a differently-named file cannot desync `test_discovery_matches_the_frozen_spec_table`. |

**Three further passages were proposed as falsified and are not, and I am not carrying them as falsity claims.**

- `docs/specs/m3.md:202` — "an empty tick moves nothing, trace hits included". A reviewer refuted this: it scopes L3.15's empty-tick claim, and trace hits *do* occur (`record=True`) and *do* move nothing. It is not the same claim as `:339`. The replacement proposed for it ("served from the store") also contradicted the corrected `:339` text, which says the body re-runs. **Leave `:202` alone.**
- `docs/specs/m3.md:324` — the six-argument `advance` signature. Incomplete, not false: a six-positional call is valid today (`src/tannen/incremental.py:466-475`) and the bullet never claims exhaustiveness. Offered below as a completeness companion with honest grounds, not as a falsity.
- `docs/specs/m3.md:318` — "(`deltaop/1`: operator name, canonical params)". Incomplete: `replay` is a **top-level** descriptor key beside `params` (`src/tannen/incremental.py:363-370`, with `self.replay = replay or operator in _ALWAYS_REPLAYS` at `:362`), and the declared params now also carry `<kind>_code` (`:439-447`). No record establishes it false and no reviewer confirmed it false. Offered as a completeness companion only.

For item 2, the falsified passages are prose about the fix rather than spec text; both reviewers confirmed the same two falsifications at every site. They are listed in **The package-qualified import** and their replacements are in the next section.

---

## The corrected text

### 1. `docs/specs/m3.md` §7, lines 335-341 — the whole "Every step is its own derivation" bullet

Replaces the four confirmed passages at `:335-337`, `:337-338` and `:339` in one block, because they are one bullet. Paste as-is into `docs/specs/m3-corrections.md`.

> - **Every step is its own derivation**: the existing `derivation_id` over the step's
>   descriptor and the step's *content-addressed inputs* — the child refs the tick passes,
>   the ledger's content address, and the state ref **when there is one** (a node's first
>   tick has no state, so the list is one shorter rather than carrying a hole).
>   `derivation_id` normalises the order of that **whole list**, not of the child refs
>   inside a fixed tuple. That is frozen M1 (m1 §8, L1.13) and `advance` inherits it rather
>   than restating it (D0167).
>
>   So order-insensitivity is a property of the step id itself, and for a binary node the
>   two operand orders are **one step id**. Whether that is sound is a property of the
>   **node**, not of the operator's algebra. `union` is sound: it is linear, so it holds no
>   per-input state and both orders compute one answer. `join` is **not** sound, though `⋈`
>   commutes: its state keeps the two children's integrals **by position**, and its delta
>   rule pairs each child's delta with the other child's integral, so the two orders are two
>   different computations under one identity. `anti_join` is not sound, because it does not
>   commute. Where both sides carry the same schema — the only shape in which a swap does
>   not raise — the divergence is real and unannounced: measured, one `step_id` and two
>   different Δout, and with the step recorded the second order is served the first order's
>   answer with `rebuilt=False` and no exception. Nothing in a type system can see it
>   (RT-M3-03, D0174 — which corrects the stated premise of D0171 ruling (2), "a caller
>   error the type system should catch", while leaving its conclusion standing).
>
>   D0171 ruling (2) keeps `derivation_id` order-insensitive. The asymmetry therefore
>   belongs to the node: **a node whose operand roles are not interchangeable must carry
>   those roles in its own declared form**, so that the descriptor — and with it the step
>   id — distinguishes them. That requirement is stated here and is not yet met by this
>   executor; the defect is recorded rather than promised away.
>
>   One derivation, one output, holds because a step is a pure function of the descriptor
>   and those inputs — and it holds **only while the descriptor names the code the node
>   runs**, not a key some registry may resolve to anything. Hence the discipline: the
>   declared form of a node **must** carry the content address of any code a parameter names
>   — a predicate, a map, a monoid or group together with its identity and witnesses — and
>   that address is over the code's **source text**, the same bytes M1 has hashed since
>   D0084, one implementation rather than two (BRIEF §2). A callable with no addressable
>   source is refused, and a registered name whose code cannot be addressed is refused **at
>   declaration**: a descriptor that cannot say which code it means is not minted at all
>   (D0197). Before that, a step was also a function of the registry, which is named in none
>   of the inputs above — two processes registering different predicates under one name
>   minted one `step_id`, the trace served the first's output to the second with
>   `rebuilt=False`, and `TraceIntegrityError` could not fire because nothing had been
>   tampered with (RT-M3-01, D0174). The rule is not yet complete: a `map_rows` node's
>   registered **out-schema** is still resolved from the registry at tick time and is in no
>   descriptor, so the class RT-M3-01 names is narrowed, not closed. Measured, and recorded
>   here for the same reason.
>
>   `TraceStore`, `AlwaysRebuild` and `VerifyingTrace` are reused **as is**. A replayed
>   stream is served without recomputing **only where the caller recorded**: `advance`
>   consults the trace on every step and writes one on none by default. `record` is
>   keyword-only, defaults off, and recording is the caller's act. This is *not* M1's split:
>   `AlwaysRebuild` and `VerifyingTrace` both record unconditionally, and the policy choice
>   there is whether a recorded output is *served*; `advance` inverts it — always consult,
>   by default never write. The default is forced rather than chosen: frozen L3.15
>   re-records under a completed step's `step_id` outside its `pytest.raises` block, and
>   `TraceStore.record` refuses a conflicting re-record, so an `advance` that recorded by
>   default would turn that law into an error rather than a pass (D0171 ruling (1)). Under
>   the default a replay **recomputes the step body and writes nothing new**, because
>   everything a step produces is content-addressed; `rebuilt` reports whether this step's
>   output was new to the **store**, which is the honest measurement of "did anything get
>   built" and is not a trace hit. A recorded output that no longer resolves is not a cache
>   miss: it raises `TraceIntegrityError`, M1's L1.14 one step on. A reordered stream is a
>   different sequence of derivations — correctly, they are different events
>   [cites: pkm-event-identity] — and L3.9/L3.12 assert the *final integrals* converge
>   byte-identically all the same.

Two properties of this spelling are deliberate. It is **normative where the code is revertible**: "the declared form must carry the content address of any code a parameter names" survives a revert of D0197 (Tier A, "revert the three files") by becoming a violated requirement rather than a false sentence; `predicate_code`-beside-`predicate_id` would not. And it states the two open defects as defects, so it is true whether or not they are fixed before the sitting.

### 2. `docs/specs/m3.md` §10, line 444 — the L3.15 row

> `| L3.15 | The executor: `DeltaNode` descriptors are content-addressed data; one derivation, one output; a replay recomputes nothing into the store, and is served from the trace where the caller recorded; a tampered trace raises; a quarantining step moves nothing; replay is byte-deterministic | `test_l3_executor.py` | **L1**, §7 |`

"code included" is **not** in this row. No frozen L3.15 node tests code addressing — `test_l3_15_a_delta_node_descriptor_is_the_address_of_its_declared_form` (`tests/laws/m3/test_l3_executor.py:68-75`) asserts only that two `select` nodes with one `predicate_id` agree and differ from a `project` node; the code-address regression lives in unfrozen `tests/test_incremental.py` (D0197). A §10 row may not describe more than the law it names — that is D0161's own holding, and repeating it here would repeat the defect the supersession exists to end.

### 3. Completeness companions (NOT falsity claims) — install only if the owner widens the scope

`docs/specs/m3.md:324`:

> - **`advance(store, traces, node, state_ref, delta_refs, ledger_ref, *, record=False)`**
>   returns the new state ref, the emitted output delta's ref, and the (possibly extended)
>   ledger ref. `record` is keyword-only and defaults off; see the derivation bullet for why
>   recording is the caller's act and not the executor's.

Grounds: the frozen bullet is not false — a six-positional call is valid. It is **incomplete once `:339` is corrected**, because the corrected prose refers to a flag the frozen signature does not mention.

`docs/specs/m3.md:318`:

> A `DeltaNode`'s descriptor is the content address of its declared form (`deltaop/1`:
> operator name, canonical params — including the content address of the code any parameter
> names — and the node's `replay` flag, which the contagion rule may set whatever the caller
> declared), so two spellings of the same node are the same descriptor, and two different
> bodies behind one registered name are not [cites: pkm-event-identity].

Grounds: incomplete, measured at `src/tannen/incremental.py:362-370` and `:439-447`. No record establishes it false and I do not claim it is.

### 4. Item 2's prose corrections

`src/tannen/laws/plugin.py:48-50` — **unfrozen and uncustodied** (`MANIFEST=0 CUSTODY=0`, anchored check), so this is a builder edit in the same commit as the fix:

```
#: the naming hazard itself. A bare name is claimable by whatever imports it first, and
#: the remedy is NOT a package-qualified import: measured 2026-09-09, a dotted
#: `from tests.laws.m3 import _delta_model as M` closes the sys.path-shadow shape and
#: leaves `sys.modules["tests.laws.m3._delta_model"] = decoy` winning exactly as before,
#: while the `__init__.py` files it needs take collection from 842 to 808 with 8 errors,
#: because the eight sibling frozen law files' bare imports stop resolving. What closes
#: both shapes is to load the oracle from the frozen bytes by file location off the law
#: file's own `__file__`. Such a file may BORROW the oracle's name in `sys.modules` for
#: the duration of the load and must put back what was there: this check reads
#: `sys.modules` once, at the END of collection, so a superseding file that KEEPS the
#: name silences it for every law file it does not supersede (measured: 52 passed, exit
#: 0, under a decoy that aborts the same run at exit 1 without it). That is a forward
#: supersession under D0106 ruling 2 — a new law file, a manifest row and a note — which
#: is Tier-A builder work on D0128's precedent, not an owner act.
```

`tests/poison/oracle-shadow-spoofed/README.md:94-99` — **custody-set** (`tests/poison/**/*`), so this one is owner work at a sitting:

> **What it does not close.** This is defence in depth and its teeth are narrower than they
> look. The check compares CODE objects, so a decoy that changes only a DATA export slips
> through: measured 2026-09-09, a decoy whose callables are the frozen module's own function
> objects and which narrows `SHAPES` from 14 entries to 1 cuts L3.16 to a single case with
> this guard silent (`1 passed`, against `14 passed` clean), and the evidence record written
> under it says `examined: {law_nodes: 1, test_cases: 1}, verdict: pass`. `MUTANTS`,
> `CAUGHT_BY`, `FAMILIES` and `ATOMS` are substitutable the same way.
>
> The actual fix is not the package-qualified import RT-M1-01 and RT-M2-01 named — measured,
> that leaves `sys.modules["tests.laws.m3._delta_model"] = decoy` winning. It is a load from
> the frozen bytes by file location, borrowing the name and putting it back, landed as a
> forward supersession under D0106 ruling 2 — Tier-A builder work, no owner key, per D0128's
> precedent. This fixture keeps its job unchanged: it runs against the SUPERSEDED
> `tests/laws/m3/test_l3_differential.py`, which a forward supersession retains unedited.
> Its invocation is single-file, so it cannot see a cross-file disarm; that property is
> pinned by `tests/test_governance_scripts.py`, and pinning it here too is queued.

`tests/poison/README.md:62-65` — custody-set, owner work at a sitting:

> It defends against one exploitation of the naming hazard, not the hazard itself. The
> hazard is closed by superseding the frozen law file FORWARD — a new file that binds its
> oracle from the frozen bytes by file location, borrowing the name and putting it back —
> which is Tier-A builder work under D0106 ruling 2 and D0128's precedent, not a sitting
> item. What IS a sitting item is this fixture: a superseding file is immune by
> construction, so a poison line aimed at one would report "guard PASSED its poison". The
> fixtures keep naming the SUPERSEDED files, which a forward supersession retains unedited.

`docs/redteam/2026-09-05-m3-boundary.md` — a dated transcript, in neither `MANIFEST.sha256` nor `governance/custody.sha256`; per D0200's step-4l lesson it is not rewritten. Header note only:

> [added 2026-09-09] SUPERSEDED IN PART by D0204. RT-M3-04's closing recommendation — a
> package-qualified import — was measured and is not the fix: it leaves
> `sys.modules["tests.laws.m3._delta_model"] = decoy` winning, and the `__init__.py` files it
> needs break the eight sibling frozen M3 law files at collection (842 → 808 collected, 8
> errors). Nor did it need the owner's key: a forward supersession under owner-signed D0106
> ruling 2 is Tier-A builder work, as D0128 already demonstrated. The heading at line 29 also
> names L3.12 where the neutered oracle is L3.16's. The text below stands as the record of
> what the pass concluded on the day.

The citation correction, for the new record's text (D0179's fields and the report are immutable / dated):

> ONE CITATION CORRECTED, FOUR SITES. D0179's title, `docs/redteam/2026-09-05-m3-boundary.md:29`
> ("L3.12's kill criterion goes vacuous with the whole gate green") and
> `tests/poison/oracle-shadow-spoofed/_delta_model.py`'s header ("`check_differential` —
> BRIEF §6's differential kill criterion, frozen L3.12") all name L3.12. `check_differential`
> is L3.16's oracle: defined at `tests/laws/m3/_delta_model.py:1237` and called only from
> `tests/laws/m3/test_l3_differential.py:35`. L3.12 is carried by
> `tests/laws/m3/test_l3_graph.py` through `check_graph_convergence`
> (`tests/laws/m3/_delta_model.py:1181`), and frozen `docs/specs/m3.md:441` maps L3.12 to
> `test_l3_graph.py` while `:453-455` declares a failure of L3.12 to be BRIEF §6's kill
> criterion. The guard is oracle-scoped, so nothing D0179 measured changes. What does change
> is the inventory: the poison corpus and `scripts/custodian.sh` name only the L3.16 file, so
> **the file carrying the declared kill criterion is pinned by no poison line.**

---

## How it lands

**The precedent, quoted, not invented.** `decisions/0106-post-sitting-review-rulings.yaml:30-39`, Tier C, **owner-signed** (`decisions/0106-post-sitting-review-rulings.yaml.sig` exists; 15 `.sig` files in `decisions/`):

> "a law found wrong AFTER its milestone's Session B closed is superseded FORWARD — a new law file under the CURRENT milestone's own directory (never back-dated into the closed milestone's frozen set, never an in-place edit), the old file retained and marked superseded in MANIFEST.sha256's notes, and a decision record binding old and new together."

`governance/laws.yaml:5-10` carries the same text as the registry's own preamble. D0128 (`tier: A`, `status: accepted`, **no** `.sig`) mechanised it for law *nodes* and performed the first supersession. D0161 (`tier: A`, accepted, no `.sig`) is the only prior falsified-frozen-**prose** case and ruled at `decisions/0161…:28-30`: "Prose is not a node; the supersession machinery (D0128) retires law nodes, and running it against prose would be a category error."

**The reconciliation, which the new record must state.** D0106 ruling 2's *file-level shape* (new file, old retained unedited, manifest note, record binding old and new) carries to prose; D0128's *node machinery* (`governance/laws.yaml` entry, strict-xfail mark) does not. D0161's cheaper shape — a record alone — is unavailable here, because D0171 ruling (1) refuses exactly it: "a known-wrong frozen sentence glossed by a decision record is refused: supersede the prose forward … rather than leaving the gap."

### Item 1 — the spec corrections

1. **New file: `docs/specs/m3-corrections.md`.** Sits beside the document it corrects; not a milestone name. Safe on all three guards that touch that directory: `src/tannen/laws/discovery.py:112-116` derives milestones from `tests/laws/m*/`, `tests/test_laws_runner.py:50` reads `docs/specs/<milestone>.md` by name, and `scripts/check_concepts.py:281-285` is the **only** thing that globs `docs/specs/*.md` (repo-wide grep) — it requires `[owns]` or a resolving `[cites: <id>]`, which the corrected §7 text satisfies through `[cites: pkm-event-identity]` (`concepts/pkm-event-identity.yaml` is registered). Citation-pin accounting is unaffected: `pins_seen` at `scripts/check_concepts.py:237` counts concept records' `sources`, not spec markers. Structure: a header naming what it supersedes and at which commit, stating that `m3.md`'s bytes are unedited and every passage not listed still stands; then one section per superseded passage, each quoting the frozen text **verbatim with its line numbers**, then the corrected text.
   *Rejected:* editing `m3.md` (forbidden, and the point); `docs/specs/m4.md` (M3 is the current milestone — `m3-close` is what this sitting mints — so D0106's "current milestone's directory" already points at an m3-named artifact, and D0201 ruling (3) exists to stop this rolling into M4); a `docs/proposals/` file (a proposal is not frozen prose and cannot carry a superseding claim).

2. **`MANIFEST.sha256`: two additions, no existing row's bytes touched.** (a) A hash row for the new file appended at the **tail**, where post-freeze additions already sit (`:104-124`: `governance/tier-c.yaml`, the schemas, the poison fixtures, `.github/workflows/ci.yml`, `governance/tag-roles.yaml`, `scripts/custodian.sh`) — **not** inside the m3-laws-freeze block at `:77-87`, which would back-date it into a freeze it was not in. (b) A second entry in the existing note block at `:89-103`, modelled on the `tests/laws/m1/test_l1_rel.py` note at `:90-103`. `parse_manifest` skips `#` lines (`scripts/_gov.py`), so no new mechanism is needed. D0135's lesson applies literally — that note had to be corrected because it named a file that has never existed; name only files that exist.

   Drafted note wording:

   ```
   # docs/specs/m3.md
   #   SUPERSEDED IN PART, FOUR PASSAGES, forward under D0106 ruling 2 — never edited.
   #   The file stays frozen at m3-laws-freeze, its bytes are unchanged, and every
   #   passage not named here still stands.
   #     §7  :335-337  "(state_ref, ledger_ref, sorted delta refs)" — derivation_id sorts
   #                   the WHOLE input list (src/tannen/kernel/derivation.py:32) and the
   #                   list is one shorter on a first tick (src/tannen/incremental.py:523);
   #                   the word `sorted` also hides an operand-order collision on binary
   #                   nodes (RT-M3-03, D0174).
   #     §7  :337-338  "a step is a pure function of those inputs" — the registry was an
   #                   input named in none of them (RT-M3-01, D0174). D0197 closed the code
   #                   half; the map_rows out-schema residue is stated in the correction.
   #     §7  :339      "Replaying a stream hits traces" — advance consults the trace and by
   #                   default writes none (D0171 ruling (1), the owner's).
   #     §10 :444      the L3.15 row, which repeats :339's claim verbatim.
   #   Carried forward corrected in docs/specs/m3-corrections.md, which is frozen and
   #   manifested below. The record binding old and new is D0203. NO governance/laws.yaml
   #   entry: prose is not a node (D0161), and check_laws.py requires a file::function node
   #   and a successor law id that a law file defines (scripts/check_laws.py:172-195).
   ```

3. **No `governance/laws.yaml` entry, and the record says so.** Not merely unnecessary — structurally impossible: `scripts/check_laws.py:172-195` requires `node` to be `file::function` matching `LAW_TEST_RE` (`:45`) in an existing law file, and `successor` to be a law id some law file defines (`_successor_exists`, `:199`). A prose passage has neither. No `conftest.py` mark either: there is no node to mark. Stating the absence is D0161's own reason for writing the distinction down.

4. **One record, Tier A** — next free id **D0203** (`decisions/` ends at `0202`). `risk_flags: ["governance-paths"]`, `status: accepted`. Bindings: `manifest → docs/specs/m3-corrections.md` (enforced); `file → docs/specs/m3.md` (documentary, "frozen and unedited"); `file → scripts/check_manifest.py` (the guard whose own failure text has been naming this remedy at every boundary: `:86-87`, "record a defect decision and supersede instead (CLAUDE.md)"). `links: [D0045, D0049, D0084, D0106, D0128, D0135, D0161, D0167, D0171, D0174, D0191, D0194, D0197, D0201]`. Tier A because reversibility sets the tier (BRIEF §9.2): nothing is deleted, no frozen byte moves, no signature is made, and deleting the new file and its row restores the tree exactly. The five Tier-C doors (`governance/tier-c.yaml:19-28`) do not include superseding a spec.

5. **Signer: the builder, throughout — no new tag, and nothing new is signed.** `governance/tag-roles.yaml` has no class for a prose supersession and ends `unknown: refuse` (`:58`); `amendment-*` is owner-signed but scoped by its own note to BRIEF §3/§10 (`:31-33`), so using it here would misdeclare the authority claimed, and adding a class is itself a trust-root change. `governance/tier-c.yaml:152` says outright that nothing signs the manifest. No custody path changes, so no custody re-signature is triggered.

**Order of operations at the sitting (item 1).**

1. Precondition: clean tree; `sha256sum docs/specs/m3.md` still equals `MANIFEST.sha256:76`.
2. Write `docs/specs/m3-corrections.md`.
3. Append its `sha256` row after `MANIFEST.sha256:124`; add the note block entry after `:103`.
4. Add `decisions/0203-<slug>.yaml`; run `make projections` **before** `git add` (a stale `DECISIONS.md` reports as D0063 and D0177 failing, and they are innocent).
5. `git add` the four paths; run `uv run python scripts/check_manifest.py` in both default and `--staged` mode — expect "frozen paths intact; seals unbroken; custody set current". `check_staged` ignores staged paths not already in the manifest (`:76-78`), so the new file is invisible to it; `check_sealed_paths` does not fire because `docs/specs` is not a sealed dir (`governance/tier-c.yaml:77-80`). Note `check_manifest.py:62-64`: a manifest row whose path is not git-tracked fails, so the row and the `git add` are one act.
6. Commit — builder-authored, as every sitting commit is, under DELEGATIONS delegation 1.
7. Owner signatures, unchanged from what this sitting already spends: D0171 and D0201 (both Tier C, `blocked-on-owner`, both already binding `docs/specs/m3.md`), the receipt, and the `m3-close` tag over the commit that contains the new file, its row and the note.

### Item 2 — the superseding law file (M4 Session A)

Same shape, one milestone on: `docs/specs/m4.md` (with the law table row), `tests/laws/m4/test_l3_16_differential_superseding.py`, a manifest row per new file plus a note entry naming the superseded file, one Tier-A record (**D0204**), and the builder-signed `m4-laws-freeze` tag — `governance/tag-roles.yaml:25-27` maps `*-laws-freeze` to `signer: builder` under delegation 1, and `git tag -v` on m1/m2/m3-laws-freeze shows three consecutive builder signatures.

Two hard constraints found only by running it:

- **The M4 spec is a precondition, not paperwork.** Creating `tests/laws/m4/` adds `m4` to `MILESTONES` (`src/tannen/laws/discovery.py:112-116`), and `tests/test_laws_runner.py:68-80` then opens `docs/specs/m4.md` (`:50`) and asserts the discovered law set equals its table. Without that file the parameterised test raises `FileNotFoundError`. This is the real reason the item is Session-A shaped, and it is a sequencing fact, not an authority one. `m3b/` is the alternative if it must land sooner, and it costs a frozen `docs/specs/m3b.md` **and** an amendment to `test_milestone_labels`'s "milestone directories are consecutive from m0" assertion (`tests/test_laws_runner.py:96-98`) — a deliberate shape assertion.
- **The basename must not be reused.** There is no `__init__.py` anywhere under `tests/laws` (checked), so pytest's prepend import mode requires globally unique law-file basenames; a first draft named `test_l3_differential.py` under a second directory and collection failed with `import file mismatch`. Nothing in the repo states or checks this.
- **No `governance/laws.yaml` entry here either, for a different reason.** `superseded:` entries are marked `xfail(strict=True)` (`conftest.py:56-75`, `governance/laws.yaml:63-76`) and must FAIL now; the superseded M3 node still passes — the law is right, only its binding is hazardous — so an entry would be a strict XPASS and a red gate. `pending:` would be a claim about a change that will never land.

---

## The package-qualified import

### The line, before and after

Before — `tests/laws/m3/test_l3_differential.py:20-21`, and the same two lines in seven sibling frozen files plus a bare `import _delta_model` at `tests/laws/m3/_delta_subject.py:47`:

```python
import _delta_model as M  # noqa: E402
from _delta_subject import TANNEN  # noqa: E402
```

After — in the **new** file, `tests/laws/m4/test_l3_16_differential_superseding.py` (the M3 file is retained unedited):

```python
import importlib.util as _ilu
import sys as _sys
from pathlib import Path as _Path

_FROZEN_M3 = _Path(__file__).resolve().parent.parent / "m3"


def _load_frozen(stem: str):
    """The module at `tests/laws/m3/<stem>.py`, loaded from THOSE BYTES."""
    path = _FROZEN_M3 / f"{stem}.py"
    spec = _ilu.spec_from_file_location(stem, path)
    module = _ilu.module_from_spec(spec)
    _sys.modules[stem] = module
    spec.loader.exec_module(module)
    return module


def _load_frozen_oracle():
    """Claim the oracle names only for the duration of the load — so the frozen
    sibling's own bare `import _delta_model` resolves to the authenticated module — and
    put back whatever was there. `tannen.laws.plugin`'s oracle-shadow guard reads
    `sys.modules` ONCE, at the END of collection, so a file that KEEPS the frozen module
    installed under the bare name silences that guard for every law file it does not
    supersede."""
    stems = ("_delta_model", "_delta_subject")
    prior = {stem: _sys.modules.get(stem) for stem in stems}
    try:
        model = _load_frozen("_delta_model")
        subject = _load_frozen("_delta_subject")
        return model, subject.TANNEN
    finally:
        for stem, was in prior.items():
            if was is None:
                _sys.modules.pop(stem, None)
            else:
                _sys.modules[stem] = was


M, TANNEN = _load_frozen_oracle()
```

`prior` must span **both** loads: restoring after the first breaks a clean run, because `tests/laws/m3/_delta_subject.py:47` does its own bare `import _delta_model` (`ModuleNotFoundError`, 1 collection error).

**The package-qualified spelling the red team recommended at three boundaries is not the fix, on two independent measurements.** It leaves `sys.modules["tests.laws.m3._delta_model"] = decoy` winning (Python's `IMPORT_FROM` falls back to `sys.modules` after `AttributeError`), so only the `sys.path`-shadow half closes; and the three `__init__.py` files it needs stop `tests/laws/m3` being placed on `sys.path`, taking collection from 842 to 808 with 8 errors as the eight sibling **frozen** files' bare imports fail — an intermediate state that cannot be repaired in place. So it is not incremental either: it would have to supersede all nine M3 files in one motion or leave the suite red.

### The attack the unqualified form permits

`tests/laws` carries no `__init__.py`, so pytest's prepend import mode puts the law file's own directory on `sys.path` and caches the module under the flat name `_delta_model`. Whatever claims that name first wins. `governance/tier-c.yaml:77-80` seals only `tests/laws`, `tests/poison` and `governance/schemas`, so a new `tests/conftest.py` plus a sibling decoy needs no manifest row and breaks no seal. The shipped guard (`src/tannen/laws/plugin.py:140-172`, called from `pytest_collection_modifyitems` at `:221-225`) compares the code a module answers with against a fresh load of the frozen file — but `_fingerprint_of` (`:113-118`) returns `None` for anything without `__code__`, on both sides.

Measured today, on the tree copy, all with the shipped guard active:

| Run | Result |
|---|---|
| `tests/laws/m3/test_l3_differential.py`, clean | `14 passed` |
| same file, **data-only decoy** (every callable is the frozen module's own function object; only `SHAPES` narrowed 14 → 1) | `1 passed in 0.45s`, exit 0, guard **silent** |
| same file, code-changing decoy (`tests/poison/oracle-shadow-spoofed`) | guard fires: `sys.modules['_delta_model'] reports the frozen …/_delta_model.py but answers with different code for ['check_differential']` |

So the guard is blind to data substitution, and `SHAPES`, `MUTANTS`, `CAUGHT_BY`, `FAMILIES` and `ATOMS` are all freely substitutable. The evidence record written under the data decoy carries `examined: {law_nodes: 1, test_cases: 1}, verdict: pass` (`src/tannen/laws/plugin.py:324`), and nothing reads `examined` back.

**The disqualifying defect in the draft, reproduced.** The first draft's loader installs the frozen module under the bare name and never puts it back. The guard reads `sys.modules` once, after every module is imported, and pytest collects `tests/laws/m3` before `tests/laws/m4`. So the eight non-superseded siblings bind the decoy, the superseding file quietly restores the frozen module under the name, and the guard sees the frozen bytes and says nothing. Measured today, same decoy, same tree, same interpreter:

| Collection | Loader | Exit | Outcome |
|---|---|---|---|
| `tests/laws/m3` | (draft) | 1 | guard fires, "answers with different code for `['check_differential']`" |
| `tests/laws/m3 tests/laws/m4` | **keeps the name (draft)** | **0** | **`52 passed` — guard silent, M3's L3.16 running fourteen vacuous cases** |
| `tests/laws/m3 tests/laws/m4` | **borrows and restores** | 1 | guard fires again |
| `tests/laws/m3 tests/laws/m4` | borrows and restores, no decoy | 0 | `52 passed` — no false positive |
| `tests/laws/m4` alone, clean | borrows and restores | 0 | `14 passed` |

The draft would have converted a hard abort into a passing gate — and no fixture would have caught it: `scripts/custodian.sh:249-252` invokes pytest on the single file `tests/laws/m3/test_l3_differential.py`, so `m4` is never collected and the poison line goes on reporting "custody floor intact".

### The regression test, and how it is watched failing first

`tests/test_governance_scripts.py::test_a_superseded_law_binds_its_oracle_from_the_frozen_bytes` — unfrozen, uncustodied (`MANIFEST=0 CUSTODY=0`, anchored), builder-landable. It constructs the violating state itself in `tmp_path` (D0092: a regression test that waits for a sitting is not a regression test), never reading a `tests/poison/` fixture, and runs its subprocesses under `TANNEN_NO_EVIDENCE=1` so no poisoned verdict reaches the store. It writes two decoys and a `-p` bootstrap plugin: a **data decoy** (re-exports every callable of the frozen module unchanged, sets `__file__` to the frozen path, narrows `SHAPES` to one entry) and a **code decoy** (a silent stub of `check_differential`).

Three assertions:

1. **The binding is immune.** Under the data decoy — which the guard cannot see, so the guard does not confound the measurement — the superseding file collects **fourteen** cases. Positive control in the same assertion: the superseded `tests/laws/m3/test_l3_differential.py` under the identical decoy collects **one**. *(Measured today: 14 and 1; clean control 14.)*
2. **The guard is not disarmed.** A run collecting the superseded file **and** the superseding file together, under the code decoy, exits non-zero with `answers with different code` in its output — asserted on the guard's own tooth text, as `scripts/custodian.sh` already does, not on the exit code alone. *(Measured today: exit 1 with the borrow-and-restore loader; **`52 passed`, exit 0** with the keep-the-name loader — that is the watched failure, and it is invisible to any single-file run.)*
3. **The decoys arrive.** The superseded file alone under the code decoy exits non-zero with the same text. *(Measured today.)*

One correction to the reviewer's own proposed assertion, which I found by running it: the earlier spelling — "the superseding file under the loud decoy exits 0 and `DECOY ANSWERED` is absent" — is **false with the corrected loader**. Under the borrow-and-restore loader, `pytest tests/laws/m4` alone with a code decoy primed now exits **1**, because the decoy is what remains in `sys.modules` at end of collection and the guard correctly fires. That is the right behaviour, and it is why immunity must be asserted through the data decoy (assertion 1), never through a code decoy the guard will abort on.

**A second, cheaper piece, landable immediately and independently:** a structural ratchet in `tests/test_laws_runner.py` counting frozen law files that bind an oracle by bare import — **19 today, derived by AST from the manifest's own law rows and the sibling `_*.py` stems, never a hand-maintained list** (D0171 ruling (3)): m1: 2, m2: 8, m3: 9. I re-derived it independently and it agrees byte for byte, including `_subject.py` and `_delta_subject.py` appearing as both oracle and importer. It goes green the day it lands and stops M4 Session A adding a twentieth. The residue grew 2 → 10 → 19 across the three boundaries the recommendation sat unactioned.

---

## What is genuinely owner-only, and what is not

**Item 1's owner-key residue is empty. Measured, not reasoned.**

- `docs/specs/m3.md` is frozen — exact-field match at `MANIFEST.sha256:76`, file hash identical. That much is real. The D0191 trap was checked for: **`MANIFEST.sha256` does not list itself** (`awk '$2=="MANIFEST.sha256"'` returns nothing), so the manifest is not frozen.
- **Zero `docs/` paths and zero `tests/laws` paths appear in `governance/custody.sha256`** (75 rows; anchored checks). `MANIFEST.sha256` is not in it either. Frozen and custody-set are different sets, and the spec is in only one of them. Nobody has ever signed a spec or a law file.
- **BRIEF §9.1 does not cover it by name.** `BRIEF.md:164` names `scripts/custodian.sh`, `allowed_signers` and `tests/poison/`; `CLAUDE.md:23-24` repeats exactly those three as "author-key territory". Tier-C door 5 (`governance/tier-c.yaml:28`) says "scripts/custodian.sh, allowed_signers, tests/poison/, **and their** MANIFEST.sha256 rows" — a closed three-path set, not any row.
- **The supersession never touches the frozen file.** Its footprint is one new file in an unsealed directory, one appended hash row, one `#` comment, one Tier-A record. `governance/policy.yaml:62-63` excludes "any **edit** to a frozen path" — a new file is not an edit. `scripts/check_manifest.py:76-78` skips staged paths not already in the manifest, so the guard cited as the blocker cannot see the act; and when it does fire, its message (`:86-87`) names the builder's remedy: *"record a defect decision and supersede instead (CLAUDE.md)"*.
- **`governance/tier-c.yaml:86-92` affirmatively refuses to put the owner's key in this path**: "the manifest is builder-maintained and GROWS AT EVERY LAW FREEZE … An owner signature over the manifest would therefore put the owner's key in the path of every milestone's Session A, spending the attention the delegation exists to save." `:152`: "nothing signs the manifest."
- **Both precedents run this way.** D0128 — the only supersession this repo has executed, retiring a node in a frozen, sealed file — is `tier: A`, accepted, **unsigned**. D0161 — the only prior falsified-frozen-prose case — is `tier: A`, accepted, **unsigned**.
- **The irreversibility argument proves too much.** D0171's `reversibility` field ("the supersession itself cannot be un-recorded — which is why it waits for the signature") applies to every record: D0045 makes all decision fields immutable. If un-un-recordability made a door, all 202 records would be Tier C. The doors are a closed list of five (`governance/tier-c.yaml:19-28`), and superseding a spec is not among them.

**Where the "owner-only" classification actually came from.** The owner's quoted words on this item are two sentences, and neither mentions the key: D0171 ruling (1) — *"the gap between what's frozen and what's true is exactly where the next D0049 will hide"* — and D0201 ruling (3) — *"frozen prose known to be false is precisely how D0049 happened."* Both are arguments for doing it **sooner**. The rest is builder-authored framing in unsigned records: D0171's preamble ("the Tier-C half of them — superseding frozen prose"), its `reversibility` field, its binding detail at `:105-111` ("no builder act may touch it" — true of `m3.md`, and irrelevant to an act that never touches `m3.md`), and D0201 `:49` ("installation stays owner territory"). `docs/proposals/2026-09-04-m3-boundary-sitting/README.md` gives the real recorded blocker for both items: *"Both need new frozen prose that nobody has drafted."* Not the key. This is D0194's failure one layer up — there a substring match turned a builder edit into a ceremony; here a tier label does the same, and it has cost two boundaries on item 1 and three on item 2.

**Item 2: the fix is builder-landable in full. The genuine residue is small, and it does not block anything.**

- `governance/laws.yaml`, `src/tannen/laws/plugin.py`, `tests/test_laws_runner.py` and `tests/test_governance_scripts.py` are in **neither** `MANIFEST.sha256` nor `governance/custody.sha256`. `conftest.py` is custody-set and needs **no** change — its supersession machinery is generic — which is the second reason to prefer the file-location spelling over the package-qualified one.
- The existing custody floor survives the fix untouched: `scripts/custodian.sh:249-252` names `tests/laws/m3/test_l3_differential.py`, which a forward supersession retains **byte-identical**, and the poison line was measured still biting with the superseding file installed.
- **Genuinely owner-only, all queueable, none blocking:** (a) a poison fixture pinning the anti-disarm property — and note it must collect `m3` **and** `m4` together, because the corpus's single-file invocations are structurally incapable of seeing a cross-file disarm; (b) the two poison README corrections and the `tests/poison/oracle-shadow-spoofed/_delta_model.py` header mis-citation, all inside `tests/poison/**/*` (custody-set, Tier-C `trust-root-changes`); (c) optionally an `m4-laws-freeze` row in `governance/tag-roles.yaml` `required_tags` (`:46-54`) — not required, since `*-laws-freeze` already matches a role pattern, but skipping it makes `m4-laws-freeze` the first laws-freeze tag deletable with no guard noticing, which is D0095's enumeration-that-lags shape.
- Until (a) lands, assertion 2 of the regression test is what holds the anti-disarm property, in an unfrozen file the builder owns. That is the honest statement of the floor, and it belongs in the record.

**What I am not doing.** The brief for this session says the builder drafts and the owner installs, so this document is a proposal and nothing was landed. But the measurement above is the loud finding the task asked for: if the owner still wants to install personally, that is an instruction and it stands — it should then be recorded as **quoted owner speech**, because as a governance classification it is measurably false and will keep generating deferrals for every future supersession.

---

## Open questions for the owner

1. **Scope of item 1: four passages or seven?** Four are confirmed false. `:202` was refuted by a reviewer and I recommend leaving it alone. `:318` and `:324` are **incomplete, not false**, and their replacements are drafted above with honest grounds. Widening enlarges what the signature installs and changes the manifest note; narrowing leaves the corrected prose referring to a `record` flag the frozen signature does not mention. My recommendation: install the four, plus `:324` and `:318` as explicitly labelled completeness companions.

2. **Sequencing: fix the executor first, or freeze the requirement?** Three defects are live in **unfrozen, uncustodied** `src/tannen/incremental.py`: operand roles absent from the declared form for `anti_join` (does not commute) and for `join` (commutes, but its state is positional — measured today, and the earlier draft called it safe), and the `map_rows` out-schema still resolved from the registry at tick time. All three are Tier-A builder work of exactly D0197's and D0198's shape. The corrected prose above is written to be true either way — it states the requirement normatively and records the defect — so nothing is blocked. But the owner may prefer the fixes to land in M4 first so the frozen prose states a clean rule. **Say which, or the builder decides and records it.**

3. **Scope of item 2: one file, two, or all nine?** The minimum is L3.16 — the file the poison corpus and the custodian already name. But `docs/specs/m3.md:453-455` declares a failure of **L3.12** the kill criterion, L3.12 lives in `tests/laws/m3/test_l3_graph.py`, and **no poison line names that file**, so the honest minimum is arguably two. The full M3 set is nine; the repo-wide residue is nineteen. Cost measured: m3 alone is 38 nodes, m3+m4 with one superseding file is 52 in ~25s. Superseding all nine roughly doubles the M3 law runtime and leaves nine laws stated twice, since the old nodes cannot be retired (a `superseded:` entry is `xfail(strict=True)` and they still pass). My recommendation: all nine in M4 Session A, plus the 19-file ratchet so nothing adds a twentieth.

4. **Is there a third registry state the owner wants?** "Retired as hazardous, still green, not collected" would let the corpus drop the duplicated statement. `governance/laws.yaml` is builder territory (created by D0128, Tier A, unsigned), but `scripts/check_laws.py` — which would have to understand the new state — is **custody-set**, so inventing one costs an owner re-signature of the custody floor. That is a reason not to invent it now, and a reason it cannot be a silent builder call if it is ever wanted.

5. **The frozen L3.15 law file is a separate act and should not be folded in silently.** `tests/laws/m3/test_l3_executor.py:19-23` (module docstring: the six-argument signature, and "rebuilt is False on a trace hit"), `:79-81` ("A step is a pure function of (descriptor, state, ledger, deltas), so replaying the same tick hits the trace"), `:88` (the assertion message) and the node **name** `test_l3_15_one_derivation_one_output_and_a_replay_hits_the_trace` all carry the falsified claims — and the assertion passes on a store hit while its message claims a trace hit. That file is in a sealed directory, so correcting it really is D0128's node mechanism: a superseding law file **plus** a `governance/laws.yaml` entry with a real successor. It belongs with item 2's M4 law work or its own record. **Fold it in, or leave it, but say which.**

6. **Is "installation stays owner territory" an instruction or a classification?** If the owner said it, one sentence at the sitting records it as quoted speech and it stands. If it is the builder's own reading — which is what the records show — then D0203 should correct it forward, because D0171 and D0201 will be signed as written and immutable, and the false classification would otherwise survive its own correction. That is D0135's exact lesson about a note naming a file that never existed.

**Artefacts.** All measurements above are reproducible from the scratchpad: `<scratchpad>/join_swap2.py`, `.../map_residue.py`, `.../antijoin_swap_check.py` (run with `uv run python <path>`), and the tree copy at `.../scratchpad/repo`, which now carries the borrow-and-restore loader at `tests/laws/m4/test_l3_16_differential_superseding.py` (the refuted keep-the-name draft is preserved at `.../scratchpad/m4-keepname-backup.py` and `.../scratchpad/m4-orig.py`). Decoys: `.../scratchpad/decoy-data`, `.../scratchpad/decoy-loud`, and the repo's own `tests/poison/oracle-shadow-spoofed`. `git status --porcelain` in the repository root is empty.
