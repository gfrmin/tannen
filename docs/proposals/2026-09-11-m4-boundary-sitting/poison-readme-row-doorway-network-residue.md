
### Installed at the M4 boundary sitting: `doorway-network-residue/` (RT-M4-02, D0248)

The shell's IO doorway, derived. Frozen L4.9 scans the shell against a hand-written network
set and never looks at `subprocess` or `os`; `lint-imports`' `kernel-no-io` contract forbids
both, but its `source_modules` is `tannen.kernel` alone. `scripts/check_doorway.py` derives the
network set from each import's static closure and refuses shell-outs by AST, outside the named
doors. L4.9's own scanner finds nothing in this tree, which is the finding.

| Fixture | Guard | Intended violation | Marker |
|---|---|---|---|
| `doorway-network-residue/` | `scripts/check_doorway.py`, driven with `--root` | a miniature `src/tannen/` whose shell modules read the world outside `tannen.oracles`: subprocess and `os` shell-outs, and socket-reaching stdlib modules absent from L4.9's list, beside controls that must stay silent | `reads the world outside the doorway` |
