"""Poison fixture package: the import below deliberately violates the fixture's
import-linter contract, so `lint-imports --config tests/poison/lint-imports/pyproject.toml`
must exit non-zero with BROKEN in its output (guard liveness, BRIEF §9.1)."""

import os  # noqa: F401  — the whole point
