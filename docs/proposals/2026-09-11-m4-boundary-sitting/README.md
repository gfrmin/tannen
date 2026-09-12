# M4 boundary sitting — proposals (opened at Session A, 2026-09-11)

This directory is the M4 sitting's staging area. It exists from the milestone's first
session because its absence is a recorded defect class: the M2 sitting's custodian step
diffed against the previous milestone's proposals directory, that directory shipped no
`custodian.sh`, and the fixture the sitting itself installed never got its poison line
(D0152 item 6). The sitting's driver is drafted near the boundary, as at M2 and M3, and
joins this directory then.

Nothing here enforces anything. Every file that lands here is a draft the owner installs, or
declines, at the sitting, under the owner's key.

## The queue

The M4 boundary queue is every record `blocked-on-owner`, at any tier — ROADMAP.md §3 is the
query, and it is the one to read, because the digest's "Requires owner" section filters Tier
C and cannot see a Tier-A item that needs the key. At Session A it holds:

| Record | Tier | Ask |
|---|---|---|
| D0214 | C | Upgrade a Tier-C record's bindings in the same step that flips its status, before signing |
| D0215 | C | Stop storing a clock- and tag-dependent verdict in a hash-checked projection |
| D0217 | A | Wire `gen_roadmap.py` into pre-commit and make; the sitting's tier filter |
| D0228 | C | Whether, and on what terms, the store may write to a real R2 bucket |
| D0229 | A | Five custody-set items Session A found |

Added after Session A, by the owner's D0238 ruling of 2026-09-12 (D0240, D0241): D0241 joins
the queue, and two drafted patches land in this directory — `policy-envelope-sentence.md`
(the sentence claiming SpendGuard enforces the envelope operationally, which is false of the
SpendGuard that shipped) and `check-manifest-current-envelope.md` (D0229 item (5), the
comparison against every envelope rather than the current one). Both are custody-set files;
both are preconditions to the first nonzero envelope, so they belong to the pre-budget
sitting below as much as to this one.

Added again the same day by the owner's ruling on D0240/D0241 (D0242, D0244): D0242 and D0243
join the queue, and `check-manifest-current-envelope.md` now carries a **second** change — the
pre-budget lock, which refuses a nonzero envelope or ceiling while `governance/laws.yaml` lacks
the superseded entry retiring L4.4's third node, or while the clamp is absent from
`src/tannen/cli.py`. It is folded into that patch rather than drafted separately so the sitting
pays one custody regeneration and one signature; the two changes are signed, or declined,
together. The builder half of the same ruling already landed as `tests/test_spend_preconditions.py`
(D0243), which pins all four preconditions — including the two this sitting itself applies, and
which the folded guard therefore cannot honestly test about itself.

The mandatory extra sitting BRIEF §9.1 names — before any nonzero budget — is separate, and
its input is docs/specs/m4.md §4: which oracles M4 invokes, how they are priced, and what a
ceiling is a count of.

## Owed to the M4 driver, not yet drafted

Carried in from M3 and from the roadmap; each belongs in this milestone's copy of the driver.

- **Delete step 11** once `required_tags` is derived (D0205).
- **Move the receipt behind the commit confirm** — D0201 ruling (4), implemented by moving the
  confirm earlier (D0201's own reading).
- **Wire the roadmap** — D0217's pre-commit hook and make target.
- **Bootstrap an ssh-agent before offering `ssh-add`.** Measured on the owner's machine at the
  M3 sitting: no agent runs by default, the driver's bare `ssh-add` fails, and the failure is
  accepted silently, which leaves the passphrase prompt on every signature. The preflight
  should also tell "key not loaded" apart from "no agent at all" — they have different remedies.

## What Session A froze, for the sitting's reference

docs/specs/m4.md and `tests/laws/m4/` at the `m4-laws-freeze` tag: laws L4.1–L4.25, the
boundary model, its adapter, the frozen loader, and the `capture/1` schema and vectors. The
nine M3 law files are superseded forward there, not edited; their manifest note names the
successors.
