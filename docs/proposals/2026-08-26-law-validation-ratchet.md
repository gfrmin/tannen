# The freeze gate proves the laws do not run, not that they could ever pass

**Status: proposed, scheduled for M2 (decision D0094). Not binding.** Written at the M1
laws freeze, immediately after D0093 found an unsatisfiable axiom in an already-frozen law
file. It generalises that defect rather than restating it.

## The hole

BRIEF §8's frozen-oracle protocol freezes a milestone's laws before its implementation
exists, so the implementation cannot be written to fit weakened laws. The price is that
**every law is a skip at the moment it becomes unrewritable**:

```
$ uv run pytest tests/laws/m1 -q
12 skipped in 0.10s
```

That output is byte-identical whether the laws are correct, mutually contradictory, or
nonsense. Session A's completion check — "every law a SKIP, zero passes, zero errors"
(`docs/specs/m1.md`, the Session A plan) — is a check that the laws **do not run**. Nothing
anywhere checks that they **could ever pass**.

D0093 is what that hole produces: `test_l1_2_multiplicity_axioms` asserted
`(multiplicity(a) > 0) == (a != zero)`, which is unsatisfiable for any product semiring and
directly contradicted another test twelve lines below it in the same file. Both were frozen
into `MANIFEST.sha256` in the same commit. The gate was green throughout.

## The hole has a second side, found later: a law that cannot fail

**Added 2026-08-29 (D0114).** D0093 is a law that could never *pass*. Working on
`anti_join` at the M1 close turned up its mirror image, and the pair is what makes the
proposal below need both of its halves.

`tests/laws/m1/test_l1_ops.py::test_l1_9_the_fragment_preserves_the_non_negative_cone`
asserts that no operator in M1's surface can manufacture a negative annotation:

```python
for _, annotation in result:
    assert Z.multiplicity(annotation) >= 0
result.to_bag()  # raises SemiringError on a negative; reaching here is the assertion
```

That is a true and load-bearing claim — D0107's narrowing of `anti_join`'s presence test
rests on it, and D0109 dates that reliance to M3. But it is not a claim this law
*tests*. Its inputs come from `tests/laws/m1/_fragment.py`:

```python
st.tuples(row, st.integers(min_value=1, max_value=MAX_MULTIPLICITY))
```

Every drawn multiplicity is at least 1, and no operator in the fragment subtracts. There is
no input, reachable by any draw Hypothesis can make, under which this assertion can be
false. It is green for the same reason `assert True` is green.

**Why it matters that this is the opposite failure.** A frozen model (§1 below) catches
D0093 on its own: transcribe §2.1's axioms, run the frozen law against them, watch it fail.
A model catches *nothing* here — a naive transcription of the operators is just as unable to
produce a negative as the implementation is, so the law passes against the model, exactly as
it passes against the package, and the gate stays green through both. **Only the mutant half
of §2 discriminates**: a law that passes against a deliberately broken model is not testing
what it claims, and a model whose `Z` is mutated to subtract on `anti_join` makes L1.9 fail
the way a real cone violation would.

So the two halves of §2 are not belt-and-braces. They catch disjoint defects, and the mutant
half — the one most likely to be dropped as gold-plating when this is implemented — is the
half with the only known instance in this repository that the model half cannot reach.

**One consequence, recorded so it is not rediscovered.** D0107 narrowed `anti_join`'s
presence test from `annotation != zero` to the bag image, which under `Z` refuses a negative
by the cone law instead of counting it as present. D0107 justified the narrowing by L1.9 —
nothing reachable can produce a negative — and D0109 dated that justification to M3, when
the delta executor starts producing retractions. If L1.9 cannot fail, then the justification
never rested on a *proved* property of the operator set; it rested on the fragment's
generator never drawing one. That does not weaken D0107's fix, which stands on L1.2 as
amended by D0093. It strengthens D0109's expiry: the thing M3 has to supply is an answer,
not a re-reading of a law that was never asked the question.

## A third side, measured: the generator decides how much a law tests, and nothing records it

**Added 2026-08-30 (D0118).** D0093 is a law that could never pass; L1.9 is one that could
never fail. Both are absolutes. Measuring L1.16 — the one law family that already has an
independent oracle, and therefore the one that should look best — turned up the graded
version of the same thing, and it is worse than an absolute because there is no line to
cross.

`tests/laws/m1/_fragment.py:83` draws each table's contents with
`st.lists(..., max_size=MAX_ROWS)` and **no `min_size`**. An empty relation is a legitimate
and interesting input, so that is not a defect on its face. What it produces is:

**Under the gate's own settings — `conftest.py` registers `derandomize=True`, so `make
verify` draws the same examples on every run and every machine — L1.16 evaluates 2200
example-draws across its 22 shapes, and 865 of them compare an empty result to an empty
result.** These are exact integers, not estimates, and they reproduce:

| shape | effective examples (of 100) | | shape | effective examples (of 100) |
|---|---|---|---|---|
| `select-text` | **29** | | `anti-join`, `anti-join-then-project` | 63 |
| `join`, `join-then-project`, `join-then-distinct`, `aggregate-of-join` | **34** | | `select-or-not` | 68 |
| `join-text` | 42 | | `project-two`, `aggregate-two-keys` | 73 |
| `select-and` | 45 | | `project-one`, `distinct`, `project-then-distinct`, `aggregate-sum`, `aggregate-count`, `aggregate-of-distinct` | 74 |
| `select-gt` | 49 | | `union-of-selects` | 74 |
| | | | `union`, `union-then-distinct` | **88** |

On an empty draw, `test_l1_16_the_fragment_agrees_with_duckdb` compares `[] == []` — true
for any implementation of anything — and `test_l1_16_no_null_ever_appears_on_either_side`
executes zero assertions. So `select-text` and `union-then-distinct` differ threefold in
what they actually examine, both report `pass`, and **the number above appears in no
artifact this repository produces**. This is also where §2's mutant half is weakest: a
mutant that misbehaves only on non-empty input has 29 draws in which to be caught on
`select-text`, not 100.

`tests/test_provenance_homomorphism.py:66` has the same shape —
`pairs = st.lists(..., max_size=4)`, no `min_size` — and it matters more than its line
count suggests, because `test_the_operators_never_manufacture_an_empty_why` is the closure
proof D0107 cites for witnessed-in-witnessed-out and D0110 cites as half the reason the
`(n, 0_Why)` door is safe today. On an empty draw it asserts nothing.

### Where the empty draws come from — three causes, measured separately

Attributed under a randomised sweep (400 draws per shape, counting only the tables a
shape's own plan reads), the empty draws divide into three independent causes, and the
division is what rules out every single-knob fix:

| cause | evidence | reaches |
|---|---|---|
| **the row-list length** — `st.lists(max_size=6)` puts real mass on `[]`, four tables are drawn independently, and empty is absorbing | every single-source shape attributes **100%** of its empty draws to an empty source; setting `min_size=1` alone takes the mean empty rate from 35.2% to **17.3%**, with nine of 22 shapes reaching exactly **0.0%** | all shapes |
| **key overlap** — random keys on both sides of a join often miss | joins attribute 50–77% of empties to an empty source and the rest to misses; drawing `b`/`c`/`d`'s keys from `a`'s own takes every join-shaped plan to **0.0%** | joins, anti-joins |
| **predicate selectivity** — `t = 'a'` over a six-letter alphabet and ≤6 rows misses with probability `(5/6)^n` | `select-text` stays at ~65% under *every* variant of the other two | filters |

### Three cures, measured. Two do not work, and the third only works per shape.

**Narrowing the key domain does essentially nothing here.** It is the good idea on its face
— `tests/test_provenance_homomorphism.py` already draws `key_range=(-2, 2)` for exactly
this reason, so the repo knows the trick — and applied to the fragment it moves the mean
from **35.2% to 34.7%**. It moves individual shapes in both directions: `join` 61.5% →
54.0%, but `anti-join-then-project` 26.0% → **38.0%**, because more matching keys means an
anti-join drops more rows. It does not bite because the fragment's keys are *already*
narrow — `_value("k")` is `st.one_of(st.integers(-4, 4), st.sampled_from([0, INT_MIN,
INT_MAX]))`, so about half of key draws already come from a nine-value domain. Key width
was never the cause.

**`min_size=1` is the largest single move and still the wrong fix.** It deletes the empty
relation, which is a real case and one of the few that separates a correct implementation
from a lazy one.

**Coupling the keys is right for joins and actively wrong for anti-joins.** On top of
`min_size=1` it takes the mean to **11.0%** and every join-shaped plan to **0.0%** — while
taking `anti-join` from 13.8% to **41.0%** and `anti-join-then-project` from 26.2% to
**53.8%**, for the obvious reason: if every right-hand key is present on the left, an
anti-join deletes everything. **There is no key policy that is simultaneously right for a
join and an anti-join**, which is the finding that generalises past this fragment.

### Why a floor assertion on the non-degenerate rate is still refused

It was the first proposal here, and the first argument against it was wrong and is
withdrawn: "a floor on a random process fails intermittently" does **not** apply to the
default gate, because `derandomize=True` makes 865/2200 an exact and reproducible integer.
A floor would be perfectly stable under `make verify`. Three objections survive, and they
are better ones.

1. **It is a threshold on a quantity that is already exact and simply unrecorded.** The
   number exists, is deterministic, and can be computed today. Asserting a bound on a
   number nobody writes down is a worse instrument than writing it down — which is D0117,
   and is why this section is downstream of that record.
2. **It is intermittent on the one run that matters most.** `make laws-sweep`
   (`pytest --hypothesis-seed=N`) exists precisely to explore beyond the fixed corpus, and
   there the rate is a genuine random variable: seven runs of 400 draws put the per-shape
   spread between best and worst at

| | spread between best and worst of 7 runs |
   |---|---|
   | `join-then-project` | **20.2pp** (50.0% → 70.2%) |
   | `aggregate-of-join` | 19.2pp |
   | `select-and`, `distinct` | 16.5pp |
   | `project-one` | 14.5pp |
   | `select-or-not` | 14.0pp |
   | … 15 further shapes … | 2.5–13.5pp |
   | **mean over all 22** | **11.6pp** |

   A floor tuned on the derandomized corpus is red on some sweeps and green on others with
   nothing about the code having changed, and the observed institutional response to an
   intermittently red gate is that it gets relaxed rather than investigated.
3. **It treats the symptom.** It detects a badly shaped distribution instead of producing a
   well-shaped one, and the three-cause table above says a single bound cannot even tell
   you which of the three moved.

### The rule worth taking to M2

Three causes, no single knob, and the two most attractive knobs each make one shape worse
while making another better:

> **Draw the degenerate case as a named case, not as a side effect of the size
> distribution — and let each shape state what its own interesting case is.**

```python
st.one_of(
    st.just([]),                                              # the empty relation, named
    st.lists(row_and_multiplicity, min_size=1, max_size=MAX_ROWS),
)
```

The empty relation keeps its place in the corpus; what it loses is its status as the default
outcome of several independent draws. Beside it, each shape declares the case it exists to
exercise — a join wants overlapping keys, an anti-join wants *partial* overlap, a filter
wants a literal drawn from the column it filters — so "nothing matched" becomes a case that
was chosen rather than one that happened.

Then **each generator reports its own shape through hypothesis's `event()`**, and the run
reports a distribution somebody deliberately shaped rather than one somebody is policing.
The difference between those two is the whole of this section, and it is why no part of it
proposes a threshold.

### What this cannot reach from here, and what it depends on

`tests/laws/m1/_fragment.py` is frozen, sealed and inside `tests/laws` — the fix cannot be
applied to M1 in place. That is D0103's supersession question for the third time (D0110 was
the second), and the honest statement is that L1.16's 1335 effective examples stand as
measured for M1 and the rule applies from M2 forward.

And a shaped distribution is worth only as much as the record that carries it. An evidence
record's required fields are `format_version, law_id, milestone, verdict, run_at, seed,
descriptors, environment`, with `additionalProperties: false` — there is no field in which
an `event()` distribution, an example count, or a non-degenerate count could be written, and
`tannen laws report` prints `ok  pass` identically for all 22 rows above. Shaping the
generators without that field means the next skew is found the way this one was: because
somebody decided to measure. That is **D0117**, and it is why this section is a consequence
of that record rather than a substitute for it.

## Why the existing guards could not catch it

- `check_manifest.py` verifies frozen bytes are unchanged. Bytes, not meaning.
- `tannen laws report` reports evidence freshness for descriptors. A pending milestone
  (D0090) has no evidence by definition, so there is nothing to be fresh or stale.
- `check_decisions.py` resolves bindings. A `manifest:` binding resolves iff the row
  exists — again, bytes.
- pytest collects the module and skips it at `importorskip`, before any assertion runs.

Each guard is doing its job. None of them is a satisfiability check, because none was ever
meant to be.

## What the repo already does right, twice, without generalising it

1. **`tests/laws/m1/_fragment.py`** is a reference oracle frozen beside the laws that
   imports nothing from tannen. L1.16 is differentially checked against DuckDB through it —
   so exactly one M1 law family has an independent model, and it is not the family that
   broke. The pattern exists; it was not applied to the algebra.
2. **`unenforced_reason`** makes a decision record's missing binding *visible and counted*,
   and D0044's ratchet forces the count down. Laws have no equivalent field, so "nobody
   validated this law family" is not merely unenforced — it is unrepresentable, and
   therefore silent.

The proposal below is those two mechanisms, applied to laws.

## The proposal

### 1. Freeze a model beside the laws

Each algebraic law family gets `tests/laws/<milestone>/_model.py`: a naive, self-contained
transcription of the spec's definitions, frozen inside the seal. D0089 already settles both
the location and the precedent — shared law helpers are frozen inside the seal, not parked
outside it — so this needs no new mechanism.

The model is **not** the implementation and must not become it:

- it imports nothing from `tannen`, exactly as `_fragment.py` does not;
- it may be naive, quadratic, and partial, because nothing ships it;
- Session B may not import it, and the seal already prevents adding anything beside it.

The one written ad hoc for D0093 was ninety lines and found the defect on its first run.

### 2. The freeze gate gains a second assertion

Today Session A's gate is *every law SKIPs against the package*. It becomes:

| | against the package | against the model | against a stated mutant |
|---|---|---|---|
| model-checked law | SKIP | **PASS** | **FAIL** |
| machinery law | SKIP | — | — |

The mutant half is D0092's discipline generalised: a law that passes against a deliberately
broken model is not testing what it claims. **It is also the only half that catches L1.9**
(see "a law that cannot fail", above): a model of an operator set with no subtraction cannot
produce the negative L1.9 forbids, so the model half passes L1.9 as vacuously as the package
does, and only a mutant that CAN subtract makes the law say anything. It is the same argument that made the
receipt-clock regression test worth rewriting — pass-before/fail-after is the only evidence
that an assertion discriminates. Both halves would have caught D0093 immediately: the
corrected axiom passes against the model exhaustively over a 45-element product domain, and
the frozen one fails on twelve of those elements.

### 3. Make the gap countable

Every frozen law file declares one of:

```yaml
validated_by: tests/laws/m1/_model.py      # and a recorded pass/mutant-fail transcript
validation_reason: >-                       # why this family cannot be model-checked
  L1.11 is about the quarantine machinery; a model of it would BE the implementation,
  which is what the A/B separation exists to prevent.
```

`scripts/check_laws.py` fails any law file under a sealed milestone directory carrying
neither. **`unvalidated` then joins `unenforced` and `residue` as a ratchet metric** in the
digest, and must trend down like the others.

This is the load-bearing part, and it is the part that would have caught D0093 with no
cleverness at all. The Session A plan listed three executed pre-freeze validations —
antichain-`Why` as a commutative semiring (L1.1), 22 shapes against DuckDB (L1.16), and the
sibling-import probe. `BagSemiring` was introduced in the same plan's Call 2 and no
validation covered it. Under rule 3, `test_l1_semiring.py` would have been forced to declare
a `validation_reason` for L1.2, and **there is no honest one to write** — the family is pure
algebra over finite domains, the single easiest thing in the milestone to model-check.

### Scope, stated honestly

Not every law is model-checkable. L1.11 (quarantine), L1.12 (the registry), L1.13–L1.14
(derivation identity and the rebuilders), L1.15 (replay) and L1.17 (the harness subject) are
about machinery; a model of them is the implementation, and writing it in Session A destroys
the adversarial separation the protocol exists for. Those declare a reason. The rule does
not make them safe — it makes their unsafety **counted** instead of invisible, which is the
same bargain `unenforced_reason` strikes and the reason that field works.

Candidates for M2, on this reading: L2's semiring/provenance laws are model-checkable; the
executor and store laws are not.

## What this does not fix

A model that is wrong in the same way the law is wrong catches nothing. Two mitigations,
neither complete: the model is transcribed from the **spec** rather than from the law, so it
takes a second independent error to line up; and the mutant requirement means a law that
asserts nothing at all still fails, because it passes against the mutant too. D0093 itself
is evidence the first mitigation bites — the spec's §2.1 axiom list was correct, and it was
the law that had drifted from it.
