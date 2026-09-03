"""Tier C is affirmative signature only, never silence (BRIEF §9.2; RT-06, D0064).

Hermetic: ephemeral owner and builder keys, a throwaway decisions/ tree. A test that
used the real owner key would be testing whether this machine happens to hold it; what
is under test is that a record cannot grant itself a one-way door, and that the two
arguments which would make the check vacuous — the principal and the namespace — are
both actually being enforced.
"""

from __future__ import annotations

import datetime as dt
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from _gov import git_env, input_hash, receipt_state  # noqa: E402
from gen_projections import header  # noqa: E402

GUARD = REPO_ROOT / "scripts" / "check_decisions.py"
MARKER = "Tier-C record accepted without an owner signature"
TODAY = "2026-08-25"


def sh(*args: str) -> subprocess.CompletedProcess:
    run = subprocess.run(args, capture_output=True, text=True, check=False, env=git_env())
    assert run.returncode == 0, f"{args}\n{run.stdout}\n{run.stderr}"
    return run


def record(rid: str, tier: str, status: str) -> str:
    return (
        f"id: {rid}\n"
        f"title: A record for the guard to judge\n"
        f"tier: {tier}\n"
        f'date: "2026-08-25"\n'
        f"decision: Walk through a one-way door.\n"
        f"rationale: Exercises the Tier-C signature check.\n"
        f"reversibility: None; that is what makes it Tier C.\n"
        f"status: {status}\n"
        f"bindings:\n"
        f"  - type: file\n"
        f"    target: decisions/{rid[1:]}-a-record.yaml\n"
    )


@pytest.fixture
def world(tmp_path: Path):
    root = tmp_path / "repo"
    (root / "decisions").mkdir(parents=True)
    keys = {}
    for principal in ("owner@tannen", "builder@tannen"):
        key = tmp_path / principal.split("@")[0]
        sh("ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", principal, "-f", str(key))
        keys[principal] = key
    (root / "allowed_signers").write_text("".join(
        f"{p} {k.with_suffix('.pub').read_text().strip()}\n" for p, k in keys.items()))

    def write(rid: str, tier: str = "C", status: str = "accepted") -> Path:
        path = root / "decisions" / f"{rid[1:]}-a-record.yaml"
        path.write_text(record(rid, tier, status))
        return path

    def sign(path: Path, principal: str = "owner@tannen",
             namespace: str = "tannen-decision") -> None:
        sh("ssh-keygen", "-Y", "sign", "-f", str(keys[principal]), "-n", namespace, str(path))

    def run() -> subprocess.CompletedProcess:
        # DECISIONS.md freshness is not what these tests are about, so it is made fresh
        # here — otherwise every case would exit non-zero and the positive ones would
        # prove nothing.
        #
        # RT-M2-05 gave the projection a SECOND thing it must carry: the attention-receipt
        # line this run computes, because the input hash above cannot see the clock. A bare
        # header stopped being a fresh projection the moment that check landed, and this
        # fixture said so by turning every exit-0 case below red. Rendered from
        # `receipt_state` — the function the guard itself calls — so a throwaway tree with
        # no receipts/ states the STALE verdict it actually has instead of faking a FRESH
        # one. The record cases are unaffected: none of them carries a veto_by, so the
        # guard's Tier-B row comparison has nothing to look for.
        paths = sorted((root / "decisions").glob("*.yaml"))
        fresh, detail = receipt_state(root, dt.date.fromisoformat(TODAY))
        (root / "DECISIONS.md").write_text(
            header(input_hash(paths, root))
            + f"\nAttention receipt: **{'FRESH' if fresh else 'STALE'}** — {detail}\n")
        return subprocess.run(
            [sys.executable, str(GUARD), "--root", str(root), "--today", TODAY],
            capture_output=True, text=True, check=False, env=git_env(),
        )

    return type("World", (), dict(root=root, write=staticmethod(write),
                                  sign=staticmethod(sign), run=staticmethod(run)))


def test_an_owner_signed_tier_c_record_passes(world):
    world.sign(world.write("D0001"))
    run = world.run()
    assert run.returncode == 0, run.stdout + run.stderr
    assert "1 Tier-C door(s) owner-signed, 0 queued" in run.stdout


def test_an_unsigned_tier_c_record_cannot_accept_itself(world):
    world.write("D0001")
    run = world.run()
    assert run.returncode != 0
    assert MARKER in run.stderr


def test_a_builder_signature_does_not_open_an_owner_door(world):
    """The `-I owner@tannen` argument, under test. Both principals are enrolled, so
    dropping it would make an enrolled builder key sufficient for a one-way door."""
    path = world.write("D0001")
    world.sign(path, principal="builder@tannen")
    run = world.run()
    assert run.returncode != 0
    assert MARKER in run.stderr


def test_a_signature_from_another_namespace_does_not_carry_over(world):
    """The `-n tannen-decision` argument, under test: an owner signature taken over a
    receipt or a policy file must not be replayable onto a decision record."""
    path = world.write("D0001")
    world.sign(path, namespace="tannen-receipt")
    run = world.run()
    assert run.returncode != 0
    assert MARKER in run.stderr


def test_editing_a_record_after_signing_breaks_its_signature(world):
    """Signing is over whole bytes (D0063 ruling 2), so a binding upgrade on a Tier-C
    record costs a re-signature at the next sitting. That cost is the design, and this
    test is what makes it impossible to forget."""
    path = world.write("D0001")
    world.sign(path)
    assert world.run().returncode == 0
    path.write_text(path.read_text().replace("one-way door.", "one-way door, amended."))
    run = world.run()
    assert run.returncode != 0
    assert MARKER in run.stderr


def test_a_blocked_tier_c_record_needs_no_signature(world):
    """Queued is the honest state for a door the owner has not yet opened, and the
    non-blocking rule (§9.2) depends on reaching it costing nothing."""
    world.write("D0001", status="blocked-on-owner")
    run = world.run()
    assert run.returncode == 0, run.stdout + run.stderr
    assert "0 Tier-C door(s) owner-signed, 1 queued" in run.stdout


def test_tier_a_and_b_records_are_untouched(world):
    """Over-reach would put the owner's key in the path of ordinary reversible work,
    which is the whole thing the tiers exist to prevent."""
    world.write("D0001", tier="A")
    run = world.run()
    assert run.returncode == 0, run.stdout + run.stderr
    assert "0 Tier-C door(s) owner-signed, 0 queued" in run.stdout
