"""The pytest plugin that makes evidence automatic (BRIEF §5.11).

Running any law writes its evidence record — not as a step someone remembers, as a
consequence of the run. Registered from the repo-root `conftest.py`.

A record attests to a *whole* law: it is written only when every test function the
frozen law file defines for that law actually ran. A filtered or partly skipped run
attests to nothing, so it writes nothing and `tannen laws report` keeps saying the
evidence is missing — the failure mode of a half-run law is silence, never a green
record covering tests that never executed.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tannen.laws.discovery import (
    LAWS_DIR,
    discover_laws,
    implementation_subject,
    law_descriptor,
    law_id_of,
    milestone_label,
)
from tannen.laws.evidence import EvidenceStore, build_record

__all__ = ["LawEvidencePlugin", "DISABLE_ENV"]

DISABLE_ENV = "TANNEN_NO_EVIDENCE"
_TRUE = {"1", "true", "yes", "on"}

#: RT-M1-01 (2026-08-26 boundary red team) and RT-M2-01 (2026-09-01).
#: `tests/laws/m1/test_l1_duckdb.py` (frozen, manifested) loads its L1.16 oracle half
#: with a bare `import _fragment as F` — `tests/` carries no `__init__.py` anywhere, so
#: D0089's frozen `_fragment.py` is a plain top-level module, not a package member.
#: Python caches imports by NAME in `sys.modules`, so anything that imports a different
#: module also named `_fragment` FIRST wins: a new, unmanifested `tests/conftest.py`
#: doing `import _fragment` from a directory pytest's "prepend" import mode puts ahead
#: of `tests/laws/m1/` on `sys.path` gets cached first, and `test_l1_duckdb.py` silently
#: receives THAT module instead of the frozen one. Confirmed live: a decoy
#: `tests/_fragment.py` re-exporting the real module's names passed every test while
#: `sys.modules['_fragment'].__file__` pointed outside `tests/laws/m1/` the whole run,
#: and no guard in `make verify` noticed. This check is defence in depth, not a fix for
#: the naming hazard itself — the real fix is a package-qualified import in the frozen
#: law file, which only the owner may make (CLAUDE.md: frozen paths are read-only
#: outside a supersession).
#:
#: THE SET IS DERIVED, NOT ENUMERATED — that is RT-M2-01. The first spelling pinned the
#: single name `_fragment`. M2 then added `tests/laws/m2/_model.py`, bare-imported by
#: five frozen law files, and this guard did not cover it: a decoy `_model` stubbing
#: `check_differential` to return None makes L2.9 — BRIEF §6's kill criterion — vacuous
#: while all 113 M2 law nodes pass and `check_manifest` still reports the seals
#: unbroken. Reproduced live before this widening was written, then again after it
#: (docs/redteam/2026-09-01-m2-boundary.md). A guard that must be widened by hand at
#: every boundary is a guard that is a milestone behind at every boundary, so the map is
#: read off the filesystem: every `tests/laws/m*/_*.py`. Those paths are themselves
#: frozen, so shrinking the map means deleting a manifested file, and `check_manifest`
#: is the check that says so.


def _frozen_oracles(root: Path) -> dict[str, list[Path]]:
    """Oracle module name → the frozen file(s) entitled to answer to it.

    A list rather than a single path because two milestones CAN name their oracles
    alike, and a bare `import` cannot say which one a law received. That is reported as
    a defect in its own right below, not silently resolved in favour of either.
    """
    oracles: dict[str, list[Path]] = {}
    for path in sorted((root / LAWS_DIR).glob("m*/_*.py")):
        if path.stem.startswith("__"):
            continue
        oracles.setdefault(path.stem, []).append(path.resolve())
    return oracles


def _oracle_shadow_problem(root: Path) -> str | None:
    """None if every frozen oracle imported this run came from its frozen file; else a
    message naming EVERY one that did not. All of them, because a run that shadows two
    oracles and is told about one has been told the smaller half of its problem."""
    problems: list[str] = []
    for name, frozen in sorted(_frozen_oracles(root).items()):
        if len(frozen) > 1:
            listed = ", ".join(str(path) for path in frozen)
            problems.append(
                f"{name!r} is defined by more than one frozen law directory ({listed}), "
                "so a bare import cannot say which one a law received and neither can this check"
            )
            continue
        module = sys.modules.get(name)
        if module is None:
            continue
        actual_file = getattr(module, "__file__", None)
        actual = Path(actual_file).resolve() if actual_file else None
        if actual == frozen[0]:
            continue
        problems.append(f"sys.modules[{name!r}] is {actual}, not the frozen {frozen[0]}")
    if not problems:
        return None
    return "; ".join(problems) + (
        " — a differential oracle was shadowed by a different module of the same name "
        "(RT-M1-01, docs/redteam/2026-08-26-m1-boundary.md; RT-M2-01, "
        "docs/redteam/2026-09-01-m2-boundary.md)"
    )


@dataclass
class _LawRun:
    milestone: str
    observed: set[str] = field(default_factory=set)
    #: The NODE IDS that reported a result, not merely the function names. A parametrised
    #: law function is one entry in `observed` and one entry PER CASE here, and that gap is
    #: what D0117 is about: `observed` says the law ran, this says how much of it ran. A
    #: set and not a counter so a node reporting twice — a failure at setup and again at
    #: teardown — counts once.
    nodes: set[str] = field(default_factory=set)
    failed: bool = False
    skipped: bool = False
    uses_hypothesis: bool = False


class LawEvidencePlugin:
    def __init__(self, config: Any, superseded: Any = ()) -> None:
        self.config = config
        self.root = Path(config.rootpath)
        self.enabled = os.environ.get(DISABLE_ENV, "").lower() not in _TRUE
        self._runs: dict[str, _LawRun] = {}
        self._functions: dict[str, tuple[str, str]] = {}  # nodeid → (law_id, function)
        # Law nodes a forward supersession has retired (D0106 ruling 2, D0128), as
        # {law-file relpath: {function names}}. They are marked xfail(strict=True) by the
        # root conftest, and a strict xfail reports as SKIPPED — which would otherwise make
        # every law sharing the file attest nothing at all, turning a retirement into a
        # silent hole in the evidence. They are excluded from both the run and the expected
        # set instead, so the law's REMAINING nodes still attest.
        #
        # Passed in rather than read here: the registry is YAML, pyyaml is a dev
        # dependency, and a governance file is not something the shipped package parses.
        self._superseded: dict[str, set[str]] = {}
        for nodeid in superseded:
            path, _, function = str(nodeid).partition("::")
            self._superseded.setdefault(path, set()).add(function.split("[", 1)[0])

    # ------------------------------------------------------------------ hooks

    def pytest_collection_modifyitems(self, items: list[Any]) -> None:
        # Checked unconditionally, even under TANNEN_NO_EVIDENCE: an evidence-disabled
        # run still runs the frozen laws (D0041 turns off only the record, never the
        # test), so a shadowed oracle would be just as undetected either way (RT-M1-01).
        problem = _oracle_shadow_problem(self.root)
        if problem is not None:
            import pytest

            pytest.exit(f"tannen evidence: {problem}", returncode=1)
        if not self.enabled:
            return
        for item in items:
            located = self._locate(item.nodeid)
            if located is None:
                continue
            milestone, law, function = located
            path = item.nodeid.partition("::")[0]
            if function in self._superseded.get(path, ()):
                continue
            self._functions[item.nodeid] = (law, function)
            run = self._runs.setdefault(law, _LawRun(milestone=milestone))
            if getattr(getattr(item, "function", None), "is_hypothesis_test", False):
                run.uses_hypothesis = True

    def pytest_runtest_logreport(self, report: Any) -> None:
        if not self.enabled:
            return
        located = self._functions.get(report.nodeid)
        if located is None:
            return
        law, function = located
        run = self._runs[law]
        if report.skipped:
            run.skipped = True
        elif report.failed:
            run.failed = True
            run.observed.add(function)
            run.nodes.add(report.nodeid)
        elif report.when == "call":
            run.observed.add(function)
            run.nodes.add(report.nodeid)

    def pytest_sessionfinish(self, session: Any, exitstatus: object) -> None:
        if not self.enabled or not self._runs:
            return
        written, incomplete = self._emit()
        message = f"tannen evidence: {written} record(s) written to {self._display_root()}"
        if incomplete:
            message += f"; {len(incomplete)} law(s) partly run, no record: {', '.join(sorted(incomplete))}"
        reporter = session.config.pluginmanager.get_plugin("terminalreporter")
        if reporter is not None:
            reporter.write_line(message)
        else:  # pragma: no cover - pytest always provides one outside -p no:terminal
            print(message)

    # ------------------------------------------------------------------ internals

    def _locate(self, nodeid: str) -> tuple[str, str, str] | None:
        """(milestone dir, law id, function name) for a law node, else None."""
        path, _, rest = nodeid.partition("::")
        parts = Path(path).parts
        laws_parts = LAWS_DIR.parts
        if len(parts) < len(laws_parts) + 2 or parts[: len(laws_parts)] != laws_parts:
            return None
        function = rest.split("[", 1)[0]
        law = law_id_of(function)
        return (parts[len(laws_parts)], law, function) if law else None

    def _emit(self) -> tuple[int, list[str]]:
        evidence = EvidenceStore(self.root)
        subject = implementation_subject(self.root)
        seed = self._seed()
        expectations: dict[str, dict[str, dict[str, frozenset[str]]]] = {}
        written = 0
        incomplete: list[str] = []

        for law, run in sorted(self._runs.items()):
            if run.milestone not in expectations:
                expectations[run.milestone] = discover_laws(self.root, run.milestone)
            modules = expectations[run.milestone].get(law, {})
            expected = {
                name
                for rel, names in modules.items()
                for name in names
                if name not in self._superseded.get(rel, ())
            }
            if run.skipped or not expected or run.observed != expected:
                incomplete.append(law)
                continue
            record = build_record(
                law_id=law,
                milestone=milestone_label(run.milestone),
                verdict="fail" if run.failed else "pass",
                descriptors=[law_descriptor(self.root, law, modules, subject=subject)],
                seed=seed if run.uses_hypothesis else None,
                examined={"law_nodes": len(run.observed), "test_cases": len(run.nodes)},
            )
            evidence.put(record)
            written += 1
        return written, incomplete

    def _seed(self) -> str:
        """The generation token, named honestly (evidence-record schema, `seed`).

        Only the public `--hypothesis-seed` option and the loaded profile are consulted:
        reading a private attribute could silently stop working and turn the recorded
        seed into a lie, which is worse than recording no seed at all.
        """
        try:
            forced = self.config.getoption("hypothesis_seed", default=None)
        except ValueError:  # pragma: no cover - hypothesis plugin absent
            forced = None
        if forced is not None:
            return f"hypothesis-seed:{forced}"
        try:
            from hypothesis import settings
        except ImportError:  # pragma: no cover
            return "hypothesis-absent"
        return "hypothesis-derandomize" if settings.default.derandomize else "hypothesis-random-unrecorded"

    def _display_root(self) -> str:
        from tannen.laws.evidence import evidence_root

        target = evidence_root(self.root)
        try:
            return str(target.relative_to(self.root))
        except ValueError:
            return str(target)
