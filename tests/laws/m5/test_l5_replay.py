"""M5 law L5.10 — the vertical replays from its captures (docs/specs/m5.md §4; BRIEF §6 L1,
§5.10, P1).

FROZEN at m5-laws-freeze. Frozen inputs mean the vertical asks the world nothing: every value
it reads is already a capture or a source in `.dogfood/store/`, so `tannen.dogfood.run` — which
opens its oracle context replay-only (the default, BRIEF §5.10) — completes with no novel
invocation, and fresh interpreters with randomised hash seeds answer every item with the same
output refs as this one. A novel invocation would be refused by name and fail the run; nothing
here can reach a network (docs/specs/m5.md §8).
"""

from __future__ import annotations

import importlib.util as _ilu
import json
import os
import random
import subprocess
import sys
from pathlib import Path as _Path

import pytest

REPO_ROOT = _Path(__file__).resolve().parents[3]
DOGFOOD = REPO_ROOT / ".dogfood"
if not (DOGFOOD / "corpus.json").is_file():
    pytest.skip("M5 dogfood corpus absent — every M5 law goes live together when an authorised "
                "corpus is present at .dogfood/corpus.json (docs/specs/m5.md §8)",
                allow_module_level=True)

pytest.importorskip("tannen.dogfood", reason=(
    "M5 dogfood not implemented yet (law suite frozen ahead of Session B); M5's laws go "
    "live together — docs/specs/m5.md §8"))

_spec = _ilu.spec_from_file_location("tannen_frozen_m5._dogfood_bind",
                                     _Path(__file__).with_name("_dogfood_bind.py"))
bind = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(bind)

bind.m5("_dogfood_subject")  # the sentinel: tannen.dogfood present, or a visible skip

from tannen import dogfood  # noqa: E402
from tannen.store import Store  # noqa: E402

VALIDATION_REASON = (
    "replay across interpreters is machinery — the store, the codec and the process boundary — "
    "and a model of it would BE the implementation (the L1.15, L2.8 and L4.12 precedent)."
)

RUNS = 2

_CHILD = r'''
import json, sys
from tannen import dogfood
from tannen.store import Store

root = sys.argv[1]
corpus = json.loads(open(root + "/corpus.json", encoding="utf-8").read())
print(json.dumps(dict(dogfood.run(Store(root + "/store"), corpus)), sort_keys=True))
'''


def test_l5_10_fresh_interpreters_replay_every_item_to_the_same_outputs() -> None:
    corpus = json.loads((DOGFOOD / "corpus.json").read_text(encoding="utf-8"))
    here = json.dumps(dict(dogfood.run(Store(DOGFOOD / "store"), corpus)), sort_keys=True)
    for _ in range(RUNS):
        env = {k: v for k, v in os.environ.items()
               if k not in ("TANNEN_EVIDENCE_ROOT", "TANNEN_NO_EVIDENCE")}
        env["PYTHONHASHSEED"] = str(random.randrange(1, 2**32))
        run = subprocess.run([sys.executable, "-c", _CHILD, str(DOGFOOD)], capture_output=True,
                             text=True, check=False, cwd=REPO_ROOT, env=env)
        assert run.returncode == 0, f"a fresh interpreter could not replay the vertical:\n" \
                                    f"{run.stdout}{run.stderr}"
        assert run.stdout.strip() == here, (
            f"PYTHONHASHSEED={env['PYTHONHASHSEED']}: a fresh interpreter answered the corpus "
            "with different output refs (BRIEF §6 L1)")
