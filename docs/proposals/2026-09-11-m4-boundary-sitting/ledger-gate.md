# The findings ledger and its gate (RT-M4-07, D0246 A3)

**Status:** a draft for the M4 boundary sitting, which is the first sitting to run under this
gate. The ledger is `docs/redteam/LEDGER.yaml`; the gate is `ledger_gate.py` in this directory.
The driver embeds the gate verbatim at step 8c, and checks it again before step 10 mints the
close tag. It is **not** in `make verify` and not custody-set; promoting it is a later ruling
(D0249).

## The rule

A boundary sitting cannot close while any red-team finding is unaccounted for. Accounted for
means exactly one ledger row, with one of four dispositions:

| disposition | required fields | meaning |
|---|---|---|
| `closed` | `record` | the decision that closed it |
| `scheduled` | `where`, `record` | a named sitting or session, under a record that commits to it |
| `deferred` | `reason`, `revisit` | why nothing is happening yet, and the boundary at which it is looked at again |
| `non-goal` | `cite` (`BRIEF §…`) | the BRIEF clause that rules it out |

Every row also needs `id`, `report` and `severity` (as the report states it), and may carry a
`note`. The gate refuses the following:
- a finding with no row;
- a row naming no finding (an orphan);
- a duplicate row;
- an unknown field;
- an invalid disposition, or a missing required field;
- a `record` with no `decisions/<nnnn>-*.yaml`;
- a `report` that does not name the id;
- a non-goal that cites no BRIEF clause.

Status audits (RT-M1-06, RT-M2-08, RT-M3-06, RT-M4-06) are closed by the record that filed
their pass; everything they carry is dispositioned under its own id.

## Where the ids come from, and why that is structure and not state

The id set is derived from the reports, never written down (D0171 ruling (3), D0211). The
gate reads two forms:
- `## RT-… —` headings (every report);
- `| RT-… |` table rows (the M2–M4 summary tables, and RT-M4-07, which exists only in the
  2026-09-13 addendum's table).

The M0 report's `## S-01`…`S-04` "suspected" entries do not match, deliberately: they were never
confirmed findings.

The standing rule is that no test may learn another artifact's **state** from its prose (D0213).
The gate does not. It reads which finding ids a report *declares* — the report's section
structure — and never what a report says about a finding's status. Status lives in exactly one
place, the ledger row, which the builder drafts and the owner confirms at the sitting. A report
that declares a new id joins the gate by existing, and the gate then fails until someone
dispositions it. That is the service-rate measurement RT-M4-07 found missing.

## Watched failing, 2026-09-13

Every mutation ran against a scratch copy of `docs/redteam/` and `decisions/`, never the real
files. Exit status was measured directly.

| # | Mutation | Exit | What it printed |
|---|---|---|---|
| a | the real ledger | 0 | `OK — 42 finding(s) accounted for: 24 closed, 4 scheduled, 14 deferred`, then the 18 open rows |
| b | RT-M2-03's row deleted | 1 | `RT-M2-03: no ledger row — named in docs/redteam/2026-09-01-m2-boundary.md` |
| c | `deferred` rewritten to `parked` | 1 | 15 problems, including `disposition 'parked' is not one of …` |
| d | RT-05's `reason` renamed `rationale` | 1 | `disposition 'deferred' requires 'reason'` + `unknown field 'rationale'` |
| e | RT-M3-05's record set to D9999 | 1 | `record D9999 has no decisions/9999-*.yaml` |
| f | an appended RT-M9-01 row | 1 | `no report in docs/redteam/ names this finding (an orphan row)` |
| g | a second RT-01 row | 1 | `RT-01: 2 rows — exactly one is allowed` |
| h | every `RT-` in the reports rewritten to `XX-` | 1 | the positive control: RT-01 and RT-M4-07 not derived, and no ids at all |

Row (h) is the one that earns the positive control. Without it, a derivation that matched
nothing would report every ledger as fully covered.

## What the owner is asked at step 8c

Confirm the 18 rows that are not `closed`, or edit them and re-run the gate. The 14 `deferred`
rows are builder proposals until confirmed. Several say plainly that the evidence does not
settle them, and those are the ones to read:
- **RT-14:** last audited at M1.
- **RT-M2-02:** is the `laws.yaml` residue accepted?
- **RT-M2-03:** it dropped out of every audit after M2.
