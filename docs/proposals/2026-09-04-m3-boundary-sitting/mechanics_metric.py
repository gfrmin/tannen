#!/usr/bin/env python3
"""DRAFT — the governance-mechanics metric, corrected (D0106 item 3, D0145, D0171 ruling 5).

NOT INSTALLED AND NOT WIRED IN. `scripts/gen_projections.py`, `scripts/check_decisions.py`
and `scripts/_gov.py` are custody-set, so the digest line this computes is an owner act at
a sitting. This file is the measurement half, which BRIEF §9.1's metric-calibration rule
requires FIRST: land the measurement, publish one digest carrying true values, only then
compare (D0145 clause (d) — "step one is measurement, and measurement is not an owner act").

WHAT D0145 LEFT UNANSWERED, AND WHAT ANSWERS IT NOW. D0145 declined to script item 3 and
named six parameters a decision would have to fix. D0171 ruling 5 answers the one that was
blocking — measure at boundaries only — and this draft proposes the other five, each with
the measurement that motivates it (see D0173 for the series and the argument).

  1. NUMERATOR ARMS   scripts/*.py (guards) + scripts/*.sh (drivers) + tests/poison/**
                      — D0145's own arms, unchanged, so its series stays comparable.
  2. DENOMINATOR      src/tannen/**/*.py — the WHOLE package, not src/tannen/kernel.
                      Milestones deliberately alternate between kernel and shell (M2's
                      deliverable was sources.py; M3's was delta.py plus incremental.py),
                      and a kernel-only denominator misreads a shell milestone as pure
                      mechanism growth: M2 reads 5.1x against the package and 27.9x
                      against the kernel alone. The larger number is the artefact.
  3. COUNTING RULE    raw newline count of the git blob. One fixture under tests/poison/
                      is binary (a git bundle); it is counted the same way and its count
                      is reported separately so nobody has to guess (D0145 clause (b)).
  4. MEASUREMENT POINT  *-close tags only (ruling 5). Session A adds guards while the
                      kernel is frozen, so any commit-wise ratchet fires at every
                      laws-freeze BY CONSTRUCTION — that is the two-session protocol
                      working, not a regression.
  5. WHAT IS REPORTED   a PAIR of per-milestone deltas, not a ratio. D0145's first finding
                      was that the ratio is dominated by its denominator — it fell from
                      384 to 2.79 while mechanism nearly tripled — and measuring at close
                      tags does NOT fix that: the close-tag series is 11.69, 2.74, 3.62,
                      which is neither monotone nor readable. "Mechanism +1562, product
                      +308" says the thing a ratio cannot.
  6. FLAG, NOT FAIL, and no threshold yet. Three closed milestones is not a baseline. The
                      metric-calibration rule is the whole reason this is a reporter.

THE TRAP D0145 RECORDED, restated because this is the file that would spring it: a third
digest metric must go on ITS OWN COMMENT LINE WITH ITS OWN REGEX. Every existing digest
carries exactly two fields, INCLUDING tests/poison/check-decisions-ratchet/digest/
2020-01-01.md, which is MANIFEST.sha256 row 35 and custody-set — the builder can never
regenerate it. Extending `_gov.py`'s `METRICS_RE` in place silently disarms the ratchet:
the poison fixture stops emitting RATCHET BREACH and three nodes of
tests/test_governance_ratchet.py go red.

Run: python3 docs/proposals/2026-09-04-m3-boundary-sitting/mechanics_metric.py
"""

from __future__ import annotations

import subprocess
import sys

#: The numerator's three arms and the denominator, as prefix/suffix rules over a git tree.
GUARDS = ("scripts/", (".py",))
DRIVERS = ("scripts/", (".sh",))
FIXTURES = ("tests/poison/", ())
PRODUCT = ("src/tannen/", (".py",))


def _tree(ref: str) -> list[str]:
    out = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", ref], capture_output=True, text=True, check=True
    )
    return out.stdout.splitlines()


def _select(paths: list[str], rule: tuple[str, tuple[str, ...]]) -> list[str]:
    prefix, suffixes = rule
    return [p for p in paths if p.startswith(prefix) and (not suffixes or p.endswith(suffixes))]


def _count(ref: str, paths: list[str]) -> tuple[int, int]:
    """(newlines, binary file count). Binary is reported, never silently excluded."""
    total = binary = 0
    for path in paths:
        blob = subprocess.run(["git", "show", f"{ref}:{path}"], capture_output=True, check=True).stdout
        if b"\x00" in blob[:8000]:
            binary += 1
        total += blob.count(b"\n")
    return total, binary


def close_tags() -> list[str]:
    """Every `*-close` tag, in tag order. DERIVED, never enumerated (D0171 ruling 3)."""
    out = subprocess.run(
        ["git", "tag", "--list", "*-close", "--sort=creatordate"],
        capture_output=True, text=True, check=True,
    )
    return [t for t in out.stdout.split() if t]


def measure(ref: str) -> dict[str, int]:
    paths = _tree(ref)
    guards, _ = _count(ref, _select(paths, GUARDS))
    drivers, _ = _count(ref, _select(paths, DRIVERS))
    fixtures, binary = _count(ref, _select(paths, FIXTURES))
    product, _ = _count(ref, _select(paths, PRODUCT))
    return {
        "guards": guards,
        "drivers": drivers,
        "fixtures": fixtures,
        "mechanism": guards + drivers + fixtures,
        "product": product,
        "binary_fixtures": binary,
    }


def main() -> int:
    refs = close_tags() + ["HEAD"]
    print(f"{'ref':<12} {'guards':>7} {'drivers':>8} {'fixt':>6} {'MECH':>6} {'Δmech':>7} "
          f"{'product':>8} {'Δprod':>7}  ratio")
    previous: dict[str, int] | None = None
    for ref in refs:
        m = measure(ref)
        dm = m["mechanism"] - previous["mechanism"] if previous else 0
        dp = m["product"] - previous["product"] if previous else 0
        ratio = m["mechanism"] / m["product"] if m["product"] else float("nan")
        print(f"{ref:<12} {m['guards']:>7} {m['drivers']:>8} {m['fixtures']:>6} "
              f"{m['mechanism']:>6} {dm:>+7} {m['product']:>8} {dp:>+7}  {ratio:.2f}")
        previous = m
    print()
    print("HEAD's mechanism is FLAT only because the M3 sitting has not happened: the M3")
    print("driver is not drafted, and installing it adds roughly the M2 driver's 1,950")
    print("lines. Read the last row as a floor, not as a plateau.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
