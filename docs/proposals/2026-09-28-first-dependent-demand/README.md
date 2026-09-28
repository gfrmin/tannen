# The first dependent's demand, read from its own plan

D0273 ruling 5 made the first real use the demand signal for everything after M5: a private
sibling repository pins `m5-close`, and M5b, a persisted-output vertical and the pre-budget
sitting wait until use asks for them. This page records what that sibling's own plan says it
would ask of tannen. It is a reading, not a request. On 2026-09-28 the sibling carries no
dependency on tannen and its plan schedules none. Following D0268 ask 4, the sibling is not
named, and only its demands on tannen are recorded here.

## What its plan asks for, and what tannen has at m5-close

| Stated use | Tannen at m5-close | Gap |
|---|---|---|
| Its model as a content-addressed operator: a pure function of (row, world version, model version) | `@transform` addresses a function by its own source text and `params` (`src/tannen/transform.py`) | The model's function closes over a large derived index and its weights, and the code address sees neither. This is RT-M4-04, deferred to `m6-boundary`, in the exact shape the first dependent has. Until it closes, the dependent must pass the world in as an input ref. |
| Incremental re-runs: a world update is a Z-set delta, and only rows whose result depended on a changed world value re-run | Delta rules for the eight operators (`src/tannen/kernel/delta.py`); `map_rows` over an opaque function is linear in its input rows only | A change to the world is not a change to the input rows, so no operator's delta rule reaches the model's function. The index it would need, from world value to the rows citing it, is the row's `Why` support. |
| Why-provenance carried downstream as columns | `Why` atoms must be refs in the pinned grammar (`src/tannen/kernel/semiring.py` refuses anything else) | The sibling's provenance atoms are names, not refs. Each named entry would have to be content-addressed and cited by its ref. |
| A stable boundary to consume | `src/tannen/__init__.py` exported nothing and described a pre-M0 package | Closed by D0275: `tannen.SURFACE`, `tannen.NOT_SURFACE`, `tests/test_surface.py` and a CONTRIBUTING.md section. |

## Candidates for the next Session A (none is chartered here)

1. **Closure-aware code addresses (RT-M4-04).** Hash a transform's source together with what it
   captures, walking free variables and module globals, and refuse a captured value that is not
   a content-addressed input.
2. **A delta rule for an opaque row transform, keyed on its `Why` support.** When a world value
   changes by a delta over its atoms, re-run exactly the rows whose support cites a changed
   atom. Provenance becomes the dependency index for a transform the algebra cannot see into.
   That carries BRIEF §1's one mechanism, incrementality and provenance, one step past the
   operators. It needs a superseding L4 law, incremental equal to reference, over a
   world-delta generator.
3. **Foreign provenance atoms.** No kernel change; the sentence a dependent needs is now in
   CONTRIBUTING.md (D0275). Listed so a Session A can decide whether it wants more than that.
4. **A frozen provenance-homomorphism law.** `tests/test_provenance_homomorphism.py` is unfrozen
   by design (`docs/specs/m2.md` §3). A dependent that adopts `semiring-relations` at Grade L
   needs a frozen law to cite.
5. **Every future law names the failure it catches** in its docstring. This is a convention for
   the next law set, and it costs nothing.

## What stays out

- Any import, vendoring, path or copy in either direction (BRIEF §1, guard-enforced). Any PR to
  the sibling is door `external-bytes`.
- Designing candidate 1 or 2 outside a Session A: 1 touches M1's frozen transform laws, and 2
  needs a law.
- Building a vertical for the sibling now. Per D0273 (5), that waits until the sibling asks.
