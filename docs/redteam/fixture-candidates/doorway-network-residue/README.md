# Fixture candidate — a shell module reads the world past L4.9 (RT-M4-02)

**Finding:** RT-M4-02 (`docs/redteam/2026-09-12-m4-boundary.md`), high.
**Status: DRAFT, no guard exists yet — do not install.**

L4.9 (`tests/laws/m4/test_l4_doorway.py`, frozen) enforces BRIEF §5.3's "the only IO doorway is
`oracles/`" for the shell, but only over a HAND-WRITTEN network-name set, and it does not scan
`subprocess`/`os` at all. `lint-imports`' `kernel-no-io` contract does forbid those names, but
its `source_modules = ["tannen.kernel"]` never reaches the shell. So there is **no live guard**
this fixture can poison: the frozen law passes the payloads, and the kernel contract does not scan
them. The guard it must poison is the one D0229 item (2) already queues — a custody-set
import-linter contract that scans the shell — plus a superseding L4.9 that derives its forbidden
set from that contract the way the clock set is derived today.

## What the fixture must demonstrate

A shell module (a stand-in for `tannen.store`/`executor`/`cli`) that reads the world outside the
capture doorway, in each of the ways L4.9 misses. Each must FAIL the future shell contract /
superseded L4.9:

- `import subprocess` + `subprocess.run(["curl", url])` — the sharpest: not in any scanned set.
- `import os` + `os.system("curl …")` — same.
- `import imaplib` / `poplib` / `socketserver` / `xmlrpc.client` + a real connection — live
  socket-opening stdlib modules absent from L4.9's NETWORK literal.

Positive control: the same module importing only `os.path`/`pathlib` (legitimate shell IO) must
PASS, so the contract distinguishes reading-the-world from reading-the-filesystem.

## Why it can't be a fixture yet

The guard is owner-key and Session-A-shaped: the shell import-linter contract lives in custody-set
`governance/importlinter.toml` (D0229 item 2), and the superseding frozen law is a new file under
`tests/laws/m4/` with an L4 id, the old L4.9 marked superseded in the manifest notes — the frozen
path is never edited (CLAUDE.md). When both land, this fixture installs as usual (owner-key,
Tier-C `trust-root-changes`). Deriving the forbidden set (rather than hand-listing it) is the
D0171-ruling-3 / D0211 discipline the clock set already follows and the network set does not.

## Owner review (D0246)

**This is the boundary sitting's FIRST item (A2)** — RT-M4-02 is the only *live* high finding, its
threat model is the builder, and the repository is now published, so `make verify` green does not
today mean "no IO." **The obligation runs the other way (A4):** the obligation to install this
fixture sits on the decision record that closes RT-M4-02 (the shell contract + superseding L4.9),
which **must account for this candidate**, not on this draft.
