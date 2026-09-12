"""The pre-budget lock: a nonzero envelope is refused while D0240's preconditions are open.

The owner ruled (D0242) that the deferral of the CLI clamp to M5 Session A (D0241) rests on
the gap being inert here — zero ceilings, zero envelopes, no credentials, no network in any
test — and that the load-bearing element of that argument is the ABSENCE OF CREDENTIALS,
which is a property of a machine and not of this repository. Nothing in the repo enforces it.
The ruling: the deferral should carry a lock, not a hope, so D0240's three preconditions bind
the first nonzero envelope MECHANICALLY rather than documentarily.

Two of the three are prose-and-code the owner must re-sign, and no structural check can judge
prose on its semantics. They are tested the only honest way available: both files are
signature-protected (check_manifest verifies `governance/policy.yaml` and the custody set), so
"has it been corrected?" is tested as "is it still byte-identical to the version D0240 found
defective?". A differing hash implies an owner re-signature; it does NOT imply the correction
is right, and this file does not claim otherwise.

The third — the clamp — is tested behaviourally against the live parser and structurally
against `governance/laws.yaml`, never by reading source prose (the standing rules: no guard
learns another artifact's state from its prose, and none depends on a hand-maintained
enumeration — D0171 ruling (3), D0211).

[cites: D0240, D0241, D0242, D0229 item (5), BRIEF §9.2, BRIEF §5.3]
"""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

# The bytes D0240 found defective. Not a claim about what the correction should say — only
# that the artifact has not moved. Both are signature-protected, so a differing hash means
# the owner re-signed something.
DEFECTIVE_POLICY = "96988c5987917bfde693886603935769f6dbfb4ebc750423955acd3679a2b6f7"
DEFECTIVE_CHECK_MANIFEST = "dc89de2beeeca1a9b3ea23f1e9049806a69bed5de2b4afd92fd1f4268fdc9d61"

# The one node the clamp retires. NAMED, not enumerated: it is the subject of the rule, not a
# list that can drift out of date behind the guard's back (D0211 forbids the latter). L4.4's
# third `tannen run` node — the one that spends through the CLI against a budget of its own.
L4_4_CLAMPED_NODE = (
    "tests/laws/m4/test_l4_modes.py::"
    "test_l4_4_tannen_run_spend_is_the_one_spelling_that_can_call"
)

# `tannen.laws` reads two documented, non-credential variables (the evidence root and the
# plugin disable switch). It is the one stated exemption; everything else is DERIVED.
ENVIRONMENT_READING_IS_DECLARED = ("laws",)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text()) or {}


def shipped_modules(root: Path = REPO_ROOT) -> tuple[Path, ...]:
    """Every shipped module except the declared exemption — derived by walking, never listed."""
    package = root / "src" / "tannen"
    return tuple(sorted(
        path for path in package.rglob("*.py")
        if not set(path.relative_to(package).parts) & set(ENVIRONMENT_READING_IS_DECLARED)
    ))


def spend_is_authorised(root: Path = REPO_ROOT) -> bool:
    """True once any envelope or any operational ceiling is nonzero — the lock's trigger."""
    envelopes = _yaml(root / "governance" / "policy.yaml").get("budget_envelopes") or {}
    ceilings = _yaml(root / "budget.yaml").get("ceilings") or {}
    return any(v > 0 for v in envelopes.values()) or any(v > 0 for v in ceilings.values())


def run_accepts(flag: str) -> bool:
    """Whether `tannen run` accepts `flag`, decided by PARSING it, not by reading the source.

    Public API only: a flag declared nowhere makes argparse exit 2, and a flag that exists
    only in a docstring does not satisfy the clamp.
    """
    from tannen.cli import build_parser

    try:
        build_parser().parse_args(["run", "m:f", "--store", ".", flag, "x"])
    except SystemExit:
        return False
    return True


def unmet_spend_preconditions(
    root: Path = REPO_ROOT, *, override_flag: bool | None = None
) -> tuple[str, ...]:
    """D0240's preconditions still open. Empty means the first nonzero envelope may be signed."""
    has_override = run_accepts("--budget-override") if override_flag is None else override_flag
    superseded = _yaml(root / "governance" / "laws.yaml").get("superseded") or []
    retired = {entry.get("node") for entry in superseded}

    unmet = []
    if _sha256(root / "governance" / "policy.yaml") == DEFECTIVE_POLICY:
        unmet.append(
            "policy-sentence: governance/policy.yaml is byte-identical to the version whose "
            "sentence claims SpendGuard enforces the envelope operationally (D0240 item 1)"
        )
    if _sha256(root / "scripts" / "check_manifest.py") == DEFECTIVE_CHECK_MANIFEST:
        unmet.append(
            "current-envelope: scripts/check_manifest.py still compares each ceiling against "
            "the MAXIMUM envelope over all milestones (D0240 item 3, D0229 item 5)"
        )
    if L4_4_CLAMPED_NODE not in retired:
        unmet.append(
            f"successor-law: governance/laws.yaml has no superseded entry retiring "
            f"{L4_4_CLAMPED_NODE} — M5 Session A owes it (D0240 item 2, D0241)"
        )
    if not has_override:
        unmet.append(
            "clamp: `tannen run` accepts no --budget-override, so --budget is still honoured "
            "as given and the CLI is unclamped (D0240 item 2)"
        )
    return tuple(unmet)


def test_the_lock_is_not_armed_today_and_that_is_measured_not_assumed() -> None:
    """The deferral's premise, made checkable: nothing here authorises a spend yet."""
    assert not spend_is_authorised(), (
        "an envelope or ceiling went nonzero — the lock below is now load-bearing"
    )


def test_each_d0240_precondition_is_open_today_and_the_gate_names_it() -> None:
    """Non-vacuous by construction: the gate can only pass today by naming all four.

    Each identifier disappears when its precondition LANDS, and this is what says so out loud
    rather than letting the gate quietly weaken to a tautology (produce-the-failure).
    """
    open_now = {item.split(":", 1)[0] for item in unmet_spend_preconditions()}
    assert open_now == {"policy-sentence", "current-envelope", "successor-law", "clamp"}


def test_a_nonzero_envelope_is_refused_while_any_precondition_is_open() -> None:
    """The lock itself, armed against a synthetic authorisation: it must refuse, and say why."""
    assert unmet_spend_preconditions(override_flag=False), (
        "the gate admitted a spend with every precondition open"
    )


def test_the_lock_opens_only_when_all_four_are_satisfied(tmp_path: Path) -> None:
    """The positive control: a tree meeting all four returns empty.

    Without it the gate could be stuck-red — refusing for a reason that can never clear, which
    is as useless as one that never fires.
    """
    (tmp_path / "governance").mkdir()
    (tmp_path / "scripts").mkdir()
    (tmp_path / "governance" / "policy.yaml").write_text("budget_envelopes: {M4: 5}\n")
    (tmp_path / "scripts" / "check_manifest.py").write_text("# corrected\n")
    (tmp_path / "governance" / "laws.yaml").write_text(
        yaml.safe_dump({"superseded": [{"node": L4_4_CLAMPED_NODE, "successor": "L5.1"}]})
    )
    (tmp_path / "budget.yaml").write_text("ceilings: {total: 0}\n")
    assert unmet_spend_preconditions(tmp_path, override_flag=True) == ()


def test_the_derived_module_set_is_not_empty() -> None:
    """A scan over nothing passes. Prove the input set exists before trusting the verdict."""
    assert len(shipped_modules()) >= 5


def environment_reads(source: str) -> tuple[int, ...]:
    """The lines of `source` that reach for an ambient variable. Separated from the test so the
    detector itself can be shown to fire — a scan nobody has watched catch anything is not
    evidence of a clean tree (produce-the-failure)."""
    return tuple(
        node.lineno for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Attribute) and node.attr in {"environ", "getenv"}
    )


@pytest.mark.parametrize("module", shipped_modules(), ids=lambda p: p.name)
def test_no_shipped_module_reads_a_credential_from_the_environment(module: Path) -> None:
    """The half of "no credentials" that IS a repository property, so it stops being a hope.

    Absence of credentials on a machine is not enforceable here. That the code cannot pick one
    up implicitly is: credentials are constructor arguments, never ambient (BRIEF §5.3).
    """
    found = environment_reads(module.read_text())
    assert not found, f"{module.name} reads the environment at line(s) {found}"


def test_the_environment_detector_fires_on_a_module_that_does_read_one() -> None:
    """The detector's positive control. Without it, a scan that can never fire reads as clean."""
    assert environment_reads("import os\nKEY = os.environ['R2_SECRET_ACCESS_KEY']\n") == (2,)
    assert environment_reads("import os\nKEY = os.getenv('X')\n") == (2,)
    assert environment_reads("KEY = 'handed in, not reached for'\n") == ()


@pytest.mark.parametrize(
    "envelopes, ceilings, armed",
    [
        ("{M4: 0}", "{total: 0}", False),
        ("{M4: 5}", "{total: 0}", True),
        ("{M4: 0}", "{total: 5}", True),
    ],
)
def test_the_trigger_arms_on_either_a_nonzero_envelope_or_a_nonzero_ceiling(
    tmp_path: Path, envelopes: str, ceilings: str, armed: bool
) -> None:
    """The trigger's BOTH branches, which nothing else here exercises.

    Every other test in this file runs against today's all-zero tree or passes `override_flag`
    directly. So a `spend_is_authorised` that always returned False would leave the whole lock
    inert with every test still green — the exact shape of a guard whose input set is empty.
    """
    (tmp_path / "governance").mkdir()
    (tmp_path / "governance" / "policy.yaml").write_text(f"budget_envelopes: {envelopes}\n")
    (tmp_path / "budget.yaml").write_text(f"ceilings: {ceilings}\n")
    assert spend_is_authorised(tmp_path) is armed
