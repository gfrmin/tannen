"""CLAUDE.md tells every fresh session which commands to run before ending an
implementation session. Nothing checked that those commands work.

D0108 is the instance: the verification block says `uv run lint-imports`, and run exactly
as written it prints "Could not read any configuration." and reads NO contracts, because
the contracts moved to governance/importlinter.toml under D0063/RT-02 and only the
Makefile and scripts/custodian.sh were updated to pass `--config`. The guard was fine; the
instruction was stale, and stale in the direction that reads as green.

This file turns that instance into a standing detector, the same move the provenance
homomorphism law made for `anti_join`: compare what the manual TELLS you to run against
what `make verify` — the gate CI actually runs — DOES run, and fail on any divergence
that changes what gets checked.

It deliberately does not execute the commands. `make verify` takes fifteen-odd minutes and
contains this suite, so running it from inside itself is not available. What is available,
and is what went wrong, is a comparison of the two lists.

Both CLAUDE.md and the Makefile are custody-set members (governance/tier-c.yaml) and
MANIFEST-frozen. This file only READS them; it changes nothing and needs no signature.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: Empty since the M1 boundary sitting, where D0108's one-line fix to CLAUDE.md landed and
#: this entry was deleted in the same step (D0113). The map stays as the declared home for a
#: tolerated divergence: a new entry needs a decision record saying why the manual and the
#: gate are allowed to disagree, and the tests below keep one honest once it exists.
KNOWN_DIVERGENCES: dict[tuple[str, str | None, str | None], str] = {}


def _repo_text(name: str, root: Path = ROOT) -> str:
    return (root / name).read_text(encoding="utf-8")


def _identity(command: str) -> str | None:
    """What a command line actually CHECKS, independent of how it is spelled. The two files
    invoke the same guards very differently on purpose — the Makefile runs
    `.venv/bin/python -I -P scripts/x.py` because the floor may depend only on OS tools and
    literally-named paths (D0063 ruling 3), while CLAUDE.md spells the same thing
    `uv run python scripts/x.py`. Comparing the raw lines would be noise; comparing what
    they run is the question."""
    script = re.search(r"scripts/[\w.]+\.(?:py|sh)", command)
    if script:
        return script.group(0)
    if "lint-imports" in command or "lint_imports_command" in command:
        return "import-linter"
    if re.search(r"\btannen laws report\b", command):
        return "tannen laws report"
    if re.search(r"\bpytest\b", command):
        return "pytest"
    return None


def _config_of(command: str) -> str | None:
    """The `--config <path>` a command carries, if any. This is the dimension D0108 lives
    on: same tool, same intent, different answer to "configured with what?"."""
    match = re.search(r"--config\s+(\S+)", command)
    return match.group(1) if match else None


def documented_checks(root: Path = ROOT) -> dict[str, str]:
    """The commands in CLAUDE.md's "Verification" fenced block, by identity."""
    text = _repo_text("CLAUDE.md", root)
    heading = re.search(r"^##+ *Verification.*$", text, re.MULTILINE)
    assert heading, "CLAUDE.md has no Verification section — the manual changed shape"
    block = re.search(r"```[^\n]*\n(.*?)```", text[heading.end() :], re.DOTALL)
    assert block, "CLAUDE.md's Verification section has no fenced command block"
    found: dict[str, str] = {}
    for raw in block.group(1).splitlines():
        command = raw.split("#", 1)[0].strip()
        identity = _identity(command) if command else None
        if identity:
            found[identity] = command
    return found


def verify_target(root: Path = ROOT) -> dict[str, str]:
    """The commands in the Makefile's `verify` target, by identity."""
    text = _repo_text("Makefile", root)
    body = re.search(r"^verify:.*?\n((?:\t.*\n|\n)*)", text, re.MULTILINE)
    assert body, "Makefile has no verify target — the gate changed shape"
    found: dict[str, str] = {}
    for raw in body.group(1).splitlines():
        command = raw.strip()
        identity = _identity(command) if command.startswith("$") or command else None
        if identity:
            found[identity] = command
    return found


def test_the_manual_and_the_gate_both_parse() -> None:
    """A detector that silently matched nothing would be worse than none at all — the exact
    failure mode D0108 is an instance of. Pin that both sides were actually read."""
    documented, gate = documented_checks(), verify_target()
    assert len(documented) >= 4, f"parsed too few commands from CLAUDE.md: {documented}"
    assert len(gate) >= 6, f"parsed too few commands from the Makefile: {gate}"
    assert "import-linter" in documented and "import-linter" in gate


def test_every_documented_check_is_in_make_verify() -> None:
    """CLAUDE.md may not tell a session to run something the gate does not. The reverse is
    fine and expected: `make verify` also runs check_tag_signers, check_receipts and the
    custodian, which the manual's five-check list does not name."""
    missing = sorted(set(documented_checks()) - set(verify_target()))
    assert not missing, (
        f"CLAUDE.md documents checks that `make verify` does not run: {missing}. "
        "Either the gate lost a check or the manual gained one that does not exist."
    )


def test_documented_checks_are_configured_the_way_the_gate_configures_them() -> None:
    """The D0108 dimension. Same tool, same intent — but a guard whose configuration is not
    passed reads no configuration at all, exits non-zero for an unrelated reason, and looks
    from the outside like a check that ran."""
    documented, gate = documented_checks(), verify_target()
    divergences = {}
    for identity, command in documented.items():
        if identity not in gate:
            continue  # the test above owns that case
        mine, theirs = _config_of(command), _config_of(gate[identity])
        if mine != theirs:
            divergences[(identity, mine, theirs)] = command

    unexpected = {k: v for k, v in divergences.items() if k not in KNOWN_DIVERGENCES}
    assert not unexpected, (
        "CLAUDE.md configures a check differently from `make verify`:\n"
        + "\n".join(
            f"  {identity}: manual passes --config {mine!r}, gate passes {theirs!r}\n"
            f"    manual line: {command}"
            for (identity, mine, theirs), command in unexpected.items()
        )
        + "\nA session following the manual would not be checking what it thinks it is."
    )

    fixed = sorted(KNOWN_DIVERGENCES[k] for k in KNOWN_DIVERGENCES if k not in divergences)
    assert not fixed, (
        f"{', '.join(fixed)} is FIXED — CLAUDE.md and `make verify` now agree. "
        "Delete the entry from KNOWN_DIVERGENCES in this file; the record can be closed. "
        "This failure is the good outcome, not a regression."
    )


# ------------------------------------------------- the detector, watched failing

_FAKE_MANUAL = """\
## Verification

```
uv run python scripts/check_manifest.py
{lint_line}
```
"""

_FAKE_MAKEFILE = """\
verify:
\t$(PY) -I -P scripts/check_manifest.py
\t$(PY) -I -P -c 'lint_imports_command()' --config governance/importlinter.toml

other:
\t@echo unrelated
"""


def _fake_repo(tmp_path: Path, lint_line: str) -> Path:
    (tmp_path / "CLAUDE.md").write_text(_FAKE_MANUAL.format(lint_line=lint_line))
    (tmp_path / "Makefile").write_text(_FAKE_MAKEFILE)
    return tmp_path


def test_the_detector_catches_a_missing_config(tmp_path: Path) -> None:
    """D0108's own shape, reproduced against fixtures: the manual names the tool but not
    its configuration. Without this, the comparison above could be vacuously true and
    nobody would know — which is the failure mode the whole file exists to prevent."""
    root = _fake_repo(tmp_path, "uv run lint-imports")
    documented, gate = documented_checks(root), verify_target(root)
    assert set(documented) == {"scripts/check_manifest.py", "import-linter"}
    assert _config_of(documented["import-linter"]) is None
    assert _config_of(gate["import-linter"]) == "governance/importlinter.toml"


def test_the_detector_is_quiet_when_the_manual_agrees(tmp_path: Path) -> None:
    """The other direction: with the config passed, there is nothing to report. A detector
    that fires either way is not a detector."""
    root = _fake_repo(tmp_path, "uv run lint-imports --config governance/importlinter.toml")
    documented, gate = documented_checks(root), verify_target(root)
    for identity, command in documented.items():
        assert _config_of(command) == _config_of(gate[identity])


def test_the_detector_catches_a_documented_check_the_gate_does_not_run(tmp_path: Path) -> None:
    """The other failure the manual can have: telling a session to run a guard that is not
    in the gate at all."""
    root = _fake_repo(tmp_path, "uv run python scripts/check_nonexistent.py")
    missing = set(documented_checks(root)) - set(verify_target(root))
    assert missing == {"scripts/check_nonexistent.py"}


def test_the_tolerance_list_is_empty_and_any_entry_in_it_names_a_real_command() -> None:
    """The tolerance map, checked at both of its sizes, without vanishing at the empty one.

    A tolerance entry that no longer matches anything real would silence the detector
    quietly, so each one must name a check both files still contain. And an EMPTY map — the
    state since the M1 sitting deleted D0108's entry (D0113) — has to report as a PASS that
    says the set is empty, not as an absence.

    This was `@pytest.mark.parametrize("identity", sorted(KNOWN_DIVERGENCES)[:])`, and
    pytest given an empty parameter set SKIPS, with the reason "got empty parameter set for
    (identity)". That reason is not on `check_decisions.ALLOWED_SKIP_REASON_PREFIXES` (one
    entry, "S-pending: "), so the next FILE-level pytest binding on this file — the repo's
    dominant binding form — would have failed on an unexplained skip from a test that was
    behaving correctly (D0124; applied here per D0131 item 6). Widening that allow-list was
    the other option and is the worse one: the list is the guard's whole discrimination, and
    admitting a pytest-generated string admits every future empty parametrize including the
    ones that are real defects. This is the D0116 shape instead — a check whose input set is
    empty says the set is empty rather than dropping out of the run.
    """
    documented, gate = documented_checks(), verify_target()
    stale = sorted(
        f"{name} (tolerated by {record})"
        for (name, _, _), record in KNOWN_DIVERGENCES.items()
        if name not in documented or name not in gate
    )
    assert not stale, (
        f"KNOWN_DIVERGENCES tolerates a divergence on a check that is no longer in both "
        f"files: {stale}. A tolerance naming nothing real silences the detector quietly — "
        "delete the entry, or correct the check identity it names."
    )
    assert not KNOWN_DIVERGENCES, (
        f"KNOWN_DIVERGENCES is not empty: {sorted(KNOWN_DIVERGENCES.values())}. An entry "
        "means CLAUDE.md and `make verify` are allowed to disagree, which needs a decision "
        "record saying why — cite it and relax this assertion in the same change. The "
        "empty list is the intended end state, so this failure is the reminder, not a "
        "regression."
    )


# --------------------------------------------------------------------------------------
# The same shape, one level down: what the PACKAGE says about its environment versus the
# interpreter this repository is actually proven against.
#
# D0191 is the instance. `pyproject.toml` declared `requires-python = ">=3.12"`, and that
# was never true: the frozen M1 replay law runs its fixture in fresh interpreters via
# `python -c`, the kernel hashes a transform's SOURCE TEXT before admitting it to a graph
# (BRIEF §5.1), and on 3.12 `inspect.getsource` cannot recover source for `-c` code — so
# `transform.register` raises. It could not be falsified by any local run, because a local
# run never chose 3.12. It took the first-ever CI run, on a machine that was not the
# builder's, to pick Ubuntu's 3.12.3 and go red.
#
# `.python-version` was added as the fix and made the red thing green. The untrue sentence
# survived, because a pin is not a correction. This is that sentence's detector.
# --------------------------------------------------------------------------------------


def declared_python_floor(root: Path = ROOT) -> str:
    """The lower bound `pyproject.toml` advertises to anyone installing this package."""
    text = _repo_text("pyproject.toml", root)
    match = re.search(r"^requires-python\s*=\s*\"[^0-9]*([0-9]+\.[0-9]+)", text, re.MULTILINE)
    assert match, "pyproject.toml has no parseable requires-python — the metadata changed shape"
    return match.group(1)


def pinned_interpreter(root: Path = ROOT) -> str:
    """The interpreter every environment actually resolves — uv reads this file, locally
    and in CI alike."""
    return _repo_text(".python-version", root).strip()


def test_the_declared_python_floor_is_the_interpreter_the_repo_pins() -> None:
    """One interpreter is proven; advertising a lower one is a claim nothing tests.

    The frozen law suite is green on exactly the version `.python-version` names. A floor
    below it tells an installer that some other interpreter will work, and the only place
    that claim can be falsified is a machine the builder does not have — which is precisely
    how D0191 reached the first public CI run undetected."""
    floor, pinned = declared_python_floor(), pinned_interpreter()
    assert floor == pinned, (
        f"pyproject.toml advertises >={floor} but this repository is proven only against "
        f"{pinned} (.python-version). Raise the floor, or freeze and pass the laws on "
        f"{floor} — do not leave the package claiming an environment nothing runs."
    )


def _fake_python_metadata(tmp_path: Path, floor: str, pinned: str) -> Path:
    (tmp_path / "pyproject.toml").write_text(
        f'[project]\nname = "x"\nrequires-python = ">={floor}"\n'
    )
    (tmp_path / ".python-version").write_text(f"{pinned}\n")
    return tmp_path


def test_the_floor_detector_catches_a_floor_below_the_pin(tmp_path: Path) -> None:
    """D0191's own state, reproduced: floor 3.12, pin 3.13. Watched failing here, because a
    guard that has never been seen to fail is not yet a guard (CONTRIBUTING.md)."""
    root = _fake_python_metadata(tmp_path, floor="3.12", pinned="3.13")
    assert declared_python_floor(root) == "3.12"
    assert pinned_interpreter(root) == "3.13"
    assert declared_python_floor(root) != pinned_interpreter(root)


def test_the_floor_detector_is_quiet_when_they_agree(tmp_path: Path) -> None:
    """The other direction. A detector that fires either way is not a detector."""
    root = _fake_python_metadata(tmp_path, floor="3.13", pinned="3.13")
    assert declared_python_floor(root) == pinned_interpreter(root)


# ------------------------------------------------------------- counts stated in prose
# Owner ruling (3) of 2026-09-10 extends the standing rule against hand-maintained
# enumerations (D0171 ruling 3) from guards to PROSE: "load-bearing counts and ETAs in
# generated or operator-facing documents are derived at generation time or not stated."
#
# The instance was this repository's own M3 boundary-sitting README, which described the
# driver as having 24 steps for three commits after it grew its 25th and 26th — in the one
# document whose distinguishing virtue is measuring rather than asserting. Its sibling defect
# landed the same week: the driver advertised "35-40 minutes" and "712 tests" for a gate that
# is 842 tests and, after the cp that installs it, seven lines. Nothing could catch either.
# Prose is not executable, so the enumeration rule had no purchase on it.
#
# This is the purchase. The pairing is derived, not listed: every boundary-sitting proposal
# directory holds its own driver beside its own README, so the glob finds the pairs and a
# new milestone is covered the day its directory exists. `say "Step ` at column zero is the
# driver's own step header — the same anchor its --abort-at breadcrumb counts — so this
# compares the prose against the artifact rather than against another summary of it.

#: "all 26 steps" and "a 26-step ceremony" are the two shapes these READMEs actually use.
_STEP_CLAIM = re.compile(r"\b(?:all\s+)?(\d+)[- ]steps?\b")


def driver_step_count(driver: Path) -> int:
    """How many steps a boundary driver announces, counted from the driver."""
    return len(re.findall(r'^say "Step ', driver.read_text(), re.MULTILINE))


def _sitting_proposals(root: Path = ROOT) -> list[tuple[Path, Path]]:
    """(driver, README) for every boundary-sitting proposal that has both."""
    pairs = []
    for driver in sorted(root.glob("docs/proposals/*boundary-sitting/boundary_sitting.sh")):
        readme = driver.with_name("README.md")
        if readme.exists():
            pairs.append((driver, readme))
    return pairs


def test_a_step_count_stated_in_prose_matches_the_driver_it_describes() -> None:
    """A README that names a step count names the right one.

    The failure this prevents is not a typo. A stale count in the proposal README is the
    surface an owner reads to decide whether the ceremony they are about to run is the one
    that was rehearsed, and it was wrong by two for three commits without anything noticing
    (D0206's neighbourhood, owner ruling (3) of 2026-09-10)."""
    pairs = _sitting_proposals()
    assert pairs, "no boundary-sitting proposal directories found — this guard reads nothing"
    wrong = []
    for driver, readme in pairs:
        actual = driver_step_count(driver)
        for claimed in _STEP_CLAIM.findall(readme.read_text()):
            if int(claimed) != actual:
                wrong.append(f"{readme.relative_to(ROOT)} says {claimed} steps; "
                             f"{driver.relative_to(ROOT)} announces {actual}")
    assert not wrong, (
        "a step count stated in prose disagrees with the driver it describes:\n  "
        + "\n  ".join(wrong)
        + "\nDerive it or drop it — do not re-type it (owner ruling (3), 2026-09-10)."
    )


def _fake_proposal(tmp_path: Path, steps: int, claimed: int) -> Path:
    d = tmp_path / "docs" / "proposals" / "2099-01-01-mX-boundary-sitting"
    d.mkdir(parents=True)
    body = "".join(f'say "Step {i} — something"\n' for i in range(steps))
    (d / "boundary_sitting.sh").write_text("#!/usr/bin/env bash\n" + body)
    (d / "README.md").write_text(f"The driver walks all {claimed} steps.\n")
    return tmp_path


def test_the_step_count_detector_catches_the_readme_that_went_stale(tmp_path: Path) -> None:
    """The real defect reproduced: a driver at 26, a README still saying 24. Watched failing
    here, because a guard nobody has seen fail is not yet a guard (CONTRIBUTING.md)."""
    root = _fake_proposal(tmp_path, steps=26, claimed=24)
    (driver, readme), = _sitting_proposals(root)
    assert driver_step_count(driver) == 26
    assert _STEP_CLAIM.findall(readme.read_text()) == ["24"]


def test_the_step_count_detector_is_quiet_when_they_agree(tmp_path: Path) -> None:
    """The other direction. A detector that fires either way is not a detector."""
    root = _fake_proposal(tmp_path, steps=26, claimed=26)
    (driver, readme), = _sitting_proposals(root)
    assert [int(c) for c in _STEP_CLAIM.findall(readme.read_text())] == [driver_step_count(driver)]


def test_the_step_count_detector_reads_a_non_empty_input() -> None:
    """And the input set is non-empty in the REAL tree, not only in a fixture. A guard whose
    corpus is empty passes for the same reason a correct one does — the failure mode this
    milestone recorded a dozen times."""
    pairs = _sitting_proposals()
    assert len(pairs) >= 3, f"expected every milestone's proposal; found {len(pairs)}"
    counts = {driver.parent.name: driver_step_count(driver) for driver, _ in pairs}
    assert all(n > 0 for n in counts.values()), counts
