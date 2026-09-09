<!-- FROZEN CORRECTIONS to docs/specs/m3.md. This file supersedes prose FORWARD; the frozen
     bytes of m3.md are not edited and cannot be. Recorded by D0204. See MANIFEST.sha256's
     supersession notes. -->

# m3 spec — corrections

`docs/specs/m3.md` is frozen at `m3-laws-freeze` and its bytes are correct as a record of what
was believed at the freeze. Four of its sentences are now false. They are **superseded forward**
here: the frozen file is retained and unedited, this file carries the claims at their true
strength, and `MANIFEST.sha256`'s supersession notes point from the old locations to this one.

**What this file does NOT use, and why.** D0161 holds that the `governance/laws.yaml` retirement
machinery — a node, plus `conftest.py` marking it `xfail(strict=True)` — "retires law nodes, and
running it against prose would be a category error". That is right and this file does not use it:
no node is retired, `laws.yaml` is untouched, and no law changes status. What is used is the
other half of D0106 ruling 2's mechanism, the half that applies to any frozen artifact — a new
file, the old one retained and annotated in the manifest notes, and a record binding the two.
D0171 ruling (1) directed the correction "under the D0128 mechanism"; this is that mechanism
minus the part D0161 showed cannot apply to prose.

Each correction below states what the frozen sentence claimed, what falsified it, and the text
that replaces it. Where a defect is still open, it is stated as an open defect rather than
promised away — a corrected sentence that overclaims is the failure this supersession exists to
end.

---

## 1. §7, lines 335-341 — "Every step is its own derivation"

**Superseded because** three claims in this bullet are false as frozen. (a) The input triple
`(state_ref, ledger_ref, sorted delta refs)` names three inputs where a node's first tick has
two, and `derivation_id` normalises the order of the *whole* input list rather than the child
refs inside a fixed tuple (`src/tannen/kernel/derivation.py:32`;
`src/tannen/incremental.py:523-524`). The word `sorted` also conceals a live collision: a binary
node's two operand orders share one `step_id` (RT-M3-03, D0174). (b) "a pure function of those
inputs" was false when frozen — a step was also a function of the module-level registry, named in
none of the inputs (RT-M3-01, D0174) — and is true today only because of D0197, which the frozen
sentence cannot name. (c) "Replaying a stream hits traces" was ruled false by the owner at D0171
ruling (1): `advance` consults the trace and by default writes none, so there is no trace row to
hit.

**Replacement text:**

- **Every step is its own derivation**: the existing `derivation_id` over the step's
  descriptor and the step's *content-addressed inputs* — the child refs the tick passes,
  the ledger's content address, and the state ref **when there is one** (a node's first
  tick has no state, so the list is one shorter rather than carrying a hole).
  `derivation_id` normalises the order of that **whole list**, not of the child refs
  inside a fixed tuple. That is frozen M1 (m1 §8, L1.13) and `advance` inherits it rather
  than restating it (D0167).

  So order-insensitivity is a property of the step id itself, and for a binary node the
  two operand orders are **one step id**. Whether that is sound is a property of the
  **node**, not of the operator's algebra. `union` is sound: it is linear, so it holds no
  per-input state and both orders compute one answer. `join` is **not** sound, though `⋈`
  commutes: its state keeps the two children's integrals **by position**, and its delta
  rule pairs each child's delta with the other child's integral, so the two orders are two
  different computations under one identity. `anti_join` is not sound, because it does not
  commute. Where both sides carry the same schema — the only shape in which a swap does
  not raise — the divergence is real and unannounced: measured, one `step_id` and two
  different Δout, and with the step recorded the second order is served the first order's
  answer with `rebuilt=False` and no exception. Nothing in a type system can see it
  (RT-M3-03, D0174 — which corrects the stated premise of D0171 ruling (2), "a caller
  error the type system should catch", while leaving its conclusion standing).

  D0171 ruling (2) keeps `derivation_id` order-insensitive. The asymmetry therefore
  belongs to the node: **a node whose operand roles are not interchangeable must carry
  those roles in its own declared form**, so that the descriptor — and with it the step
  id — distinguishes them. That requirement is stated here and is not yet met by this
  executor; the defect is recorded rather than promised away.

  One derivation, one output, holds because a step is a pure function of the descriptor
  and those inputs — and it holds **only while the descriptor names the code the node
  runs**, not a key some registry may resolve to anything. Hence the discipline: the
  declared form of a node **must** carry the content address of any code a parameter names
  — a predicate, a map, a monoid or group together with its identity and witnesses — and
  that address is over the code's **source text**, the same bytes M1 has hashed since
  D0084, one implementation rather than two (BRIEF §2). A callable with no addressable
  source is refused, and a registered name whose code cannot be addressed is refused **at
  declaration**: a descriptor that cannot say which code it means is not minted at all
  (D0197). Before that, a step was also a function of the registry, which is named in none
  of the inputs above — two processes registering different predicates under one name
  minted one `step_id`, the trace served the first's output to the second with
  `rebuilt=False`, and `TraceIntegrityError` could not fire because nothing had been
  tampered with (RT-M3-01, D0174). The rule is not yet complete: a `map_rows` node's
  registered **out-schema** is still resolved from the registry at tick time and is in no
  descriptor, so the class RT-M3-01 names is narrowed, not closed. Measured, and recorded
  here for the same reason.

  `TraceStore`, `AlwaysRebuild` and `VerifyingTrace` are reused **as is**. A replayed
  stream is served without recomputing **only where the caller recorded**: `advance`
  consults the trace on every step and writes one on none by default. `record` is
  keyword-only, defaults off, and recording is the caller's act. This is *not* M1's split:
  `AlwaysRebuild` and `VerifyingTrace` both record unconditionally, and the policy choice
  there is whether a recorded output is *served*; `advance` inverts it — always consult,
  by default never write. The default is forced rather than chosen: frozen L3.15
  re-records under a completed step's `step_id` outside its `pytest.raises` block, and
  `TraceStore.record` refuses a conflicting re-record, so an `advance` that recorded by
  default would turn that law into an error rather than a pass (D0171 ruling (1)). Under
  the default a replay **recomputes the step body and writes nothing new**, because
  everything a step produces is content-addressed; `rebuilt` reports whether this step's
  output was new to the **store**, which is the honest measurement of "did anything get
  built" and is not a trace hit. A recorded output that no longer resolves is not a cache
  miss: it raises `TraceIntegrityError`, M1's L1.14 one step on. A reordered stream is a
  different sequence of derivations — correctly, they are different events
  [cites: pkm-event-identity] — and L3.9/L3.12 assert the *final integrals* converge
  byte-identically all the same.

---

## 2. §10, line 444 — the L3.15 law-table row

**Superseded because** the row repeats "a replayed stream hits traces" verbatim — the same claim
corrected at §7 above, restated in the summary table a reader reaches for first. Correcting the
body and leaving the row is the D0049 shape: a corrected artifact with a stale index. This
falsification was found only because the first draft of this correction was attacked rather than
read (D0203).

**Replacement row:**

`| L3.15 | The executor: `DeltaNode` descriptors are content-addressed data; one derivation, one output; a replay recomputes nothing into the store, and is served from the trace where the caller recorded; a tampered trace raises; a quarantining step moves nothing; replay is byte-deterministic | `test_l3_executor.py` | **L1**, §7 |`

Verified safe to restate here: `tests/test_laws_runner.py:50` reads the law table only from
`docs/specs/<milestone>.md`, so a corrected row in this differently-named file cannot desync
`test_discovery_matches_the_frozen_spec_table`.

---

## What is NOT corrected here

Three further passages were proposed as falsified and are **not** carried, because adversarial
review showed them sound (D0203). `docs/specs/m3.md:202` ("an empty tick moves nothing, trace
hits included") is correctly scoped to L3.15's empty-tick claim, and its proposed replacement
contradicted the corrected §7 text. `:324` (the six-argument `advance` signature) and `:318` (the
`deltaop/1` params) are **incomplete, not false** — neither claims exhaustiveness, and no record
establishes either as wrong. A correction to something that was never wrong is worse than no
correction, and freezing new prose that asserts a falsity which does not exist would manufacture
exactly the frozen-versus-true gap this file closes.
