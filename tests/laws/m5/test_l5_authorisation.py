"""M5 law L5.8 — door 3 in a law: the corpus present was opened by the owner (docs/specs/m5.md
§0.2, §3; BRIEF §9.1, §9.2 door renavon-first-contact; D0019, D0240).

FROZEN at m5-laws-freeze. BRIEF §9.2 makes "first contact with Renavon inputs (the M5 gate)" a
one-way door that opens by AFFIRMATIVE owner signature only, never silence, and D0019 recorded
that its mechanical enforcement — "the M5 vertical refusing without the door signature" — would
land with M5's code. D0240 settles where it may not land: a library enforces the authorisation it
is handed and must not read the constitution. So `tannen.dogfood` does not read this repository's
governance, and THIS LAW does: the corpus at `.dogfood/corpus.json` names, in `authorisation`,
the decision record that opened the door, and that record must be

  - a file under `decisions/`, `tier: C`, `status: accepted`;
  - bound to the door by its `links` naming `renavon-first-contact` — a door id this law reads
    out of `governance/tier-c.yaml`, so a renamed or removed door cannot be satisfied;
  - signed by `owner@tannen` over its whole bytes under namespace `tannen-decision`, verified
    against `allowed_signers` with BOTH `-I` and `-n` (without either the check is vacuous —
    `scripts/_gov.py::verify_owner_signature`'s own warning, restated here rather than imported).

A corpus that fails any of these FAILS this law by name; it is never a skip. The verifier is
proven to refuse before it is trusted: each refusal is watched against ephemeral keys in a
scratch tree (an unsigned record, a builder signature, a wrong namespace, a tampered record, a
record not linked to the door, a Tier-B record), and the positive control accepts a correct one.

WHAT IT DOES NOT CLAIM. That the corpus's bytes are the ones the owner saw: the record authorises
first contact, and the corpus's own refs are what bind the bytes (L5.5). The shape of the
authorisation record is queued for the gate sitting; a different shape there is a superseding
law, not an edit.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
CORPUS = REPO_ROOT / ".dogfood" / "corpus.json"
if not CORPUS.is_file():
    pytest.skip("M5 dogfood corpus absent — every M5 law goes live together when an authorised "
                "corpus is present at .dogfood/corpus.json (docs/specs/m5.md §8)",
                allow_module_level=True)

pytest.importorskip("tannen.dogfood", reason=(
    "M5 dogfood not implemented yet (law suite frozen ahead of Session B); M5's laws go "
    "live together — docs/specs/m5.md §8"))

import yaml  # noqa: E402

VALIDATION_REASON = (
    "a property of signed governance artefacts, checked with ssh-keygen: its refusals are watched "
    "against ephemeral keys in a scratch tree below, which is the model a model would be."
)

NAMESPACE = "tannen-decision"
OWNER = "owner@tannen"


def door_id(root: Path) -> str:
    ids = [door["id"] for door in yaml.safe_load(
        (root / "governance" / "tier-c.yaml").read_text(encoding="utf-8"))["tier_c"]]
    matches = [door for door in ids if door == "renavon-first-contact"]
    assert matches, f"governance/tier-c.yaml has no door renavon-first-contact: {ids}"
    return matches[0]


def refusals(root: Path, authorisation: str) -> list[str]:
    """Why the record at `authorisation` does NOT open the door; empty when it does."""
    path = root / authorisation
    if path.parent.resolve() != (root / "decisions").resolve() or not path.is_file():
        return [f"{authorisation} is not a decision record under decisions/"]
    record = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    found = []
    if record.get("tier") != "C":
        found.append(f"tier is {record.get('tier')!r}, not C — a door opens by Tier-C record only")
    if record.get("status") != "accepted":
        found.append(f"status is {record.get('status')!r}, not accepted")
    if door_id(root) not in (record.get("links") or []):
        found.append("its links do not name the door renavon-first-contact")
    sig = path.with_name(path.name + ".sig")
    signers = root / "allowed_signers"
    if not sig.is_file():
        found.append("it carries no signature — an optional signature is not a signature (RT-04)")
    elif subprocess.run(["ssh-keygen", "-Y", "verify", "-f", str(signers), "-I", OWNER,
                         "-n", NAMESPACE, "-s", str(sig)],
                        input=path.read_bytes(), capture_output=True).returncode != 0:
        found.append(f"its signature does not verify as {OWNER} under {NAMESPACE}")
    return found


def test_l5_8_the_corpus_present_was_opened_by_the_owner() -> None:
    authorisation = json.loads(CORPUS.read_text(encoding="utf-8"))["authorisation"]
    found = refusals(REPO_ROOT, authorisation)
    assert not found, ("the corpus at .dogfood/corpus.json is not authorised — Tier-C door "
                       "renavon-first-contact is closed:\n  " + "\n  ".join(found))


# ------------------------------------------------------------------ the verifier, watched


def _sh(*args: str, **kwargs) -> subprocess.CompletedProcess:
    run = subprocess.run(args, capture_output=True, **kwargs)
    assert run.returncode == 0, f"{args}: {run.stdout!r} {run.stderr!r}"
    return run


@pytest.fixture
def scratch(tmp_path: Path):
    """A root with tier-c.yaml copied from the repository, ephemeral owner and builder keys
    enrolled, and a helper that writes and optionally signs a record."""
    (tmp_path / "governance").mkdir()
    shutil.copy(REPO_ROOT / "governance" / "tier-c.yaml", tmp_path / "governance" / "tier-c.yaml")
    (tmp_path / "decisions").mkdir()
    keys = {}
    lines = []
    for principal in (OWNER, "builder@tannen"):
        key = tmp_path / principal.split("@")[0]
        _sh("ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", principal, "-f", str(key))
        keys[principal] = key
        lines.append(f"{principal} {key.with_suffix('.pub').read_text().strip()}")
    (tmp_path / "allowed_signers").write_text("\n".join(lines) + "\n")

    def record(name: str = "0999-gate.yaml", *, tier: str = "C", status: str = "accepted",
               links: tuple = ("renavon-first-contact",), signer: str | None = OWNER,
               namespace: str = NAMESPACE) -> str:
        path = tmp_path / "decisions" / name
        path.write_text(yaml.safe_dump({"id": "D0999", "tier": tier, "status": status,
                                        "links": list(links)}))
        if signer is not None:
            _sh("ssh-keygen", "-Y", "sign", "-f", str(keys[signer]), "-n", namespace, str(path))
        return f"decisions/{name}"

    return tmp_path, record


def test_l5_8_the_verifier_accepts_a_correct_authorisation(scratch) -> None:
    root, record = scratch
    assert refusals(root, record()) == []


@pytest.mark.parametrize("variant", ["unsigned", "builder-signed", "wrong-namespace", "tampered",
                                     "not-linked-to-the-door", "tier-b", "not-accepted",
                                     "outside-decisions"])
def test_l5_8_the_verifier_refuses(scratch, variant) -> None:
    root, record = scratch
    if variant == "unsigned":
        name = record(signer=None)
    elif variant == "builder-signed":
        name = record(signer="builder@tannen")
    elif variant == "wrong-namespace":
        name = record(namespace="tannen-custody")
    elif variant == "tampered":
        name = record()
        path = root / name
        path.write_text(path.read_text() + "# edited after signing\n")
    elif variant == "not-linked-to-the-door":
        name = record(links=("spend-envelopes",))
    elif variant == "tier-b":
        name = record(tier="B")
    elif variant == "not-accepted":
        name = record(status="blocked-on-owner")
    else:
        record()
        name = "docs/0999-gate.yaml"
    assert refusals(root, name), f"the verifier accepted a {variant} authorisation"
