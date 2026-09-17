"""scripts/measure_dogfood_candidates.py, exercised over SYNTHETIC files only — this
script is meant to run on the owner's machine against real Renavon source, after the gate
sitting; nothing here reads or names anything from the Renavon monorepo (docs/specs/m5.md
§0.2). It owes one mechanical fact, `loc/1`, and this proves that fact and the refusals
the script raises before the frozen laws would (D0257 ask (2)).
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "measure_dogfood_candidates.py"


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True,
                          text=True, check=False)


def test_loc_1_excludes_blank_and_comment_only_lines_but_not_trailing_comments(tmp_path: Path) -> None:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    try:
        from measure_dogfood_candidates import count_loc
    finally:
        sys.path.remove(str(REPO_ROOT / "scripts"))
    src = tmp_path / "a.py"
    src.write_text(textwrap.dedent("""\
        # a whole-line comment
        import os


        x = 1  # a trailing comment still counts
        # another comment
        y = 2
        """))
    assert count_loc(src) == 3  # import os / x = 1 .../ y = 2


def test_loc_1_refuses_an_unknown_extension(tmp_path: Path) -> None:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    try:
        from measure_dogfood_candidates import count_loc
        import pytest
        src = tmp_path / "a.mystery"
        src.write_text("whatever\n")
        with pytest.raises(ValueError, match="no loc/1 comment rule"):
            count_loc(src)
    finally:
        sys.path.remove(str(REPO_ROOT / "scripts"))


def _write_root(tmp_path: Path) -> Path:
    root = tmp_path / "synthetic-source"
    (root / "parsers").mkdir(parents=True)
    (root / "parsers" / "alpha.py").write_text(
        "# alpha parser (synthetic, not Renavon)\n"
        "def parse(x):\n"
        "    return x\n"
    )
    (root / "parsers" / "beta.py").write_text(
        "def parse(x):\n"
        "    # a comment\n"
        "    y = x\n"
        "    return y\n"
    )
    return root


def test_writes_measurement_1_with_computed_loc(tmp_path: Path) -> None:
    root = _write_root(tmp_path)
    spec = tmp_path / "candidates.yaml"
    spec.write_text(yaml.safe_dump({
        "root": str(root),
        "candidates": [
            {"source": "alpha", "visible_export": True,
             "parser_files": ["parsers/alpha.py"], "operators": ["select"]},
            {"source": "beta", "visible_export": False,
             "parser_files": ["parsers/beta.py"], "operators": ["select", "project"]},
        ],
    }))
    out = tmp_path / "measurement.json"
    result = run("--input", str(spec), "--out", str(out))
    assert result.returncode == 0, result.stdout + result.stderr
    measurement = json.loads(out.read_text())
    assert measurement["tannen"] == "measurement/1"
    assert measurement["counter"] == "loc/1"
    by_source = {c["source"]: c for c in measurement["candidates"]}
    assert by_source["alpha"]["parser_loc"] == 2  # def parse / return x
    assert by_source["beta"]["parser_loc"] == 3   # def parse / y = x / return y
    assert by_source["alpha"]["visible_export"] is True
    assert by_source["beta"]["visible_export"] is False


def test_refuses_a_source_named_twice(tmp_path: Path) -> None:
    root = _write_root(tmp_path)
    spec = tmp_path / "candidates.yaml"
    spec.write_text(yaml.safe_dump({
        "root": str(root),
        "candidates": [
            {"source": "alpha", "visible_export": True,
             "parser_files": ["parsers/alpha.py"], "operators": ["select"]},
            {"source": "alpha", "visible_export": True,
             "parser_files": ["parsers/beta.py"], "operators": ["select"]},
        ],
    }))
    result = run("--input", str(spec), "--out", str(tmp_path / "measurement.json"))
    assert result.returncode != 0
    assert "more than once" in result.stderr


def test_refuses_an_operator_outside_the_catalogue(tmp_path: Path) -> None:
    root = _write_root(tmp_path)
    spec = tmp_path / "candidates.yaml"
    spec.write_text(yaml.safe_dump({
        "root": str(root),
        "candidates": [
            {"source": "alpha", "visible_export": True,
             "parser_files": ["parsers/alpha.py"], "operators": ["not_a_real_operator"]},
        ],
    }))
    result = run("--input", str(spec), "--out", str(tmp_path / "measurement.json"))
    assert result.returncode != 0
    assert "not_a_real_operator" in result.stderr


def test_refuses_a_measurement_the_frozen_schema_rejects(tmp_path: Path) -> None:
    """A shape the mechanical build never produces on its own (an uppercase source id),
    refused whole and nothing written — the FROZEN schema (tests/laws/m5/measurement/
    schema.json) is the authority, read by path, not restated here."""
    root = _write_root(tmp_path)
    spec = tmp_path / "candidates.yaml"
    spec.write_text(yaml.safe_dump({
        "root": str(root),
        "candidates": [
            {"source": "Alpha", "visible_export": True,
             "parser_files": ["parsers/alpha.py"], "operators": ["select"]},
        ],
    }))
    out = tmp_path / "measurement.json"
    result = run("--input", str(spec), "--out", str(out))
    assert result.returncode != 0
    assert "frozen measurement/1 schema" in result.stderr
    assert not out.exists()


def test_watched_firing_on_a_genuine_frozen_model_disagreement(tmp_path: Path, monkeypatch,
                                                                 capsys) -> None:
    """Before this cross-check is trusted, it must be watched catching a REAL mismatch — the
    handoff's own lesson: a sabotage whose wrong answer happens to coincide with the right one
    proves nothing. `tannen.dogfood.select` is forced to refuse unconditionally; independently
    computed via the frozen model, the real answer for this measurement is a source id, never
    "refused", so the two are checked to actually differ before the warning is trusted."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    try:
        import measure_dogfood_candidates as mdc
        import tannen.dogfood as dogfood

        def _sabotaged_select(measurement: dict) -> str:
            raise dogfood.SelectionRefused("sabotaged for a genuine-mismatch test")

        monkeypatch.setattr(dogfood, "select", _sabotaged_select)

        root = _write_root(tmp_path)
        spec = tmp_path / "candidates.yaml"
        spec.write_text(yaml.safe_dump({
            "root": str(root),
            "candidates": [
                {"source": "alpha", "visible_export": True,
                 "parser_files": ["parsers/alpha.py"], "operators": ["select"]},
            ],
        }))
        out = tmp_path / "measurement.json"
        monkeypatch.setattr(sys, "argv", [
            "measure_dogfood_candidates.py", "--input", str(spec), "--out", str(out),
            "--preview-selection",
        ])
        rc = mdc.main()
        captured = capsys.readouterr()
        assert rc == 0  # the measurement itself still writes; the preview only warns

        written = json.loads(out.read_text())
        model = mdc.bind_frozen_model()
        from tannen.kernel.ops import OPERATORS
        real_expected = model.expected_selection(written, tuple(OPERATORS))
        assert real_expected != model.REFUSED, (
            "the fixture must have a real winner or this sabotage proves nothing "
            "(both sides would agree on 'refused')"
        )
        assert "WARNING" in captured.err
        assert real_expected in captured.err
    finally:
        sys.path.remove(str(REPO_ROOT / "scripts"))
        sys.modules.pop("measure_dogfood_candidates", None)


def test_preview_selection_is_labelled_a_preview_not_a_choice(tmp_path: Path) -> None:
    root = _write_root(tmp_path)
    spec = tmp_path / "candidates.yaml"
    spec.write_text(yaml.safe_dump({
        "root": str(root),
        "candidates": [
            {"source": "alpha", "visible_export": True,
             "parser_files": ["parsers/alpha.py"], "operators": ["select"]},
        ],
    }))
    result = run("--input", str(spec), "--out", str(tmp_path / "measurement.json"),
                 "--preview-selection")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "preview only, NOT a choice" in result.stdout
    assert "alpha" in result.stdout
