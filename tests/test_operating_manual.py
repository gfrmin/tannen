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

import pytest

ROOT = Path(__file__).resolve().parents[1]

#: The one divergence that exists today, and why it is still here. D0108 is Tier C: the fix
#: is one line in CLAUDE.md, which is frozen AND custody-set, so only the owner may make it.
#: When they do, this test fails with the message below and the entry gets deleted in the
#: same sitting. A SECOND entry should never be added without a decision record saying why.
KNOWN_DIVERGENCES = {
    ("import-linter", None, "governance/importlinter.toml"): "D0108",
}


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


@pytest.mark.parametrize("identity", sorted(KNOWN_DIVERGENCES)[:])
def test_a_known_divergence_still_names_a_real_command(identity) -> None:
    """A tolerance entry that no longer matches anything real would silence the detector
    quietly. Require each one to name a check both files still contain."""
    name = identity[0]
    assert name in documented_checks(), f"{name} is no longer documented in CLAUDE.md"
    assert name in verify_target(), f"{name} is no longer in the Makefile's verify target"
