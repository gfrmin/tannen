# M3→M4 red-team findings — disposition for the sitting

The M3→M4 boundary red team ran on 2026-09-12 (D0244 item 2 sequenced it first, ahead of this
driver and any merge). Full report: `docs/redteam/2026-09-12-m4-boundary.md`; records D0245, and
**D0246 after owner review** (the report's `# Addendum, 2026-09-13`): P5's clean re-verified from
the failing side (earned, not accepted), **RT-M4-07 filed**, **RT-M4-02 promoted ahead of the
queue**, the fixture-install obligation inverted, and a pre-budget corollary added — all folded
into this note below.
This note maps each finding to who owns its remedy, so the sitting sees the queue in its own
directory. **Nothing here is an owner-apply-now patch** — no finding produced one, which is why
there is no new `.md` patch draft beside `policy-envelope-sentence.md` and
`check-manifest-current-envelope.md`. The findings are queued, not actioned (the D0104 norm).

| Finding | Sev | Owner of the remedy | This sitting? |
|---|---|---|---|
| RT-M4-01 spend fold trusts caller-written store values | High | The **pre-budget sitting** (BRIEF §9.1): a design choice on authenticating fold inputs, decided when a nonzero ceiling first makes it live. Inert while every ceiling is zero. | No — pre-budget sitting |
| RT-M4-02 L4.9 hand-written network set; subprocess/os unscanned | High | **D0229 item (2)** (the shell import-linter contract, already queued here) **plus** a superseding frozen L4.9 that derives from it (M5 Session A, or a dedicated Session A). | **FIRST (D0246 A2)** — the only *live* high, threat model is the builder, repo now published; `make verify` green ≠ "no IO" |
| RT-M4-03 export trusts `built.layer`, never re-derives it | Medium | Builder, a future session: one additive `layer_of(built.operators) is SERVE` line in unfrozen `export.py`; stricter than frozen L4.10, no supersession. D0092 binding written then. | No — builder-landable later |
| RT-M4-04 code address blind to closure captures (M1-inherited) | Medium | A decision record + future session: a design choice (refuse an un-addressable closure, or fold encodable captures in), touching unfrozen `incremental.py` and `transform.py`; a superseding law likely. | No — future session |
| RT-M4-05 error classification looser than docstrings (fail-closed) | Low | Builder, optional: R2Error mapping + the `tannen run` exit-code note. | No — builder, optional |
| RT-M4-06 status audit; `required_tags` still lags | Info | `required_tags` is **D0229 item (4)** / D0205, already queued here. The rest are the standing infrastructure findings (RT-05/-07/-10/-11/-12/-M1-02/-M1-04). | The `required_tags` half is already on this queue |
| RT-M4-07 the queue has no measured service-rate (D0246 A3) | Info (process) | **This sitting** owns the mechanism: a coverage-ledger-shaped gate — a boundary sitting that cannot account for every standing finding (scheduled / deferred-with-reason / non-goal) should not close. | **Yes** — the gate is a sitting deliverable, and this sitting is the first to run under it |

## What the sitting should carry forward

- **RT-M4-02 is the sitting's FIRST item, not a sharpening (D0246 A2).** It is the only *live*
  high finding — RT-M4-01 is inert while every ceiling is zero — its threat model is the builder,
  and the repository is now published, so a gate runs off this machine and `make verify` green does
  not today mean "no IO." The shell import-linter contract (D0229 item 2) is therefore load-bearing,
  not tidy-up: without it (and a superseded L4.9 deriving from it) a shell module reads the world
  via `subprocess`/`curl` or `imaplib` with `make verify` green. The contract must scan the shell,
  not only the kernel, forbid `subprocess`/`os`-shell-outs as well as the network names, and DERIVE
  the network set rather than hand-list it (D0171 ruling 3, D0211), the way the clock set already is.
- **RT-M4-01 is a precondition-shaped item for the pre-budget sitting**, alongside D0238/D0240:
  before a nonzero ceiling is signed, decide how SpendGuard's fold refuses a caller-authored
  reservation/capture. **Corollary (D0246 A5), free to record now:** RT-M4-01(b) is irreversible in a
  write-once store, so the store in use when the first nonzero ceiling is signed may *already* carry
  a poisoned reservation with no mutation path (BRIEF §10) — therefore signing the first nonzero
  ceiling should **start a fresh spend namespace, not inherit one.**
- **The fixture-install obligation runs the other way now (D0246 A4).** Three fixture candidates are
  drafted under `docs/redteam/fixture-candidates/` (spend-fold-forged-reservation,
  doorway-network-residue, code-address-closure). A candidate enforces nothing (D0143), so the
  obligation to install it sits on the **guard's closing decision record**, not on the draft:
  closing RT-M4-01 must account for `spend-fold-forged-reservation`, RT-M4-02 for
  `doorway-network-residue`, RT-M4-04 for `code-address-closure` (each install owner-key, Tier-C).
- **RT-M4-07 — this sitting runs under the gate it proposes (D0246 A3).** The queue has no measured
  service-rate: standing findings are "unchanged" across four boundaries and nothing gates a sitting
  on accounting for them. The proposed mechanism — a sitting cannot close without dispositioning
  every standing finding as scheduled, deferred-with-reason, or non-goal — is itself a deliverable
  of this sitting, and this sitting is the first that must satisfy it (see the standing list in
  RT-M4-06: RT-05, RT-07, RT-10/-11/-12, RT-M1-02, RT-M1-04, and `required_tags`/D0095).
- **RT-M4-03 and RT-M4-04 are the recurring "public constructor / trusted self-report" class** the
  D0235 review already fought on the world-authored side; they are builder/future-session work,
  not owner-key, and are listed so the sitting knows they are open, not so it acts on them.
