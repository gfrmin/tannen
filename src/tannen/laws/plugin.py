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


@dataclass
class _LawRun:
    milestone: str
    observed: set[str] = field(default_factory=set)
    failed: bool = False
    skipped: bool = False
    uses_hypothesis: bool = False


class LawEvidencePlugin:
    def __init__(self, config: Any) -> None:
        self.config = config
        self.root = Path(config.rootpath)
        self.enabled = os.environ.get(DISABLE_ENV, "").lower() not in _TRUE
        self._runs: dict[str, _LawRun] = {}
        self._functions: dict[str, tuple[str, str]] = {}  # nodeid → (law_id, function)

    # ------------------------------------------------------------------ hooks

    def pytest_collection_modifyitems(self, items: list[Any]) -> None:
        if not self.enabled:
            return
        for item in items:
            located = self._locate(item.nodeid)
            if located is None:
                continue
            milestone, law, function = located
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
        elif report.when == "call":
            run.observed.add(function)

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
            expected = {name for names in modules.values() for name in names}
            if run.skipped or not expected or run.observed != expected:
                incomplete.append(law)
                continue
            record = build_record(
                law_id=law,
                milestone=milestone_label(run.milestone),
                verdict="fail" if run.failed else "pass",
                descriptors=[law_descriptor(self.root, law, modules, subject=subject)],
                seed=seed if run.uses_hypothesis else None,
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
