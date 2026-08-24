# TANNEN — a kernel for pure, content-addressed, provenance-native data pipelines

*Design brief v2, for implementation by coding agent. Supersedes v1 wholesale.*
*v2 changes: (a) the constellation is unified at the level of **concepts, never repos** — every concept has exactly one owning document, adopted elsewhere by reference and conformance test, never by restatement; (b) the kernel is designed so the **easy path is the lawful path** (§5); (c) owner involvement during development is minimised by a tiered **autonomy protocol** (§9) that replaces most escalation with recorded, vetoable decisions.*

---

## 1. What this is, where it sits

**Is:** a small semantic kernel plus an embedded Python DSL for defining data pipelines as compositions of pure, total, versioned transformations over content-addressed values, with semiring-annotated collections (incrementality and provenance as two instances of one mechanism), memoized Merkle derivation graphs, and executable laws with recorded evidence.

**Is not:** an orchestrator, a scheduler UI, a distributed system, a SQL parser, a decision-maker, or a replacement for any existing repo.

### The constellation (border treaty)

| Repo | Role | Tannen's relationship |
|---|---|---|
| `life-agent` | The architecture: KB **derives**, agent **decides** (PRINCIPLES §1); L0–L4 layer cycle (derivation-engine-design §0) | Tannen is strictly KB-side. It derives; it never decides. It is a candidate future algebra under pkm's L1 — by contract, not import. |
| `pkm` | Owns identity, events, recording, determinism (SPEC-PRINCIPLES) | Tannen **defers** to pkm on those concepts (§2) and adds what pkm lacks: the operator algebra and its laws. |
| `credence` | The brain (belief, utility, EU) behind a language-neutral seam | Future occupant of the Governor seam (§7). Never imported. |
| `proplang` | Frozen. Supplier of disciplines: exactness, the door, the frozen-oracle protocol | Concepts adopted (§2); the repo is never extended by this project. |
| Renavon monorepo | The business; funds and supplies the empirical substrate | M5 dogfood inputs only. No imports either direction. |

**Standing rule: repos never import each other.** Unification happens in §2's registry and §7's seam. Any PR that adds a cross-repo code dependency is wrong by definition.

---

## 2. Concept ownership registry (the DRY mechanism)

Strict conceptual DRY: **each concept has exactly one normative home**. Everyone else adopts by *pin + conformance test* — never by restating the definition. Restatement is duplication; duplication is drift; drift is the bug.

Mechanism — **the registry is data the build consumes; prose is a generated projection**:

- `concepts/<id>.yaml`: one schema-validated record per adopted concept — owner repo/doc/section, pinned commit, content hash of the vendored snapshot, grade (§2.1), artifact paths. These records are the **test manifest**: the conformance suite is parameterised over them at collection time, so a record naming a missing vector corpus fails pytest collection, and a vendored artifact with no record fails the completeness check. The registry cannot rot without turning CI red, because it is not documentation of the tests — it is their input.
- `CONCEPTS.md` is **generated** from the records (freshness-gated in pre-commit) and never hand-edited.
- Upstream drift is reported, not policed by prose: a scheduled job diffs each pinned commit against the owner's HEAD and files a Tier-B decision record when an owner has moved, prompting a re-pin.
- Normative prose in this repo is minimised; what remains carries `[owns]` or `[cites: <concept-id>]` markers, checked mechanically. Semantic paraphrase detection is not attempted — the defence is having almost nothing to paraphrase.

Changing an owned concept happens **only in its owner** (a Tier-C act, §9); tannen then re-pins.

### 2.1 Grades — every concept at the strongest affordable formality

A concept's *shape* determines its treaty artifact:

- **Grade S — schema/language + frozen vectors**, for **data-shaped** concepts (anything crossing a repo boundary *as data*: provenance refs, capture envelopes, evidence records, descriptors, the Governor wire). The owner publishes an executable grammar/schema plus a frozen corpus of positive and negative test vectors, and may publish a reference validator. Adopters vendor the **vectors, never the code**; conformance = parse all positives, reject all negatives, round-trip. This is the proplang method generalised: the Haskell port conformed to a frozen Python oracle byte-for-byte without sharing a line of code.
- **Grade L — law + generator**, for **behaviour-shaped** concepts (determinism, idempotency, convergence): quantified statements over executions cannot be schema-checked; their executable form is a property test with a generator and recorded evidence (§6).
- **Grade P — prose + review**, for **judgment-shaped** concepts (derive/decide split, governor-is-premature): formalising these buys nothing; they gate PRs through review, citing the owner.

**Wire-first rule:** a concept that crosses a repo boundary as data MUST be Grade S. If it can only be stated in prose, it is not yet ready to cross a boundary.

**Anti-Babel rule (standing; Tier C to change):** there is no lingua-franca DSL in which multiple repos are written, and no shared runtime or toolchain dependency between repos. Shared *language definitions and vectors* are data; shared *implementations* are the repo unification this brief forbids. The constellation's languages are exactly three: tannen's algebra (the derive layer), proplang (the decide layer), and Grade-S wire schemas at each boundary between them.

| Concept | Owner (normative home) | Tannen's posture |
|---|---|---|
| Source identity (bytes hashed outside the system); event identity (hash of inputs incl. producer config); cache as view over the event record; recording makes no truth claims | `pkm` SPEC-PRINCIPLES §1–§4 | **Adopt.** Tannen's "descriptor + derivation + trace store" must satisfy pkm's event-tuple diagnostic; conformance test asserts the mapping. |
| Determinism contract (semantic equivalence; a cache hit is deterministic regardless of producer behaviour on a miss); reproducibility as a **declared per-producer property** (bit / in-distribution / non-reproducible) | `pkm` SPEC-PRINCIPLES + SPEC §7.1 | **Adopt.** Every oracle declares its reproducibility class; the kernel treats the declaration as data. Do not redefine, do not "fix". |
| Provenance ref grammar (`sha256:<hex>` prefix discipline; typed opaque refs) | `pkm` SPEC-PRINCIPLES §1 (hash prefix); Renavon ADR-002 (ref kinds) | **Adopt.** Tannen's Why-semiring elements are refs in this grammar, so lineage is portable across all systems. |
| Derive/decide split; faculties over language-neutral seams; governor-is-premature-until-demand-logs | `life-agent` PRINCIPLES §1, §3, §5; derivation-engine-design §0 | **Adopt.** Encoded as the Governor *seam* (§7): interface now, implementation never (here). |
| Exactness at the decision layer (Rational, no floats, no tolerances); the door (declared namespace covered exactly or refused by name; no silent defaults); the world supplies every constant | `proplang` KERNEL.md | **Adopt.** Kernel keys refuse floats by default (§5); anything crossing toward a decision layer is exact or explicitly declared lossy. |
| Frozen-oracle build protocol (tests frozen + manifest signed before implementation; author/builder key custody; delegation recorded in tag messages) | `proplang` WRITEUP.md / CLAUDE.md | **Adopt as process** (§8), with standing delegation to minimise owner touchpoints (§9). |
| Semiring-annotated relations; operator algebra with type/delta/provenance rules; laws L1–L6; layers as sublanguages; correct-by-default catalogue | **tannen (this repo)** — this brief until code exists, then `KERNEL.md` here | **Own.** Other repos may one day adopt from here by the same mechanism; tannen never exports by copy-paste. |
| Credence-functor generalisation: derivation codomain lifted to `(Distribution[Value], Provenance)` | `life-agent` derivation-engine-design §0 | **Acknowledge as the L2 generalisation of tannen's semiring parameter.** Documented seam; out of scope to implement. |

---

## 3. Design principles

P1. **Pure core, effectful shell.** Transformations are deterministic functions of content-addressed inputs and a descriptor. All nondeterminism enters through oracles whose outputs are captured immutably before anything reads them. (Identity and event semantics per the pkm rows of §2.)

P2. **Content addressing everywhere.** Values, collections, code, oracle specs, derivations: all identified by hashes of canonical encodings.

P3. **Totality.** A node yields `Ok(rows) | Quarantine(reason+provenance)`. Exceptions never cross a node boundary; "empty" is a declared, distinguishable outcome.

P4. **One annotated-relation type.** `Rel[K, S]`, S a commutative semiring: `ℤ` → Z-sets/deltas (DBSP); `𝔹` → sets; `Why` → support-set provenance (refs in the §2 grammar); products compose. Default is `ℤ × Why` (§5).

P5. **Incrementality is derived, never hand-written.** Users declare algebraic structure (commutative monoid; abelian group for subtractability); the kernel derives delta forms and property-tests the declared laws at registration.

P6. **Laws are executable and evidence is recorded.** Every law run emits a content-addressed evidence record (law id, seed/distribution, descriptors, verdict). Evidence records are the future belief-update stream for the Governor (§7).

P7. **No hidden clock, no NULL, no unpriced floats.** Time is an oracle; optionality is `Option[T]`; floats enter keys only through an explicit lossy declaration (the door, per §2).

P8. **Layers are sublanguages.** `capture` (oracles only) → `decode` (total map/filter, quarantine-producing) → `derive` (full algebra) → `serve` (project/filter only). Membership is statically checked.

P9. **The easy path is the lawful path.** Wherever a discipline exists, the API's shortest spelling satisfies it and violations require explicit, ugly opt-outs. §5 is the normative catalogue; every new API is reviewed against it.

---

## 4. Core calculus (condensed; v1's definitions stand where not amended)

- **Store:** content-addressed, write-once, append-only; local fs (M0), R2 (M4). `gc` prints a refusal.
- **Canonical encoding — DECIDED:** canonical JSON (UTF-8, NFC, sorted keys, integers exact, decimals as tagged strings, no floats untagged), following the production `canonical_json` precedent. Golden-tested across interpreters. CBOR is a benchmark-gated future migration, not a discussion.
- **Descriptors:** `H(kind, name, code_hash, params_hash)` with a human label *derived automatically* from module path + semver-ish counter — there is no "forgot to bump" state (§5.2). Oracle descriptors include the full effective spec (model id, prompt hash, tool-schema hash, params; or request template hash) and a **declared reproducibility class** (§2).
- **Oracles & captures:** invocation writes the capture before any read; policy = invoke iff no capture for `(oracle_descriptor, input_key)`, subject to SpendGuard (default-deny over a checked-in budget file). Built-ins at M4: Fetch (full WARC-shaped envelope), LLM (full request/response incl. resolved model + usage), Clock.
- **Operator algebra:** the v1 table stands (map/project, filter, union, join, distinct, aggregate-over-declared-monoid, anti_join), each operator shipping (type rule, delta rule, provenance rule, laws + property tests). Reference semantics: the DBSP paper; ambiguity resolved by the Lean formalisation; silence resolved by a pinning property test, recorded as a decision record bound to that test (§9).
- **Derivations:** `DerivationId = H(transform_descriptor, sorted(input_ids))`; TraceStore = verifying traces. Rebuilders shipped: `AlwaysRebuild`, `VerifyingTrace`. Everything smarter lives behind the Governor seam (§7).

---

## 5. Correct by default (normative catalogue)

The kernel's job is to make violations *unwritable*, not merely detectable:

1. **No unversioned code.** The only way to define a transform is the registering decorator, which computes `code_hash` and derives the label. An unhashed function cannot enter a graph.
2. **No silent behaviour drift.** Golden hashes bind (descriptor → outputs on fixtures); a behaviour change without a new descriptor fails CI mechanically, and regenerating goldens is a one-command, reviewable diff.
3. **No hidden IO.** The kernel package imports no IO modules — enforced by an import-linter contract in CI. The only IO doorway is `oracles/`, and the only way to read the world is through a capture handle.
4. **Raising is safe.** An exception inside a transform is wrapped into `Quarantine` with provenance by the runtime. The lazy path (just `raise`) is thereby the correct path; crashing the pipeline requires opting out.
5. **Lineage without asking.** The default semiring is `ℤ × Why`: every pipeline gets deltas *and* support-set provenance unless it explicitly opts down (`annotations=Z_ONLY`) with a recorded reason.
6. **Aggregates carry their laws.** `aggregate` accepts only a `Monoid`/`AbelianGroup` object, whose laws are property-tested at registration. An aggregate with untested algebra cannot be constructed.
7. **No wall clock.** `now()` does not exist in the kernel namespace; the Clock oracle is the only source of time, so replay determinism is not a discipline but a fact.
8. **Keys refuse floats.** Canonical encoding rejects bare floats in keys; `Lossy(f, grid)` is the explicit door, priced and visible.
9. **Layer defaults are strict.** A node's layer defaults to the most restrictive admitting its operators; widening is explicit. Exports default to `serve` (trivial provenance by construction).
10. **Spending is opt-in.** `tannen run` is replay-only by default and refuses novel oracle invocations; `tannen run --spend` engages SpendGuard against the budget file.
11. **Evidence is automatic.** Running any law writes its evidence record; `tannen laws report` fails CI when current descriptors lack fresh evidence for the milestone's law set.

---

## 6. Laws (the empirical layer)

L1 replay determinism (fixed captures + descriptors ⇒ byte-identical outputs, incl. fresh interpreter with randomized hash seed) · L2 idempotency (empty delta ⇒ no change) · L3 convergence (random batch partitions ≡ one-shot; declared-monoid laws tested directly) · L4 incremental ≡ reference (per operator and on random composite graphs) · L5 provenance soundness by deletion test (delete a source row; every changed output row must have carried its ref) · L6 differential correctness vs DuckDB on the SQL-expressible fragment (with the no-NULL mapping explicit). Hypothesis throughout — examples cost milliseconds here.

---

## 7. The Governor seam (L3, specified, not implemented)

One interface, three future call sites (life-agent L3, this kernel's rebuilder, the Renavon decision registry). JSON-RPC over stdio (the credence seam pattern):

- **Request:** derivation graph summary (nodes, descriptors, staleness), cost model (compute time, oracle spend, owner attention), evidence records (§6), demand (which outputs are wanted, by when).
- **Response:** ranked actions from {derive, recompute, verify(law), invoke(oracle), abstain}, each with expected value and cost.

The wire is **Grade S**: a versioned JSON Schema plus frozen positive/negative vectors live in this repo (first speaker owns v0; ownership may transfer to `life-agent` when credence implements — a Tier-C act). Conformance for any future governor is against the vectors, never against tannen's code. Evidence records (§6) are likewise Grade-S data: their schema and vectors ship alongside the laws that emit them.

Implementers: today `VerifyingTrace` (a degenerate governor whose prior is a dirty bit); eventually credence; policy-language candidate proplang (deliberation priced exactly; the floor answers the metareasoning regress). Per the life-agent doctrine adopted in §2: **the governor is premature until demand logs exist** — tannen ships the seam, the evidence stream, and nothing else.

---

## 8. Milestones (unchanged scope from v1; process amended)

M0 store & identity → M1 Rel + algebra + reference executor (kill: flaky L6 ⇒ fix encoding before anything else) → M2 provenance (L5) → M3 delta executor (L2–L4, arrival-perturbation generators) → M4 boundary (oracles, R2, optional ClickHouse emission for `serve` only) → M5 dogfood: one Renavon vertical, byte-identical vs production on frozen inputs, divergences analysed (production bugs found = wins) → **M5b (optional):** one pkm document vertical as the generality test. Post-M5 seams: governor implementation, ℕ[X] provenance, Rust port, Feldera as alternative delta executor.

**Frozen-oracle protocol per milestone** (adopted from proplang, §2): the milestone's law/property files are frozen and `MANIFEST.sha256` signed **before** implementation begins; implementation ends when the frozen suite is green. Signing custody per §9 — builder-signed under standing delegation, author countersign only at M0 (opening) and M5 (close).

**Selection rules replace escalations.** M5 vertical: the agent selects the Renavon source minimising (parser LOC × distinct operators required) among sources with a visible export, and records the choice + measurement as a decision record (§9). M5b vertical: smallest pkm source type by producer count. No question is asked.

---

## 9. Autonomy protocol (minimising owner dependence)

Decisions are **append-only event records, not a journal**: `decisions/<seq>-<slug>.yaml`, schema-validated (id, tier, decision, rationale, reversibility, status, `veto_by` for Tier B, and **bindings**). `DECISIONS.md` and the weekly digest are generated projections of the records — a digest cannot omit a decision, because it is a query, not authorship. Truth is the fold of the records: the life-agent §7 pattern applied to the repo's own governance.

**Bindings make decisions load-bearing.** A record may bind to the artifact that enforces it — a property-test path, a golden file, a guard-config key. CI fails if a binding's target is missing or skipped; the generated report flags any unbound decision as `unenforced` — visible debt, never silence. Tier-B veto clocks are computed from `veto_by` by the digest job, and expiry transitions status mechanically. The Tier-C closed list below lives as `governance/tier-c.yaml`, consumed by the pre-commit/CI guards themselves — the list the human reads is the list the machine enforces; one source.

The owner's involvement is a weekly batch, not a stream.

- **Tier A — agent decides, records, proceeds.** Reversible, in-repo, contract-conformant: naming, module layout, test design, pinning ambiguous semantics via property tests, dependency choices within the stack, selection-rule outcomes.
- **Tier B — decide provisionally, flag, proceed-unless-vetoed.** Anything reversible but taste-laden (DSL surface syntax, CLI ergonomics, golden regeneration after intended behaviour change). Collected into a weekly decision digest; **silence for one review cycle = consent.** Work never blocks on Tier B.
- **Tier C — hard stop, owner required.** Closed list: spend beyond the budget file; modifying an *owned concept* in another repo (§2); any cross-repo code dependency; publishing/licensing; deleting or overwriting any store content; changing this brief's principles (§3) or non-goals (§10); M0 opening and M5 closing signatures.

Standing delegations, recorded once in-repo (the proplang tag-message pattern): builder key signs law-freeze tags and implementation commits; budget file authorises oracle spend up to its ceiling without asking; goldens regenerate freely when the descriptor moved with them.

Pre-decided in this brief so they are never asked again: canonical encoding (§4); default semiring (§5.5); no-NULL/no-float policy (P7); the name (tannen — veto in a weekly batch if disliked); milestone order (§8); DuckDB as the differential oracle (L6).

### 9.1 Custody floor (owner amendment, 2026-08-24 — applied additively at Session 0; decision records D0017–D0022)

- **The custodian.** `scripts/custodian.sh` is small and author-frozen (manifested together with `allowed_signers` and `tests/poison/`). It verifies: signed tags; frozen-path hashes; that the CI config's hash is manifested; and **guard liveness by poison** — every guard must FAIL against `tests/poison/` (one deliberately violating fixture per guard). A guard that passes its poison is weakened, and the custodian says so.
- **Attention receipts.** Each custodian run writes an author-signed dated receipt. Tier-B silence-as-consent is valid **only while the latest receipt is fresh**; stale ⇒ Tier-B blocks accumulate and work pauses at the next milestone boundary.
- **Cadence.** Owner sittings at **milestone boundaries only**; receipt validity = next boundary + 7 days. Mandatory extra sittings gate M4 (before any nonzero budget) and M5 (before touching Renavon inputs).
- **Exception-only digest.** The digest surfaces risk-flagged decisions (spend, public surface, ref grammar, governance paths) plus K=3 randomly sampled others; the rest auto-consent under a fresh receipt. Ratcheted metrics: the unenforced count and the Grade-P/S-pending residue must trend down.
- **Red team.** At each milestone boundary; findings become poison fixtures.
- **Opening.** `docs/OPENING.md` includes custodian cron setup on the owner's machine with hardware-key signing (touch = presence), and the first receipt.

### 9.2 Reversibility tiers & graduated autonomy (owner amendment 2, 2026-08-24 — applied additively at Session 0; decision records D0023–D0027; supersedes §9's tier boundaries where they conflict)

Tiers classify by **reversibility, not importance**:

- **Tier A — decide, record, proceed:** ALL reversible in-repo work, absorbing former Tier B (DSL surface syntax, CLI ergonomics, goldens-with-descriptor-bump, test design, dependencies). Machine gates (laws, guards, CI) are the only gates. No owner reading obligation beyond the sampled spot-checks.
- **Tier B — vestigial:** reversible but **externally visible pre-release surfaces** only. Silence-consent under a fresh receipt, as before (§9.1).
- **Tier C — one-way doors; AFFIRMATIVE owner signature only, never silence:** (1) nonzero or raised spend envelopes; (2) bytes leaving the repo boundary — publishing, PRs to any other constellation repo, network writes outside captured oracles; (3) first contact with Renavon inputs (the M5 gate); (4) constitution amendments (BRIEF principles §3 / non-goals §10); (5) trust-root changes (custodian, allowed_signers, poison corpus, their manifest rows). Former Tier-C items that are enforceable mechanically (cross-repo imports, store deletion) cease to be approvals: they are **guard-enforced impossibilities**; only changing those RULES is Tier C.

**Policy as data.** `governance/policy.yaml` (owner-signed at the opening sitting) holds: budget envelopes per milestone; licence defaults (MIT code / CC BY-SA docs, per proplang); external-surface rules; the spot-check sample rate K. Guards consume it; being asked something answerable from policy.yaml is a bug — file it as one.

**Non-blocking rule.** No Tier-C request may halt the project: queue the blocked branch, continue elsewhere, batch requests to the next boundary sitting.

**Graduated autonomy.** Defaults widen by ratchet as law evidence accumulates; any tripped guard or failed law auto-narrows the affected class until re-earned — no owner action required in either direction.

---

## 10. Non-goals (enforced by Tier C)

No orchestrator, scheduler, retries, cron. No distributed execution. No SQL parsing. No schema evolution beyond descriptor bump + re-derive. No UI. No performance work before M5. No NULLs. No store mutation, ever. No decision layer, utility model, or governor *implementation*. No repo unification, in either direction. No extending proplang. No dependency on the Renavon monorepo, pkm, credence, or life-agent code.

---

## 11. Prior art (crib, don't reinvent)

DBSP (VLDB 2023) + Chajed's Lean formalisation — operator delta semantics and the differential-testing method (via Feldera). Green–Karvounarakis–Tannen (PODS 2007) — the semiring algebra; ProvSQL's tests as a correctness quarry for L5. *Build Systems à la Carte* — scheduler/rebuilder vocabulary; verifying traces. Nix derivations; Salsa. WARC/WACZ for the fetch envelope. Unison — the existence proof for content-addressed code; study before building, steal freely.
