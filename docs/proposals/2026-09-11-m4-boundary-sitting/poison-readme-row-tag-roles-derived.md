
### Installed at the M4 boundary sitting: `tag-roles-derived/` (D0205, D0229 item 4)

`required_tags` lagged one milestone at every boundary for five boundaries, because it was a
hand list patched at step 11 of every sitting (D0095). It is now derived from the frozen specs,
and a non-empty hand list is refused. This fixture is the derivation's tooth: specs m0 to m4,
every derived tag present and correctly signed except `m3-close`. Its `repo.bundle` and
`allowed_signers` are generated at the sitting by `make-fixture.sh` (conferral ruling 6).

| Fixture | Guard | Intended violation | Marker |
|---|---|---|---|
| `tag-roles-derived/` | `scripts/check_tag_signers.py`, driven with `--root` and `--repo` | a tree whose specs require `m3-close` and whose tag set lacks it, while `governance/tag-roles.yaml` enumerates nothing | `required tag missing: m3-close` |
