# M3→M4 red-team findings — disposition for the sitting

The M3→M4 boundary red team ran on 2026-09-12 (D0244 item 2 sequenced it first, ahead of this
driver and any merge). Full report: `docs/redteam/2026-09-12-m4-boundary.md`; one record, D0245.
This note maps each finding to who owns its remedy, so the sitting sees the queue in its own
directory. **Nothing here is an owner-apply-now patch** — no finding produced one, which is why
there is no new `.md` patch draft beside `policy-envelope-sentence.md` and
`check-manifest-current-envelope.md`. The findings are queued, not actioned (the D0104 norm).

| Finding | Sev | Owner of the remedy | This sitting? |
|---|---|---|---|
| RT-M4-01 spend fold trusts caller-written store values | High | The **pre-budget sitting** (BRIEF §9.1): a design choice on authenticating fold inputs, decided when a nonzero ceiling first makes it live. Inert while every ceiling is zero. | No — pre-budget sitting |
| RT-M4-02 L4.9 hand-written network set; subprocess/os unscanned | High | **D0229 item (2)** (the shell import-linter contract, already queued here) **plus** a superseding frozen L4.9 that derives from it (M5 Session A, or a dedicated Session A). | Partly — D0229 item (2) is already on this queue |
| RT-M4-03 export trusts `built.layer`, never re-derives it | Medium | Builder, a future session: one additive `layer_of(built.operators) is SERVE` line in unfrozen `export.py`; stricter than frozen L4.10, no supersession. D0092 binding written then. | No — builder-landable later |
| RT-M4-04 code address blind to closure captures (M1-inherited) | Medium | A decision record + future session: a design choice (refuse an un-addressable closure, or fold encodable captures in), touching unfrozen `incremental.py` and `transform.py`; a superseding law likely. | No — future session |
| RT-M4-05 error classification looser than docstrings (fail-closed) | Low | Builder, optional: R2Error mapping + the `tannen run` exit-code note. | No — builder, optional |
| RT-M4-06 status audit; `required_tags` still lags | Info | `required_tags` is **D0229 item (4)** / D0205, already queued here. The rest are the standing infrastructure findings (RT-05/-07/-10/-11/-12/-M1-02/-M1-04). | The `required_tags` half is already on this queue |

## What the sitting should carry forward

- **RT-M4-02 sharpens D0229 item (2).** The shell import-linter contract this sitting already
  queues is not just tidy-up: without it (and a superseded L4.9 deriving from it) a shell module
  can read the world via `subprocess`/`curl` or `imaplib` with `make verify` green. The contract
  must scan the shell, not only the kernel, and forbid `subprocess`/`os`-shell-outs as well as the
  network names — and the network set must be DERIVED, not hand-listed (D0171 ruling 3, D0211),
  the way the clock set already is.
- **RT-M4-01 is a precondition-shaped item for the pre-budget sitting**, alongside D0238/D0240:
  before a nonzero ceiling is signed, decide how SpendGuard's fold refuses a caller-authored
  reservation/capture. Three fixture candidates are drafted under
  `docs/redteam/fixture-candidates/` (spend-fold-forged-reservation, doorway-network-residue,
  code-address-closure); each installs once its guard exists (owner-key, Tier-C).
- **RT-M4-03 and RT-M4-04 are the recurring "public constructor / trusted self-report" class** the
  D0235 review already fought on the world-authored side; they are builder/future-session work,
  not owner-key, and are listed so the sitting knows they are open, not so it acts on them.
