"""Repo-root pytest configuration: the Hypothesis profile and the evidence plugin.

Both exist so that a law run *records what it was*: the profile fixes how examples are
generated (so a verdict is replayable), and the plugin writes the evidence record that
`tannen laws report` reads (BRIEF P6, §5.11).
"""

from __future__ import annotations

from hypothesis import settings

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


def pytest_configure(config) -> None:
    try:
        from tannen.laws.plugin import LawEvidencePlugin
    except ImportError:  # pre-implementation trees: laws still run, they just attest nothing
        return
    config.pluginmanager.register(LawEvidencePlugin(config), "tannen-law-evidence")
