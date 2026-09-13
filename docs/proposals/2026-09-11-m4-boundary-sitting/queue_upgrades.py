#!/usr/bin/env python3
"""D0214's recommendation, applied to this sitting's own queue (M4 driver step 8).

    python3 queue_upgrades.py <RECORD_ID>

D0214 found that the records a sitting discharges are exactly the ones whose bindings it has
just made enforceable, and exactly the ones a builder may not touch afterwards: a Tier-C
record's signature covers its whole bytes, so its bindings move only under the owner's key.
The cheap window is the moment step 8 flips the record's status, BEFORE it signs. The driver
calls this there, shows the diff, then accepts and signs (Tier C) or flips (Tier A).

EVERY UPGRADE IS GATED ON A DETECTOR THAT ITS ARTIFACT LANDED IN THE WORKING TREE. A step the
owner declined earlier in the sitting leaves its binding documentary, because an upgraded
detail over an artifact that is not there is the false report D0122 is about. Detectors read
code and config, never a comment or a docstring (D0131 item 1, D0211): `code_has` skips
comment lines, and a Python detector names a `def`, not a sentence.

Output:
  - edited:          the record's path on stdout, exit 0
  - nothing fired:   "<id>: nothing landed for this record", exit 0
  - already applied: "<id>: already upgraded", exit 0
  - an upgrade fired but its binding is not the expected pre-state: "<id>: …", exit 1
The script never signs.
"""
from __future__ import annotations

import glob
import pathlib
import re
import sys
from dataclasses import dataclass, field
from typing import Callable

ROOT = pathlib.Path(".")


def text(rel: str) -> str:
    p = ROOT / rel
    return p.read_text(encoding="utf-8") if p.exists() else ""


def code_has(rel: str, needle: str) -> bool:
    """`needle` on a line that is not a comment (#-led, after indentation)."""
    return any(needle in line and not line.lstrip().startswith("#")
               for line in text(rel).splitlines())


# ------------------------------------------------------------------ detectors
def doorway_contract_landed() -> bool:
    return ('id = "shell-no-subprocess"' in text("governance/importlinter.toml")
            and (ROOT / "scripts" / "check_doorway.py").exists())


def delegations_marker_fixed() -> bool:
    return (ROOT / "DELEGATIONS.md").exists() and "$marker" not in text("DELEGATIONS.md")


def derivation_landed() -> bool:
    return "def derive_required_tags(" in text("scripts/check_tag_signers.py")


def m4_laws_freeze_enumerated() -> bool:
    return re.search(r"^  - m4-laws-freeze$", text("governance/tag-roles.yaml"), re.M) is not None


def current_envelope_landed() -> bool:
    return "def current_milestone(" in text("scripts/check_manifest.py")


def prebudget_lock_landed() -> bool:
    return "def unmet_spend_preconditions(" in text("scripts/check_manifest.py")


def policy_sentence_landed() -> bool:
    return "WHAT SPENDGUARD DOES AND DOES NOT DO" in text("governance/policy.yaml")


def roadmap_hook_landed() -> bool:
    return code_has(".pre-commit-config.yaml", "id: regen-roadmap")


def roadmap_make_landed() -> bool:
    return code_has("Makefile", "scripts/gen_roadmap.py")


def m4_driver_installed() -> bool:
    return code_has("scripts/boundary_sitting.sh", "PROPOSALS_M4=")


#: The M3 driver's step-8 tier prefilter, verbatim. Its ABSENCE, beside a step 8 that still
#: greps the status line, is the code-level fact that the queue is selected at any tier.
M3_TIER_PREFILTER = """[ "$(sed -n 's/^tier: *//p' "$rec" | head -1)" = "C" ] || continue"""


def queue_at_any_tier() -> bool:
    src = text("scripts/boundary_sitting.sh")
    return (m4_driver_installed() and "^status: blocked-on-owner$" in src
            and M3_TIER_PREFILTER not in src)


def driver_offers_queue_upgrades() -> bool:
    return (code_has("scripts/boundary_sitting.sh", "queue_upgrades.py")
            and code_has("scripts/boundary_sitting.sh", "upgrade_binding.py"))


def decisions_verdict_out() -> bool:
    """D0215's remedy: the generator no longer renders the verdict into DECISIONS.md (the
    digest's `- Attention receipt:` line is a different spelling and stays), and the guard no
    longer compares one — and does refuse one, citing D0215 in code."""
    gen = text("scripts/gen_projections.py")
    chk = text("scripts/check_decisions.py")
    return (bool(gen) and 'f"Attention receipt: **{' not in gen
            and bool(chk) and "attention-receipt line is not what today computes" not in chk
            and code_has("scripts/check_decisions.py", "D0215"))


def anti_disarm_fixture() -> str | None:
    """The installed anti-disarm fixture's directory name, if it and its README row landed."""
    readme = text("tests/poison/README.md")
    # The fixture's name is `oracle-shadow-cross-file` (its sibling family's naming), so a glob on
    # "disarm" never matched it — reconciled with the drafted candidate, by name.
    d = ROOT / "tests" / "poison" / "oracle-shadow-cross-file"
    if d.is_dir() and f"| `{d.name}/` |" in readme:
        return d.name
    return None


# ------------------------------------------------------------------ upgrades
@dataclass
class Upgrade:
    name: str
    detector: Callable[[], bool]
    old: str
    new: str | Callable[[], str]
    count: tuple[int, int] | None = None   # bindings_count before -> after, when it moves


@dataclass
class Record:
    glob: str
    upgrades: list[Upgrade] = field(default_factory=list)


def _driver_note() -> str:
    return ("Type stays `file`: custody-set with no MANIFEST.sha256 row, so a revert shows as "
            "check_custody drift.")


UPGRADES: dict[str, Record] = {
    # ---------------------------------------------------------------- Tier C
    "D0214": Record("decisions/0214-*.yaml", [
        Upgrade("the driver offers the upgrade before the signature", driver_offers_queue_upgrades,
                """  - type: file
    target: scripts/boundary_sitting.sh
    strength: documentary
    detail: >-
      Step 4c, where each Tier-C queue record is flipped and signed — the one window in which
      these upgrades are cheap, and the place the recommendation above would land. Documentary
      and it must stay so until the owner writes it in: the file is custody-set, and a
      drafted change awaiting the owner's key enforces nothing (D0143).
""",
                """  - type: file
    target: scripts/boundary_sitting.sh
    strength: enforced
    detail: >-
      ENFORCED at the M4 boundary sitting: the recommendation landed. Step 8 of the M4 driver
      offers each queue record's drafted binding upgrades before it flips the status and signs,
      so the upgrade and the signature are one act, and its step 8b applies the nine upgrades
      this record found to the five already-signed records. Type stays `file`: custody-set with
      no MANIFEST.sha256 row, so a revert shows as check_custody drift.
"""),
    ]),
    "D0215": Record("decisions/0215-*.yaml", [
        Upgrade("the projection stops carrying the verdict", decisions_verdict_out,
                """  - type: file
    target: scripts/check_decisions.py
    strength: documentary
    detail: >-
      The comparison at :459 and the comment at :445 that names the clock half and argues the
      fix that produced it. Cited for both: the reasoning is sound about RT-M2-05 and is the
      proximate cause of a projection that can only be correct at the tip.
""",
                """  - type: file
    target: scripts/check_decisions.py
    strength: enforced
    detail: >-
      ENFORCED at the M4 boundary sitting: the recommendation landed. gen_projections.py no
      longer renders the FRESH/STALE verdict into DECISIONS.md, and check_decisions no longer
      compares the tracked file against a verdict computed from today's date and today's tag
      set, which is what reddened every tagged sitting commit. It still computes and prints
      the verdict at run time, and refuses a projection that carries one. Type stays `file`:
      custody-set with no MANIFEST.sha256 row, so a revert shows as check_custody drift.
"""),
        Upgrade("the M3 line citations keep a true home", m4_driver_installed,
                """  - type: file
    target: scripts/boundary_sitting.sh
    strength: documentary
    detail: >-
      Step 10's clean-tree requirement at :2664 and step 11's argument at :2746-2760 that no
      earlier regeneration point exists. Together they are the proof that this is structural:
      the driver already knows both halves and neither it nor anything else says what they
      imply for the commit the tag names. Documentary and must stay so — the file is
      custody-set (D0143).
""",
                """  - type: file
    target: docs/proposals/2026-09-04-m3-boundary-sitting/boundary_sitting.sh
    strength: documentary
    detail: >-
      Retargeted at the M4 boundary sitting from scripts/boundary_sitting.sh, which that
      sitting replaced with the M4 driver, so the line numbers kept a file in which they are
      still true. Step 10's clean-tree requirement at :2664 and step 11's argument at
      :2746-2760 that no earlier regeneration point exists: together, the proof that this is
      structural. Documentary: a proposal copy detects nothing.
"""),
    ]),
    "D0238": Record("decisions/0238-*.yaml", [
        Upgrade("policy.yaml's sentence corrected", policy_sentence_landed,
                """  - type: file
    target: governance/policy.yaml
    strength: documentary
    detail: Lines 10-13, the sentence the shipped SpendGuard does not yet make true; owner-signed and custody-set.
""",
                """  - type: file
    target: governance/policy.yaml
    strength: enforced
    detail: >-
      ENFORCED at the M4 boundary sitting, on D0240's ruling: the sentence claiming SpendGuard
      enforces the envelope operationally was replaced with one stating that SpendGuard enforces
      the budget its caller supplies and scripts/check_manifest.py binds budget.yaml to the
      envelope. The corrected bytes are owner-signed and check_manifest's required_signatures
      verifies them, so a revert to the false sentence breaks the signature.
"""),
    ]),
    "D0240": Record("decisions/0240-*.yaml", [
        Upgrade("item (1): policy.yaml's sentence corrected", policy_sentence_landed,
                """  - type: file
    target: governance/policy.yaml
    strength: documentary
    detail: >-
      Item (1)'s target — the sentence at :10-13 that claims SpendGuard enforces the envelope
      operationally. Owner-signed and custody-set, so the correction is drafted and installed
      under the owner's key; a drafted change awaiting the key enforces nothing (D0143).
""",
                """  - type: file
    target: governance/policy.yaml
    strength: enforced
    detail: >-
      Item (1), ENFORCED at the M4 boundary sitting: the sentence claiming SpendGuard enforces
      the envelope operationally was replaced with one stating what SpendGuard does and does
      not do. The corrected bytes are owner-signed and check_manifest's required_signatures
      verifies them, so a revert to the false sentence breaks the signature.
"""),
        Upgrade("item (3): the current envelope", current_envelope_landed,
                """  - type: file
    target: scripts/check_manifest.py
    strength: documentary
    detail: >-
      Item (3)'s target — the max-over-all-envelopes comparison at :221-222. Custody-set, which
      was measured rather than assumed, so this is owner-applied and not the builder work the
      ruling took it for. D0229 item (5) binds the same path for the same defect.
""",
                """  - type: file
    target: scripts/check_manifest.py
    strength: enforced
    detail: >-
      Item (3), ENFORCED at the M4 boundary sitting: each budget.yaml ceiling is compared
      against the CURRENT milestone's envelope, derived from MANIFEST.sha256's own rows, rather
      than the maximum over all of them; a missing current envelope and an underivable current
      milestone both fail. D0229 item (5) binds the same path for the same defect. Type stays
      `file`: custody-set with no MANIFEST.sha256 row, so a revert shows as check_custody drift.
"""),
    ]),
    "D0242": Record("decisions/0242-*.yaml", [
        Upgrade("item (3)'s lock in its owner-held home", prebudget_lock_landed,
                """links: ["D0240", "D0241", "D0239", "D0238", "D0229", "D0128", "D0106", "D0171", "D0211", "D0143", "D0063", "D0064"]
""",
                """  - type: file
    target: scripts/check_manifest.py
    strength: enforced
    detail: >-
      Item (3), ADDED at the M4 boundary sitting when the lock landed in its stronger home
      (D0244 item 1): check_manifest refuses a nonzero budget envelope or ceiling while
      governance/laws.yaml lacks the superseded entry retiring L4.4's third node or
      src/tannen/cli.py declares no --budget-override. D0243's test file still pins all four
      preconditions; this is the half only the owner can remove. Type `file`: custody-set with
      no MANIFEST.sha256 row, so a revert shows as check_custody drift.
links: ["D0240", "D0241", "D0239", "D0238", "D0229", "D0128", "D0106", "D0171", "D0211", "D0143", "D0063", "D0064"]
""", count=(3, 4)),
    ]),
    "D0244": Record("decisions/0244-*.yaml", [
        Upgrade("item (1): the folded lock landed",
                lambda: prebudget_lock_landed() and current_envelope_landed(),
                """  - type: file
    target: scripts/check_manifest.py
    strength: documentary
    detail: >-
      Where the folded lock lands at the sitting. Documentary, not `manifest`: this file is
      custody-set (governance/tier-c.yaml) and has NO row in MANIFEST.sha256, which holds only
      scripts/check_tag_signers.py and scripts/custodian.sh. Custody-set means owner-applied
      with a re-signature; regenerating the custody hash does not re-sign it (D0242 item (2)).
""",
                """  - type: file
    target: scripts/check_manifest.py
    strength: enforced
    detail: >-
      ENFORCED at the M4 boundary sitting: the folded patch landed, with both changes. Ceilings
      are compared against the current milestone's envelope, and a nonzero envelope or ceiling
      is refused while the L4.4 superseded entry or the --budget-override flag is absent, the
      flag read off the syntax tree rather than grepped. `file`, not `manifest`: this path is
      custody-set with no MANIFEST.sha256 row, so a revert shows as check_custody drift and
      needs a re-signature (D0242 item (2)).
"""),
    ]),
    # ---------------------------------------------------------------- Tier A, blocked-on-owner
    "D0217": Record("decisions/0217-*.yaml", [
        Upgrade("item (1): the regen-roadmap hook", roadmap_hook_landed,
                """  - type: file
    target: .pre-commit-config.yaml
    strength: documentary
    detail: >-
      Where the `regen-roadmap` hook goes, beside `regen-projections`. Documentary because
      the file is custody-set: a builder cannot add the hook, and a drafted one enforces
      nothing (D0143).
""",
                """  - type: file
    target: .pre-commit-config.yaml
    strength: enforced
    detail: >-
      Item (1), ENFORCED at the M4 boundary sitting: the `regen-roadmap` hook landed beside
      `regen-projections`, so a commit adding a decision record regenerates ROADMAP.md in the
      same motion. tests/test_roadmap.py still detects a stale copy. Type stays `file`:
      custody-set with no MANIFEST.sha256 row, so a revert shows as check_custody drift.
"""),
        Upgrade("item (2): make projections names three generators", roadmap_make_landed,
                """  - type: file
    target: Makefile
    strength: documentary
    detail: >-
      The `projections` target, which names two generators and should name three.
      Custody-set (row 6).
""",
                """  - type: file
    target: Makefile
    strength: enforced
    detail: >-
      Item (2), ENFORCED at the M4 boundary sitting: `make projections` runs
      scripts/gen_roadmap.py beside gen_projections.py. Type stays `file`: custody-set with no
      MANIFEST.sha256 row, so a revert shows as check_custody drift.
"""),
        Upgrade("item (3): the queue at any tier", queue_at_any_tier,
                """  - type: file
    target: scripts/boundary_sitting.sh
    strength: documentary
    detail: >-
      Step 8's queue selection, which tests tier before status and therefore cannot see this
      record. Custody-set; the M4 driver is where it would change, alongside D0205's step-11
      deletion and D0201 ruling (4)'s receipt reorder — one rework of the ceremony, not
      three.
""",
                """  - type: file
    target: scripts/boundary_sitting.sh
    strength: enforced
    detail: >-
      Item (3), ENFORCED at the M4 boundary sitting: step 8 of the M4 driver selects its queue
      by `status: blocked-on-owner` at any tier, with no Tier-C prefilter, so a Tier-A record
      that needs the owner's key (this one) reaches the sitting that discharges it. Type stays
      `file`: custody-set with no MANIFEST.sha256 row, so a revert shows as check_custody drift.
"""),
    ]),
    "D0229": Record("decisions/0229-*.yaml", [
        Upgrade("item (1): DELEGATIONS.md's literal $marker", delegations_marker_fixed,
                """  - type: file
    target: DELEGATIONS.md
    strength: documentary
    detail: Item (1).
""",
                """  - type: manifest
    target: DELEGATIONS.md
    strength: enforced
    detail: >-
      Item (1), ENFORCED at the M4 boundary sitting: the literal `$marker` the publication
      rewrite left in the founding ratification was replaced with the text it stood for, and
      the file's MANIFEST.sha256 row was regenerated over the corrected bytes, so a regression
      breaks a seal.
"""),
        Upgrade("item (2): the shell doorway contract", doorway_contract_landed,
                """  - type: file
    target: governance/importlinter.toml
    strength: documentary
    detail: Item (2).
""",
                """  - type: manifest
    target: governance/importlinter.toml
    strength: enforced
    detail: >-
      Item (2), ENFORCED at the M4 boundary sitting: the `shell-no-subprocess` contract scans
      the whole `tannen` package, not only the kernel, and the file's MANIFEST.sha256 row pins
      it. The derived network scan installed beside it is scripts/check_doorway.py (RT-M4-02);
      the superseding frozen L4.9 is owed by M5 Session A, for D0241's reason.
"""),
        Upgrade("item (3): the anti-disarm fixture", lambda: anti_disarm_fixture() is not None,
                """  - type: file
    target: tests/poison/README.md
    strength: documentary
    detail: Item (3) — the corpus the fixture and the corrections join.
""",
                lambda: f"""  - type: manifest
    target: tests/poison/README.md
    strength: enforced
    detail: >-
      Item (3), ENFORCED at the M4 boundary sitting: the anti-disarm fixture
      `tests/poison/{anti_disarm_fixture()}/` was installed with its README row. It collects an
      M3 law file and its M4 superseding file together, so a cross-file disarm is watched
      failing by the custodian, which no single-file invocation can see. The README carries a
      MANIFEST.sha256 row.
"""),
        Upgrade("item (4): required tags, derived or extended",
                lambda: derivation_landed() or m4_laws_freeze_enumerated(),
                """  - type: file
    target: governance/tag-roles.yaml
    strength: documentary
    detail: Item (4).
""",
                lambda: ("""  - type: manifest
    target: governance/tag-roles.yaml
    strength: enforced
    detail: >-
      Item (4), ENFORCED at the M4 boundary sitting by the better half: D0205's derivation was
      installed, so `required_tags` is refused as an enumeration and every milestone with a
      frozen spec requires its laws-freeze tag, m4-laws-freeze included, by construction. The
      file carries a MANIFEST.sha256 row.
""" if derivation_landed() else """  - type: manifest
    target: governance/tag-roles.yaml
    strength: enforced
    detail: >-
      Item (4), ENFORCED at the M4 boundary sitting by the lesser half: D0205's derivation was
      declined, and m4-laws-freeze was added to the `required_tags` enumeration instead, so its
      deletion fails check_tag_signers. The enumeration still lags one boundary (D0095). The
      file carries a MANIFEST.sha256 row.
""")),
        Upgrade("item (5): the current envelope", current_envelope_landed,
                """  - type: file
    target: scripts/check_manifest.py
    strength: documentary
    detail: Item (5) — the comparison against every envelope rather than the current one.
""",
                """  - type: file
    target: scripts/check_manifest.py
    strength: enforced
    detail: >-
      Item (5), ENFORCED at the M4 boundary sitting: each ceiling is compared against the
      CURRENT milestone's envelope, derived from MANIFEST.sha256's rows, not the maximum over
      all of them (D0240 item 3). Type stays `file`: custody-set with no MANIFEST.sha256 row, so
      a revert shows as check_custody drift.
"""),
    ]),
    # D0241 carries a pytest binding already enforced and two draft citations. Nothing this
    # sitting lands moves it: the clamp and the successor law are M5 Session A's.
    "D0241": Record("decisions/0241-*.yaml", []),
}


def main() -> int:
    if len(sys.argv) != 2:
        sys.exit(f"usage: queue_upgrades.py {{{'|'.join(UPGRADES)}}}")
    rid = sys.argv[1]
    record = UPGRADES.get(rid)
    if record is None:
        print(f"{rid}: nothing landed for this record (no drafted upgrades)")
        return 0
    hits = glob.glob(record.glob)
    if len(hits) != 1:
        print(f"{rid}: expected exactly one record for {record.glob}, found {len(hits)}",
              file=sys.stderr)
        return 1
    path = pathlib.Path(hits[0])
    src = path.read_text(encoding="utf-8")

    applied, already = [], []
    for up in record.upgrades:
        if not up.detector():
            continue
        new = up.new() if callable(up.new) else up.new
        if new in src:
            already.append(up.name)
            continue
        if src.count(up.old) != 1:
            print(f"{rid}: '{up.name}' landed, but its binding is not the expected pre-state "
                  f"({src.count(up.old)} matches) — upgrade by hand", file=sys.stderr)
            return 1
        src = src.replace(up.old, new)
        if up.count:
            before, after = (f"bindings_count: {n}\n" for n in up.count)
            if src.count(before) != 1:
                print(f"{rid}: bindings_count is not {up.count[0]} — upgrade by hand",
                      file=sys.stderr)
                return 1
            src = src.replace(before, after)
        applied.append(up.name)

    if applied:
        path.write_text(src, encoding="utf-8")
        for name in applied:
            print(f"   upgraded: {name}", file=sys.stderr)
        print(path)
    elif already:
        print(f"{rid}: already upgraded ({'; '.join(already)})")
    else:
        print(f"{rid}: nothing landed for this record")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
