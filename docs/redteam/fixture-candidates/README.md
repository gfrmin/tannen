# Poison fixture candidates — M0→M1 boundary red team (2026-08-24)

Drafts. **Staged outside `tests/poison/` on purpose**: the corpus is author-key
territory (BRIEF §9.1 Tier-C door `trust-root-changes`; CLAUDE.md hard rules), so the
builder drafts and the owner installs at the boundary sitting under the standing
exception recorded in BRIEF §9.1 point 5 ("red-team findings become poison fixtures").

Installing one is a `git mv` into `tests/poison/`, a row per file in `MANIFEST.sha256`,
a `poison` line in `scripts/custodian.sh`, and a row in `tests/poison/README.md`'s
table. Fixtures marked **needs patch** additionally require the guard change quoted
below them; installing those before the patch would leave the custodian permanently
red, which is the opposite of what a poison fixture is for.

Findings are `RT-nn` from `docs/redteam/2026-08-24-m0-boundary.md` (the M0→M1 pass) or
`RT-M1-nn` from `docs/redteam/2026-08-26-m1-boundary.md` (the M1 boundary pass), or
`RT-M2-nn` from `docs/redteam/2026-09-01-m2-boundary.md` (the M2 boundary pass). Rows are
appended without renumbering earlier ones.

---

## Status, 2026-09-04 — **this staging area is spent**

Every candidate below has been installed. The table is kept as the record of what each one
was drafted to prove and what was believed about it at drafting time; it is no longer a
queue, and its "Bites today?" column is answered in the past tense from here on. Where a
row's claim was falsified by the guard work that followed, the retraction is written into
the row rather than the row deleted — the wrong belief is part of what the fixture cost.

- **m0 boundary sitting** (`c64a5ba`, 2026-08-25): `check-decisions-nested-hatch/`,
  `check-decisions-ratchet/`, `check-decisions-unsigned-tier-c/`, `check-manifest-sealed/`,
  `check-manifest-unsigned-policy/`, `custodian-tag-signer/`, `lint-imports-kernel/`.
- **m1 boundary sitting** (`65b68a3`, 2026-08-31): `oracle-shadow/`,
  `check-decisions-file-skip/`.
- **m2 boundary sitting** (`25523a4`, 2026-09-03): `oracle-shadow-model/`.

What is left in this directory: `check-decisions-file-skip/rt-m1-05-check-decisions.patch`,
the drafted guard change whose fixture went ahead of it. The fixture directories themselves
are gone — `git mv`d into `tests/poison/`, where they are custody-set and author-key
territory. **Do not re-stage a fixture here that is already installed**; the copy would be
unsealed, unmanifested, and indistinguishable from a decoy.

The next pass's candidates append below the table as usual.

### Re-opened 2026-09-05 by the M2→M3 pass

One new candidate, `oracle-shadow-spoofed/`, plus its guard patch. The staging area is no
longer spent. Note the shape of the recurrence: `oracle-shadow-model/` was installed at the
M2 sitting on the belief that the derived map closed the class, and the row below records
that belief being retracted once already. It is now retracted a second time in a different
direction — the map is derived correctly, and the **identity test the map feeds** is what a
decoy defeats. Deriving *which* modules to check did not make *how* they are checked sound.

---

| Candidate | Guard poisoned | Closes | Bites today? |
|---|---|---|---|
| `lint-imports-kernel/` | `lint-imports` against the **repo's own** contracts | RT-02 | **yes** |
| `check-decisions-ratchet/` | `scripts/check_decisions.py` (ratchet sub-check) | RT-07, D0047 ask | **yes** |
| `check-decisions-nested-hatch/` | `scripts/check_decisions.py` (pytest bindings) | RT-08 | **yes** (pins the pytest-binding tooth; the hatch itself needs a call-site fix, not a fixture) |
| `check-manifest-sealed/` | `scripts/check_manifest.py` (sealed-paths check) | RT-01, RT-03, RT-13 | **yes** (patch landed, D0056) |
| `check-manifest-unsigned-policy/` | `scripts/check_manifest.py` (required-signature check) | RT-04 | **yes** (patch landed, D0056) |
| `check-decisions-unsigned-tier-c/` | `scripts/check_decisions.py` (Tier-C signature check) | RT-06 | **yes** — the guard landed 2026-08-25 (D0064); a `git mv` plus one manifest row |
| `custodian-tag-signer/` | `scripts/check_tag_signers.py` | D0049's open ask **and** RT-15 | **yes** — one bundle, two teeth (renamed from `custodian-tag-signer/`, 2026-08-25) |
| `check-decisions-file-skip/` | `scripts/check_decisions.py` (pytest bindings) | RT-M1-05 | **INSTALLED** 2026-08-31 → `tests/poison/check-decisions-file-skip/`; the guard patch landed with it at that sitting, so the qualifier below is spent and only `rt-m1-05-check-decisions.patch` remains staged here. As drafted: **yes against the drafted fix** (`ALLOWED_SKIP_REASON_PREFIXES`) — drafted and verified this session, **not committed**: `scripts/check_decisions.py` is a custody-set member (`governance/tier-c.yaml`), so landing it reddens `check_manifest.py`'s custody check, which cascades into D0063's own file-level binding on `tests/test_governance_scripts.py` and blocks pre-commit's `check-decisions` hook on every commit thereafter. The patch is queued for the owner to apply together with the custody re-signature at the M1 boundary sitting; this pins the tooth against the drafted, not-yet-live guard |
| `oracle-shadow/` | `src/tannen/laws/plugin.py`'s collection-time oracle check | RT-M1-01 | **yes** — the check already landed this session (`_oracle_shadow_problem`); this pins the tooth. Does not close the underlying naming hazard (queued) |
| `oracle-shadow-model/` | `src/tannen/laws/plugin.py`'s oracle check, **as widened by RT-M2-01** | RT-M2-01 | **INSTALLED** 2026-09-03 → `tests/poison/oracle-shadow-model/`, and it bites: exit 1 at collection, naming RT-M2-01 and `shadowed`. Exercised by `tests/test_governance_scripts.py::test_oracle_shadow_model_fails_its_poison` (D0141's binding, upgraded to *enforced* 2026-09-04). ~~needs patch: the shipped check pins the single name `_fragment` (plugin.py:50-51), so this fixture PASSES today~~ — **retracted**: D0142 replaced those two constants with `_frozen_oracles()`, which derives the map from `tests/laws/m*/_*.py` off the filesystem rather than enumerating names, so the widening cannot lag a milestone again. What remains true: M2 added `_model` and `_subject`, bare-imported across seven frozen law files, and `tests/` is not a sealed dir. Verified 2026-09-01: 34 tests pass against the decoy; with `check_differential` stubbed, L2.9 is vacuous and all 113 M2 law tests still pass with `check_manifest` clean. The plugin patch is builder-landable (no manifest row, not custody-set); installation under `tests/poison/` is owner work |
| `oracle-shadow-spoofed/` | `src/tannen/laws/plugin.py`'s oracle check, **as widened by RT-M3-04** | RT-M3-04 | **needs patch** — the shipped check compares `sys.modules[name].__file__` against the frozen path, and `__file__` is a plain attribute a decoy can set. Verified 2026-09-05 against the shipped check: the decoy reproduces the hole (`exit=0`, 14 passed) with `check_differential` — frozen L3.12, BRIEF §6's kill criterion — answered 1,400 times by a stub, 38 M3 law nodes green, 16 fresh evidence records, `check_manifest` clean and `tannen laws report` showing `L3.12 ok pass`. Against `rt-m3-04-plugin-code-identity.patch` it exits 1 naming `['check_differential']`, the clean tree stays green, and `oracle-shadow/` + `oracle-shadow-model/` both still bite. The patch is builder-landable (`plugin.py` is neither manifested nor custody-set); installation under `tests/poison/` is owner work |

---

## `lint-imports-kernel/` — the real contracts, poisoned

**Guard:** `lint-imports` (import-linter), driven by the repo's own `pyproject.toml`.

**Intended violation:** a package tree that shadows `tannen` on `PYTHONPATH` and
imports, from modules named exactly as the real ones, everything the three real
contracts forbid: `os`/`subprocess`/`pathlib`/`tempfile` (`kernel-no-io`),
`datetime`/`random`/`time`/`uuid` (`kernel-no-clock`), `pkm`/`proplang`
(`no-cross-repo`).

**Why it is needed:** `tests/poison/lint-imports/` builds a synthetic `poisonpkg` and
checks it against a synthetic contract in its own `pyproject.toml`. That proves
import-linter runs. It proves nothing about `kernel-no-io`, `kernel-no-clock` or
`no-cross-repo`, which is why RT-02 passes every guard. This fixture is checked
against `pyproject.toml` — the real file — so it goes silent exactly when the real
contracts are neutered, and the custodian then says *"guard PASSED its poison — the
guard is weakened"*.

**Marker(s)** — one `poison` line per contract, all against this one fixture:

| Contract | Marker |
|---|---|
| `kernel-no-io` | `tannen.kernel is not allowed to import os` |
| `kernel-no-clock` | `tannen.kernel is not allowed to import datetime` |
| `no-cross-repo` | `tannen is not allowed to import pkm` |

**Command that must exit non-zero** (run from the repo root):

```sh
env PYTHONPATH=tests/poison/lint-imports-kernel uv run lint-imports --config pyproject.toml
```

**Custodian lines to add:**

```sh
for marker in "tannen.kernel is not allowed to import os" \
              "tannen.kernel is not allowed to import datetime" \
              "tannen is not allowed to import pkm"; do
    poison lint-imports-kernel "$marker" \
        env PYTHONPATH=tests/poison/lint-imports-kernel uv run lint-imports \
        --config pyproject.toml
done
```

**Verified** (2026-08-24, against `8ad2087` in a throwaway worktree):

- unmodified contracts → exit 1, all three markers present;
- contracts neutered with `ignore_imports = ["tannen.kernel.* -> *"]` (a neutering that
  makes the *real* tree pass with a forbidden import planted in it) → exit 0,
  `Contracts: 3 kept, 0 broken` → custodian reports the guard as weakened.

**Known limit:** narrowing `source_modules` to a single module that this fixture also
carries (e.g. `tannen.kernel.refs`) still breaks the contract here, so that spelling of
RT-02 is not covered by any poison fixture. It is covered by the contract-shape check
in `check-manifest-sealed/`'s patch (see below) — the two are complementary.

---

## `check-decisions-ratchet/` — a rise the guard must refuse

**Guard:** `scripts/check_decisions.py` (`check_ratchet`).

**Intended violation:** two unbound (unenforced) decision records against a baseline
digest recording `unenforced=0`. The baseline is dated `2020-01-01` so it is always
strictly older than `--today`, whatever the real date is.

**Why it is needed:** D0047 asks for exactly this ("if wanted, a poison fixture for the
newly hardened ratchet sub-check"). The ratchet is today covered only by
`tests/test_governance_ratchet.py`, which is builder-editable and outside the custodian
matrix. RT-07 is the reason it matters: the baseline is a hand-editable comment in an
unmanifested, never-validated file.

**Marker:** `RATCHET BREACH`

**Command that must exit non-zero:**

```sh
uv run python scripts/check_decisions.py --root tests/poison/check-decisions-ratchet
```

**Verified** (2026-08-24): exit 1, message
`RATCHET BREACH — unenforced count rose 0 → 2 since the 2020-01-01 digest`.
Collateral (expected, per `tests/poison/README.md`): the fixture has no `DECISIONS.md`.

---

## `check-decisions-nested-hatch/` — a pytest binding that does not collect

**Guard:** `scripts/check_decisions.py` (`resolve_pytest_bindings`).

**Intended violation:** a record bound to `tests/this_test_file_does_not_exist.py::test_nothing`.

**Why it is needed:** the corpus has no fixture for the pytest-binding tooth at all —
`tests/poison/check-decisions/` only exercises a missing `file` target. And RT-08: with
`TANNEN_CHECK_DECISIONS_NESTED` set in the ambient environment, all 15 real pytest
bindings are skipped while the script still prints `15 pytest binding(s) green`.

**Marker:** `binding does not resolve`

**Custodian entry (installable today):**

```sh
poison check_decisions_pytest "binding does not resolve" \
    env -u TANNEN_CHECK_DECISIONS_NESTED \
    uv run python scripts/check_decisions.py --root tests/poison/check-decisions-nested-hatch
```

**Verified** (2026-08-24): with the hatch unset, exit 1 with the marker. With
`TANNEN_CHECK_DECISIONS_NESTED=1` set, exit 1 **without** the marker — the guard
skipped the binding entirely. That is RT-08, reproduced.

**On closing RT-08 — be honest about what is closable.** An inheritable environment
variable cannot be authenticated: any nonce, pid or token the parent passes to its child
is equally settable by whoever launched the parent. So there is no patch that makes the
`env TANNEN_CHECK_DECISIONS_NESTED=1 …` spelling of this fixture bite, and no poison
entry should promise one. Two changes close the part that is closable:

1. **Clear it at every top-level call site**, which removes the accidental case (a
   leftover export in the builder's shell) entirely and makes the deliberate case a
   visible diff to `Makefile` / `.pre-commit-config.yaml` / `scripts/custodian.sh`:

   ```make
   verify:
   	env -u TANNEN_CHECK_DECISIONS_NESTED uv run python scripts/check_decisions.py
   ```

2. **Stop reporting unresolved bindings as green** — in `scripts/check_decisions.py`,
   track them separately so the summary line cannot claim what it declined to check:

   ```python
   # resolve_pytest_bindings returns (results, unresolved)
   return fail.finish(
       f"{len(record_paths)} records valid; "
       f"{len(pytest_bindings) - len(unresolved)} pytest binding(s) green; "
       + (f"{len(unresolved)} NOT VERIFIED (nested run); " if unresolved else "")
       + ...
   )
   ```

   Today the line reads `15 pytest binding(s) green` in exactly the run where none of
   them was resolved. A transcript a reviewer reads should say so.

---

## `check-manifest-sealed/` — **needs patch** — a file inside a sealed directory with no manifest row

**Guard:** `scripts/check_manifest.py` (new `check_sealed_paths`).

**Intended violation:** `sealed/smuggled.txt` exists inside a directory declared sealed
by `governance/tier-c.yaml`, and carries no row in `MANIFEST.sha256`. `sealed/kept.txt`
is manifested, so the fixture also proves the check is not simply rejecting every
sealed directory.

**Why it is needed:** closes both halves of the biggest hole. RT-01: a manifest row can
be *deleted*, which unfreezes the path with no trace (7 of the 27 current rows have no
other protection, including two frozen M0 law files). RT-03: a file can be *added*
inside a frozen directory — `tests/laws/m0/conftest.py` with an autouse fixture is
enough to make a violating implementation pass its own frozen law. Sealing turns the
manifest from a whitelist of hashes into a seal over a directory. It also closes RT-13
once `governance/tier-c.yaml` is itself manifested.

**Marker:** `unmanifested file in sealed path`

**Command that must exit non-zero:**

```sh
uv run python scripts/check_manifest.py --root tests/poison/check-manifest-sealed
```

**Patch — `scripts/check_manifest.py`:**

```python
def check_sealed_paths(root: Path, fail: Failures) -> None:
    """A sealed directory is sealed, not a whitelist (RT-01, RT-03).

    MANIFEST.sha256 does not list itself and nothing enumerates what it *should*
    contain, so a row can be deleted (unfreezing the path) and a file can be added
    inside a frozen directory (changing what the frozen tests mean) with no trace.
    Under a seal, both are violations of the same rule: every file under a sealed
    directory carries a manifest row.
    """
    tier_c = load_yaml(root / "governance" / "tier-c.yaml") or {}
    sealed = (tier_c.get("frozen_paths") or {}).get("sealed_dirs") or []
    manifest = root / "MANIFEST.sha256"
    entries = parse_manifest(manifest) if manifest.exists() else {}
    for rel in sealed:
        base = root / rel
        if not base.is_dir():
            fail.add(f"sealed directory does not exist: {rel}")
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            key = path.relative_to(root).as_posix()
            if key not in entries:
                fail.add(
                    f"unmanifested file in sealed path: {key} — a sealed directory is "
                    "sealed, not a whitelist: rows may not be removed from it and files "
                    "may not be added to it (BRIEF §9.1 custody floor)"
                )
```

called from `main()` next to `check_frozen_files`, plus in `governance/tier-c.yaml`:

```yaml
frozen_paths:
  manifest: MANIFEST.sha256
  sealed_dirs:
    - tests/laws
    - tests/poison
    - governance/schemas
```

**And the companion contract-shape check** (same file, closing the `source_modules`
spelling of RT-02 that no fixture can reach):

```python
    # A contract's teeth are its shape, not just its forbidden list. Coverage of
    # tier-c.yaml's modules says nothing about WHO is checked or what is excused.
    for contract in contracts:
        cid = contract.get("id")
        if cid not in ("kernel-no-io", "kernel-no-clock", "no-cross-repo"):
            continue
        expected_source = ["tannen"] if cid == "no-cross-repo" else ["tannen.kernel"]
        if contract.get("type") != "forbidden":
            fail.add(f"import contract {cid} is not a 'forbidden' contract")
        if contract.get("source_modules") != expected_source:
            fail.add(
                f"import contract {cid} source_modules is "
                f"{contract.get('source_modules')!r}, expected {expected_source!r} — "
                "narrowing the source silently excuses the rest of the package"
            )
        for key in ("ignore_imports", "unmatched_ignore_imports_alerting"):
            if contract.get(key):
                fail.add(f"import contract {cid} carries {key} — a contract with "
                         "exceptions is not the contract tier-c.yaml declares")
```

**Two manifest rows the owner should add regardless of the patch:**
`governance/tier-c.yaml` (RT-13) and `MANIFEST.sha256`'s own signature (RT-01; see the
report's §RT-01 remedy).

---

## `check-manifest-unsigned-policy/` — **needs patch** — an owner artifact whose signature was deleted

**Guard:** `scripts/check_manifest.py` (new `check_custody_signatures`), mirrored in
`scripts/custodian.sh` check 4.

**Intended violation:** `allowed_signers` enrols `owner@tannen`, `governance/policy.yaml`
exists with a raised envelope and an opened external surface, and
`governance/policy.yaml.sig` is absent.

**Why it is needed:** RT-04. The custodian verifies the policy signature only
`if [ -f governance/policy.yaml.sig ]`, so `rm` on the signature returns the repo to
its pre-opening custody state, the custodian prints
`policy.yaml unsigned (expected before the opening sitting)` and exits 0, and every
Tier-C value in policy becomes builder-editable. D0048's premise — "the builder cannot
edit it — any edit invalidates the signature" — is true only while the signature is
required to exist.

**Marker:** `missing owner signature` — the shipped check is data-driven from
`tier-c.yaml`'s `required_signatures` rather than a hard-coded tuple, so the fixture
declares what it then deletes the signature for (updated 2026-08-25, D0056).

**Command that must exit non-zero:**

```sh
uv run python scripts/check_manifest.py --root tests/poison/check-manifest-unsigned-policy
```

**Patch — `scripts/check_manifest.py`** (imports `owner_key_enrolled` from `_gov`):

```python
#: Artifacts whose signature is not optional once the opening sitting has happened.
OWNER_SIGNED = ("governance/policy.yaml", "MANIFEST.sha256")


def check_custody_signatures(root: Path, fail: Failures) -> None:
    """Deleting a signature must not silently downgrade the custody floor (RT-04)."""
    if not owner_key_enrolled(root):
        return  # genuinely pre-opening; nothing has been signed yet
    for rel in OWNER_SIGNED:
        if (root / rel).exists() and not (root / f"{rel}.sig").exists():
            fail.add(
                f"owner signature missing while an owner key is enrolled: {rel}.sig — "
                "the custody floor may not be lowered by deleting a signature"
            )
```

**Companion patch — `scripts/custodian.sh` check 4** (owner-applied; trust root):

```sh
# 4. Policy signature. Optional only while no owner key is enrolled: once the opening
#    sitting has happened, an ABSENT signature is a downgrade, not a pre-state (RT-04).
owner_enrolled=0
grep -qE '^owner@tannen[[:space:]]' allowed_signers && owner_enrolled=1
if [ -f governance/policy.yaml.sig ]; then
    ...existing verify...
elif [ "$owner_enrolled" -eq 1 ]; then
    bad "governance/policy.yaml.sig is absent but owner@tannen is enrolled — the custody floor was lowered"
else
    say "policy.yaml unsigned (expected before the opening sitting)"
fi
```

---

## `check-decisions-unsigned-tier-c/` — a Tier-C door walked through by assertion

**Guard:** `scripts/check_decisions.py` (new Tier-C signature check).

**Intended violation:** a `tier: C` record with `status: accepted`, an unremarkable
title, no `risk_flags`, and no owner signature — deciding to publish bytes and to depend
on another constellation repo.

**Why it is needed:** RT-06. BRIEF §9.2 says Tier C is "AFFIRMATIVE owner signature
only, never silence". No artifact checks that. `check_decisions` treats tier `C` like
any other value of an enum, and `gen_projections.gen_digest` surfaces Tier-C records
only when their effective status is `blocked-on-owner` — so a Tier-C record that says
`accepted` appears in no section of the owner's digest at all.

**Marker:** `Tier-C record accepted without an owner signature`

**Command that must exit non-zero:**

```sh
uv run python scripts/check_decisions.py --root tests/poison/check-decisions-unsigned-tier-c
```

**Verified** (2026-08-24): before the patch this command exited 1 for the *wrong* reason
(missing `DECISIONS.md`) and the marker was absent — the fixture reproduced the hole.

**Verified** (2026-08-25, after D0064 landed the guard): exit 1 with the marker present,
alongside the pre-existing `DECISIONS.md` failure. Ready to install as a `git mv`.

**Patch — LANDED 2026-08-25 (D0064).** Shipped shape differs from the draft below in
two ways: the verification call moved to `_gov.verify_owner_signature`, which requires
`-I` and `-n` so no call site can drop the arguments that would make it vacuous; and the
exempt statuses are a named constant, `TIER_C_UNSIGNED_OK`. The draft, for the record:

```python
        # Tier C is affirmative signature only (BRIEF §9.2). A record cannot grant
        # itself a one-way door by writing `accepted` in its own status field.
        if record["tier"] == "C" and record["status"] not in ("blocked-on-owner", "rejected", "superseded"):
            sig = path.with_name(path.name + ".sig")
            verified = sig.exists() and subprocess.run(
                ["ssh-keygen", "-Y", "verify", "-f", str(root / "allowed_signers"),
                 "-I", "owner@tannen", "-n", "tannen-decision", "-s", str(sig)],
                input=path.read_bytes(), capture_output=True,
            ).returncode == 0
            if not verified:
                fail.add(
                    f"{rel}: Tier-C record accepted without an owner signature "
                    f"({sig.name} missing or not verifying under namespace "
                    "tannen-decision) — BRIEF §9.2: affirmative signature only, never silence"
                )
```

**Companion digest patch — `scripts/gen_projections.py`: LANDED with it.** Surfacing
*every* Tier-C record in the owner queue, not only `blocked-on-owner` ones — the queue
was defined by absence, so the unsigned claim was the one case it never showed. Shipped
with two additions: each line states whether the record is `owner-signed` or `UNSIGNED`,
and the decision `.sig` files joined the digest's input hash, or a signature appearing or
vanishing would change what the digest says while leaving it "fresh". Draft:

```python
    for rec in records:
        if rec["tier"] == "C":
            owner_items.append(
                f"**{rec['id']}** [{effective_status(rec, today, receipts_fresh)}] "
                f"{rec['title']}: {rec['decision'].strip().splitlines()[0]}"
            )
```

---

## `custodian-tag-signer/` — **needs the owner to build it** — a builder-signed close tag

**Guard:** `scripts/custodian.sh` check 3 (signer principal ↔ tag kind).

**Intended violation:** a `*-close` tag signed by `builder@tannen`. D0049 decided close
tags stay owner-signed because the builder already mints the `*-laws-freeze` tags that
*start* the consent clock; letting it mint the closes would let the measured party
control both ends of the measurement.

**Why it cannot be a directory of files:** the violation is a signed git object. The
fixture is therefore a git bundle. `make-fixture.sh` in this directory builds it; the
red team must not create tags, and the builder key is needed, so **the owner runs it
once at the sitting** and commits `repo.bundle` next to it.

**Marker:** `milestone close tag is not owner-signed`

**Command that must exit non-zero** — this requires check 3 to be callable against an
arbitrary repo, i.e. extracting it from `custodian.sh` into `scripts/check_tags.sh`
(taking `--root` and `--signers`), which the custodian then calls twice: once on the
real repo, once on the fixture:

```sh
tmp=$(mktemp -d) && git clone -q tests/poison/custodian-tag-signer/repo.bundle "$tmp/repo"
bash scripts/check_tags.sh --root "$tmp/repo" \
    --signers tests/poison/custodian-tag-signer/allowed_signers
```

The check-3 body itself is already drafted by the parent session at
`docs/proposals/2026-08-24-custodian-close-tag-signer.md`; this directory supplies the
fixture that proposal says it needs.

---

## Findings with no fixture (guard/Makefile change only)

**RT-05 (forged evidence).** No poison fixture closes this: the store is a directory,
and a fixture proving "a hand-written record is accepted" would have to be accepted to
be installed. The closing change is two lines of `Makefile`, making the gate's report
see only records the gate's own run produced:

```make
verify:
	uv run python scripts/check_manifest.py
	uv run python scripts/check_concepts.py
	uv run python scripts/check_decisions.py
	rm -rf .verify-evidence
	TANNEN_EVIDENCE_ROOT=$$PWD/.verify-evidence uv run pytest -q
	TANNEN_EVIDENCE_ROOT=$$PWD/.verify-evidence uv run tannen laws report
	uv run lint-imports
	bash scripts/custodian.sh --check-only
```

With that, `tannen laws report` inside `make verify` can only be green if this run's
pytest actually produced the records — pre-seeded or hand-written evidence in
`evidence/` is invisible to the gate. The persistent `evidence/` store keeps its
role as the accumulating stream for graduated autonomy (BRIEF §9.2); it just stops
being the thing the gate trusts.

**RT-15 (deleting tags erases the trust root and the consent clock).** Confirmed against
`ca48a8b`, i.e. against `scripts/check_tag_signers.py` as it shipped: with every tag
deleted the guard prints `trust root: brief-freeze does not exist yet (nothing to pin)`
and `0 tag(s); every signer matches its tag class`, and the custodian says
`custody floor intact`. The fixture is the same shape as `custodian-tag-signer/` — a
`repo.bundle` the owner generates, here simply with the tags stripped — so the two
should share one generator rather than getting two. The guard change it pins:

```python
def check_trust_root(repo: Path, pin: dict, fail: Failures, *, required: bool) -> None:
    tag = pin["tag"]
    if git(repo, "rev-parse", "-q", "--verify", f"refs/tags/{tag}").returncode != 0:
        if required:
            # Absent is "not created yet" only before the opening sitting. Afterwards it
            # is a deletion, and it takes bless_epoch and the receipt clock with it.
            fail.add(f"trust root missing: {tag} (an owner key is enrolled, so it exists)")
        else:
            print(f"  trust root: {tag} does not exist yet (nothing to pin)")
        return
    ...


# in main(), alongside the roles table:
for tag in table.get("required_tags", []):
    if git(repo, "rev-parse", "-q", "--verify", f"refs/tags/{tag}").returncode != 0:
        fail.add(f"required tag missing: {tag} — the tag set is not optional (RT-15)")
```

with `governance/tag-roles.yaml` gaining `required_tags: [brief-freeze, m0-laws-freeze]`
and, itself, a `MANIFEST.sha256` row.

**RT-09 (the descriptor does not address the harness).** A one-line widening in
`src/tannen/laws/discovery.py`, but `discovery.py` is inside `src/tannen`, so changing
it moves every descriptor and invalidates all existing evidence — deliberately. The
change belongs at the start of M1, not retrofitted at the boundary:

```python
HARNESS_FILES = (Path("conftest.py"), Path("pyproject.toml"))


def implementation_subject(root: Path) -> str:
    sources = {
        path.relative_to(root).as_posix(): ref_for_bytes(path.read_bytes())
        for path in sorted((root / IMPLEMENTATION_DIR).rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }
    # The harness decides how hard a law was tested (hypothesis profile, deadlines,
    # dependency pins). Evidence earned under one harness is not evidence under
    # another, so the harness is part of the subject.
    sources.update({
        rel.as_posix(): ref_for_bytes((root / rel).read_bytes())
        for rel in HARNESS_FILES if (root / rel).is_file()
    })
    sources.update({
        p.relative_to(root).as_posix(): ref_for_bytes(p.read_bytes())
        for p in sorted((root / LAWS_DIR).rglob("conftest.py"))
    })
    return content_address(sources)
```

Note the `rglob("*")` change: it also brings non-`.py` files under `src/tannen` into
the subject, which today are invisible to it.

---

## `check-decisions-file-skip/` — a skip hidden inside an otherwise-passing file binding

**Guard:** `scripts/check_decisions.py` (`pytest_violation`).

**Intended violation:** a record bound to a whole test FILE holding one passing test
and one `pytest.mark.skip`-ed test whose reason is not on the allow-list. This is the
common shape of a real binding in this repo — most pytest bindings in `decisions/*.yaml`
name a file, not a single node (`docs/redteam/2026-08-26-m1-boundary.md`, RT-M1-05).

**Why it is needed:** `check-decisions-nested-hatch/` proves the guard notices a binding
that does not collect at all; nothing in the corpus proves it notices a binding that
*partly* runs while its file, as a whole, exits 0. Before RT-M1-05's fix this fixture's
`check_decisions.py` run was **fully green**.

**Marker:** `unexplained skip`

**Command that must exit non-zero (against the drafted, not-yet-committed fix):**

```sh
uv run python scripts/check_decisions.py --root docs/redteam/fixture-candidates/check-decisions-file-skip
```

**Not installable yet.** Installing this fixture under `tests/poison/` before the fix
lands would leave the custodian permanently red against the *shipped* guard, exactly the
condition the fixture-marking convention above ("needs patch") exists to prevent. This
row stays a draft until the owner applies the patch at the boundary sitting.

**Verified** (2026-08-26, against the drafted fix applied locally, then reverted —
`scripts/check_decisions.py` itself was not committed with the fix; see the M1 boundary
report's RT-M1-05 section for why):

```
check_decisions: FAIL (1 violation(s))
  - decisions/0001-poison-file-skip.yaml: binding does not resolve — pytest node has an
    unexplained skip inside an otherwise-passing run (RT-M1-05: a whole-file binding with
    a mix of passed and skipped tests reads as fully enforced) — tests/test_mixed.py: the
    enforcement this binding claims never actually runs
```

**Verified against the pre-fix guard** (reverting `pytest_violation` to the M0 form):
exit 0, `check_decisions: OK — 1 records valid; 1 pytest binding(s) green; …`.

**Known limit:** the fix's allow-list (`ALLOWED_SKIP_REASON_PREFIXES = ("S-pending: ",)`)
is intentionally narrow — it exists so `tests/test_conformance.py`'s designed
S-pending skip (D0009) does not regress into a false positive. A future designed skip
with a different reason prefix needs its own allow-list entry; this fixture does not
by itself prevent the allow-list from being widened carelessly (that is an ordinary code
review question, not a guard-liveness one).

---

## `oracle-shadow/` — the L1.16 oracle module answers to a name, not an identity

**Guard:** `src/tannen/laws/plugin.py`'s `LawEvidencePlugin.pytest_collection_modifyitems`
(the `_oracle_shadow_problem` check added this session).

**Intended violation:** a decoy `_fragment.py`, faithfully re-exporting the real frozen
oracle's names, primed into `sys.modules['_fragment']` by a `-p`-loaded bootstrap plugin
BEFORE `tests/laws/m1/test_l1_duckdb.py` is collected — so the frozen file's bare
`import _fragment as F` receives the decoy instead of `tests/laws/m1/_fragment.py`
(`docs/redteam/2026-08-26-m1-boundary.md`, RT-M1-01). Run against the **real** frozen
law file, the same way `lint-imports-kernel/` runs against the real import contracts,
so it goes silent exactly when the check is neutered.

**Why it is needed:** this is the one M1 finding that reaches BRIEF §6's kill criterion
directly, and without touching a single frozen or manifested byte. No fixture in the
corpus exercises `sys.modules` name-collision at all.

**Marker:** `RT-M1-01`

**Command that must exit non-zero** (run from the repo root):

```sh
env PYTHONPATH=docs/redteam/fixture-candidates/oracle-shadow \
    uv run pytest -p bootstrap_shadow tests/laws/m1/test_l1_duckdb.py \
    -k test_l1_16_the_catalogue_covers_every_operator_of_the_fragment -q
```

**Verified** (2026-08-26): with the check in place, the run aborts via `pytest.exit`
naming `RT-M1-01` and the actual (shadow) vs. expected (frozen) paths; with the check
commented out, the same command exits 0, `1 passed`, silently.

**Known limit — this fixture proves the DEFENCE, not a closure of the underlying
hazard.** The bare `import _fragment as F` in the frozen `test_l1_duckdb.py` is still
collision-prone; this check only catches the one shadow shape reachable through that
exact name. A package-qualified import in the frozen file (superseding, per CLAUDE.md,
since the file is frozen) is the actual fix and needs the owner's key — see RT-M1-01 in
the M1 boundary report for the specific rewrite proposed.
