# Fixture candidates — staged, installed by the driver at step 4

`tests/poison/` is author-key territory (BRIEF §9.1), so these are staged here as trees the
driver `cp`s into place under your confirmation, adds a `MANIFEST.sha256` row per file
(sealed directory), and wires with a `poison()` line in `scripts/custodian.sh`, a row in
`tests/poison/README.md` and the pytest mirror in `tests/test_governance_scripts.py`. Every
one of them has been watched biting — and, where the tooth has a green side, watched going
green — in a scratch clone, and the whole install has been rehearsed end to end
(`rehearse_publication.sh`, D0183).

| Tree | Guard | Marker | Needs |
|---|---|---|---|
| `check-concepts/governance/policy.yaml` | narrows the existing `check-concepts/` fixture back to ONE reason | (unchanged: `snapshot content drifted`) | patch 01 — **mandatory with it** |
| `check-concepts-brief-row/` | `check_concepts.py` tooth 2 (patch 05) | `brief_row` | patch 05 |
| `check-decisions-retired-enforced/` | `check_decisions.py` retirement refusal (patch 06) | `only a documentary binding may be retired` | patch 06 |
| `docs/redteam/fixture-candidates/oracle-shadow-spoofed/` | `src/tannen/laws/plugin.py` as sharpened by RT-M3-04 | `answers with different code` — **not** the `RT-M3-04` its README claims; that string never appears in the guard's output | nothing: D0179 landed the guard |

## 1. `check-concepts/governance/policy.yaml` — one file, three lines

Patch `01` makes `check_concepts.py` read `concept_registry.expected_citation_pins` from
`governance/policy.yaml` and fail when it is missing — deliberately, because a degraded
citation check with no expectation to meet is the vacuous pass the whole condition exists
to prevent (D0115, D0116 species I). The existing poison tree has no policy of its own, so
after patch `01` it fails for **two** reasons instead of one. The custodian still passes —
`poison()` only requires the marker — but a fixture that fails for a reason it does not name
is a fixture nobody reads. This file narrows it back. One record, one `snapshot.path`, so
the expectation is 1.

Measured 2026-09-07 in a scratch clone with patch 01 applied: without the file, 3
violations (drift, policy missing, CONCEPTS.md missing); with it, 2 (drift and the
pre-existing CONCEPTS.md line). The CONCEPTS.md line predates this package.

## 2. `check-concepts-brief-row/` — patch 05's tooth

A one-record tree whose `brief_row` quotes a row naming **two** owners while `sources` cites
**one**, with no `brief_row_divergence`. It carries its own `BRIEF.md`: one synthetic
§2-shaped row. The guard reads the constitution at the root it is pointed at and **never
falls back to the real one** — a fixture forced to quote the real §2 would be duplicating
the governance corpus, which is the thing poison trees exist not to do. So the tree needs
its own excerpt, exactly as `check-concepts/` needs its own policy.

Measured, both directions, 2026-09-07 (patch 05 applied, `--root` at the tree):

```
check_concepts: FAIL (2 violation(s))
  - concepts/poison-brief-row-drift.yaml: brief_row owners per BRIEF §2 are ['pkm', 'proplang'] but sources[].repo names ['pkm'] — undeclared divergence: ['proplang'] …
  - CONCEPTS.md missing or lacks the generated input-hash header — run make projections
```

and with a `brief_row_divergence: {omits: [proplang], …}` block appended to the record the
first line disappears and only the pre-existing CONCEPTS.md line remains — so the fixture
pins the tooth, not a malformed record.

## 3. `check-decisions-retired-enforced/` — patch 06's refusal

Two records: D0001 binds `enforced` to an absent path; D0002 (accepted) retires that
binding. Everything a legitimate retirement has — an accepted retiring record, a real
binding, an absent target — except the strength. `check_decisions` must refuse it:

```
check_decisions: FAIL (2 violation(s))
  - decisions/0001-…: binding to this-target-is-deliberately-absent.txt is retired by D0002, but the binding is enforced — only a documentary binding may be retired; …
  - DECISIONS.md missing or lacks the generated input-hash header — run make projections
```

The other three refusals patch 06 makes (non-accepted retiring record, stale retirement,
retirement of a binding the record does not carry) were each watched going red in the
scratch clone against the real D0115/D0181 pair; they share the code path this fixture
pins and are not given trees of their own.

## 4. `oracle-shadow-spoofed/` — install-ready, and its README's marker is wrong

Its guard patch landed as D0179, so the driver `git mv`s the three files (the `.patch` stays
in `docs/redteam/` as the record) and D0179's file binding follows the README to its new
path (D0045: bindings are present-tense; the first draft of the driver moved the file and
left D0179 dangling — the shape D0181 is about, found by the partial rehearsal).

The README says **Marker: `RT-M3-04`**. The guard's output never contains that string: its
tooth text is `answers with different code for […]`, and the trailing citation names
RT-M1-01 and RT-M2-01 only. A `poison()` line keyed on `RT-M3-04` would report *failed its
poison for the wrong reason (marker absent)* and redden the custodian. Found by wiring the
line and running the custodian; the driver keys on the real text, and so does the pytest
mirror.
