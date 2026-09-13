
# --- M4 DRAFT HUNK: check_tag_signers, derived (D0205, D0229 item 4) ---------
# required_tags is derived from the frozen specs (D0205), so a hand list can no longer lag.
# The fixture carries specs m0..m4 and every derived tag, correctly signed, EXCEPT m3-close.
# The marker names the tag rather than the phrase, so a run failing for some OTHER missing
# tag cannot pass as this one. repo.bundle and allowed_signers are generated at the sitting
# by the fixture's make-fixture.sh with a key that exists only inside it (conferral ruling 6).
poison check_tag_signers_derived "required tag missing: m3-close" \
    "$PY" -I -P scripts/check_tag_signers.py \
    --root tests/poison/tag-roles-derived --repo tests/poison/tag-roles-derived/repo.bundle
# --- end M4 DRAFT HUNK: check_tag_signers, derived ---------------------------
