"""ROADMAP.md is a query, and it is a query over this commit only (D0215).

Five controls, and the third is the one that matters. `scripts/gen_roadmap.py` renders a
projection of open work by who can close it; the failure it must never repeat is the one
D0215 filed the day before this file was written — a generated artifact whose content
depends on `git tag -l` and on the wall clock, so that it is correct at the tip and wrong
everywhere else in history, and every close tag points at a commit that fails `make
verify`.

Freshness here is byte-equality against a fresh render, not a header-hash comparison.
That is deliberately stronger than `check_decisions.py`'s input-hash check: a hash in the
header cannot notice a hand edit to the body (`test_stale_projection_detected` records
that exact hole for CONCEPTS.md). The cost of the stronger check is that it trusts the
generator — a generator rendering the wrong thing would render it into both sides — which
is why T2 through T4 exercise the generator's behaviour independently of its output.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from gen_roadmap import (  # noqa: E402
    ROADMAP_MARKER,
    read_roadmap_header,
    render,
    roadmap_inputs,
)


def _git(*args: str, **kwargs) -> subprocess.CompletedProcess:
    """git with every GIT_* stripped, so `-C` is actually authoritative about which
    repository is touched. Under pre-commit, GIT_DIR and GIT_INDEX_FILE point at the real
    repo, and a fixture repo would otherwise write into the real index."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    return subprocess.run(["git", *args], check=True, env=env, **kwargs)


def minimal_tree(dest: Path) -> Path:
    """A tree containing EXACTLY the generator's declared inputs, and nothing else.

    Doubles as an assertion: if `render` ever reads a file outside `roadmap_inputs`, every
    test built on this helper fails with a missing file rather than passing quietly. It
    also gives T3 a tree with no `.git` directory for free.
    """
    dest.mkdir(parents=True, exist_ok=True)
    for src in roadmap_inputs(REPO_ROOT):
        target = dest / src.relative_to(REPO_ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, target)
    return dest


# ----------------------------------------------------------------- T1: freshness
def test_roadmap_is_fresh() -> None:
    """ROADMAP.md is exactly what the generator produces from this commit."""
    committed = (REPO_ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    assert committed == render(REPO_ROOT), (
        "ROADMAP.md is stale or hand-edited — run "
        "`.venv/bin/python -I -P scripts/gen_roadmap.py`; never hand-edit. "
        "Nothing regenerates it automatically: .pre-commit-config.yaml and Makefile are "
        "both custody-set (D0215's sibling record)."
    )


def test_the_header_carries_the_input_hash() -> None:
    """The header parses and names this marker, not gen_projections'."""
    header = read_roadmap_header(REPO_ROOT / "ROADMAP.md")
    assert header is not None and len(header) == 64, (
        f"ROADMAP.md's header is missing or malformed: {header!r}"
    )
    assert ROADMAP_MARKER in (REPO_ROOT / "ROADMAP.md").read_text(
        encoding="utf-8").splitlines()[0]


# ------------------------------------------------- T2: every declared input is load-bearing
def input_group(relpath: str) -> str:
    """The declared input a path belongs to. Derived from the path, never listed."""
    if relpath.startswith("decisions/"):
        return "decisions/*.yaml.sig" if relpath.endswith(".sig") else "decisions/*.yaml"
    if relpath.startswith("concepts/"):
        return "concepts/*.yaml"
    return relpath


def _edit(path: Path, old: str, new: str) -> None:
    """Replace once, and FAIL if the anchor was not there.

    A control that silently edits nothing is a control that cannot fail, which is the
    defect class D0196/D0198/D0199 were each caught by. The perturbation asserting its
    own arrival is what makes the test below mean anything.
    """
    text = path.read_text(encoding="utf-8")
    assert old in text, f"perturbation anchor absent from {path.name}: {old!r}"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _flip_a_record(root: Path) -> None:
    victim = next(p for p in sorted((root / "decisions").glob("*.yaml"))
                  if "\ntier: A\n" in p.read_text(encoding="utf-8")
                  and "\nstatus: accepted\n" in p.read_text(encoding="utf-8"))
    _edit(victim, "\nstatus: accepted\n", "\nstatus: blocked-on-owner\n")


def _drop_a_signature(root: Path) -> None:
    """Delete a signature that a SECTION depends on, derived rather than picked.

    The first draft deleted the alphabetically-first `.sig`, whose record appears in no
    section — so the control passed while proving nothing, and the body comparison caught
    it. A signature only reaches the output through §3's "Signed" column or §5's "who can
    apply", so choose one whose record is in §5: a documentary `type: file` binding on an
    already-frozen target.
    """
    import yaml

    frozen = {
        line.split(maxsplit=1)[1].strip()
        for line in (root / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }
    for record_path in sorted((root / "decisions").glob("*.yaml")):
        sig = record_path.with_name(record_path.name + ".sig")
        if not sig.exists():
            continue
        record = yaml.safe_load(record_path.read_text(encoding="utf-8"))
        for binding in record.get("bindings") or []:
            target = binding.get("target", "").split("#", 1)[0].split("::", 1)[0].strip()
            if (binding.get("type") == "file"
                    and binding.get("strength") == "documentary"
                    and target in frozen):
                sig.unlink()
                return
    raise AssertionError(
        "no signed record carries a documentary file binding on a frozen target, so this "
        "control cannot reach §5 — the section or the corpus has changed shape"
    )


def _downgrade_a_concept(root: Path) -> None:
    victim = next(p for p in sorted((root / "concepts").glob("*.yaml"))
                  if "\ngrade: P\n" in p.read_text(encoding="utf-8"))
    _edit(victim, "\ngrade: P\n", "\ngrade: L\n")


def _drop_a_manifest_row(root: Path) -> None:
    path = root / "MANIFEST.sha256"
    kept = [ln for ln in path.read_text(encoding="utf-8").splitlines()
            if not ln.endswith("  docs/specs/m0.md")]
    assert len(kept) < len(path.read_text(encoding="utf-8").splitlines())
    path.write_text("\n".join(kept) + "\n", encoding="utf-8")


def _drop_a_custody_row(root: Path) -> None:
    path = root / "governance" / "custody.sha256"
    kept = [ln for ln in path.read_text(encoding="utf-8").splitlines()
            if not ln.endswith("  Makefile")]
    assert len(kept) < len(path.read_text(encoding="utf-8").splitlines())
    path.write_text("\n".join(kept) + "\n", encoding="utf-8")


#: One perturbation per declared input, each chosen to be SEMANTICALLY visible rather
#: than a stray byte. Appending junk would pass vacuously for every input, because the
#: header carries an input hash over all of them — so the assertion below compares the
#: BODY with the header line stripped, and the perturbation has to reach a section.
PERTURBATIONS = {
    "BRIEF.md": lambda r: _edit(r / "BRIEF.md", "## 8. ", "## 8. \n\nPERTURBED ARC.\n\n## 8x. "),
    "MANIFEST.sha256": _drop_a_manifest_row,
    ".pre-commit-config.yaml": lambda r: (r / ".pre-commit-config.yaml").write_text(
        (r / ".pre-commit-config.yaml").read_text(encoding="utf-8")
        + "\n# entry: scripts/gen_roadmap.py\n", encoding="utf-8"),
    "governance/custody.sha256": _drop_a_custody_row,
    "governance/policy.yaml": lambda r: _edit(
        r / "governance" / "policy.yaml", "\n  M4: 0\n", "\n  M4: 7\n"),
    "governance/tier-c.yaml": lambda r: _edit(
        r / "governance" / "tier-c.yaml", "\n    - tests/laws\n", "\n"),
    "decisions/*.yaml": _flip_a_record,
    "decisions/*.yaml.sig": _drop_a_signature,
    "concepts/*.yaml": _downgrade_a_concept,
}


def test_every_declared_input_has_a_control() -> None:
    """Derived completeness: adding an input without a control reddens here.

    The standing rule is that no guard may depend on a hand-maintained enumeration.
    PERTURBATIONS *is* hand-written — so this test derives the truth from
    `roadmap_inputs()` and asserts the two agree, in both directions. That is the same
    shape as `test_every_installed_fixture_is_exercised_by_this_suite` (D0213).
    """
    declared = {input_group(str(p.relative_to(REPO_ROOT)))
                for p in roadmap_inputs(REPO_ROOT)}
    missing = sorted(declared - PERTURBATIONS.keys())
    assert not missing, (
        f"declared input(s) with no control: {missing} — an input nothing perturbs is an "
        "input that may be hashed and never read, which is how a projection goes "
        "stale-but-green"
    )
    stale = sorted(PERTURBATIONS.keys() - declared)
    assert not stale, (
        f"control(s) for input(s) no longer declared: {stale} — the mapping has rotted"
    )


@pytest.mark.parametrize("group", sorted(PERTURBATIONS), ids=lambda s: s)
def test_every_declared_input_reaches_the_body(group: str, tmp_path: Path) -> None:
    """Perturbing each declared input must change a SUBSTANTIVE section of ROADMAP.md.

    Two parts of the output are excluded from the comparison, and both exclusions were
    forced by watching this test fail to fail. The header line carries an input hash over
    every input; §9 Sources prints each input's sha256. Either one alone makes *any*
    perturbation move the bytes, so a comparison that included them would pass for an
    input that is hashed and read by nothing — which is the exact stale-but-green hole
    this test exists to close. Compare §1 through §8 only.
    """
    root = minimal_tree(tmp_path / "tree")

    def substance(text: str) -> str:
        return text.split("\n", 1)[1].split("## 9. Sources", 1)[0]

    before = substance(render(root))
    PERTURBATIONS[group](root)
    assert substance(render(root)) != before, (
        f"{group} is a declared input, but perturbing it changed nothing outside the "
        "header and the Sources table — it is hashed and unread, so ROADMAP.md would go "
        "stale-but-green when it changes"
    )


# --------------------------------------------- T3: the D0215 control — no clock, no refs
def test_the_output_does_not_move_with_the_clock(tmp_path: Path) -> None:
    """`--today` is accepted and inert. A parameter proven not to matter is a stronger
    claim than one that was never offered."""
    import datetime as dt

    root = minimal_tree(tmp_path / "tree")
    assert render(root, dt.date(2020, 1, 1)) == render(root, dt.date(2030, 1, 1))


def test_the_output_does_not_need_a_repository(tmp_path: Path) -> None:
    """A tree with no `.git` renders identically to the real one.

    If any ref or reflog entered the output, this differs or raises.
    """
    root = minimal_tree(tmp_path / "tree")
    assert not (root / ".git").exists()
    assert render(root) == render(REPO_ROOT)


def test_the_output_does_not_move_with_the_tag_set(tmp_path: Path) -> None:
    """THE D0215 CONTROL, in the shape D0215 measured it.

    D0215's own evidence was CI run 34434680220: commit af41fe8 passed on 2026-09-10 and
    the byte-identical re-run failed on 2026-09-11, because `m3-close` had been minted in
    between and `DECISIONS.md`'s attention-receipt line is computed from `git tag -l`.
    Here the same perturbation is applied deliberately: mint a boundary tag the real repo
    has never had, and assert the rendered bytes do not move.
    """
    root = minimal_tree(tmp_path / "tree")
    before = render(root)

    _git("-C", str(root), "init", "-q", "--initial-branch=master", capture_output=True)
    _git("-C", str(root), "-c", "user.email=t@example.com", "-c", "user.name=t",
         "commit", "-q", "--allow-empty", "-m", "fixture", capture_output=True)
    _git("-C", str(root), "tag", "m9-close", capture_output=True)
    assert "m9-close" in _git("-C", str(root), "tag", "-l",
                              capture_output=True, text=True).stdout, "control is inert"

    assert render(root) == before, (
        "minting a boundary tag changed ROADMAP.md — the generator is reading refs, "
        "which is exactly the defect D0215 filed (every close tag now points at a commit "
        "that fails `make verify`)"
    )


# ------------------------------------------------- T4: the blindness fix actually queries
def test_a_tier_a_record_blocked_on_owner_reaches_the_queue(tmp_path: Path) -> None:
    """§3's whole purpose: a Tier-A record recorded `blocked-on-owner` must appear.

    The digest cannot see one — `gen_projections` filters `tier == "C"` before looking at
    status, and so does the sitting driver. BRIEF §9.2 classifies tiers by reversibility,
    not by custody, so a reversible decision whose artifact is custody-set still needs the
    owner's key. Both directions are asserted: a section that lists everything is not a
    query.
    """
    root = minimal_tree(tmp_path / "tree")
    victim = next(
        p for p in sorted((root / "decisions").glob("*.yaml"))
        if "\ntier: A\n" in p.read_text(encoding="utf-8")
        and "\nstatus: accepted\n" in p.read_text(encoding="utf-8")
    )
    record_id = f"D{victim.stem[:4]}"

    assert record_id not in _queue_section(render(root)), (
        f"{record_id} is `accepted` and already appears in the owner queue"
    )
    victim.write_text(
        victim.read_text(encoding="utf-8").replace(
            "\nstatus: accepted\n", "\nstatus: blocked-on-owner\n", 1),
        encoding="utf-8",
    )
    assert record_id in _queue_section(render(root)), (
        f"{record_id} was recorded `blocked-on-owner` at Tier A and the owner queue did "
        "not list it — §3 is filtering by tier, which is the defect it exists to fix"
    )


def _queue_section(text: str) -> str:
    """§3 only, so a record named elsewhere in the document cannot fake a pass."""
    start = text.index("## 3. The owner queue")
    return text[start:text.index("\n## 4.", start)]


# ------------------------------------------------------- T5: nothing untracked is an input
def test_no_input_is_a_git_ignored_path() -> None:
    """No declared input may be git-ignored — D0215's defect wearing a different hat.

    An ignored file is absent from a fresh clone, so an artifact reading one would render
    differently for the next person than it does here, exactly as `DECISIONS.md` renders
    differently once a tag is minted. `.gitignore` covers `evidence/`, `.reference/` and
    `.venv/` among others, and each is a plausible thing for a generator to reach into:
    law evidence and the parked cross-repo scoping document both live there.

    FIRST DRAFT ASSERTED TRACKEDNESS AND WAS WRONG. `git ls-files` lists staged and
    committed paths, so it reddened for every new `decisions/*.yaml` in the window between
    writing the record and staging it — which is most of a working session. `make verify`
    caught it, on this very commit: D0216 and D0217 were the untracked inputs. Ignoredness
    is the property actually at stake, and it does not move when a file is staged.
    """
    declared = sorted(str(p.relative_to(REPO_ROOT)) for p in roadmap_inputs(REPO_ROOT))
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "check-ignore", "--stdin"],
        input="\n".join(declared), capture_output=True, text=True,
        env={k: v for k, v in os.environ.items() if not k.startswith("GIT_")},
    )
    ignored = sorted(name for name in result.stdout.splitlines() if name.strip())
    assert not ignored, (
        f"gen_roadmap reads git-ignored file(s): {ignored} — they are absent from a fresh "
        "clone, so the output would differ for the next reader"
    )
