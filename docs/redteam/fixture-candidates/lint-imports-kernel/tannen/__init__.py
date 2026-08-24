"""Poison fixture: a `tannen` package that shadows the real one on PYTHONPATH.

The point of this fixture is that it is checked against the REPO'S OWN
`pyproject.toml` contracts — not a throwaway contract of its own. It therefore
proves that `kernel-no-io`, `kernel-no-clock` and `no-cross-repo` still have teeth,
which is what `tests/poison/lint-imports/` (a synthetic `poisonpkg` with a synthetic
contract) does not prove.

Module names mirror `src/tannen/` exactly, so an `ignore_imports` entry crafted to
excuse the real tree matches here too — and the contract then comes out KEPT, which
the custodian reports as "guard PASSED its poison — the guard is weakened".
"""
