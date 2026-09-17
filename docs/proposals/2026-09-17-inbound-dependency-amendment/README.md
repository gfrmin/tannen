# Inbound dependency amendment — draft, for the M5 gate sitting

Drafted from the m4 session, on the owner's question of 2026-09-17: BRIEF §1 forbids a
cross-repo code dependency "in either direction", but the only guard that checks it —
`no-cross-repo` (`governance/importlinter.toml`) — has `source_modules = ["tannen"]`. It
cannot see, and never could see, a sibling repo importing tannen. So the rule as written
makes tannen unusable by anything else, and the guard never enforced that half of it. The
owner ruled: split the direction. Outbound stays exactly as guarded; inbound opens, but only
to a pinned release, never a moving dependency.

Nothing here is applied. This directory holds two patches to custody-set files, one patch to
two unfrozen files, and a decision record drafted without an id — the m5 session files it
under its next free one and applies the patches at the same sitting that signs it, alongside
D0257/D0268's door and the gate ceremony.

## Where the rule lives, and which direction each site actually enforces

| Site | What it says | Direction it enforces today |
|---|---|---|
| `BRIEF.md` §1 line 24 (standing rule) | "repos never import each other" | Prose only — no guard reads this line |
| `BRIEF.md` §1 life-agent row | "by contract, not import" | Prose only |
| `BRIEF.md` §9 Tier-C list | "any cross-repo code dependency" | Prose; the mechanism it names (below) is outbound |
| `BRIEF.md` §10 non-goals | "No repo unification, in either direction" / "No dependency on … code" | Prose; unaffected by this amendment (see below) |
| `CLAUDE.md` hard rule 1 | "Never add a dependency on, or import from, any other repo … In either direction" | Prose only |
| `CONTRIBUTING.md` / `NOTICE` | mirror the above | Prose only |
| `governance/importlinter.toml` `no-cross-repo` | `source_modules = ["tannen"]`, forbidding pkm/life_agent/credence/proplang/renavon | **Outbound only** — the one place any of this is machine-checked |

Every prose site said "either direction"; the one guard was always one-directional. This
amendment brings the prose to match the guard, and adds a real (though process-level, not
CI-checked) rule for the direction the guard cannot see: a pinned release.

## What changes

- `brief.patch` — adds §1.1 after §1's standing rule (BRIEF §1 line 24), additive, does not
  edit the frozen sentence. States the asymmetry and reads §9's Tier-C item as outbound.
- `claude-md.patch` — hard rule 1 gains one clause: a sibling may depend on tannen at a
  signed close tag or published version.
- `contributing-notice.patch` — the matching sentences in the two publication-drafted files
  (neither frozen nor custody-set; applied by the builder, after the sitting, not before).
- `record.yaml` — the decision, Tier C, `blocked-on-owner`, drafted without an id (see the
  file's own header comment for why).

## What does not change

- `no-cross-repo`'s forbidden list, and every kernel-io/kernel-clock/shell-no-subprocess
  contract — none of them mention direction and none are touched.
- §10's non-goals list, verbatim. "No repo unification" and "no dependency on sibling code"
  are both outbound claims about tannen; a sibling pinning tannen is neither a unification
  nor a dependency tannen carries. Door `constitution-amendments` is not opened.
- §2's concept registry: a sibling importing tannen's code still adopts tannen's *concepts*
  only by pin-and-conformance, never by restating them from the import.
- Any spend, publication, or store-mutation door. This amendment is entirely about the
  direction of a code dependency; it authorises no bytes to leave the repo boundary beyond
  what a public release already does (D0115), and D0115's door is already open.

## The owner's act, at the sitting, in order

1. Read this README and `record.yaml`.
2. Sign `record.yaml` (namespace `tannen-decision`) once it carries its filed id, or amend it
   first — the same `blocked-on-owner` → `sign_owner_rollback` pattern every Tier-C record in
   this project's sittings uses.
3. Apply `brief.patch` and `claude-md.patch`; refresh `MANIFEST.sha256`'s two rows for
   `BRIEF.md` and `CLAUDE.md` (`sha256sum <path>` replacing the existing row — the pattern
   `scripts/boundary_sitting.sh`'s `regen_manifest_row` already implements); re-sign the
   custody set (`governance/custody.sha256`) in the same custody step the sitting already
   performs for its other patches.
4. The builder applies `contributing-notice.patch` afterward, in an ordinary commit — neither
   file is frozen or custody-set, so no signature gates it.

## Downstream (informational — decided elsewhere, not by this record)

Once a `<milestone>-close` tag exists to pin, a consumer depends on it the ordinary way a
Python project pins a git dependency (e.g. under `uv`: `tannen = { git =
"https://github.com/gfrmin/tannen.git", tag = "m5-close" }`, or a published version once one
exists — `pyproject.toml`'s `version = "0.0.0"` has never been bumped). Whether and when to
actually take that dependency is life-agent's decision (D0212: cross-constellation scoping
lives in the consumer, not here), most plausibly reached through §8's optional M5b (the pkm
document vertical) once M5 itself closes.

## A concurrent-edit note for whoever applies this

The m5 session's own prep work (`docs/proposals/2026-09-16-m5-gate-sitting-prep/`) carries
its own `claude-md.patch` for a different, already-ruled change (D0267: proportional
records, CI-is-the-gate, no dated builder-work bullets). Both patches touch `CLAUDE.md`.
Apply them in whichever order the sitting reaches them and re-diff before the second one —
they touch different paragraphs (this one edits the hard-rules bullet under "Hard rules";
D0267's edits the "Decisions" and "Verification" headings), so a clean sequential apply is
expected, but re-check rather than assume.
