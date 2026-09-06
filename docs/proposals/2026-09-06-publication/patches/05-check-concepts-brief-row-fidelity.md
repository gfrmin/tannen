# Patch 05 — `brief_row` is unchecked, so a concept record can misreport BRIEF §2's owners

**Status: drafted, not applied.** `scripts/check_concepts.py` is custody-set
(`governance/tier-c.yaml#custody.set`), so the owner applies this. Filed by D0180.

## The finding

`brief_row` is a required field whose stated job is to carry the BRIEF §2 row a concept
record answers to. **No guard reads it.** `check_concepts.py` validates the schema (a
non-empty string), and stops. So a record may say anything at all about what the frozen
constitution says, and the whole gate stays green.

That is not hypothetical. D0180 rules that the fourth sibling's `source` entry comes out of
`concepts/provenance-ref-grammar.yaml`, while BRIEF §2 — frozen at `brief-freeze` — will
still name two owners for that row. The record becomes deliberately narrower than the row
it quotes. **The divergence is intended, and it is invisible to every check in the
repository**; it would survive only as prose in the record's own `notes`, which is exactly
the kind of guarantee this repo does not accept anywhere else.

The withdrawal is **ruled but not yet executed in the tracked tree** — D0181 explains why it
cannot be until patch 06 lands. It *was* executed and measured before being reverted, so the
numbers below are real rather than predicted.

Note the shape, because it is the reason the first spelling of this patch was thrown away:
`brief_row`'s quoted span is only BRIEF §2's **Concept** column. The **Owner** column —
the half that says who owns the concept, and the half D0180 changed — is free prose after
the closing quote. A check on the quoted span alone is green on the very case it exists for.
Measured, not reasoned: the first draft returned `GREEN` against a record with its owner
list redacted.

## The check, in two teeth

**Tooth 1 — the quoted span is verbatim in `BRIEF.md`** (markup-normalised: strip `` ` ``
and `*`, collapse whitespace). Catches a record that rewrites the concept title.

**Tooth 2 — the owner tokens BRIEF §2 names for that row equal the record's
`sources[].repo` set**, over the constellation vocabulary
(`pkm`, `life-agent`, `proplang`, `renavon`, `tannen`) — unless the record carries an
explicit declaration:

```yaml
brief_row_divergence:
  omits: [renavon]          # owner named by BRIEF §2 but deliberately not cited here
  reason: >-
    Withdrawn ahead of publication so the public registry carries no internal document
    path, ADR heading or private commit SHA of that repository.
  decision: D0180
```

The declaration is the point. It converts "a human wrote a paragraph explaining this" into
data the guard reads, so the *next* divergence — the undeclared one — is the one that fails.
Add `brief_row_divergence` to `governance/schemas/concept-record.schema.json` with
`additionalProperties: false` on its sub-object, and require `reason` and `decision`.

## Measured, both directions

Probe: `probes/brief_row_fidelity.py` in this package, run against the tree at the time of
writing.

**Tooth 1, direction green** — all 8 records:

```
OK — 8 brief_row quotes verbatim in BRIEF.md
```

Two of the eight only pass because of the markup normalisation, and that was found by
running it rather than by reading: `credence-functor-seam` and `pkm-determinism` differ
from BRIEF.md solely in `` `backticks` `` and `**bold**` (similarity 0.990 and 0.991, prose
identical). Without the normalisation this patch would redden a faithful tree — a false
positive on 2 of 8, which is how the first spelling died.

**Tooth 2, both directions.** On the tree as it stands today — withdrawal ruled but not
executed — both teeth are clean, which is the correct answer and not a vacuous one:

```
tooth 1 (quoted span verbatim in BRIEF.md): 8/8 ok
tooth 2 (owner set matches sources[].repo): 8/8 ok
```

With D0180's withdrawal applied (measured, then reverted per D0181) it goes red on exactly
the one record that changed, and on nothing else:

```
record                     BRIEF §2 owners    sources[].repo   match
credence-functor-seam      life-agent         life-agent       ok
derive-decide-split        life-agent         life-agent       ok
exactness-and-the-door     proplang           proplang         ok
frozen-oracle-protocol     proplang           proplang         ok
pkm-determinism            pkm                pkm              ok
pkm-event-identity         pkm                pkm              ok
provenance-ref-grammar     pkm,renavon        pkm              *** MISMATCH: brief has ['renavon'] extra ***
semiring-relations         tannen             tannen           ok
```

The single red is a **true positive**: the check goes red exactly when the divergence is
introduced and at no other time — which is the property a fidelity check has to have, and
the one a green-on-everything check cannot demonstrate. At the sitting, apply this patch,
execute D0180's withdrawal, and add the declaration above to
`concepts/provenance-ref-grammar.yaml`; the tree returns to green with the divergence
enforced rather than narrated.

## Poison fixture

Warranted, and specified as **fixture candidate 2** in `../fixture-candidates/README.md`:
`tests/poison/check-concepts-brief-row/` — a one-record tree whose owner list drops a repo
BRIEF §2 names, with no `brief_row_divergence`. Marker `brief_row`. Author-key territory;
installs at the sitting, and **only after this patch** — the tooth it poisons does not exist
until then.

## What this does not close

The vocabulary is a hand-written five-token list, and CLAUDE.md's standing rule is that no
guard may depend on a hand-maintained enumeration. Deriving it is possible — the
constellation table is BRIEF §1 and could be parsed for the repo names — and that is the
better spelling if the owner wants it before installing. It is not done here because BRIEF
§1's first column is prose (`Renavon monorepo`, not a slug), so the derivation needs a
normalisation step that is itself a judgement. Named as a known weakness rather than left
for the next red team to find.
