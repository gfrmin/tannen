# The three owner-key edits, drafted

Each of these files is custody-set and/or in `required_signatures`, so none is applied
here: a builder edit would redden `check_manifest::check_custody` until the owner
re-signs, and the gate must stay green between now and the sitting. Apply at the sitting,
then `gen_custody.py` and re-sign.

---

## 1. `governance/policy.yaml` — two changes, one signature

### 1a. The external-surface clause

`external_surface.publishing: forbidden` is the clause D0115's signature has to change.
Replace with an explicit scope rather than a bare `allowed`, so the file keeps saying what
is and is not permitted:

```yaml
external_surface:
  # D0115 (owner-signed) and D0176: this repository is published at
  # github.com/gfrmin/tannen and developed in public. `publishing` names THIS repository
  # only — every other byte-leaving act stays a Tier-C door.
  publishing: this-repo-public
  cross_repo_prs: forbidden
  network_writes: captured-oracles-only
```

**Note for the record, and it is not a small one:** no guard reads this key. Grep at
`5f206cc` finds `external_surface.publishing` in prose and in the
`check-manifest-unsigned-policy` poison fixture, nowhere else. Its owner signature makes
the clause unforgeable; it does not stop a push. D0115 binds it `strength: enforced`,
which overstates what it does — recorded in D0176 rather than silently corrected, since
D0115's text is immutable under D0045.

### 1b. The citation-pin expectation

Required by patch `01`. It must live here rather than anywhere under `concepts/`, because
an expectation derived from the files it is checking lets a truncated registry agree with
itself:

```yaml
# Citation pins the concept registry must account for (D0115 mechanism (a), D0176).
# NOT derived from concepts/ — see scripts/check_concepts.py. Raise or lower this only
# when a concept record's `sources` list actually changes, and re-sign.
concept_registry:
  expected_citation_pins: 12
```

**`12` — but only AFTER you execute D0180's withdrawal, which is a step of this sitting.**
The tracked tree today has **13**: the fourth sibling's `source` entry is still present,
because withdrawing it is blocked until `patches/06` lands (D0181). Withdrawing it retires
one pin *and* one snapshot file together — `check_concepts.py`'s orphan check couples them,
and that coupling was watched biting rather than assumed.

So the ordering inside step 2 matters: **apply `patches/06`, execute the withdrawal, then
set this value to what you measure.** Setting `12` before the withdrawal reddens the guard
this patch exists to make honest.

Re-measure rather than trusting this line; the command is one grep:

```sh
grep -rh '      path: concepts/snapshots/' concepts/*.yaml | sort -u | wc -l
```

---

## 2. `governance/tag-roles.yaml` — the trust-root repin, and a lag to close

### 2a. `trust_root.object` (Tier-C door `trust-root-changes`)

The file pins the `brief-freeze` **tag object** hash, and the rewrite changes it. Measured
in the rehearsal: `c219e63819beb4052b326e47b9cbd5d208779cda` → a new hash not knowable
until `brief-freeze` is re-signed at the sitting.

```diff
 trust_root:
   tag: brief-freeze
-  object: c219e63819beb4052b326e47b9cbd5d208779cda
+  object: <the re-signed brief-freeze tag object, read off after step 6>
   signer: owner
```

This is the act the file itself calls "the one act that would otherwise redefine every
other check in the custody floor". It is being performed deliberately, under signature,
with the old value preserved here and in D0176.

### 2b. `required_tags` — the third recurrence, closed while the file is open

`git tag` lists 8; `required_tags` lists 7. `m3-laws-freeze` has been missing since it was
created (D0095 → D0154 item 6 → D0172 (C)).

```diff
 required_tags:
+  - m3-laws-freeze
   - m2-laws-freeze
   - m2-close
   - m1-laws-freeze
   - m1-close
   - m0-close
   - brief-freeze
   - m0-laws-freeze
```

Adding the entry is the smaller half. D0171 ruling (3) says no guard may depend on a
hand-maintained enumeration, and this list is one — but `required_tags` is the case where
derivation genuinely over-fires (a shallow clone has no tags to derive from, which is the
attack RT-15 describes). It is therefore ruling (3)'s "derive **and** assert" case, and
the deriving half is not attempted here: it is a guard change, and this package is already
asking for three signatures.

---

## 3. `.pre-commit-config.yaml` — optional, D0175's queued item

D0175 found the M3 red-team report's own home-path disclosure only after it was committed,
because `tests/test_no_pii.py` scans `git ls-files` and the file was untracked when the
suite ran. A pre-commit measurement of a tracked-file guard is a measurement of the
*previous* commit.

The fix is a hook that runs the tracked-file guards over the **staged** set. Not drafted
as a diff here because the shape depends on whether the owner wants the whole PII suite at
commit time or only the four assertion tests — D0112's rationale anticipated exactly this
choice and left it open ("If publication is approved (D0115) the owner may want it at
commit time as well — that is an addition to this, not a replacement").
