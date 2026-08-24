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

