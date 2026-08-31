"""Repo-root pytest configuration: the Hypothesis profile, the evidence plugin, and the
supersession registry.

All three exist so that a law run *records what it was*: the profile fixes how examples
are generated (so a verdict is replayable), the plugin writes the evidence record that
`tannen laws report` reads (BRIEF P6, §5.11), and the registry marks the law nodes a
forward supersession has retired (D0106 ruling 2, D0128).

The registry is read HERE and not inside `tannen.laws` on purpose: pyyaml is a dev
dependency, and a governance file is not something the shipped package should need to
parse. conftest is already the composition root for the plugin, so supersession — a fact
about this repository's history, not about the kernel — is passed in from the same place.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from hypothesis import settings

ROOT = Path(__file__).resolve().parent
SUPERSEDED_REGISTRY = ROOT / "governance" / "laws.yaml"

#: Deadlines are a performance judgement, and there is no performance work before M5
#: (BRIEF §10); a law that times out on a slow filesystem would be flaky, not false.
#: `derandomize` makes each run of a given law file against a given implementation draw
#: the same examples, so an evidence record is reproducible from the record alone.
#: `pytest --hypothesis-seed=N` overrides it for a random sweep, and the emitted
#: records name the seed they ran under (see `make laws-sweep`).
settings.register_profile(
    "tannen-laws",
    derandomize=True,
    deadline=None,
    print_blob=True,
)
settings.load_profile("tannen-laws")


def superseded_entries() -> list[dict]:
    """The ACTIVE retired law nodes, from governance/laws.yaml (D0128).

    Only the `superseded` list. The registry's `pending` list holds entries whose node
    still passes because the change that retires it has not landed yet — marking one
    `xfail(strict=True)` would turn a passing test red, which is why the split exists.
    `scripts/check_laws.py` validates both lists identically.
    """
    if not SUPERSEDED_REGISTRY.exists():
        return []
    data = yaml.safe_load(SUPERSEDED_REGISTRY.read_text(encoding="utf-8")) or {}
    return [entry for entry in (data.get("superseded") or []) if entry.get("node")]


def pytest_collection_modifyitems(config, items) -> None:
    """Mark every retired law node `xfail(strict=True)`.

    STRICT, and not a skip: the retirement stays a live assertion. The node was retired
    because the behaviour it depends on changed, so it must now FAIL — and if it starts
    passing again, because that change was reverted, this turns the gate red instead of
    looking away. It is also why no SKIP line is emitted, which keeps the retirement clear
    of `check_decisions.ALLOWED_SKIP_REASON_PREFIXES` (D0124).
    """
    retired = {entry["node"]: entry for entry in superseded_entries()}
    if not retired:
        return
    for item in items:
        entry = retired.get(item.nodeid.split("[", 1)[0])
        if entry is None:
            continue
        item.add_marker(
            pytest.mark.xfail(
                strict=True,
                reason=(
                    f"superseded by {entry['successor']} ({entry['record']}) — frozen, so "
                    f"retired forward rather than edited: {entry['reason'].strip()}"
                ),
            )
        )


def pytest_configure(config) -> None:
    try:
        from tannen.laws.plugin import LawEvidencePlugin
    except ImportError:  # pre-implementation trees: laws still run, they just attest nothing
        return
    nodes = frozenset(entry["node"] for entry in superseded_entries())
    config.pluginmanager.register(LawEvidencePlugin(config, superseded=nodes), "tannen-law-evidence")
