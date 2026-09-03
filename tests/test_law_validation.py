"""The law-validation ratchet (decision D0129; proposal 2026-08-26-law-validation-ratchet).

D0094's finding: under the frozen-oracle protocol every law becomes an `importorskip` at
exactly the moment it becomes unrewritable, so `pytest tests/laws/<m>` prints the same
"N skipped" whether the laws are correct, contradictory or nonsense. Session A's gate was
a check that the laws do NOT run; nothing checked that they could ever pass. D0093 is what
that hole produced.

This file is the other half. It imports `tests/laws/m2/_model.py` directly — no tannen, no
sentinel — and runs every model-checked family against the model and against its stated
mutant. It therefore runs at EVERY commit, including the freeze commit at which every M2
law is a skip, which is the whole point: the assertions are exercised before the code they
are about exists.

It also drives `scripts/check_laws.py`, which since the M2 boundary sitting is a
`make verify` step in its own right (D0131 item 4). Driving it from pytest as well is
not redundant: the five trees below make it FAIL, which the gate's success path never
does — the custodian is the floor, and pytest is the distance between weakening a guard
and finding out.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = REPO_ROOT / "tests" / "laws" / "m2" / "_model.py"
REGISTRY = REPO_ROOT / "governance" / "laws.yaml"

#: Enough draws for every mutant to die, measured rather than guessed: the whole matrix
#: runs in about five seconds at this budget. `make laws-sweep` is where the search goes
#: wider; this is a gate, and a gate that costs a minute gets disabled.
EXAMPLES = 25


def _load_model():
    """Import the frozen model by path. `tests/laws` carries no `__init__.py`, and
    `sys.dont_write_bytecode` keeps a `__pycache__` out of a sealed directory."""
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec = importlib.util.spec_from_file_location("_m2_model", MODEL_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.dont_write_bytecode = previous


M = _load_model()


# --------------------------------------------------------------- the model and its mutants


@pytest.mark.parametrize("family", M.FAMILIES)
def test_the_model_passes_every_family(family: str) -> None:
    """Half one of D0094 §2: the frozen laws' assertions hold against a transcription of
    the spec. D0093 — an axiom demanding a semiring with no zero divisors, frozen into a
    product semiring — fails this on its first run."""
    M.run_family(M.MODEL, family, EXAMPLES)


@pytest.mark.parametrize("mutant", sorted(M.MUTANTS))
def test_every_mutant_dies_by_the_check_that_names_it(mutant: str) -> None:
    """Half two, and the half most likely to be dropped as gold-plating: a law that passes
    against a deliberately broken model is not testing what it claims. It is also the only
    half that catches a law which cannot FAIL — a model with no subtraction cannot produce
    the negative L1.9 forbids, so only a mutant that can makes that law say anything.

    `antijoin-disjunctive` is not a hypothetical. It is tannen's own M1 behaviour, kept as
    a mutant so D0132's defect cannot come back quietly.
    """
    family = M.CAUGHT_BY[mutant]
    with pytest.raises(AssertionError):
        M.run_family(M.MUTANTS[mutant], family, EXAMPLES)


def test_every_family_is_aimed_at_by_a_mutant() -> None:
    """A mutant nobody aims a check at proves nothing, and a family nothing is aimed at is
    a family whose discrimination is unmeasured."""
    assert set(M.CAUGHT_BY.values()) == set(M.FAMILIES)
    assert set(M.CAUGHT_BY) == set(M.MUTANTS)


# ------------------------------------------------------------------------ scripts/check_laws.py


def run_check_laws(root: Path | None = None) -> subprocess.CompletedProcess:
    args = [sys.executable, str(REPO_ROOT / "scripts" / "check_laws.py")]
    if root is not None:
        args += ["--root", str(root)]
    return subprocess.run(args, cwd=REPO_ROOT, capture_output=True, text=True)


def test_check_laws_passes_on_the_real_tree() -> None:
    result = run_check_laws()
    assert result.returncode == 0, result.stdout + result.stderr


def _tree(tmp_path: Path, law_body: str, registry: str | None = None) -> Path:
    """A miniature repo, built here rather than by mutating the real one (D0092)."""
    laws = tmp_path / "tests" / "laws" / "m9"
    laws.mkdir(parents=True)
    (laws / "test_l9_demo.py").write_text(textwrap.dedent(law_body), encoding="utf-8")
    (tmp_path / "decisions").mkdir()
    (tmp_path / "decisions" / "0001-demo.yaml").write_text("id: D0001\n", encoding="utf-8")
    digest = subprocess.run(
        ["sha256sum", "tests/laws/m9/test_l9_demo.py"],
        cwd=tmp_path, capture_output=True, text=True, check=True,
    ).stdout
    (tmp_path / "MANIFEST.sha256").write_text(digest, encoding="utf-8")
    (tmp_path / "governance").mkdir()
    (tmp_path / "governance" / "laws.yaml").write_text(
        textwrap.dedent(registry if registry is not None else """
            version: 1
            validation:
              declarations_required_from: m9
            superseded: []
            pending: []
        """),
        encoding="utf-8",
    )
    return tmp_path


DECLARED = '''
    VALIDATED_BY = "tests/laws/m9/test_l9_demo.py::check_nothing"

    def check_nothing():
        pass

    def test_l9_1_something():
        pass
'''

UNDECLARED = '''
    def test_l9_1_something():
        pass
'''


def test_check_laws_accepts_a_frozen_law_that_declares_its_validation(tmp_path: Path) -> None:
    """The positive control. Without it the negative below would pass for any reason at
    all, including the fixture being broken."""
    result = run_check_laws(_tree(tmp_path, DECLARED))
    assert result.returncode == 0, result.stdout + result.stderr


def test_check_laws_refuses_a_frozen_law_that_declares_nothing(tmp_path: Path) -> None:
    """D0094 §3, and the part that would have caught D0093 with no cleverness: forced to
    write a `validation_reason` for L1.2 there was no honest one to write."""
    result = run_check_laws(_tree(tmp_path, UNDECLARED))
    assert result.returncode != 0
    assert "declares neither VALIDATED_BY nor VALIDATION_REASON" in result.stderr


def test_check_laws_refuses_a_supersession_whose_successor_no_law_defines(tmp_path: Path) -> None:
    """D0106 ruling 2: the claim a retired node made must be carried forward. A
    supersession pointing at nothing is a claim dropped."""
    result = run_check_laws(_tree(tmp_path, DECLARED, registry='''
        version: 1
        validation:
          declarations_required_from: m9
        superseded: []
        pending:
          - node: "tests/laws/m9/test_l9_demo.py::test_l9_1_something"
            successor: "L9.404"
            record: "D0001"
            reason: "a successor nothing defines"
    '''))
    assert result.returncode != 0
    assert "successor L9.404" in result.stderr


def test_check_laws_refuses_a_supersession_of_a_node_that_is_not_there(tmp_path: Path) -> None:
    result = run_check_laws(_tree(tmp_path, DECLARED, registry='''
        version: 1
        validation:
          declarations_required_from: m9
        superseded:
          - node: "tests/laws/m9/test_l9_demo.py::test_l9_1_renamed_away"
            successor: "L9.1"
            record: "D0001"
            reason: "the node moved"
        pending: []
    '''))
    assert result.returncode != 0
    assert "is not a law node" in result.stderr


def test_check_laws_refuses_an_entry_that_is_both_active_and_pending(tmp_path: Path) -> None:
    """An entry is either retired or awaiting the change that retires it. Both at once
    means conftest marks it xfail while the registry still says the behaviour has not
    landed — a contradiction that would read as a passing gate."""
    entry = '''
          - node: "tests/laws/m9/test_l9_demo.py::test_l9_1_something"
            successor: "L9.1"
            record: "D0001"
            reason: "in two places at once"
    '''
    result = run_check_laws(_tree(tmp_path, DECLARED, registry=f'''
        version: 1
        validation:
          declarations_required_from: m9
        superseded:
        {entry}
        pending:
        {entry}
    '''))
    assert result.returncode != 0
    assert "in BOTH superseded and pending" in result.stderr


# ------------------------------------------------------------------------ the registry itself


RETIRED_NODE = "tests/laws/m1/test_l1_rel.py::test_l1_5_mixing_semirings_is_refused_by_name"


def test_the_retirement_is_the_node_the_spec_names_and_it_is_now_ACTIVE() -> None:
    """docs/specs/m2.md §8 names one node awaiting retirement, and it must be the one the
    registry holds.

    Session A froze it under `pending`, because before D0110 landed the node still PASSED
    and a strict xfail on a passing test is a red gate. Session B landed D0110 and PROMOTED
    it to `superseded` in the same change — which is the moment the retirement became true
    rather than a claim about the future — so what this test asserts moved with it. The
    node, successor and record did not move, and that is what is checked here; the
    `pending` list is now empty, and an empty `pending` is the normal resting state
    (an entry sits there only between a Session A freeze and the Session B change that
    activates it).
    """
    import yaml

    registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    assert registry["pending"] == [], "nothing is awaiting activation now that D0110 has landed"
    superseded = registry["superseded"]
    assert len(superseded) == 1
    assert superseded[0]["node"] == RETIRED_NODE
    assert superseded[0]["successor"] == "L2.2"
    assert superseded[0]["record"] == "D0128"


def test_the_retired_node_actually_fails_now() -> None:
    """The half a registry entry cannot state about itself, and the half that makes strict
    xfail worth choosing over a skip (D0128): the node must FAIL for the retirement to be
    honest. Run in a subprocess with `--runxfail`, which reports the underlying outcome
    instead of the xfail mark, so this reads the node's real verdict rather than the
    conftest marking it was given.

    Without this, a supersession would be self-certifying — the registry says retired, the
    conftest says xfail, and nothing anywhere checks that the behaviour changed.
    """
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--runxfail", "-q", "-p", "no:cacheprovider", RETIRED_NODE],
        cwd=REPO_ROOT, capture_output=True, text=True,
        env={**os.environ, "TANNEN_NO_EVIDENCE": "1"},
    )
    assert result.returncode != 0, (
        "the retired node PASSES — D0110's door is open again, and the supersession is "
        f"claiming a retirement that has not happened:\n{result.stdout}"
    )
    assert "RelError" in result.stdout, result.stdout + result.stderr
