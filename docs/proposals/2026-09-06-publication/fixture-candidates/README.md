# Fixture candidate — `tests/poison/check-concepts/governance/policy.yaml`

`tests/poison/` is author-key territory (BRIEF §9.1), so this is staged, not installed.
One file, three lines of content.

## Why

Patch `01` makes `check_concepts.py` read `concept_registry.expected_citation_pins` from
`governance/policy.yaml` and fail when it is missing — deliberately, because a degraded
citation check with no expectation to meet is the vacuous pass the whole condition exists
to prevent (D0115, D0116 species I).

The poison fixture at `tests/poison/check-concepts/` has no `governance/policy.yaml` of its
own, so after patch `01` it fails for **two** reasons instead of one. Measured against the
patched guard:

```
check_concepts: FAIL (3 violation(s))
  - concepts/poison-snapshot-drift.yaml: vendored snapshot content drifted: ...
  - governance/policy.yaml is missing, so the citation-pin expectation cannot be read ...
  - CONCEPTS.md missing or lacks the generated input-hash header — run make projections
```

The custodian still passes: `poison()` requires the guard to fail **and** the marker
`snapshot content drifted` to appear, and both hold. (The third line shows the fixture
already failed for more than one reason before this change, so multi-reason failure is
pre-existing here, not introduced.) Installing this file narrows it back so the fixture
tests the tooth it names.

## The file

`tests/poison/check-concepts/governance/policy.yaml`:

```yaml
# Minimal policy for the check-concepts poison tree. The fixture must violate ONE guard —
# snapshot content drift — so it carries the citation-pin expectation its single record
# needs, and nothing else. `_gov.load_schema` already falls back to the real repo's frozen
# schemas for exactly this reason: a poison tree violates a guard, it does not duplicate
# the governance corpus.
concept_registry:
  expected_citation_pins: 1
```

One record, one `snapshot.path`, so the expectation is 1.

## Watched failing, both directions

Before installing, confirm in a scratch copy that the fixture still bites and still bites
for the right reason:

```
python scripts/check_concepts.py --root tests/poison/check-concepts   # FAIL, marker present
sed -i 's/expected_citation_pins: 1/expected_citation_pins: 9/' \
  tests/poison/check-concepts/governance/policy.yaml
python scripts/check_concepts.py --root tests/poison/check-concepts   # FAIL, now also on the count
```

And that the count guard is not merely decorative in the real tree — the four probes run
for patch `01` are recorded in the package README.

---

# Fixture candidate 2 — `tests/poison/check-concepts-brief-row/` — **needs patch 05**

Staged, not installed, and **it must not be installed before patch `05`**: the guard tooth
it poisons does not exist yet, so installing it now would leave the custodian permanently
red, which is the opposite of what a poison fixture is for. Same rule the M3 red team's
`oracle-shadow-spoofed/` follows.

## Why

Patch `05` adds the check that a concept record's `sources[].repo` set matches the owners
BRIEF §2 names for that row. Its whole point is that **`brief_row` is currently read by
nothing**, so a record can disagree with the frozen constitution about who owns a concept
and every guard stays green. A tooth with no fixture is a tooth nobody watches fail.

## The tree

A one-record poison tree, mirroring `tests/poison/check-concepts/`'s shape:

`tests/poison/check-concepts-brief-row/concepts/poison-brief-row-drift.yaml` — a record
whose `brief_row` quotes a real BRIEF §2 row naming **two** owners, whose `sources` lists
**one**, and which carries **no** `brief_row_divergence` declaration. Plus the minimal
`governance/policy.yaml` (`expected_citation_pins: 1`) that fixture candidate 1 explains.

**Marker:** `brief_row` (the substring patch 05's message is required to contain, the way
`check-concepts/` keys on `snapshot content drifted`).

## Watched failing — against the probe, since the guard is not applied yet

`probes/brief_row_fidelity.py` is patch 05's logic. Run today against the real tree it
reports `tooth 2: 7/8 ok`, the single RED being `provenance-ref-grammar` — the true
positive D0180 created and declared. That is the *undeclared* form of the same shape this
fixture pins:

```
provenance-ref-grammar     pkm,renavon   pkm   ok   RED
```

Before installing, confirm in a scratch copy that (a) the fixture fails patch 05's guard,
(b) the message carries the marker, and (c) adding a `brief_row_divergence` declaration to
the fixture record turns it green — so the fixture is pinning the tooth and not merely a
malformed record.
