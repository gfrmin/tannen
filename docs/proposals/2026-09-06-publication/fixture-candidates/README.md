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
