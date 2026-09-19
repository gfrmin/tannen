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
  - verifies the generated DECISIONS.md is fresh (input-hash header, and its receipt line
    against receipts/), and that it stores no attention-receipt verdict — the verdict moves
    with the clock and the tag set, so it is printed here and rendered in the dated digest
    only (D0215);
  - honours a per-binding retirement (`retires_bindings`, D0181): a `type: file` binding
    whose target was legitimately deleted resolves iff an ACCEPTED record retires exactly
    that (record, target) pair, the binding is DOCUMENTARY, and the target is still
    absent — and prints every retirement it honours.

Three ways to resolve a `pytest` binding (D0266 item 2; D0267 ruling 3 — commit hooks are
structural, CI is the gate): the default spawns pytest itself, batching every binding into
one invocation; `--collect-only` checks that a bound node still collects and nothing more
(cheap enough for the pre-commit hook; a red-but-collecting node is CI's to catch, not the
hook's); `--pytest-report FILE` reads a prior `pytest --junitxml=FILE` run instead of
spawning a second one over the same nodes (the gate's own run, Makefile order: pytest,
then this guard).

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
    receipt_line,
    receipt_state,
    resolve_dotted,
    schema_errors,
    verify_owner_signature,
    REPO_ROOT,
    STORED_VERDICT_RE,
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


def frozen_paths(root: Path) -> frozenset[str]:
    """Where an xfail may stand for a retirement: every MANIFEST.sha256 path, plus each node
    governance/xfail-retirements.yaml lists by exact id (RT-M5-04)."""
    manifest = root / "MANIFEST.sha256"
    paths = set(parse_manifest(manifest)) if manifest.is_file() else set()
    listed = root / "governance" / "xfail-retirements.yaml"
    if listed.is_file():
        paths |= {entry["node"] for entry in (load_yaml(listed) or {}).get("retired") or []}
    return frozenset(paths)


#: `-rx` adds one line per xfail: `XFAIL <nodeid> - <reason>`.
_XFAIL_RE = re.compile(r"^XFAIL (\S+)", re.MULTILINE)


def unfrozen_xfails(out: str, frozen: frozenset[str]) -> list[str]:
    """Xfailed nodes outside a frozen file. A strict xfail is a sanctioned retirement only
    where a builder cannot write one: in a MANIFEST.sha256 path (RT-M5-04)."""
    return [node for node in _XFAIL_RE.findall(out)
            if node.split("::")[0] not in frozen and node not in frozen]


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
        return pytest_violation(root, [target], target, frozen_paths(root))
    return f"unknown binding type: {kind}"


def collect_retirements(root: Path, record_paths: list[Path],
                        fail: Failures) -> dict[tuple[str, str], str]:
    """{(retired record id, target): retiring record id} from every record's
    `retires_bindings` (D0181), read in a pass of its own BEFORE bindings resolve —
    records resolve in sequence order and the retiring record is, by construction, later
    than the one it retires.

    Why this exists: any record may bind to a path, and nothing stops that path being
    legitimately retired later. D0045 makes the record immutable and `binding_violation`
    resolves a file binding by bare existence, so without this every such retirement is a
    permanent red — measured on D0115's binding to a snapshot the owner ruled deleted,
    where one dangling binding also took down every record bound to the governance test
    suite (3 violations, not 1).

    Four refusals keep the mechanism from becoming the hole it patches. Honoured only from
    an `accepted` record: a provisional or blocked record cannot quietly satisfy another
    record's binding. Only for a `documentary` binding — checked at the binding, in main():
    an enforced binding is the record's claim on reality, and if reality moved the owner
    re-issues the record. A retirement whose target still EXISTS is a violation: a dormant
    retirement would silently cover a future deletion of the same path — species I of
    D0116's taxonomy arriving through the door built to close species I. And every
    honoured retirement is printed, so nothing resolves invisibly.
    """
    retirements: dict[tuple[str, str], str] = {}
    for path in record_paths:
        record = load_yaml(path)
        if not isinstance(record, dict) or not record.get("retires_bindings"):
            continue
        rel = path.relative_to(root)
        rid = record.get("id", path.stem)
        for entry in record["retires_bindings"]:
            if not isinstance(entry, dict) or not {"record", "target"} <= entry.keys():
                continue   # malformed: the schema check in main() reports it
            if record.get("status") != "accepted":
                fail.add(
                    f"{rel}: retires a binding of {entry['record']} but is "
                    f"{record.get('status')!r}, not accepted — only an accepted record may "
                    "retire another record's binding"
                )
                continue
            if (root / entry["target"]).exists():
                fail.add(
                    f"{rel}: stale retirement — {entry['target']} still exists, so the "
                    f"binding of {entry['record']} it retires is not dangling; a retirement "
                    "that outlives its reason would silently cover the NEXT deletion of "
                    "that path (D0116 species I)"
                )
            retirements[(entry["record"], entry["target"])] = rid
    return retirements


def run_pytest(root: Path, targets: list[str]) -> subprocess.CompletedProcess:
    """One pytest invocation. `sys.executable` is the interpreter this script already
    runs under (`uv run python scripts/check_decisions.py`), so this reuses the resolved
    environment instead of paying `uv run`'s resolution cost per binding."""
    return subprocess.run(
        [sys.executable, "-m", "pytest", *targets, "-q", "--no-header", "-rsx",
         "-p", "no:cacheprovider"],
        cwd=root, capture_output=True, text=True, check=False,
        env={**os.environ, NESTED_ENV: "1"},
    )


def pytest_violation(root: Path, targets: list[str], label: str,
                     frozen: frozenset[str]) -> str | None:
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
    xfails = unfrozen_xfails(out, frozen)
    if xfails:
        return f"{XFAIL_OUTSIDE_FREEZE} — {label}: {', '.join(xfails)}"
    return None


# ------------------------------------------------------- --collect-only (D0266 item 2)
#
# The pre-commit hook (D0267 ruling 3: "commit hooks do structural checks only ...
# bindings collect") does not need to know that a bound node PASSES — only that it still
# EXISTS and still imports: a rename or a deleted test is a typo the author should see at
# commit time, and a red assertion is CI's to catch, not the hook's (a red node may sit on
# a branch until CI; master stays gated). `--collect-only` resolves every binding with one
# `pytest --collect-only` batch, which does not execute a single test body, so it costs
# seconds against the same target set that costs minutes to actually run.


def run_pytest_collect(root: Path, targets: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pytest", *targets, "--collect-only", "-q", "--no-header",
         "-p", "no:cacheprovider"],
        cwd=root, capture_output=True, text=True, check=False,
        env={**os.environ, NESTED_ENV: "1"},
    )


def collect_violation(root: Path, target: str) -> str | None:
    run = run_pytest_collect(root, [target])
    # rc 2 is pytest's own "interrupted: N error(s) during collection" (an import or
    # syntax error in the module); rc 4 is its usage error for an explicit nodeid that
    # does not exist (a named test function that was renamed or removed). Checked by
    # RETURNCODE ALONE, never a substring of the output: an "error" (or "oserror")
    # substring check used to flag a perfectly fine tree, because a test's OWN NAME can
    # contain the word — tests/test_export_cli.py::test_a_target_without_a_callable_is_
    # a_usage_error and tests/test_r2.py::test_any_other_status_is_an_oserror both
    # collect cleanly (rc 0) and both tripped it, caught running this against the real
    # tree right after the collect/report split landed.
    if run.returncode not in (0, 5):
        return f"pytest node does not collect: {target}"
    return None


def resolve_by_collection(root: Path, targets: list[str]) -> dict[str, str | None]:
    batch = run_pytest_collect(root, targets)
    if batch.returncode in (0, 5):
        # exit 5 is pytest's own "no tests collected" for the WHOLE batch, which cannot
        # happen here (targets is non-empty and each names something); kept only so a
        # future empty-batch caller does not read exit 5 as a failure of every target.
        return {target: None for target in targets}
    return {target: collect_violation(root, target) for target in targets}


# --------------------------------------------------- --pytest-report FILE (D0266 item 2)
#
# The gate's own `uv run pytest -q --junitxml=FILE` (Makefile: pytest now runs BEFORE
# this guard) already executed every bound node once. Reading its report resolves every
# binding from that one run instead of spawning a second pytest process over the same
# ~130 nodes — the duplicate D0266 measured at 15:24 of make verify's 41-minute CI. A
# node this report does not mention was not run at all, which is refused exactly as a
# node that does not collect: an absent result is not silent success.

_JUNIT_NS = ""  # pytest's junitxml carries no namespace


def _junit_classname(rel: str) -> str:
    """The dotted module path pytest's junitxml reports a file under (no `file` attribute
    is emitted by this pytest; `classname` is module-path-dotted, optionally with a test
    class appended) — verified against a live report before this was trusted (D0266 note)."""
    stem = rel[:-3] if rel.endswith(".py") else rel
    return stem.replace("/", ".")


def _junit_cases(report: Path) -> list[tuple[str, str, str | None, str]]:
    """`(classname, name, verdict, message)` for every `<testcase>`, `verdict` one of
    None (passed), 'failure', 'error', 'skipped', 'xfail'.

    pytest's junitxml plugin reports a strict xfail as `<skipped type="pytest.xfail">`
    (verified against a live report: D0124's law-retirement xfail carries no SKIP line
    in `-rs` text output, but IS a `<skipped>` element here) — conflating that with a
    real skip is exactly the D0124 hole this guard exists to keep closed, so `type` is
    read to tell the two apart before either is judged. `message` is the skip reason
    (`pytest.skip(reason=...)`'s text lands here verbatim, confirmed against a live
    report), the same text the default mode's `_SKIP_REASON_RE` extracts from `-rs`.
    """
    import xml.etree.ElementTree as ET
    root = ET.parse(report).getroot()
    cases = []
    for case in root.iter("testcase"):
        verdict = None
        message = ""
        for tag in ("failure", "error", "skipped"):
            node = case.find(tag)
            if node is not None:
                verdict = "xfail" if tag == "skipped" and node.get("type") == "pytest.xfail" else tag
                message = node.get("message", "")
                break
        cases.append((case.get("classname", ""), case.get("name", ""), verdict, message))
    return cases


def _matches(target: str, classname: str, name: str) -> bool:
    """Whether a `<testcase>` answers a binding `target` — a bare file (every case under
    it, function- or class-scoped) or `file.py::[Class::]func` (that one case, a
    parametrized name matched by prefix: `pytest_violation`'s own batching already
    treats a whole-file binding as "every case", so a single-node binding is the same
    rule narrowed to one classname/name pair)."""
    file_part, sep, rest = target.partition("::")
    base = _junit_classname(file_part)
    if not sep:
        return classname == base or classname.startswith(base + ".")
    parts = rest.split("::")
    want_class, want_name = (parts[0], parts[1]) if len(parts) == 2 else (None, parts[0])
    want_classname = f"{base}.{want_class}" if want_class else base
    return classname == want_classname and (name == want_name or name.startswith(want_name + "["))


XFAIL_OUTSIDE_FREEZE = ("pytest node xfails in an unfrozen file; an xfail is a sanctioned "
                        "retirement only inside a frozen law file (RT-M5-04)")


def report_violation(cases: list[tuple[str, str, str | None, str]], target: str,
                     frozen: frozenset[str]) -> str | None:
    matches = [(c, n, v, m) for c, n, v, m in cases if _matches(target, c, n)]
    if not matches:
        return f"pytest node is absent from the gate's report (not run): {target}"
    failed = [f"{c}::{n} ({v})" for c, n, v, m in matches if v in ("failure", "error")]
    if failed:
        return f"pytest node fails: {target}: {'; '.join(failed)}"
    # An xfail retirement (D0124) is a live, strict assertion, not a skip — excluded
    # before either "all skipped" or "some skipped" is judged, same as the default
    # mode never seeing it (no SKIPPED line in -rs text for an xfail).
    xfailed = [f"{c}::{n}" for c, n, v, m in matches if v == "xfail"]
    if xfailed and target.partition("::")[0] not in frozen and target not in frozen:
        return f"{XFAIL_OUTSIDE_FREEZE} — {target}: {', '.join(xfailed)}"
    live = [(c, n, v, m) for c, n, v, m in matches if v != "xfail"]
    if not live:
        return None
    skipped = [(c, n, m) for c, n, v, m in live if v == "skipped"]
    if skipped and len(skipped) == len(live):
        return f"pytest node is skipped (a skipped binding is not enforcement): {target}"
    unexplained = [f"{c}::{n}" for c, n, m in skipped if not m.startswith(ALLOWED_SKIP_REASON_PREFIXES)]
    if unexplained:
        return (
            f"pytest node has an unexplained skip inside an otherwise-passing run "
            f"(RT-M1-05) — {target}: {', '.join(unexplained)}"
        )
    return None


def resolve_from_report(report: Path, targets: list[str],
                        frozen: frozenset[str]) -> dict[str, str | None]:
    if not report.is_file():
        return {target: f"--pytest-report names a file that does not exist: {report}"
                for target in targets}
    cases = _junit_cases(report)
    return {target: report_violation(cases, target, frozen) for target in targets}


def resolve_pytest_bindings(root: Path, targets: list[str], *, collect_only: bool = False,
                            report: Path | None = None) -> dict[str, str | None]:
    """Resolve every pytest binding, batching the healthy case.

    Three modes, and exactly one applies: `report` replays the gate's own junitxml
    (the CI/local-verify path, D0266 item 2); `collect_only` checks that every node
    still collects and nothing more (the pre-commit path, D0267 ruling 3); the default
    runs pytest itself, all targets in one invocation, only re-running alone the ones a
    dirty batch cannot attribute individually. The cost of the guard should not be a
    reason to stop binding decisions to tests.
    """
    if not targets:
        return {}
    if os.environ.get(NESTED_ENV):
        print(f"  pytest bindings: {len(targets)} NOT RESOLVED (nested run; the outer run "
              "enforces). If you did not expect a nested run, this variable is set in your "
              "ambient environment and binding enforcement is OFF (RT-08).")
        return {target: NOT_RESOLVED for target in targets}
    frozen = frozen_paths(root)
    if report is not None:
        return resolve_from_report(report, targets, frozen)
    if collect_only:
        return resolve_by_collection(root, targets)
    batch = run_pytest(root, targets)
    combined = batch.stdout + batch.stderr
    if (batch.returncode == 0 and not re.search(r"\b[1-9]\d* skipped\b", combined)
            and not unfrozen_xfails(combined, frozen)):
        return {target: None for target in targets}
    return {target: pytest_violation(root, [target], target, frozen) for target in targets}


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
    resolution = parser.add_mutually_exclusive_group()
    resolution.add_argument("--collect-only", action="store_true",
                            help="resolve pytest bindings by collection only, not execution "
                                 "(the pre-commit hook; D0267 ruling 3 — structural checks only)")
    resolution.add_argument("--pytest-report", type=Path, metavar="FILE",
                            help="resolve pytest bindings from a prior `pytest --junitxml=FILE` "
                                 "run instead of spawning a second one (the gate's own run; "
                                 "D0266 item 2)")
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
    counted: list[str] = []
    valid_records: list[dict] = []
    pytest_bindings: dict[str, list[str]] = {}
    retirements = collect_retirements(root, record_paths, fail)
    honoured: set[tuple[str, str]] = set()

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
            retired_by = retirements.get((rid, binding["target"]))
            if binding["type"] == "file" and retired_by is not None:
                # D0181. A retired binding resolves without its target — but only a
                # documentary one, and never silently (see collect_retirements).
                honoured.add((rid, binding["target"]))
                if (root / binding["target"]).exists():
                    pass   # still present: collect_retirements reported the stale retirement
                elif binding.get("strength", "enforced") != "documentary":
                    fail.add(
                        f"{rel}: binding to {binding['target']} is retired by {retired_by}, "
                        "but the binding is enforced — only a documentary binding may be "
                        "retired; an enforced one that no longer holds needs a new record"
                    )
                else:
                    print(f"  retired: {rid} <- {retired_by} (target absent by ruling): "
                          f"{binding['target']}")
                continue
            problem = binding_violation(root, binding["type"], binding["target"])
            if problem:
                fail.add(f"{rel}: binding does not resolve — {problem}")
        if not record["bindings"]:
            unenforced.append(f"{rid} ({record['title']}): {record['unenforced_reason']}")

        # D0106 item (1). A guard verifies that a record is WELL-FORMED, never that it says
        # what its author meant: D0049 carried a folded YAML list that was valid, resolved,
        # and was silently one binding short. `bindings_count` is the author's own count of
        # the same fact, so the two can be made to disagree out loud. Optional by design —
        # absent means the record makes no claim and nothing is checked, which is why the
        # summary reports the coverage rather than implying the checksum is universal.
        declared = record.get("bindings_count")
        if declared is not None:
            counted.append(rid)
            if declared != len(record["bindings"]):
                fail.add(
                    f"{rel}: bindings_count is {declared} but the record carries "
                    f"{len(record['bindings'])} binding(s) — the author's count and the "
                    "file's bytes disagree (D0106 item 1, the D0049 failure mode)."
                )

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

    for (retired_id, target), by in retirements.items():
        if (retired_id, target) not in honoured:
            fail.add(
                f"{by} retires a binding that {retired_id} does not carry (no `type: file` "
                f"binding to {target}, or no such record) — a retirement must name a real "
                "binding, or it is a permission waiting for a path"
            )

    resolved = resolve_pytest_bindings(root, sorted(pytest_bindings), collect_only=args.collect_only,
                                       report=args.pytest_report)
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

    # D0215, replacing RT-M2-05's comparison (D0141). DECISIONS.md used to STORE the
    # attention-receipt verdict and every Tier-B record's effective status, and this block
    # compared both with what today computes. Both are functions of the clock and of
    # `git tag -l`, and no commit contains either — so the comparison was right at the tip
    # and wrong everywhere in history, and minting a close tag reddened the very commit it
    # attests (m1-, m2- and m3-close all point at such commits; CI run 34481481487 on
    # e33adf8). The remedy removes the claim rather than checking it harder: the verdict and
    # the veto clocks are still computed and PRINTED by this run, and rendered into the
    # dated digest, which is never recompared.
    #
    # So RT-M2-05's failure — a tracked file asserting FRESH after the receipt went stale —
    # stays impossible, because no tracked projection asserts it at all; the first check
    # below is what keeps that true. The second asserts the one receipt fact the file does
    # carry against the tree it sits in. `receipt_line` is shared with the generator on
    # purpose, as `input_hash` is: its output is a pure function of files in the commit, so
    # this is a freshness comparison. D0141's objection to a shared renderer was about a
    # clock verdict whose CORRECTNESS the guard had to judge, and there is none left here.
    if projection.exists():
        body = projection.read_text(encoding="utf-8")
        if STORED_VERDICT_RE.search(body):
            fail.add("DECISIONS.md stores an attention-receipt verdict (FRESH/STALE) — it "
                     "moves with the clock and the tag set, so it lives only in "
                     "digest/<date>.md (D0215); run make projections")
        want = receipt_line(root)
        if want not in body.splitlines():
            fail.add(f"DECISIONS.md's receipt line does not match this tree's receipts/ "
                     f"({want!r}) — run make projections")

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
        f"{len(counted)}/{len(record_paths)} declare bindings_count; "
        f"{enforced_n} enforced / {documentary_n} documentary binding(s); "
        f"{len(clocks)} Tier-B clock(s) computed; "
        f"{len(tier_c_signed)} Tier-C door(s) owner-signed, {len(tier_c_queued)} queued; "
        "DECISIONS.md fresh"
    )


if __name__ == "__main__":
    sys.exit(main())
