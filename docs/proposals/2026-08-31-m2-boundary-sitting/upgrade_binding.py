import pathlib, sys, glob

def one(pattern):
    hits = glob.glob(pattern)
    if len(hits) != 1:
        sys.exit(f"{pattern}: expected exactly one record, found {len(hits)}")
    return pathlib.Path(hits[0])

WHICH = sys.argv[1]

EDITS = {
"D0110": (one("decisions/0110-*.yaml"), """  - type: file
    target: src/tannen/kernel/rel.py
    strength: documentary
    detail: >-
      Where the check would go: beside the existing zero-annotation drop, which is already
      the place that decides what a retained row may be.
""", """  - type: file
    target: src/tannen/kernel/rel.py
    strength: enforced
    detail: >-
      ENFORCED at the M2 boundary sitting: the check is there. `_refuse_unwitnessed`
      (rel.py:93) sits beside the zero-annotation drop and is called from `Rel._init`
      (rel.py:155), so `__init__`, `_build`, `_from_pairs`, `from_value` and every
      operator's output are covered at once. Located structurally by `why_slot` (D0109),
      so Z and B are untouched. The earlier text — "where the check WOULD go" — was a
      true future tense and is now a false present one.
  - type: pytest
    target: "tests/laws/m2/test_l2_sources.py::test_l2_2_an_annotation_claiming_copies_it_cannot_derive_is_refused"
    strength: enforced
    detail: >-
      ENFORCED at the M2 boundary sitting: L2.2 is the FROZEN M2 law carrying this claim,
      and tests/laws/m2/test_l2_sources.py has a MANIFEST.sha256 row, so the assertion
      cannot be softened without breaking a seal. The M1 law this record named as its
      blocker — test_l1_5_mixing_semirings_is_refused_by_name, which built `(2, Why.zero)`
      as incidental filler — was retired forward by D0128 in the same change that landed
      the check, which is that mechanism's first real use.
"""),
"D0108": (one("decisions/0108-*.yaml"), """  - type: manifest
    target: CLAUDE.md
    strength: documentary
    detail: >-
      The frozen document carrying the stale command. Its "Verification" block is the
      text to correct; the Makefile `verify` target already holds the correct spelling.
""", """  - type: manifest
    target: CLAUDE.md
    strength: enforced
    detail: >-
      ENFORCED at the M2 boundary sitting. The one-line fix landed at the M1 sitting
      (driver step 4d, D0113): CLAUDE.md:91 now spells the command
      `uv run lint-imports --config governance/importlinter.toml`, and CLAUDE.md carries a
      MANIFEST.sha256 row, so the CORRECTED bytes are what the seal pins — a regression to
      the vacuous spelling turns check_manifest red. tests/test_operating_manual.py (D0111)
      is the second detector and no longer tolerates this divergence by name.
"""),
"D0095": (one("decisions/0095-*.yaml"), """  - type: config
    target: governance/tag-roles.yaml#required_tags
    strength: documentary
    detail: >-
      The list as it stands, three entries and one milestone behind. DOCUMENTARY and that
      is the honest grade: the key exists and is consumed by check_tag_signers.py, but what
      this record proposes is not in it, so nothing here is enforced yet. Upgrades to an
      enforced binding when the owner applies either half at the sitting (D0045).
""", """  - type: config
    target: governance/tag-roles.yaml#required_tags
    strength: enforced
    detail: >-
      ENFORCED at the M2 boundary sitting, exactly as this binding's earlier text said it
      would be "when the owner applies either half". HALF (1) IS APPLIED: m1-laws-freeze
      and m1-close joined the list at the M1 sitting (commit c5d53c9), and the key is
      consumed by scripts/check_tag_signers.py, which fails "required tag missing" from
      both `make verify` and scripts/custodian.sh — so deleting a required tag is detected
      rather than silent (RT-15). HALF (2), replacing the enumeration with a derived rule
      — the half this record calls the one that matters more — is applied by NOTHING, which
      is why step 11 of every sitting still adds that boundary's tags by hand.
"""),
}

path, old, new = EDITS[WHICH]
src = path.read_text(encoding="utf-8")
if new.splitlines()[2].strip() in src and "ENFORCED at the M2 boundary sitting" in src:
    sys.exit(f"{WHICH}: already upgraded — nothing to do")
if src.count(old) != 1:
    sys.exit(f"{path}: the binding is not the expected text — apply by hand")
path.write_text(src.replace(old, new), encoding="utf-8")
print(path)
