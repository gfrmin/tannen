    # Installed at the M4 boundary sitting (D0205, D0229 item 4), beside the derivation that
    # retired the hand-maintained required_tags. Specs m0..m4 and every derived tag except
    # m3-close; the marker names the tag, so a failure for another missing tag cannot pass.
    # repo.bundle is generated at the sitting by the fixture's make-fixture.sh.
    ("check_tag_signers_derived",
     ["scripts/check_tag_signers.py", "--root", "tests/poison/tag-roles-derived",
      "--repo", "tests/poison/tag-roles-derived/repo.bundle"],
     "required tag missing: m3-close"),
