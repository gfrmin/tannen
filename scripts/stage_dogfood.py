"""Stage the M5 vertical's pipeline module, and nothing else, for the gate's PYTHONPATH (RT-M5-01).

    .venv/bin/python -I -P scripts/stage_dogfood.py STAGE_DIR

The gate used to put `.dogfood/` itself on PYTHONPATH, so any file there joined the interpreter:
a `sitecustomize.py` beside the pipeline ran at startup and could register a pytest plugin that
rewrote L5.9's failure into a pass before evidence or junit saw it. Now STAGE_DIR is emptied and
receives one file: the module `corpus.json`'s `pipeline` names, copied from `.dogfood/<module>.py`.
A name Python or pytest would load on its own is refused. No corpus means an empty STAGE_DIR,
which is CI's case.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULE = re.compile(r"^[a-z][a-z0-9_]*$")
#: Names the interpreter or pytest imports without being asked, plus the package under test.
AUTOLOADED = frozenset({"sitecustomize", "usercustomize", "conftest", "pytest", "tannen"})


def main(stage: Path, root: Path = ROOT) -> int:
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    corpus = root / ".dogfood" / "corpus.json"
    if not corpus.is_file():
        return 0
    pipeline = json.loads(corpus.read_text(encoding="utf-8")).get("pipeline", "")
    module = pipeline.partition(":")[0]
    if not MODULE.match(module) or module in AUTOLOADED:
        print(f"stage_dogfood: refused — corpus.json names pipeline module {module!r}; it must be "
              f"one plain module name, and not one Python or pytest loads by itself (RT-M5-01)",
              file=sys.stderr)
        return 1
    source = root / ".dogfood" / f"{module}.py"
    if not source.is_file():
        print(f"stage_dogfood: refused — {source.relative_to(root)} does not exist; the pipeline "
              "is one module file in .dogfood/ (D0268 ask 6)", file=sys.stderr)
        return 1
    shutil.copyfile(source, stage / source.name)
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__.splitlines()[2].strip())
    sys.exit(main(Path(sys.argv[1])))
