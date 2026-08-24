"""The signer-role guard bites (D0050).

Before this guard, three acts passed the custody floor with "custody floor intact":
a builder-signed `m0-close`, a builder-signed `amendment-*`, and — the severe one —
deleting `brief-freeze` and re-issuing it under the builder key. The custodian verified
that each tag verified against `allowed_signers` and stopped there; both principals are
enrolled, so both satisfied it.

These tests are hermetic: they mint their own ephemeral owner/builder keys with
ssh-keygen and build throwaway repos, so nothing here depends on the real signing keys
being present (CI has neither). A guard nobody has watched fail is a guard nobody knows
works.

The custodian-visible home for this is `tests/poison/`, which is author-key territory —
a builder cannot add a fixture there. Fixture candidates are staged under
`docs/redteam/fixture-candidates/` for the owner to install at the boundary sitting.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from _gov import git_env  # noqa: E402

GUARD = REPO_ROOT / "scripts" / "check_tag_signers.py"


def sh(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Always with a sanitised environment: these tests build throwaway repos, and a
    leaked GIT_DIR would make every `git -C <tmp>` command answer about the real
    repository instead — including the one that deletes and re-mints `brief-freeze`."""
    run = subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False,
                         env=git_env())
    assert run.returncode == 0, f"{args}\n{run.stdout}\n{run.stderr}"
    return run


def make_key(tmp: Path, principal: str) -> tuple[Path, str]:
    """An ephemeral ed25519 signing key and its allowed_signers line."""
    path = tmp / f"key_{principal.split('@')[0]}"
    sh("ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", principal, "-f", str(path))
    return path, f"{principal} {path.with_suffix('.pub').read_text().strip()}"


@pytest.fixture
def world(tmp_path: Path):
    """A root carrying tag-roles.yaml + allowed_signers, and a repo whose tags we sign."""
    owner_key, owner_line = make_key(tmp_path, "owner@tannen")
    builder_key, builder_line = make_key(tmp_path, "builder@tannen")
    stranger_key, _ = make_key(tmp_path, "stranger@elsewhere")

    root = tmp_path / "root"
    (root / "governance").mkdir(parents=True)
    (root / "allowed_signers").write_text(f"{owner_line}\n{builder_line}\n")

    repo = tmp_path / "repo"
    repo.mkdir()
    sh("git", "init", "-q", "-b", "master", str(repo))
    for key, value in (("user.name", "t"), ("user.email", "builder@tannen"),
                       ("gpg.format", "ssh"), ("commit.gpgsign", "false")):
        sh("git", "-C", str(repo), "config", key, value)
    (repo / "f.txt").write_text("x\n")
    sh("git", "-C", str(repo), "add", "f.txt")
    sh("git", "-C", str(repo), "commit", "-q", "-m", "init")

    def tag(name: str, key: Path) -> str:
        sh("git", "-C", str(repo), "-c", f"user.signingkey={key}",
           "tag", "-s", name, "-m", f"{name} (test)")
        return sh("git", "-C", str(repo), "rev-parse", f"refs/tags/{name}").stdout.strip()

    def write_table(trust_object: str, unknown: str = "refuse") -> None:
        (root / "governance" / "tag-roles.yaml").write_text(
            "version: 1\n"
            "trust_root:\n"
            "  tag: brief-freeze\n"
            f"  object: {trust_object}\n"
            "  signer: owner\n"
            "roles:\n"
            "  - {pattern: brief-freeze, signer: owner}\n"
            '  - {pattern: "*-laws-freeze", signer: builder}\n'
            '  - {pattern: "*-close", signer: owner}\n'
            '  - {pattern: "amendment-*", signer: owner}\n'
            f"unknown: {unknown}\n"
        )

    def run() -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(GUARD), "--root", str(root), "--repo", str(repo)],
            capture_output=True, text=True, check=False, env=git_env(),
        )

    return type("World", (), dict(
        root=root, repo=repo, owner_key=owner_key, builder_key=builder_key,
        stranger_key=stranger_key, tag=staticmethod(tag),
        write_table=staticmethod(write_table), run=staticmethod(run),
    ))


def test_correct_assignment_passes(world):
    root_obj = world.tag("brief-freeze", world.owner_key)
    world.tag("m0-laws-freeze", world.builder_key)
    world.tag("m0-close", world.owner_key)
    world.write_table(root_obj)
    run = world.run()
    assert run.returncode == 0, run.stdout + run.stderr
    assert "every signer matches its tag class" in run.stdout


def test_builder_signed_close_tag_is_refused(world):
    """Reproduction 1 from D0050: this passed the custody floor before the guard."""
    root_obj = world.tag("brief-freeze", world.owner_key)
    world.tag("m0-close", world.builder_key)
    world.write_table(root_obj)
    run = world.run()
    assert run.returncode != 0
    assert "wrong principal (expected owner@tannen, got builder@tannen): m0-close" in run.stderr


def test_builder_signed_amendment_tag_is_refused(world):
    """Reproduction 2: a constitution-level claim wearing the same clothes."""
    root_obj = world.tag("brief-freeze", world.owner_key)
    world.tag("amendment-2026-09-01", world.builder_key)
    world.write_table(root_obj)
    run = world.run()
    assert run.returncode != 0
    assert "amendment-2026-09-01" in run.stderr and "wrong principal" in run.stderr


def test_reissued_trust_root_is_refused(world):
    """Reproduction 3, the severe one: brief-freeze deleted and re-minted by the builder.

    Both halves must fire — the object no longer matches the pin, AND the signer is
    wrong for the class. Either alone would catch this instance; the pin is what
    survives an attacker who also holds a key the table trusts for something.
    """
    original = world.tag("brief-freeze", world.owner_key)
    world.write_table(original)
    sh("git", "-C", str(world.repo), "tag", "-d", "brief-freeze")
    world.tag("brief-freeze", world.builder_key)
    run = world.run()
    assert run.returncode != 0
    assert "trust root re-issued" in run.stderr
    assert "wrong principal (expected owner@tannen, got builder@tannen)" in run.stderr


def test_unknown_tag_class_is_refused_by_default(world):
    """The part that makes this a class fix: the next hole is a tag kind nobody listed."""
    root_obj = world.tag("brief-freeze", world.owner_key)
    world.tag("release-v1", world.owner_key)
    world.write_table(root_obj)
    run = world.run()
    assert run.returncode != 0
    assert "tag class not in the signer-role table" in run.stderr
    assert "release-v1" in run.stderr


def test_unknown_tag_class_can_be_allowed_deliberately(world):
    """`unknown: allow` exists so the refusal is a policy choice recorded in the table,
    not a behaviour welded into the guard — but it is not the default."""
    root_obj = world.tag("brief-freeze", world.owner_key)
    world.tag("release-v1", world.owner_key)
    world.write_table(root_obj, unknown="allow")
    assert world.run().returncode == 0


def test_tag_signed_by_an_unenrolled_key_is_refused(world):
    root_obj = world.tag("brief-freeze", world.owner_key)
    world.tag("m1-laws-freeze", world.stranger_key)
    world.write_table(root_obj)
    run = world.run()
    assert run.returncode != 0
    assert "does not verify against allowed_signers: m1-laws-freeze" in run.stderr


def test_missing_trust_root_is_reported_not_assumed(world):
    """A repo that has not minted the trust root yet is legitimate (a fresh clone of an
    early state); one that minted a DIFFERENT one is not. The guard distinguishes."""
    world.write_table("0" * 40)
    world.tag("m0-laws-freeze", world.builder_key)
    run = world.run()
    assert run.returncode == 0, run.stdout + run.stderr
    assert "does not exist yet" in run.stdout


def test_the_real_repo_passes_its_own_table():
    """The table in governance/tag-roles.yaml describes this repo, not an ideal one."""
    run = subprocess.run([sys.executable, str(GUARD)], capture_output=True, text=True,
                         cwd=REPO_ROOT, check=False, env=git_env())
    assert run.returncode == 0, run.stdout + run.stderr
    assert "brief-freeze: owner@tannen" in run.stdout
    assert "m0-laws-freeze: builder@tannen" in run.stdout


def test_the_guard_answers_about_the_repo_it_was_given_not_GIT_DIR(monkeypatch, world):
    """A git hook exports GIT_DIR, and GIT_DIR beats `git -C <path>`.

    Without sanitising, a guard invoked from pre-commit — or aimed at a poison fixture —
    would silently report on the real repository instead of the one it was handed, and
    say OK about tags it never looked at. Found the hard way: these tests errored out
    under pre-commit while passing standalone.
    """
    root_obj = world.tag("brief-freeze", world.owner_key)
    world.tag("m0-close", world.builder_key)          # the violation lives HERE
    world.write_table(root_obj)
    monkeypatch.setenv("GIT_DIR", str(REPO_ROOT / ".git"))
    monkeypatch.setenv("GIT_INDEX_FILE", str(REPO_ROOT / ".git" / "index"))
    run = world.run()
    assert run.returncode != 0, "the guard read GIT_DIR's repo, not --repo"
    assert "m0-close" in run.stderr
