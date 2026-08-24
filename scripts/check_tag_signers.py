#!/usr/bin/env python3
"""check_tag_signers.py — the right principal signed the right class of tag.

The custody floor verifies that every tag verifies against `allowed_signers`, and that
no builder-signed tag predates its delegation's blessing (D0036). Neither check looks at
WHICH principal signed WHICH kind of tag, and both principals are enrolled — so before
this guard existed, a builder-signed `m0-close`, a builder-signed `amendment-*`, and a
builder re-issue of `brief-freeze` itself all passed with "custody floor intact"
(decision D0050, reproductions in docs/proposals/2026-08-24-custodian-signer-role-table.md).

This lives in scripts/ rather than inside scripts/custodian.sh on purpose: the custodian
is trust-root, author-key territory, and every line added to it is a line the owner must
review and the poison corpus must keep honest. Keeping the *policy* in
governance/tag-roles.yaml and the *logic* here leaves the custodian with a two-line
invocation, and makes this guard testable and poisonable like the other four.

Exits non-zero on any violation.
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

# Run under `python -I -P` (conferral ruling 3, D0063): isolated mode ignores
# PYTHONPATH, PYTHONHOME and user site-packages, and -P stops any directory being
# prepended to sys.path implicitly — including this script's own. The floor may depend
# only on tools the OS provides and paths named literally, so the one path this guard
# needs is named literally here, derived from __file__ rather than inherited.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _gov import Failures, REPO_ROOT, git_env, load_yaml, owner_key_enrolled  # noqa: E402

#: `git verify-tag` prints e.g. `Good "git" signature for owner@tannen with ED25519 ...`
SIGNER_RE = re.compile(r'signature for (\S+)')


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True, check=False, env=git_env())


def verify_tag(repo: Path, signers: Path, tag: str) -> tuple[bool, str]:
    """(verified, signing principal). The principal is '' when verification failed."""
    run = subprocess.run(
        ["git", "-C", str(repo), "-c", "gpg.format=ssh",
         "-c", f"gpg.ssh.allowedSignersFile={signers}", "verify-tag", tag],
        capture_output=True, text=True, check=False, env=git_env(),
    )
    out = run.stdout + run.stderr
    if run.returncode != 0:
        return False, ""
    match = SIGNER_RE.search(out)
    return True, match.group(1) if match else ""


def role_for(tag: str, roles: list[dict]) -> str | None:
    """First matching pattern wins; None means the tag's class is unknown."""
    for entry in roles:
        if fnmatch.fnmatchcase(tag, entry["pattern"]):
            return entry["signer"]
    return None


def check_trust_root(repo: Path, pin: dict, fail: Failures, opened: bool) -> None:
    """The pin exists because the trust root defines every other check: bless_epoch
    comes from its date and the blessed delegation text from its message.

    A repo that has not had its opening sitting yet legitimately has no trust root. One
    that HAS — which is what an enrolled owner key means — and no longer has the tag has
    lost it, and absence is the more dangerous state than a wrong hash: it switches off
    delegation-precedes-signature and freezes the attention receipt fresh (RT-15).
    """
    tag = pin["tag"]
    if git(repo, "rev-parse", "-q", "--verify", f"refs/tags/{tag}").returncode != 0:
        if opened:
            fail.add(
                f"trust root MISSING: {tag} does not exist, but an owner key is enrolled "
                "in allowed_signers, so this repo has had its opening sitting. Deleting "
                "it empties bless_epoch and holds the attention receipt fresh for ever "
                "(RT-15). Restore it, or the repo is not the one the custody floor "
                "describes."
            )
        else:
            print(f"  trust root: {tag} does not exist yet (no owner key enrolled)")
        return
    actual = git(repo, "rev-parse", f"refs/tags/{tag}").stdout.strip()
    if actual != pin["object"]:
        fail.add(
            f"trust root re-issued: {tag} is tag object {actual}, expected {pin['object']} "
            "— the founding signature, the blessed delegation text and bless_epoch all "
            "come from this object (D0050)"
        )
    else:
        print(f"  trust root: {tag} pinned at {actual[:12]}…")


@contextmanager
def repo_at(target: Path):
    """Yield a working repo for `target`, cloning it first if it is a git bundle.

    The poison fixture for this guard cannot be a directory of files the way the other
    four are: the violation is a *signed git object*. A bare repo would be a dozen
    manifest rows of loose objects; a bundle is one file, one row — so the guard knows
    how to open one rather than the custodian growing a temp-dir dance around it.
    """
    if target.suffix != ".bundle":
        yield target
        return
    with tempfile.TemporaryDirectory() as tmp:
        clone = Path(tmp) / "repo"
        run = subprocess.run(["git", "clone", "--quiet", str(target), str(clone)],
                             capture_output=True, text=True, check=False, env=git_env())
        if run.returncode != 0:
            raise SystemExit(f"check_tag_signers: cannot clone bundle {target}: {run.stderr.strip()}")
        yield clone


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT,
                        help="repo holding governance/tag-roles.yaml and allowed_signers")
    parser.add_argument("--repo", type=Path, default=None,
                        help="repo whose tags are checked (default: --root); a poison "
                             "fixture points this at a .bundle carrying a bad tag")
    args = parser.parse_args()
    root = args.root.resolve()
    with repo_at((args.repo or root).resolve()) as repo:
        return check(root, repo)


def check(root: Path, repo: Path) -> int:
    fail = Failures("check_tag_signers")

    table = load_yaml(root / "governance" / "tag-roles.yaml")
    signers = root / "allowed_signers"
    if not signers.exists():
        fail.add("allowed_signers does not exist, so no tag can be attributed")
        return fail.finish("")

    opened = owner_key_enrolled(root)
    check_trust_root(repo, table["trust_root"], fail, opened)

    tags = [t for t in git(repo, "tag", "-l").stdout.splitlines() if t.strip()]
    for required in table.get("required_tags") or []:
        if required not in tags:
            fail.add(
                f"required tag missing: {required} — the tag set is part of the custody "
                "floor, not an optional decoration (RT-15). A shallow clone or an export "
                "that arrives without tags is indistinguishable from one where they were "
                "deleted, so both are refused here."
            )
    for tag in tags:
        verified, principal = verify_tag(repo, signers, tag)
        if not verified:
            fail.add(f"tag does not verify against allowed_signers: {tag}")
            continue
        role = role_for(tag, table["roles"])
        if role is None:
            if table.get("unknown", "refuse") == "refuse":
                fail.add(
                    f"tag class not in the signer-role table — add it deliberately or "
                    f"rename: {tag}"
                )
            continue
        expected = f"{role}@tannen"
        if principal != expected:
            fail.add(
                f"tag signed by the wrong principal (expected {expected}, got "
                f"{principal or 'unknown'}): {tag}"
            )
        else:
            print(f"  {tag}: {principal} (class role: {role})")

    return fail.finish(f"{len(tags)} tag(s); every signer matches its tag class")


if __name__ == "__main__":
    sys.exit(main())
