# Proposal: the shell reads the world only through the doorway (RT-M4-02)

**Status:** drafted for the M4 boundary sitting, **step 1 — the sitting's first item** (D0246 A2).
It closes the owner-key half of RT-M4-02 and is D0229 item (2). Design record: D0248.
The superseding frozen L4.9 that should derive from this guard is **not** here. It defers to M5
Session A for D0241's reason: a successor law has no legal home inside M4.

## What is broken today

Frozen L4.9 (`tests/laws/m4/test_l4_doorway.py`) is the shell's only doorway check. Its network
set is a hand-written literal, and it never scans `subprocess` or `os`. `lint-imports`'
`kernel-no-io` forbids those modules, but its `source_modules = ["tannen.kernel"]` never reaches
the shell. Measured: L4.9's own scanner, run over `doorway-network-residue/`, reports `[]` for a
tree that shells out to `curl` twice and imports `imaplib`, `xmlrpc.client`, `poplib` and
`socketserver`. `make verify` is green over that tree, so today green does not mean "no IO".

## The rule

`scripts/check_doorway.py` reads `src/tannen/**/*.py` by AST and checks two things.

- **Network.** An import is refused outside the network doors when its module-level static
  import closure reaches a seed in `{socket, _socket, ssl, _ssl}`. The set of network modules is
  derived, not listed (D0171 ruling (3), D0211). The seeds are the one constant, and they are the
  OS socket primitives rather than a list of protocols.
  - The closure is resolved without importing anything: `find_spec` is used only for top-level
    names, and submodules are found on disk.
  - It follows `if`/`try` and class bodies, which run at import, but not function bodies.
- **Process.** Outside the process doors, the guard refuses two things:
  - an import of `subprocess`, `multiprocessing` or `pty`;
  - any use of `os.system|popen|exec*|spawn*|posix_spawn*|fork*`, whether as an attribute or via
    `from os import`.

  A child process reads the world through any binary on PATH, so no closure can bound it.

A second, independent layer is the import-linter contract `shell-no-subprocess`. It is a
`forbidden` contract over `source_modules = ["tannen"]` forbidding the same three modules, with
no `ignore_imports`. It pins `tier-c.yaml`'s new `forbidden_imports.process_modules` list under
D0016. Its `expected_sources` row in `check_manifest.py` lands at step 3
(`check-manifest-shell-contract.patch`), because every edit to that file must share one step
(D0243's hash detector).

## Doors, each with its reason

| Door | Rules | Reason |
|---|---|---|
| `tannen.oracles` | network, process | the doorway itself (BRIEF §5.3) |
| `tannen.r2` | network, process | the store's R2 transport, not a way to read the world (L4.9's own door) |
| `tannen.laws` | **network only** | The evidence runner. With the door removed, exactly three imports in the shell reach a socket, and all three are here: `hypothesis`, `pytest` (plugin.py) and `jsonschema` (evidence.py). It is runner-side, which is L4.9's reason for its clock door. It has no reason to spawn, so the process rule still scans it. |

## What it does not claim

- **Dynamic imports.** `importlib.import_module` and `__import__` with a computed name are not
  scanned. `tannen.cli` loads the operator's pipeline module that way; that code is the
  operator's, not this package's.
- **Other environments.** The closure is resolved against the interpreter running the guard,
  `.venv/bin/python -I -P` at the gate. Positive controls refuse to give a verdict if the
  derivation stops seeing `imaplib`/`http.client` as network, or starts seeing
  `os`/`pathlib`/`json` as network.
- **Native code.** Anything reached through `ctypes`, `cffi` or a C extension.

## Measurements (2026-09-13, the venv interpreter, scratch clone of `5762439`)

- Real tree: `check_doorway: OK — 34 module(s) scanned`, in 1.9s.
- Derived closure:
  - reaches a socket: `imaplib`, `poplib`, `socketserver`, `xmlrpc.client`, `smtplib`,
    `http.client`, `urllib.request`, `asyncio`, `multiprocessing`, `hypothesis`, `pytest`;
  - does not: `os`, `pathlib`, `json`, `hashlib`, `yaml`, `logging`, `tempfile`, `uuid`,
    `tomllib`, `urllib.parse`, `email.utils`, `importlib.metadata`, `subprocess`.
- `subprocess`, `multiprocessing`, `pty`, `os.system`/`popen`/`exec*`/`spawn*`/`fork*` appear
  nowhere in `src/tannen`, so the whole-package contract is green today.
- With `doorway-guard.patch` applied:
  - `lint-imports --config governance/importlinter.toml` reports `Contracts: 4 kept, 0 broken`;
  - frozen L4.9 still passes (`5 passed`), because its clock set is derived from
    `kernel-no-clock` by id and is untouched;
  - `tests/test_check_doorway.py` gives `14 passed`.
- `check_manifest` after the patch, before the sitting regenerates anything, reports exactly
  these, and nothing else:
  - `frozen path modified: governance/importlinter.toml` and `… governance/tier-c.yaml`
    → `regen_manifest_row` both at step 1;
  - `custody drift: scripts/check_doorway.py is declared in the custody set but absent …`, plus
    drift on `Makefile`, `importlinter.toml` and `tier-c.yaml` → step 7's `gen_custody` and
    signature.

## Watched failing

| # | What was run | Verdict |
|---|---|---|
| 1 | Frozen L4.9's scanner over the fixture tree | `[]` — the defect, demonstrated |
| 2 | The guard over the fixture | FAIL, exactly 6 violations, one per payload; the 3 control files silent |
| 3 | The guard over the real tree | OK, 34 modules |
| 4 | Mutation: `SEEDS = frozenset()` | FAIL on the positive control (`imaplib cannot reach a socket`), and no verdict given |
| 5 | Mutation: `hypothesis` added to `MUST_NOT_REACH` | FAIL on the over-approximation control |
| 6 | Mutation: `tannen.laws` removed from the network doors | FAIL, naming jsonschema, pytest and hypothesis — the door's contents measured, not asserted |
| 7 | `os.system("curl x")` planted in a copy of the real `executor.py` | FAIL, `tannen.executor uses os.system` |
| 8 | An empty `--root` | FAIL, `a scan over nothing passes everything` |
| 9 | `shell-contract` row applied with step 1 declined (no contract) | FAIL, `import contract 'shell-no-subprocess' is missing` — so the driver applies that row only if step 1 was kept |

## What the sitting installs, and in what order

1. **Step 1:** `git apply doorway-guard.patch`. It adds `scripts/check_doorway.py`,
   `tests/test_check_doorway.py`, the Makefile `verify` line, the `tier-c.yaml` custody row plus
   `guard_enforced` row plus `process_modules`, and the importlinter contract. Then
   `regen_manifest_row` for `governance/tier-c.yaml` and `governance/importlinter.toml`. To
   decline: `git checkout -- Makefile governance/tier-c.yaml governance/importlinter.toml` and
   `rm -f scripts/check_doorway.py tests/test_check_doorway.py`.
2. **Step 3:** `check-manifest-shell-contract.patch`, only if step 1 was kept. It applies cleanly
   over the envelope patch (checked).
3. **Step 5:** `git mv docs/redteam/fixture-candidates/doorway-network-residue tests/poison/`, plus
   its manifest rows, its `tests/poison/README.md` row, and the `POISON` row:
   ```python
   ("check_doorway",
    ["scripts/check_doorway.py", "--root", "tests/poison/doorway-network-residue"],
    "reads the world outside the doorway"),
   ```
4. **Step 6:** the custodian hunk:
   ```
   poison check_doorway "reads the world outside the doorway" \
       "$PY" -I -P scripts/check_doorway.py --root tests/poison/doorway-network-residue
   ```

## The fixture obligation (D0246 A4)

The record that closes RT-M4-02 must account for `doorway-network-residue`. This guard is the
first half of that close, so the sitting installs the fixture in the same pass (step 5). The
finding stays open until the superseding L4.9 lands at M5 Session A. That law should derive its
forbidden set from this guard's rule rather than from a literal.
