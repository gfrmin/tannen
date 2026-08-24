"""The laws runner, the evidence stream and `tannen laws report` (D0040–D0042).

The frozen M0 suite proves the kernel; nothing in the freeze proves the machinery that
*records* that proof. These tests do, and in particular they pin the two properties the
whole freshness claim rests on: a descriptor moves when either the law or the
implementation moves, and a partly-run law attests nothing at all.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from tannen.kernel.encoding import content_address
from tannen.laws import discovery, report
from tannen.laws.evidence import EvidenceError, EvidenceStore, build_record

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC = REPO_ROOT / "docs" / "specs" / "m0.md"


# ------------------------------------------------------------------ discovery


@pytest.fixture(autouse=True)
def _isolated_from_the_ambient_evidence_store(monkeypatch: pytest.MonkeyPatch) -> None:
    """These tests build their own evidence stores under a tmp tree.

    TANNEN_EVIDENCE_ROOT is an ambient override honoured by both the plugin and the
    report (D0041), and `make verify` now sets it to a freshly removed per-run store so
    the gate's report can only see records the gate's own run produced (RT-05). Without
    clearing it here, every "isolated" store in this file would silently BE that shared
    store, and these tests would assert about records they never wrote — which is the
    same confusion RT-05 is about, one level down.
    """
    monkeypatch.delenv("TANNEN_EVIDENCE_ROOT", raising=False)

def spec_law_table() -> dict[str, str]:
    """The law table of the frozen spec §5, as {law id: file}."""
    rows = re.findall(r"^\|\s*(L0\.\d+)\s*\|.*\|\s*`([^`]+)`\s*\|\s*$", SPEC.read_text(encoding="utf-8"), re.M)
    return {law: file for law, file in rows}


def test_discovery_matches_the_frozen_spec_table() -> None:
    """The runner's law set is the spec's law set — checked, not assumed.

    Discovery reads the frozen test files; the spec table is prose in a frozen document.
    If they ever disagree, one of them is wrong and the report would silently attest the
    wrong set, so the disagreement is a test failure instead.
    """
    table = spec_law_table()
    assert table, "could not parse the law table out of docs/specs/m0.md §5"
    discovered = discovery.discover_laws(REPO_ROOT, "m0")
    assert sorted(discovered, key=discovery.law_sort_key) == sorted(table, key=discovery.law_sort_key)
    for law, filename in table.items():
        assert sorted(discovered[law]) == [f"tests/laws/m0/{filename}"]


def test_law_ids_sort_numerically() -> None:
    laws = list(discovery.discover_laws(REPO_ROOT, "m0"))
    assert laws == sorted(laws, key=discovery.law_sort_key)
    assert laws.index("L0.2") < laws.index("L0.10")


def test_milestone_labels() -> None:
    assert discovery.milestones(REPO_ROOT) == ["m0"]
    assert discovery.milestone_label("m0") == "M0"
    assert discovery.milestone_label("m5b") == "M5b"
    with pytest.raises(ValueError):
        discovery.milestone_label("laws")


# ------------------------------------------------------------------ descriptors


@pytest.fixture()
def tree(tmp_path: Path) -> Path:
    """A miniature repo: one law file, one implementation file."""
    (tmp_path / "MANIFEST.sha256").write_text("", encoding="utf-8")
    laws = tmp_path / "tests" / "laws" / "m0"
    laws.mkdir(parents=True)
    (laws / "test_l0_demo.py").write_text(
        "def test_l0_1_alpha():\n    pass\n\n\ndef test_l0_1_beta():\n    pass\n",
        encoding="utf-8",
    )
    source = tmp_path / "src" / "tannen"
    source.mkdir(parents=True)
    (source / "impl.py").write_text("VALUE = 1\n", encoding="utf-8")
    return tmp_path


def descriptor_of(root: Path) -> str:
    modules = discovery.discover_laws(root, "m0")["L0.1"]
    return discovery.law_descriptor(root, "L0.1", modules)


def test_descriptor_moves_when_the_implementation_moves(tree: Path) -> None:
    before = descriptor_of(tree)
    (tree / "src" / "tannen" / "impl.py").write_text("VALUE = 2\n", encoding="utf-8")
    assert descriptor_of(tree) != before


def test_descriptor_moves_when_the_law_moves(tree: Path) -> None:
    before = descriptor_of(tree)
    law = tree / "tests" / "laws" / "m0" / "test_l0_demo.py"
    law.write_text(law.read_text(encoding="utf-8") + "# a comment is a change\n", encoding="utf-8")
    assert descriptor_of(tree) != before


def test_descriptor_ignores_bytecode_caches(tree: Path) -> None:
    before = descriptor_of(tree)
    cache = tree / "src" / "tannen" / "__pycache__"
    cache.mkdir()
    (cache / "impl.cpython-313.py").write_text("noise\n", encoding="utf-8")
    assert descriptor_of(tree) == before


def test_find_root_walks_up(tree: Path) -> None:
    assert discovery.find_root(tree / "src" / "tannen") == tree


# ------------------------------------------------------------------ evidence


def evidence_tree(root: Path) -> EvidenceStore:
    schema_dir = root / "governance" / "schemas"
    schema_dir.mkdir(parents=True, exist_ok=True)
    (schema_dir / "evidence-record.schema.json").write_bytes(
        (REPO_ROOT / "governance" / "schemas" / "evidence-record.schema.json").read_bytes()
    )
    return EvidenceStore(root, store_root=root / "evidence")


def test_an_invalid_record_never_reaches_disk(tree: Path) -> None:
    evidence = evidence_tree(tree)
    record = build_record(
        law_id="not-a-law-id", milestone="M0", verdict="pass", descriptors=[], seed=None
    )
    with pytest.raises(EvidenceError, match="frozen schema"):
        evidence.put(record)
    assert list(evidence.store.iter_refs()) == []


def test_a_record_is_addressed_by_its_canonical_encoding(tree: Path) -> None:
    evidence = evidence_tree(tree)
    record = build_record(
        law_id="L0.1", milestone="M0", verdict="pass",
        descriptors=[descriptor_of(tree)], seed="hypothesis-derandomize",
    )
    ref = evidence.put(record)
    assert ref == content_address(record)
    assert [r for _, r in evidence.records()] == [record]


def test_corrupt_evidence_is_surfaced_not_skipped(tree: Path) -> None:
    evidence = evidence_tree(tree)
    evidence.store.put_value({"law_id": "L0.1", "milestone": "M0"})  # record-shaped, invalid
    problems = [problem for _, _, problem in evidence.scan() if problem]
    assert problems and "frozen schema" in problems[0]


# ------------------------------------------------------------------ the report


def report_for(root: Path) -> dict:
    return report.build_report(root, None)


def test_report_is_stale_without_evidence(tree: Path) -> None:
    evidence_tree(tree)
    result = report_for(tree)
    assert result["ok"] is False
    assert [law["status"] for law in result["laws"]] == [report.STALE]
    assert "NO FRESH EVIDENCE for L0.1" in report.render(result)


def test_report_is_fresh_with_a_matching_record_and_stale_after_an_edit(tree: Path) -> None:
    evidence = evidence_tree(tree)
    evidence.put(build_record(
        law_id="L0.1", milestone="M0", verdict="pass",
        descriptors=[descriptor_of(tree)], seed=None,
    ))
    assert report_for(tree)["ok"] is True

    (tree / "src" / "tannen" / "impl.py").write_text("VALUE = 99\n", encoding="utf-8")
    stale = report_for(tree)
    assert stale["ok"] is False
    assert stale["laws"][0]["status"] == report.STALE


def test_a_recorded_failure_is_reported_as_a_failure(tree: Path) -> None:
    evidence = evidence_tree(tree)
    evidence.put(build_record(
        law_id="L0.1", milestone="M0", verdict="fail",
        descriptors=[descriptor_of(tree)], seed=None,
    ))
    result = report_for(tree)
    assert result["ok"] is False
    assert result["laws"][0]["status"] == report.FAILING


def test_disagreeing_verdicts_for_one_descriptor_read_as_flaky(tree: Path) -> None:
    evidence = evidence_tree(tree)
    descriptor = descriptor_of(tree)
    for verdict, when in (("pass", "2026-08-24T10:00:00+00:00"), ("fail", "2026-08-24T11:00:00+00:00")):
        evidence.put(build_record(
            law_id="L0.1", milestone="M0", verdict=verdict,
            descriptors=[descriptor], seed=None, run_at=when,
        ))
    result = report_for(tree)
    assert result["laws"][0]["status"] == report.CONFLICTING
    assert result["ok"] is False


def test_the_report_over_the_real_repo_is_well_formed() -> None:
    """Ten laws, no corrupt records.

    Freshness itself is deliberately NOT asserted here: this run's own evidence is
    written at session finish, so a law can only be fresh from a previous run. The
    freshness gate is `tannen laws report` in `make verify`, which runs after pytest —
    asserting it here would either be a lie or a permanent skip.
    """
    result = report_for(REPO_ROOT)
    assert not result["problems"], result["problems"]
    assert [law["law_id"] for law in result["laws"]] == sorted(
        spec_law_table(), key=discovery.law_sort_key
    )
    assert all(law["milestone"] == "M0" for law in result["laws"])


# ------------------------------------------------------------------ emission


def run_pytest(args: list[str], evidence_root: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ, TANNEN_EVIDENCE_ROOT=str(evidence_root))
    return subprocess.run(
        [sys.executable, "-m", "pytest", *args, "-q", "-p", "no:cacheprovider"],
        cwd=REPO_ROOT, capture_output=True, text=True, env=env, check=False,
    )


def stored_records(evidence_root: Path) -> list[dict]:
    store = EvidenceStore(REPO_ROOT, store_root=evidence_root)
    return [record for _, record in store.records()]


def test_a_partly_run_law_attests_nothing(tmp_path: Path) -> None:
    """L0.3 has two test functions; running one of them proves half a law, so no
    record is written. Silence is the correct failure mode — a green record covering
    tests that never ran would be worse than no record at all."""
    result = run_pytest(
        ["tests/laws/m0/test_l0_encoding.py", "-k", "test_l0_3_decode_door"], tmp_path / "ev"
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "L0.3" in result.stdout  # named as partly run
    assert not [r for r in stored_records(tmp_path / "ev") if r["law_id"] == "L0.3"]


def test_a_fully_run_law_writes_exactly_one_record(tmp_path: Path) -> None:
    result = run_pytest(["tests/laws/m0/test_l0_descriptor.py"], tmp_path / "ev")
    assert result.returncode == 0, result.stdout + result.stderr
    records = stored_records(tmp_path / "ev")
    assert [r["law_id"] for r in records] == ["L0.9"]
    assert records[0]["verdict"] == "pass"
    assert records[0]["seed"] is None  # L0.9 is example-only
    assert records[0]["environment"]["packages"]["pytest"]


def test_a_property_law_records_the_generation_token(tmp_path: Path) -> None:
    result = run_pytest(["tests/laws/m0/test_l0_store.py"], tmp_path / "ev")
    assert result.returncode == 0, result.stdout + result.stderr
    seeds = {r["law_id"]: r["seed"] for r in stored_records(tmp_path / "ev")}
    assert seeds["L0.7"] == "hypothesis-derandomize"  # the default profile
    assert seeds["L0.6"] is None  # example-only


def test_an_explicit_seed_is_recorded_as_itself(tmp_path: Path) -> None:
    result = run_pytest(
        ["tests/laws/m0/test_l0_store.py", "--hypothesis-seed=4242"], tmp_path / "ev"
    )
    assert result.returncode == 0, result.stdout + result.stderr
    seeds = {r["law_id"]: r["seed"] for r in stored_records(tmp_path / "ev")}
    assert seeds["L0.7"] == "hypothesis-seed:4242"


def test_evidence_emission_can_be_switched_off(tmp_path: Path) -> None:
    env = dict(os.environ, TANNEN_EVIDENCE_ROOT=str(tmp_path / "ev"), TANNEN_NO_EVIDENCE="1")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/laws/m0/test_l0_descriptor.py", "-q",
         "-p", "no:cacheprovider"],
        cwd=REPO_ROOT, capture_output=True, text=True, env=env, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (tmp_path / "ev").exists()


# ------------------------------------------------------------------ the CLI


def test_cli_exit_codes(tree: Path, capsys: pytest.CaptureFixture) -> None:
    from tannen.cli import main

    evidence = evidence_tree(tree)
    assert main(["laws", "report", "--root", str(tree)]) == 1
    assert "NO FRESH EVIDENCE" in capsys.readouterr().out

    evidence.put(build_record(
        law_id="L0.1", milestone="M0", verdict="pass",
        descriptors=[descriptor_of(tree)], seed=None,
    ))
    assert main(["laws", "report", "--root", str(tree)]) == 0
    assert "OK — 1 law(s)" in capsys.readouterr().out


def test_cli_json_output(tree: Path, capsys: pytest.CaptureFixture) -> None:
    from tannen.cli import main

    evidence_tree(tree)
    main(["laws", "report", "--root", str(tree), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["laws"][0]["law_id"] == "L0.1"
    assert payload["ok"] is False


def test_cli_unknown_milestone_is_not_silently_green(tree: Path, capsys: pytest.CaptureFixture) -> None:
    from tannen.cli import main

    evidence_tree(tree)
    assert main(["laws", "report", "--root", str(tree), "--milestone", "m9"]) == 1
    assert "unknown milestone: m9" in capsys.readouterr().out
