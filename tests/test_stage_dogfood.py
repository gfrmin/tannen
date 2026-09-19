"""The gate stages only the pipeline module corpus.json names, never .dogfood/ itself (RT-M5-01)."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("stage_dogfood", REPO_ROOT / "scripts" / "stage_dogfood.py")
stage_dogfood = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(stage_dogfood)

SITECUSTOMIZE = "import pathlib, os\npathlib.Path(os.environ['MARKER']).write_text('ran')\n"


def dogfood(root: Path, pipeline: str = "vertical:pipeline") -> Path:
    d = root / ".dogfood"
    d.mkdir(parents=True)
    (d / "corpus.json").write_text(json.dumps({"pipeline": pipeline}))
    (d / "vertical.py").write_text("def pipeline(oracles, store, ref):\n    return ref\n")
    (d / "sitecustomize.py").write_text(SITECUSTOMIZE)
    return d


def starts_sitecustomize(pythonpath: Path, marker: Path) -> bool:
    env = {**os.environ, "PYTHONPATH": str(pythonpath), "MARKER": str(marker)}
    subprocess.run([sys.executable, "-c", "pass"], env=env, check=True)
    return marker.exists()


def test_a_sitecustomize_beside_the_pipeline_is_not_staged(tmp_path: Path) -> None:
    d = dogfood(tmp_path)
    stage = tmp_path / "stage"
    assert stage_dogfood.main(stage, tmp_path) == 0
    assert sorted(p.name for p in stage.iterdir()) == ["vertical.py"]
    assert not starts_sitecustomize(stage, tmp_path / "staged-marker")
    # Control: the directory the gate used to put on PYTHONPATH runs it at startup.
    assert starts_sitecustomize(d, tmp_path / "control-marker")


def test_a_pipeline_named_like_an_autoloaded_module_is_refused(tmp_path: Path) -> None:
    dogfood(tmp_path, pipeline="sitecustomize:pipeline")
    assert stage_dogfood.main(tmp_path / "stage", tmp_path) == 1


def test_no_corpus_stages_nothing(tmp_path: Path) -> None:
    stage = tmp_path / "stage"
    (stage / "leftover.py").parent.mkdir(parents=True)
    (stage / "leftover.py").write_text("")
    assert stage_dogfood.main(stage, tmp_path) == 0
    assert list(stage.iterdir()) == []
