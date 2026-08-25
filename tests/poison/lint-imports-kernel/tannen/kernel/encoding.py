"""Poison: the same violation in a second kernel module, so a narrowing of
`source_modules` to a single module cannot excuse the whole package."""

import pathlib  # noqa: F401 — kernel-no-io
import time     # noqa: F401 — kernel-no-clock
