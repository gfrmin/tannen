#!/usr/bin/env python3
"""check_decisions.py — decision records valid, bindings load-bearing, clocks computed.

Per BRIEF §9: decisions are append-only event records; bindings make them
load-bearing; CI fails if a binding's target is missing or skipped. This check:
  - validates every decisions/*.yaml against the decision-record schema;
  - enforces filename ↔ id agreement and id uniqueness;
  - resolves every binding (file exists / config key resolves / pytest node
    collects and is not skipped / path listed in MANIFEST.sha256);
  - flags unbound records as `unenforced` (acceptable only with a stated reason —
    the schema requires one, so a bare unbound record fails);
  - requires an owner signature on every Tier-C record that claims its door (BRIEF
    §9.2: affirmative signature only, never silence — RT-06);
  - computes Tier-B veto clocks (expiry transitions effective status mechanically;
    the record file is never edited);
  - enforces the ratchet (BRIEF §9.1 point 4): neither the unenforced count nor the
    Grade-P/S-pending residue may rise above the last digest's recorded metrics. Until
    M0 this was a digest flag only; decision D0020 said it hardens to a failure here at
    the M0 boundary, and it now has;
  - verifies the generated DECISIONS.md is fresh (input-hash header).

Exits non-zero on any violation.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import yaml

# Run under `python -I -P` (conferral ruling 3, D0063): isolated mode ignores
# PYTHONPATH, PYTHONHOME and user site-packages, and -P stops any directory being
# prepended to sys.path implicitly — including this script's own. The floor may depend
# only on tools the OS provides and paths named literally, so the one path this guard
# needs is named literally here, derived from __file__ rather than inherited.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _gov import (  # noqa: E402
    Failures,
    binding_strengths,
    input_hash,
    load_schema,
    load_yaml,
    parse_manifest,
    previous_metrics,
    ratchet_metrics,
    read_header_hash,
    receipt_state,
    resolve_dotted,
    schema_errors,
    verify_owner_signature,
    REPO_ROOT,
)

FILENAME_RE = re.compile(r"^(\d{4})-[a-z0-9]+(-[a-z0-9]+)*$")

#: Tier-C statuses that need no owner signature, because the record is not claiming the
#: door: it is queued, refused, or replaced. Every other status — `accepted`, and a
#: `provisional` that would consent by silence — asserts that a one-way door was walked
#: through, and BRIEF §9.2 says only the owner's key can assert that.
TIER_C_UNSIGNED_OK = ("blocked-on-owner", "rejected", "superseded")

#: A pytest binding may legitimately target a test that runs THIS script — that is how
#: "the guard is actually wired in" gets asserted. Resolving bindings inside such a run
#: would recurse for ever, so nested runs skip binding resolution and say so. The outer
#: run is the one that enforces; nothing is checked less, it is just not checked twice.
NESTED_ENV = "TANNEN_CHECK_DECISIONS_NESTED"

#: Distinct from None ("resolved, no problem"): the binding was not checked at all. A
#: guard that reports unchecked bindings as green is worse than one that says nothing
#: (RT-08) — `make verify` clears the variable so the honest path is the default one.
NOT_RESOLVED = object()

#: RT-M1-05 (2026-08-26 boundary red team): `pytest_violation` used to call a run "skipped"
#: only when NOTHING in it passed (`skipped and "passed" not in out`). A binding that names
#: a whole FILE — most of them do (see decisions/*.yaml) — can hold several test functions;
#: if ONE of them is skipped while its siblings pass, that condition never trips, the run
#: exits 0, and the binding is reported enforced/green even though the specific enforcement
#: the record cares about may be exactly the skipped one. `tests/test_conformance.py` has a
#: real, DESIGNED skip of this shape (an S-pending concept's vectors are legitimately absent
#: until the owner publishes them, D0009) and is bound at file granularity by D0087, so the
#: fix cannot simply be "any skip fails" without breaking a binding that was never broken.
#: The distinguishing fact is that a designed skip documents ITSELF: `pytest.skip(reason=…)`
#: carries why. Anything else that skips inside an otherwise-passing binding is treated as
#: unexplained and fails — a smuggled-in `pytest.mark.skip` has no such reason and nothing
#: about its presence looks different from ordinary output unless you go looking, which is
#: the whole problem this closes.
ALLOWED_SKIP_REASON_PREFIXES = ("S-pending: ",)

#: `pytest -rs` prints one line per skip in "short test summary info":
#: `SKIPPED [<count>] <file>:<line>: <reason>`. This is the only place a reason is visible
#: in captured stdout without switching to `-v` (which would also change the "N skipped"
#: counting line every other check here already parses).
_SKIP_REASON_RE = re.compile(r"^SKIPPED \[\d+\] [^:\n]+:\d+: (.*)$", re.MULTILINE)


def unexplained_skips(out: str) -> list[str]:
    """Skip reasons in a pytest run's output that are not on the allowed list."""
    return [
        reason for reason in _SKIP_REASON_RE.findall(out)
        if not reason.startswith(ALLOWED_SKIP_REASON_PREFIXES)
    ]


def binding_violation(root: Path, kind: str, target: str) -> str | None:
    if kind == "file":
        return None if (root / target).exists() else f"target does not exist: {target}"
    if kind == "manifest":
        manifest = root / "MANIFEST.sha256"
        if not manifest.exists():
            return "MANIFEST.sha256 does not exist"
        return None if target in parse_manifest(manifest) else f"not listed in MANIFEST.sha256: {target}"
    if kind == "config":
        if "#" not in target:
            return f"config target needs 'path#dotted.key': {target}"
        rel, dotted = target.split("#", 1)
        path = root / rel
        if not path.exists():
            return f"config file does not exist: {rel}"
        # A guard that raises where it could report is a guard that stops checking the
        # records after this one: one mis-typed binding would take the whole run down and
        # every later violation with it. Naming the file is also the useful answer, since a
        # config binding on something that is not TOML or YAML is a binding of the wrong
        # type — which is how this was found, on a `config` binding to .gitignore.
        try:
            if path.suffix == ".toml":
                data = tomllib.loads(path.read_text(encoding="utf-8"))
            else:
                data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (tomllib.TOMLDecodeError, yaml.YAMLError):
            return f"config file does not parse as {'TOML' if path.suffix == '.toml' else 'YAML'}: {rel}"
        if not isinstance(data, dict):
            return f"config file holds no mapping to resolve a key in: {rel}"
        try:
            resolve_dotted(data, dotted)
        except KeyError:
            return f"config key {dotted!r} does not resolve in {rel}"
        return None
    if kind == "pytest":
        return pytest_violation(root, [target], target)
    return f"unknown binding type: {kind}"


def run_pytest(root: Path, targets: list[str]) -> subprocess.CompletedProcess:
    """One pytest invocation. `sys.executable` is the interpreter this script already
    runs under (`uv run python scripts/check_decisions.py`), so this reuses the resolved
    environment instead of paying `uv run`'s resolution cost per binding."""
    return subprocess.run(
        [sys.executable, "-m", "pytest", *targets, "-q", "--no-header", "-rs",
         "-p", "no:cacheprovider"],
        cwd=root, capture_output=True, text=True, check=False,
        env={**os.environ, NESTED_ENV: "1"},
    )


def pytest_violation(root: Path, targets: list[str], label: str) -> str | None:
    run = run_pytest(root, targets)
    out = run.stdout + run.stderr
    if "no tests ran" in out or run.returncode == 4:
        return f"pytest node does not collect: {label}"
    if re.search(r"\b[1-9]\d* skipped\b", out) and " passed" not in out:
        return f"pytest node is skipped (a skipped binding is not enforcement): {label}"
    unexplained = unexplained_skips(out)
    if unexplained:
        return (
            f"pytest node has an unexplained skip inside an otherwise-passing run "
            f"(RT-M1-05: a whole-file binding with a mix of passed and skipped tests "
            f"reads as fully enforced) — {label}: {'; '.join(unexplained)}"
        )
    if run.returncode != 0:
        return f"pytest node fails: {label}"
    return None


def resolve_pytest_bindings(root: Path, targets: list[str]) -> dict[str, str | None]:
    """Resolve every pytest binding, batching the healthy case.

    All targets run in one invocation; only if that is not cleanly green does each
    target run alone, so a real violation is still attributed to the exact binding that
    caused it. The cost of the guard should not be a reason to stop binding decisions
    to tests.
    """
    if not targets:
        return {}
    if os.environ.get(NESTED_ENV):
        print(f"  pytest bindings: {len(targets)} NOT RESOLVED (nested run; the outer run "
              "enforces). If you did not expect a nested run, this variable is set in your "
              "ambient environment and binding enforcement is OFF (RT-08).")
        return {target: NOT_RESOLVED for target in targets}
    batch = run_pytest(root, targets)
    combined = batch.stdout + batch.stderr
    if batch.returncode == 0 and not re.search(r"\b[1-9]\d* skipped\b", combined):
        return {target: None for target in targets}
    return {target: pytest_violation(root, [target], target) for target in targets}


def check_ratchet(root: Path, today: dt.date, records: list[dict], fail: Failures) -> None:
    """The ratchet: visible debt may hold or fall, never rise (BRIEF §9.1, D0020).

    The baseline is the last digest strictly older than today, so a rise must appear in
    a digest — flagged, under "Requires owner" — before it can become the number the
    next session is measured against. With no earlier digest there is no baseline and
    nothing to enforce; that is stated, not silently skipped.
    """
    concept_paths = sorted((root / "concepts").glob("*.yaml"))
    concepts = [load_yaml(p) for p in concept_paths]
    unenforced, residue = ratchet_metrics(records, concepts)
    baseline = previous_metrics(root, today)
    if baseline is None:
        print(f"  ratchet: unenforced={unenforced} residue={residue} (no earlier digest to ratchet against)")
        return
    prev_date, prev_unenforced, prev_residue = baseline
    for name, now, before in (
        ("unenforced count", unenforced, prev_unenforced),
        ("Grade-P/S-pending residue", residue, prev_residue),
    ):
        if now > before:
            fail.add(
                f"RATCHET BREACH — {name} rose {before} → {now} since the {prev_date} digest; "
                "BRIEF §9.1 requires it to trend down. Bind the new record to the artifact "
                "that enforces it, or record why the debt is unavoidable (D0020)."
            )
    print(
        f"  ratchet: unenforced={unenforced} (was {prev_unenforced}), "
        f"residue={residue} (was {prev_residue}), baseline digest {prev_date}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--today", type=dt.date.fromisoformat, default=dt.date.today(),
                        help="override 'today' for veto-clock computation (tests)")
    args = parser.parse_args()
    root = args.root.resolve()
    fail = Failures("check_decisions")

    schema = load_schema(root, "decision-record.schema.json")
    record_paths = sorted((root / "decisions").glob("*.yaml"))
    if not record_paths:
        fail.add("no decision records found under decisions/")

    receipts_fresh, receipt_detail = receipt_state(root, args.today)
    print(f"  attention receipt: {'FRESH' if receipts_fresh else 'STALE'} — {receipt_detail}")

    seen_ids: set[str] = set()
    unenforced: list[str] = []
    clocks: list[str] = []
    tier_c_signed: list[str] = []
    tier_c_queued: list[str] = []
    valid_records: list[dict] = []
    pytest_bindings: dict[str, list[str]] = {}

    for path in record_paths:
        rel = path.relative_to(root)
        m = FILENAME_RE.match(path.stem)
        if not m:
            fail.add(f"{rel}: filename must be <seq>-<slug>.yaml")
            continue
        record = load_yaml(path)
        errors = schema_errors(record, schema)
        if errors:
            for err in errors:
                fail.add(f"{rel}: schema violation at {err}")
            continue
        rid = record["id"]
        if rid in seen_ids:
            fail.add(f"{rel}: duplicate decision id {rid}")
        seen_ids.add(rid)
        if rid != f"D{m.group(1)}":
            fail.add(f"{rel}: id {rid} does not match filename sequence {m.group(1)}")

        valid_records.append(record)

        for binding in record["bindings"]:
            if binding["type"] == "pytest":
                pytest_bindings.setdefault(binding["target"], []).append(str(rel))
                continue
            problem = binding_violation(root, binding["type"], binding["target"])
            if problem:
                fail.add(f"{rel}: binding does not resolve — {problem}")
        if not record["bindings"]:
            unenforced.append(f"{rid} ({record['title']}): {record['unenforced_reason']}")

        if record["tier"] == "C":
            # RT-06. Nothing used to stop a record granting itself a one-way door by
            # writing `accepted` in its own status field, and the digest surfaced Tier-C
            # records only while they said `blocked-on-owner` — so such a record was
            # invisible in every projection the owner reads. The signature is over the
            # record's whole bytes (D0063 ruling 2), which is why a later binding change
            # costs a re-signature: what was vouched for is the file, not a summary of it.
            if record["status"] in TIER_C_UNSIGNED_OK:
                tier_c_queued.append(rid)                # queued, refused or replaced
            elif verify_owner_signature(root, path, "tannen-decision"):
                tier_c_signed.append(rid)
            else:
                fail.add(
                    f"{rel}: Tier-C record accepted without an owner signature — "
                    f"{path.name}.sig is missing or does not verify as owner@tannen "
                    "under namespace tannen-decision. BRIEF §9.2: affirmative signature "
                    "only, never silence. Record it `blocked-on-owner` until the next "
                    "boundary sitting; nothing about that blocks other work."
                )

        if record["tier"] == "B" and record["status"] == "provisional":
            veto_by = dt.date.fromisoformat(record["veto_by"])
            days = (veto_by - args.today).days
            if days >= 0:
                clocks.append(f"{rid}: veto open, {days} day(s) remaining (until {veto_by})")
            elif receipts_fresh:
                clocks.append(f"{rid}: veto lapsed {-days} day(s) ago — effective status accepted (silence = consent under fresh receipt)")
            else:
                clocks.append(
                    f"{rid}: veto window passed {-days} day(s) ago but the attention receipt "
                    "is stale — BLOCKED, not consented (BRIEF §9.1; blocks accumulate)"
                )

    resolved = resolve_pytest_bindings(root, sorted(pytest_bindings))
    unresolved = sum(1 for v in resolved.values() if v is NOT_RESOLVED)
    for target, problem in resolved.items():
        if problem and problem is not NOT_RESOLVED:
            for rel in pytest_bindings[target]:
                fail.add(f"{rel}: binding does not resolve — {problem}")

    check_ratchet(root, args.today, valid_records, fail)

    projection = root / "DECISIONS.md"
    if record_paths:
        expected = input_hash(record_paths, root)
        actual = read_header_hash(projection)
        if actual is None:
            fail.add("DECISIONS.md missing or lacks the generated input-hash header — run make projections")
        elif actual != expected:
            fail.add("DECISIONS.md is stale (input-hash mismatch) — run make projections; never hand-edit")

    for line in clocks:
        print(f"  veto clock: {line}")
    for line in unenforced:
        print(f"  unenforced (visible debt): {line}")
    if tier_c_queued:
        print(f"  Tier-C doors queued to the next boundary sitting (non-blocking): "
              f"{', '.join(tier_c_queued)}")
    enforced_n, documentary_n = binding_strengths(valid_records)
    pytest_verdict = (
        f"{len(pytest_bindings)} pytest binding(s) NOT CHECKED (nested run)"
        if unresolved else f"{len(pytest_bindings)} pytest binding(s) green"
    )
    return fail.finish(
        f"{len(record_paths)} records valid; {pytest_verdict}; "
        f"{len(unenforced)} unenforced (with reasons); "
        f"{enforced_n} enforced / {documentary_n} documentary binding(s); "
        f"{len(clocks)} Tier-B clock(s) computed; "
        f"{len(tier_c_signed)} Tier-C door(s) owner-signed, {len(tier_c_queued)} queued; "
        "DECISIONS.md fresh"
    )


if __name__ == "__main__":
    sys.exit(main())
