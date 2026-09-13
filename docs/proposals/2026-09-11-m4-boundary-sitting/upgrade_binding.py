#!/usr/bin/env python3
"""D0214's nine binding upgrades, one signed Tier-C record at a time (M4 driver step 8b).

    python3 upgrade_binding.py <RECORD_ID>      # D0131 | D0154 | D0171 | D0176 | D0195

Each of the five records is Tier C and already owner-signed, and a signature covers the
record's whole bytes (D0063 ruling 2), so no builder may make these edits: the driver runs
this, shows the diff, and re-signs the record in the same breath, or reverts it. Same shape as
the M2 sitting's upgrade_binding.py (step 4h).

Exact before->after text replacement, never a sweep: prose in a record's `decision:` field is
history and is never touched (D0045); only `bindings` (and `bindings_count` where the record
carries one) move.

Every after-text was MEASURED against the tree on 2026-09-13, not copied from D0214. Two of
D0214's own claims were no longer true as written and are corrected in the text, not repeated:
  - item (1) says `governance/laws.yaml` joined the custody set at the M2 sitting. It did not:
    that sitting added `conftest.py` in its place, because RT-M2-02 showed the registry's
    POINTER is what an attacker edits (D0141). The upgrade claims check_laws.py and conftest.py.
  - item (8) says `required_tags` "is now complete". On 2026-09-13 it lacked m4-laws-freeze
    (RT-M4-06, D0229 item 4). The upgrade claims the repin and m3-laws-freeze, not completeness.

Exit status: 0 and the record's path on stdout when edited; non-zero with "<id>: <reason>" when
the record is already upgraded, partially upgraded, or not in the expected pre-state.
"""
from __future__ import annotations

import glob
import pathlib
import sys


def one(pattern: str) -> pathlib.Path:
    hits = glob.glob(pattern)
    if len(hits) != 1:
        sys.exit(f"{pattern}: expected exactly one record, found {len(hits)}")
    return pathlib.Path(hits[0])


# ------------------------------------------------------------------ D0131 (items 1, 2)
D0131_TIER_C_OLD = """  - type: file
    target: governance/tier-c.yaml
    strength: documentary
    detail: >-
      Items (3) and (4): the custody set is declared here, so adding scripts/check_laws.py
      and governance/laws.yaml to it is an edit to this file plus a re-signature.
"""
D0131_TIER_C_NEW = """  - type: manifest
    target: governance/tier-c.yaml
    strength: enforced
    detail: >-
      ENFORCED, upgraded at the M4 boundary sitting (D0214 item 1). Items (3) and (4) landed at
      the M2 boundary sitting on 2026-09-03: scripts/check_laws.py joined `custody.set`, and
      the gate runs it directly. Item (3) also named governance/laws.yaml; the sitting added
      conftest.py in its place, because RT-M2-02 showed the registry's pointer, not its data,
      is what an attack edits (D0141). So this binding claims check_laws.py and conftest.py,
      not laws.yaml. governance/tier-c.yaml carries a MANIFEST.sha256 row, so removing either
      entry breaks a seal as well as the custody signature.
"""
D0131_TAG_ROLES_OLD = """  - type: file
    target: governance/tag-roles.yaml
    strength: documentary
    detail: "Item (5): `required_tags`, now short of both m1-laws-freeze and m2-laws-freeze."
"""
D0131_TAG_ROLES_NEW = """  - type: manifest
    target: governance/tag-roles.yaml
    strength: enforced
    detail: >-
      ENFORCED, upgraded at the M4 boundary sitting (D0214 item 2). Item (5) landed at the M2
      boundary sitting: m1-laws-freeze and m2-laws-freeze joined `required_tags`, and
      scripts/check_tag_signers.py fails "required tag missing" when a required tag is deleted.
      The file carries a MANIFEST.sha256 row, so the tag requirement cannot be edited away in
      silence, whether it is held by the hand enumeration or by the derivation D0205 put in its
      place.
"""

# ------------------------------------------------------------------ D0154 (items 3-6)
D0154_CUSTODIAN_OLD = """  - type: file
    target: scripts/custodian.sh
    strength: documentary
    detail: >-
      Carries items (1), (2)'s receipt-signing clause, (3) and (4) at the lines cited.
      Documentary because every one of them is an absence or an unchecked status this
      file cannot detect in itself, and because the file is custody-set and author-key
      territory — the fact that makes this queue necessary.
"""
D0154_CUSTODIAN_NEW = """  - type: manifest
    target: scripts/custodian.sh
    strength: enforced
    detail: >-
      ENFORCED, upgraded at the M4 boundary sitting (D0214 item 3). Items (1), (2)'s
      receipt-signing clause, (3) and (4) landed at the M3 boundary sitting on 2026-09-10 as
      hunks 1a/1b/1c, 2, 4 and 3: the oracle-shadow-model poison line and the derived
      completeness pass, which refuses an installed fixture no invocation reaches and a named
      fixture that is not installed; the receipt and its .sig removed, with a non-zero exit,
      when signing fails; the previous-receipt line read from the chosen file; and the
      __pycache__ exclusion in the sealed-path find. scripts/custodian.sh carries a
      MANIFEST.sha256 row, so reverting any hunk breaks a seal and the custody signature
      together.
"""
D0154_DRIVER_OLD = """  - type: file
    target: scripts/boundary_sitting.sh
    strength: documentary
    detail: >-
      Items (2) and (5): the retarget guard, the skip-guard subset, the missing lock,
      and the decline-path receipt ordering all live here. Custody-set
      (governance/custody.sha256), so every fix is the owner's.
"""
D0154_DRIVER_NEW = """  - type: file
    target: scripts/boundary_sitting.sh
    strength: enforced
    detail: >-
      ENFORCED, upgraded at the M4 boundary sitting (D0214 item 4). Items (2) and (5) landed in
      the M3 driver installed over this path on 2026-09-10 (D0200): the retarget guard tests
      the post-state, the skip guard reads every file its decline branch reverts, and an flock
      makes the sitting a one-run ceremony. The M4 driver that replaced it keeps the lock,
      moves the receipt behind the commit confirm (D0201 ruling 4), and retires the two
      re-application steps whose guards were fixed, both already-applied no-ops by then; the
      fixed copy stays readable at docs/proposals/2026-09-04-m3-boundary-sitting/boundary_sitting.sh.
      Type stays `file`: the path is custody-set with no MANIFEST.sha256 row, so a revert is
      detected by check_custody's drift line.
"""
D0154_TAG_ROLES_OLD = """  - type: file
    target: governance/tag-roles.yaml
    strength: documentary
    detail: >-
      Item (6): `required_tags`, short of `m3-laws-freeze` from the moment this
      session's freeze tag is minted until the sitting extends it.
"""
D0154_TAG_ROLES_NEW = """  - type: manifest
    target: governance/tag-roles.yaml
    strength: enforced
    detail: >-
      ENFORCED, upgraded at the M4 boundary sitting (D0214 item 5). Item (6) landed:
      m3-laws-freeze joined `required_tags` at the publication sitting of 2026-09-07 and
      m3-close at the M3 boundary sitting, and scripts/check_tag_signers.py refuses the
      deletion of either. The file carries a MANIFEST.sha256 row, so that requirement cannot
      be edited away in silence, whether it is held by the hand enumeration or by the
      derivation D0205 put in its place.
"""
D0154_LINKS = ("links: [D0045, D0095, D0105, D0117, D0131, D0141, D0142, D0143, D0146, D0148, "
               "D0152, D0153]\n")
D0154_PYTEST = """  - type: pytest
    target: "tests/test_governance_scripts.py::test_every_installed_fixture_is_exercised_by_this_suite"
    strength: enforced
    detail: >-
      ENFORCED, added at the M4 boundary sitting (D0214 item 6): the builder half of item (1)'s
      completeness pass, landed by D0213. Every directory under tests/poison/ must be exercised
      by a POISON row or a dedicated test, and every name there must have a directory behind
      it, so the gap item (1) records, a fixture installed with no invocation, fails plain
      `uv run pytest` as well as the custodian.
"""

# ------------------------------------------------------------------ D0171 (item 7)
D0171_CUSTODIAN_OLD = """  - type: file
    target: scripts/custodian.sh
    strength: documentary
    detail: >-
      Ruling (4)'s floor-integrity set: item 1's poison line and derived completeness pass,
      item 7's `check_laws` fixture, and item 2's receipt exit-status clause all land here.
      Author-key territory, which is what "goes in this sitting" means.
"""
D0171_CUSTODIAN_NEW = """  - type: manifest
    target: scripts/custodian.sh
    strength: enforced
    detail: >-
      ENFORCED, upgraded at the M4 boundary sitting (D0214 item 7). Ruling (4)'s
      floor-integrity set landed in full at the M3 boundary sitting on 2026-09-10: item 1's
      poison line and derived completeness pass, item 7's `check_laws` fixture and its
      `poison check_laws` invocation, and item 2's receipt exit-status clause.
      scripts/custodian.sh carries a MANIFEST.sha256 row, so reverting any of them breaks a
      seal and the custody signature together.
"""

# ------------------------------------------------------------------ D0176 (item 8)
D0176_TAG_ROLES_OLD = """  - type: file
    target: governance/tag-roles.yaml
    strength: documentary
    detail: >-
      Holds `trust_root.object`, the `brief-freeze` tag-object pin the rewrite invalidates,
      and `required_tags`, still missing `m3-laws-freeze` at the third recurrence (D0095,
      D0154 item 6, D0172 (C)). Both change under one signature at the sitting.
"""
D0176_TAG_ROLES_NEW = """  - type: manifest
    target: governance/tag-roles.yaml
    strength: enforced
    detail: >-
      ENFORCED, upgraded at the M4 boundary sitting (D0214 item 8). Both changes landed under
      one signature at the publication sitting of 2026-09-07: `trust_root.object` was repinned
      to the re-created brief-freeze tag object (d60b792f), and m3-laws-freeze joined
      `required_tags`. scripts/check_tag_signers.py pins the trust root by tag-object hash and
      refuses a missing required tag, and the file carries a MANIFEST.sha256 row. NOT claimed:
      that the requirement was complete. D0214 said so, and on 2026-09-13 m4-laws-freeze was
      the one existing boundary tag the enumeration lacked (RT-M4-06, D0229 item 4).
"""

# ------------------------------------------------------------------ D0195 (item 9)
D0195_CI_OLD = """  - type: file
    target: .github/workflows/ci.yml
    strength: documentary
    detail: >-
      Item (2). Documentary because the defect IS the prose: the workflow's behaviour is
      correct and its header is false, and no guard reads a comment. Frozen and custody-set,
      which is what makes it the owner's.
"""
D0195_CI_NEW = """  - type: manifest
    target: .github/workflows/ci.yml
    strength: enforced
    detail: >-
      ENFORCED, upgraded at the M4 boundary sitting (D0214 item 9). Item (2) landed at the M3
      boundary sitting on 2026-09-10: the header claiming the workflow had never run, and that
      a remote was an unopened door, was replaced with one saying it has run since 2026-09-08.
      The workflow is frozen with a MANIFEST.sha256 row, so a revert to the false header breaks
      a seal; no guard reads the comment's meaning.
"""

#: record id -> (record glob, [(before, after), ...], [(path, substring) the tree must hold]).
#: A bindings_count bump is one more (before, after) pair. An appended binding is spelled as a
#: replacement of the `links:` line that follows it, so it is exact-text like everything else.
EDITS: dict[str, tuple[str, list[tuple[str, str]], list[tuple[str, str]]]] = {
    "D0131": ("decisions/0131-*.yaml",
              [(D0131_TIER_C_OLD, D0131_TIER_C_NEW),
               (D0131_TAG_ROLES_OLD, D0131_TAG_ROLES_NEW)],
              [("governance/tier-c.yaml", "    - scripts/check_laws.py\n"),
               ("governance/tier-c.yaml", "    - conftest.py\n")]),
    "D0154": ("decisions/0154-*.yaml",
              [(D0154_CUSTODIAN_OLD, D0154_CUSTODIAN_NEW),
               (D0154_DRIVER_OLD, D0154_DRIVER_NEW),
               (D0154_TAG_ROLES_OLD, D0154_TAG_ROLES_NEW),
               ("bindings_count: 4\n", "bindings_count: 5\n"),
               (D0154_LINKS, D0154_PYTEST + D0154_LINKS)],
              # the detail above describes the M4 driver: refuse to write it over any other
              [("scripts/boundary_sitting.sh", "flock -n 9"),
               ("scripts/boundary_sitting.sh", 'PROPOSALS_M4='),
               ("tests/test_governance_scripts.py",
                "def test_every_installed_fixture_is_exercised_by_this_suite(")]),
    "D0171": ("decisions/0171-*.yaml",
              [(D0171_CUSTODIAN_OLD, D0171_CUSTODIAN_NEW)],
              [("scripts/custodian.sh", 'poison check_laws "which no law file defines"')]),
    "D0176": ("decisions/0176-*.yaml",
              [(D0176_TAG_ROLES_OLD, D0176_TAG_ROLES_NEW)],
              [("governance/tag-roles.yaml", "object: d60b792fe2ce329806ac70c9e9aa3c22e59fa789")]),
    "D0195": ("decisions/0195-*.yaml",
              [(D0195_CI_OLD, D0195_CI_NEW)],
              [(".github/workflows/ci.yml", "THIS FILE NOW RUNS")]),
}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in EDITS:
        sys.exit(f"usage: upgrade_binding.py {{{'|'.join(EDITS)}}}")
    rid = sys.argv[1]
    pattern, pairs, requires = EDITS[rid]
    path = one(pattern)
    src = path.read_text(encoding="utf-8")

    done = [new in src for _, new in pairs]
    if all(done):
        sys.exit(f"{rid}: already upgraded — nothing to do")
    if any(done):
        sys.exit(f"{rid}: partially upgraded ({sum(done)} of {len(pairs)} edits present) — "
                 "apply the rest by hand")
    for dep, needle in requires:
        p = pathlib.Path(dep)
        if not p.exists() or needle not in p.read_text(encoding="utf-8"):
            sys.exit(f"{rid}: {dep} does not carry {needle!r}, so the upgraded detail would "
                     "claim something the tree does not hold — not applied")
    for old, _ in pairs:
        if src.count(old) != 1:
            sys.exit(f"{rid}: a binding is not the expected text ({src.count(old)} matches for "
                     f"{old.splitlines()[1].strip()!r}) — apply by hand")
    for old, new in pairs:
        src = src.replace(old, new)
    path.write_text(src, encoding="utf-8")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
