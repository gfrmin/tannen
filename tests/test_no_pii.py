"""A standing structural guard against personal data and credentials in the tree.

WHY THIS EXISTS. Publishing tannen is Tier-C door `external-bytes`
(governance/tier-c.yaml) and the owner's call. What is NOT the owner's call is whether the
repository is in a state where publishing it would be safe — that is a property of the
bytes, it changes with every commit, and until this file existed nothing measured it. The
audit that produced this guard was a one-off sweep; a one-off sweep answers a question
about a moment, and the question is about every moment after it.

PRIOR ART, CITED AND NOT VENDORED. life-agent runs a mature structural PII guard at
`.githooks/pii_check.py` (676 lines, adversarially hardened — see its own `docs/guards.md`
row 13 for the history of it being defeated and re-earned). This file is NOT that file and
does not import it: CLAUDE.md's hard rules forbid any dependency on another repo of the
constellation in either direction, and BRIEF §9 makes a cross-repo code dependency Tier C.
The relationship is the one docs/specs/m1.md §0.1 draws for DBSP and the Lean
formalisation — prior art is cited, never restated and never vendored, and it is NOT a §2
concept, because §2 covers the constellation's *definitions* and this is repo hygiene.
What is borrowed is the reasoning, and three lessons in particular:

  1. THE BYTES DECIDE (its r27/C8). A declared binary suffix is permission to be binary,
     never an assertion that a file is one. NUL is checked first, on content.
  2. AN UNSCANNABLE FILE IS A REFUSAL, NEVER A PASS (its r23/F4). Found live: running
     life-agent's guard over this repo returned exit 2 on a NUL-carrying poison fixture
     and scanned NOTHING — the refusal short-circuits the whole run before any file is
     read. Read carelessly, that reads as clean. Here a refusal is a per-file FINDING, so
     one unscannable blob can never suppress the other three hundred files' results.
  3. A NOISY GUARD GETS DISABLED, and a disabled guard is what lets the leak through.
     life-agent's general "path under a non-placeholder root" layer produced 59 findings
     on this tree and exactly one true positive, because its allowlist is its own. That
     layer is deliberately NOT reproduced. What is reproduced is the precise half: an
     absolute path under a home directory names a real user on a real machine.

WHAT THIS DOES NOT DO, stated rather than left to be discovered. It has no private-name
layer. life-agent supplements its shapes with a denylist of names, employers and domains
loaded from outside the repo, precisely because a bare personal name has no shape a regex
can find. Nothing here can catch one. A green run is evidence about shapes and credentials
and nothing else, and that limit is the reason publication still needs a human to look.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

#: Domains an address may legitimately carry. `builder@tannen` and `owner@tannen` do not
#: appear here because they cannot match at all: the pattern requires an alphabetic TLD,
#: and `tannen` is a bare label. `openssh.com` is in the list for a shape that is not an
#: address at all — `sk-ssh-ed25519@openssh.com` is OpenSSH's spelling of a key TYPE, and
#: it appears in a superseded `allowed_signers` blob in this repo's history.
ALLOWED_EMAIL_DOMAINS = frozenset({"example.com", "example.org", "example.net", "openssh.com"})

#: Tracked files that legitimately carry a NUL byte, each with the reason it is here.
#: A file NOT in this map that carries NUL is a finding, not a skip — the guard cannot
#: read it, and "I could not read it" is never "it is clean". Inspected by hand when this
#: guard was written: the bundle holds one commit, one tag and one README, all authored
#: `builder <builder@tannen>`.
DECLARED_BINARY = {
    "tests/poison/custodian-tag-signer/repo.bundle": (
        "a git bundle, by construction binary; it is the fixture that proves the "
        "custodian refuses a builder-signed *-close tag (D0050/D0054)"
    ),
}

#: Home-directory disclosures already in the tree, each one also in the published history
#: and therefore permanent. THE TREE DELIBERATELY MATCHES THE HISTORY. Redacting these
#: four lines would leave the repository looking cleaner than it is while the original
#: blobs stay one `git log -p` away, and the history cannot be rewritten: every rewrite
#: invalidates the signed tags and breaks the receipt chain. So they are declared, counted
#: and visible instead. A FIFTH is a failure. Keys are `path` — the whole file is
#: tolerated, because a line number is not stable under an edit that adds a paragraph.
KNOWN_DISCLOSURES = {
    "decisions/0048-in-repo-mechanics-are-tier-a.yaml": (
        "a decision record is an append-only event record and its text is immutable "
        "(D0045); the path is inside the rationale's undo instruction"
    ),
    "docs/proposals/2026-08-24-custodian-signer-role-table.md": (
        "a reproduction command in a proposal that has already been applied"
    ),
    "docs/proposals/2026-08-24-policy-in-repo-mechanics.md": (
        "a parenthetical locating the repo, in an applied proposal"
    ),
    "docs/redteam/2026-08-24-m0-boundary.md": (
        "the M0 red-team report naming the target it was run against; a report that "
        "misstates its own target is worth less than the disclosure costs"
    ),
}

# THIS FILE IS SCANNED BY ITSELF, and that is deliberate. A scanner that exempts its own
# source is a hole with no review trail — life-agent's K3 D-d found exactly that about its
# `PII-OK` marker, which had become an unreviewed kill switch. The cost is that the fixture
# values below cannot appear as literals in these bytes, so they are ASSEMBLED at run time.
# `_j` is not obfuscation: it is what keeps this file inside the set the guard checks
# instead of outside it. The regex definitions need no such treatment — what follows each
# prefix there is a character class, not the thing the pattern matches.
def _j(*parts: str) -> str:
    return "".join(parts)


# An address needs an alphabetic TLD of two or more letters: real domains never end in a
# numeric label, which keeps `package@1.2.3` out without missing anything real.
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@((?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,})\b")

# An ABSOLUTE path under a home directory names a real user on a real machine. The tilde
# forms this repo uses throughout (`~/git/worktrees/tannen/m1`, `~/.ssh/tannen_builder`)
# are conventions, not disclosures, and are deliberately untouched.
_HOME_PATH_RE = re.compile(r"/(?:home|Users)/[A-Za-z0-9._-]+/")

# Credential shapes. Each is a vendor's own published prefix, so a match is a token and
# not a coincidence. `BEGIN ... PRIVATE KEY` covers every armour OpenSSH, OpenSSL and GPG
# emit. None of these patterns matches this file: what follows each prefix here is a
# regex bracket, not the base62 the real thing carries.
_CREDENTIAL_RES = (
    ("private-key-block", re.compile(r"BEGIN [A-Z ]*PRIVATE KEY")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36}\b")),
    ("github-fine-grained-token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{50,}")),
    ("aws-access-key-id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("anthropic-api-key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
)

#: Every kind `scan` can emit, named ONCE. The tests below filter findings by kind, and
#: a filter that names a kind the scanner does not emit — or misses one it does — is a
#: test that cannot fail. That is not hypothetical: the credential filter was originally
#: written `{kind for _, kind in _CREDENTIAL_RES}`, which unpacks the (kind, pattern)
#: pairs BACKWARDS into a set of compiled patterns, so `kind in kinds` was never true and
#: the guard's headline assertion was decoration for its whole first day — green while
#: this very file carried an OpenSSH private-key header as a fixture. Constants plus
#: test_the_kind_filters_partition_everything_the_scan_emits are what close that class.
#: One triggering sample per credential pattern, assembled so no literal lands in these
#: bytes (see `_j`). Keyed by kind, so adding a pattern without a sample fails the
#: partition test rather than silently going untested.
_CREDENTIAL_SAMPLES = {
    "private-key-block": _j("-----BEGIN OPENSSH ", "PRIVATE KEY-----\n"),
    "github-token": "t = ghp_" + "A" * 36 + "\n",
    "github-fine-grained-token": "t = github" + "_pat_" + "B" * 50 + "\n",
    "aws-access-key-id": "k: AKIA" + "C" * 16 + "\n",
    "anthropic-api-key": "k: sk-" + "ant-" + "d" * 24 + "\n",
    "slack-token": "k: xoxb" + "-" + "e" * 12 + "\n",
}

CREDENTIAL_KINDS = frozenset(kind for kind, _ in _CREDENTIAL_RES)
EMAIL_KIND = "email (non-allowlisted domain)"
HOME_KIND = "home-directory path"
UNSCANNABLE_KIND = "unscannable (NUL byte, not declared)"
ALL_KINDS = CREDENTIAL_KINDS | {EMAIL_KIND, HOME_KIND, UNSCANNABLE_KIND}


#: `git -C <dir>` does NOT override GIT_DIR / GIT_INDEX_FILE / GIT_WORK_TREE taken from the
#: environment — the environment wins, and `-C` only changes the working directory it is
#: read from. A git hook exports all three pointing at THIS repository, and pre-commit runs
#: hooks, so every fixture below that spelled `git -C <tmp_path> add -A` wrote its files
#: into the REAL index when the suite ran under `git commit`. Observed 2026-08-30: the index
#: reduced to the nine fixture files with all 309 real paths staged-deleted. Recoverable —
#: `git reset` — but a test that writes to the repository under test is a defect whatever it
#: writes, and it is invisible from a plain shell, where these variables are unset.
def _git(*args: str, **kwargs) -> subprocess.CompletedProcess:
    """git with every GIT_* inherited from the caller stripped, so `-C` is actually
    authoritative about which repository is touched."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    return subprocess.run(["git", *args], check=True, env=env, **kwargs)


def tracked_files(root: Path = ROOT) -> list[str]:
    """Every path git tracks, which is exactly the set publishing would publish."""
    out = _git("-C", str(root), "ls-files", "-z", capture_output=True, text=True).stdout
    return [name for name in out.split("\0") if name]


def scan(root: Path = ROOT) -> list[tuple[str, str]]:
    """Every finding as `(path, kind)`. Order follows the file list, so a diff of two runs
    reads as a diff of the tree. Values are NEVER returned or printed: a guard that echoes
    what it found writes the secret into every log that captures its output."""
    findings: list[tuple[str, str]] = []
    for name in tracked_files(root):
        raw = (root / name).read_bytes()
        if b"\0" in raw:
            # The bytes decide, and they decide FIRST. A declared entry means "this file
            # is allowed to be unreadable", never "this file is known to be clean".
            if name not in DECLARED_BINARY:
                findings.append((name, UNSCANNABLE_KIND))
            continue
        text = raw.decode("utf-8", errors="replace")
        for match in _EMAIL_RE.finditer(text):
            if match.group(1).lower() not in ALLOWED_EMAIL_DOMAINS:
                findings.append((name, EMAIL_KIND))
        if _HOME_PATH_RE.search(text):
            findings.append((name, HOME_KIND))
        for kind, pattern in _CREDENTIAL_RES:
            if pattern.search(text):
                findings.append((name, kind))
    return findings


def test_the_guard_actually_read_the_tree() -> None:
    """A detector that scanned nothing is green for the wrong reason — the exact failure
    mode found in life-agent's guard when it was pointed at this repo."""
    names = tracked_files()
    assert len(names) > 100, f"only {len(names)} tracked files — did git ls-files work?"
    assert "BRIEF.md" in names


def test_the_kind_filters_partition_everything_the_scan_emits(tmp_path: Path) -> None:
    """THE REGRESSION TEST FOR THE WORST BUG THIS FILE HAS HAD (D0112).

    `test_no_credential_shape_is_tracked` filtered with `{kind for _, kind in
    _CREDENTIAL_RES}` — the (kind, pattern) pairs unpacked BACKWARDS, giving a set of
    compiled patterns. `kind in kinds` compares a string to a Pattern, so it was never
    true, `hits` was always empty, and the assertion could not fail under any input. It
    stayed green while this very file carried an OpenSSH private-key header verbatim, and
    the sitting rehearsal reported two failures where three were due — which is how it
    was noticed, by asking why the third was missing rather than by any test.

    So: build a repository violating EVERY kind at once, and prove the four assertion
    tests' filters cover all of them, disjointly. A new pattern with no test, or a filter
    that stops selecting, fails here instead of going quietly green."""
    _git("-C", str(tmp_path), "init", "-q")
    (tmp_path / "email.txt").write_text(
        _j("x: someone@realcompany", ".co", ".uk\n"), encoding="utf-8")
    (tmp_path / "home.txt").write_text(_j("cd /home", "/somebody/x\n"), encoding="utf-8")
    (tmp_path / "blob.dat").write_bytes(b"\x00\x01")
    unsampled = sorted(CREDENTIAL_KINDS - set(_CREDENTIAL_SAMPLES))
    assert not unsampled, (
        f"no triggering sample for {unsampled} — add one to _CREDENTIAL_SAMPLES, or the "
        "pattern is never exercised and could match nothing at all."
    )
    for kind, _pattern in _CREDENTIAL_RES:
        (tmp_path / f"{kind}.txt").write_text(_CREDENTIAL_SAMPLES[kind], encoding="utf-8")
    _git("-C", str(tmp_path), "add", "-A")

    emitted = {kind for _, kind in scan(tmp_path)}
    assert emitted == ALL_KINDS, (
        "the fixture repository did not produce one of every kind — missing "
        f"{sorted(ALL_KINDS - emitted)}, unexpected {sorted(emitted - ALL_KINDS)}. "
        "Either a pattern stopped matching its own sample, or ALL_KINDS is out of date."
    )

    filters = {
        "credential": lambda k: k in CREDENTIAL_KINDS,
        "email": lambda k: k == EMAIL_KIND,
        "unscannable": lambda k: k == UNSCANNABLE_KIND,
        "home": lambda k: k == HOME_KIND,
    }
    selected = {name: {k for k in emitted if f(k)} for name, f in filters.items()}
    for name, chosen in selected.items():
        assert chosen, f"the {name} filter selects nothing — it cannot fail on any input"
    union: set[str] = set()
    for name, chosen in selected.items():
        overlap = union & chosen
        assert not overlap, f"{name} overlaps another filter on {sorted(overlap)}"
        union |= chosen
    assert union == ALL_KINDS, (
        f"no test asserts on {sorted(ALL_KINDS - union)} — the scanner can report it and "
        "nothing would fail."
    )


def test_the_guard_scans_its_own_source() -> None:
    """THE REGRESSION TEST FOR THIS FILE'S OWN FIRST BUG (D0112). Its fixtures ARE the
    shapes it looks for. While it was still untracked, `git ls-files` never showed it to
    `scan()`, so the suite was green about a file that would fail the moment it was
    committed — which is exactly what happened at the sitting rehearsal's post-commit
    gate: 2 failed, 570 passed, and the driver aborted at step 9 with "verify red at the
    close". The fix was to assemble the fixture values at run time (see `_j`), NOT to
    exempt this path: a scanner with a blind spot over its own source is a hole with no
    review trail. This test is what stops either half of that from regrowing."""
    assert "tests/test_no_pii.py" in tracked_files(), (
        "this file is untracked, so the scan cannot see it and every assertion below is "
        "green about a file it never read. Stage it: git add tests/test_no_pii.py"
    )
    self_hits = sorted(kind for path, kind in scan() if path == "tests/test_no_pii.py")
    assert not self_hits, (
        "the guard flags its own source: " + ", ".join(self_hits) + ". A fixture value "
        "leaked into these bytes as a literal — assemble it with _j() instead."
    )


def test_no_credential_shape_is_tracked() -> None:
    hits = sorted(f"  {path}: {kind}" for path, kind in scan() if kind in CREDENTIAL_KINDS)
    assert not hits, "a credential shape is tracked (values withheld):\n" + "\n".join(hits)


def test_no_unallowlisted_email_address_is_tracked() -> None:
    hits = sorted(f"  {path}" for path, kind in scan() if kind == EMAIL_KIND)
    assert not hits, (
        "an email address with a non-allowlisted domain is tracked (values withheld):\n"
        + "\n".join(hits)
        + "\nIf it is not really an address, add its domain to ALLOWED_EMAIL_DOMAINS "
        "with a comment saying what it actually is."
    )


def test_every_unscannable_file_is_declared() -> None:
    hits = sorted(f"  {path}" for path, kind in scan() if kind == UNSCANNABLE_KIND)
    assert not hits, (
        "a tracked file carries a NUL byte and is not declared in DECLARED_BINARY:\n"
        + "\n".join(hits)
        + "\nRead it by hand, then declare it WITH THE REASON. An undeclared binary is "
        "a file this guard cannot see into, which is not the same as a clean one."
    )


def test_no_new_home_directory_path_is_tracked() -> None:
    hits = sorted(
        f"  {path}" for path, kind in scan()
        if kind == HOME_KIND and path not in KNOWN_DISCLOSURES
    )
    assert not hits, (
        "a tracked file discloses an absolute home-directory path:\n"
        + "\n".join(hits)
        + "\nUse the tilde form (`~/git/...`) — this repo uses it everywhere else. "
        "Adding an entry to KNOWN_DISCLOSURES instead needs a decision record saying why."
    )


def test_the_known_disclosures_are_still_there() -> None:
    """The tolerance list is not allowed to rot. If one of these is redacted the entry
    must go, or the next reader trusts a count that is no longer true."""
    disclosing = {path for path, kind in scan() if kind == HOME_KIND}
    stale = sorted(set(KNOWN_DISCLOSURES) - disclosing)
    assert not stale, (
        f"{', '.join(stale)} no longer discloses a home path. Delete the entry from "
        "KNOWN_DISCLOSURES. This failure is the good outcome, not a regression."
    )


@pytest.mark.parametrize(
    ("content", "kind"),
    [
        (_j("contact: someone@realcompany", ".co", ".uk\n"), "email (non-allowlisted domain)"),
        (_j("cd /home", "/somebody/project && make\n"), "home-directory path"),
        (_j("-----BEGIN OPENSSH ", "PRIVATE KEY-----\n"), "private-key-block"),
        ("token = ghp_" + "A" * 36 + "\n", "github-token"),
        ("aws: AKIA" + "B" * 16 + "\n", "aws-access-key-id"),
        ("key: sk-ant-" + "c" * 24 + "\n", "anthropic-api-key"),
    ],
)
def test_the_detector_catches_each_shape(tmp_path: Path, content: str, kind: str) -> None:
    """Watched failing, one case per shape. Without this the patterns could all be subtly
    wrong and every assertion above would pass, which is how a guard becomes decoration."""
    _git("-C", str(tmp_path), "init", "-q")
    (tmp_path / "leak.txt").write_text(content, encoding="utf-8")
    _git("-C", str(tmp_path), "add", "leak.txt")
    assert ("leak.txt", kind) in scan(tmp_path)


def test_the_detector_is_quiet_on_the_forms_this_repo_actually_uses(tmp_path: Path) -> None:
    """The other half of watching it fail: the conventions the repo uses everywhere must
    not trip it, or the guard gets switched off within a week."""
    _git("-C", str(tmp_path), "init", "-q")
    (tmp_path / "fine.md").write_text(
        "Worktrees live under `~/git/worktrees/tannen/m1`; the builder key is at\n"
        "`~/.ssh/tannen_builder`. Principals are builder@tannen and owner@tannen, and\n"
        "`sk-ssh-ed25519@openssh.com` is a key type. Run `#!/usr/bin/env python3`.\n",
        encoding="utf-8",
    )
    _git("-C", str(tmp_path), "add", "fine.md")
    assert scan(tmp_path) == []


def test_an_undeclared_binary_is_a_finding_not_a_skip(tmp_path: Path) -> None:
    """life-agent's guard aborts the whole run here; this one must not, or one poison
    fixture silently suppresses every other file's result."""
    _git("-C", str(tmp_path), "init", "-q")
    (tmp_path / "blob.dat").write_bytes(b"\x00\x01\x02")
    (tmp_path / "leak.txt").write_text(_j("cd /home", "/somebody/x\n"), encoding="utf-8")
    _git("-C", str(tmp_path), "add", "-A")
    findings = scan(tmp_path)
    assert ("blob.dat", UNSCANNABLE_KIND) in findings
    assert ("leak.txt", HOME_KIND) in findings, (
        "the unscannable file suppressed the rest of the scan — the short-circuit bug"
    )


def test_a_declared_binary_is_not_scanned_for_content(tmp_path: Path) -> None:
    """A declaration says 'allowed to be unreadable', so the file must not also be
    reported for whatever the replacement-character decode would have made of it."""
    _git("-C", str(tmp_path), "init", "-q")
    name = next(iter(DECLARED_BINARY))
    (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / name).write_bytes(b"\x00" + _j("/home", "/somebody/x").encode())
    _git("-C", str(tmp_path), "add", "-A")
    assert scan(tmp_path) == []


def test_the_fixtures_cannot_touch_the_repository_under_test(tmp_path: Path) -> None:
    """A test that writes to the repository it is testing is a defect whatever it writes.

    Every fixture here spells `git -C <tmp_path>`, which reads as "operate on tmp_path" and
    is not. `-C` sets the directory git starts from; GIT_DIR, GIT_INDEX_FILE and
    GIT_WORK_TREE override where it ends up, and a git hook exports all three pointing at
    the repository being committed. pre-commit runs hooks. So under `git commit` — and only
    there, which is why a plain `pytest` run stayed green — these fixtures staged their own
    files into the real index and staged every real path as deleted.

    This reproduces that environment against a victim repository of its own and asserts the
    victim is untouched. It fails if `_git` stops scrubbing GIT_*."""
    victim, fixture = tmp_path / "victim", tmp_path / "fixture"
    victim.mkdir(), fixture.mkdir()
    _git("-C", str(victim), "init", "-q")
    (victim / "real.txt").write_text("real content\n", encoding="utf-8")
    _git("-C", str(victim), "add", "real.txt")
    before = _git("-C", str(victim), "ls-files", capture_output=True, text=True).stdout

    (fixture / "leak.txt").write_text("fixture content\n", encoding="utf-8")
    # Exactly what a hook exports and no more. Adding GIT_WORK_TREE here — which git does
    # NOT set for a hook run inside the work tree — points `add -A` back at the victim's own
    # tree, the fixture's file is never reached, and this test passes with the scrub removed.
    # It did, on the first draft, which is how that was found.
    hook_env = {
        "GIT_DIR": str(victim / ".git"),
        "GIT_INDEX_FILE": str(victim / ".git" / "index"),
    }
    previous = {k: os.environ.get(k) for k in hook_env}
    os.environ.update(hook_env)
    try:
        _git("-C", str(fixture), "init", "-q")
        _git("-C", str(fixture), "add", "-A")
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    after = _git("-C", str(victim), "ls-files", capture_output=True, text=True).stdout
    assert after == before, (
        f"the fixture's `git add` reached into another repository: {before!r} -> {after!r}. "
        "`git -C` does not override GIT_DIR/GIT_INDEX_FILE from the environment; under a "
        "git hook that environment names the repository under test."
    )
