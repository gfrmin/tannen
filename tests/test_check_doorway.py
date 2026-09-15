"""scripts/check_doorway.py — the shell reads the world only through the doorway (RT-M4-02).

Builder tests for a custody-set guard, landed with it at the M4 boundary sitting (D0248).
Each test CONSTRUCTS the state that distinguishes a working guard from a broken one in
tmp_path (D0092) rather than reading the installed poison fixture, so the pair is
position-independent: this file proves the guard's rules, and the custodian's `poison`
line proves the guard against the corpus.

Two directions for every rule, because a guard that refuses everything passes every
"must fail" test: each payload must fail naming ITS module and ITS import or call, and the
controls — filesystem IO, the doors, the runner — must pass in the same tree.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GUARD = REPO_ROOT / "scripts" / "check_doorway.py"
MARKER = "reads the world outside the doorway"

#: The minimum shell the guard's positive control requires to be scanned.
CONTROL_SHELL = {
    "__init__.py": '"""tree"""\n',
    "store.py": "import os\nfrom pathlib import Path\n",
    "executor.py": "import os.path\n",
    "cli.py": "import importlib\n",
}


def run_guard(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-I", "-P", str(GUARD), "--root", str(root)],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )


def tree(tmp_path: Path, extra: dict[str, str]) -> Path:
    package = tmp_path / "src" / "tannen"
    for rel, body in {**CONTROL_SHELL, **extra}.items():
        path = package / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    return tmp_path


def test_the_real_tree_is_green() -> None:
    result = run_guard(REPO_ROOT)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "module(s) scanned" in result.stdout


def test_a_control_shell_that_only_touches_the_filesystem_passes(tmp_path: Path) -> None:
    result = run_guard(tree(tmp_path, {}))
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    "module, body, names",
    [
        ("export.py", "import imaplib\n", "imports imaplib"),
        ("export.py", "import xmlrpc.client\n", "imports xmlrpc.client"),
        ("export.py", "def f():\n    import socketserver\n", "imports socketserver"),
        ("export.py", "from poplib import POP3\n", "imports poplib"),
        ("store.py", "import subprocess\n", "imports subprocess"),
        ("store.py", "import multiprocessing.pool\n", "imports multiprocessing.pool"),
        ("executor.py", "import os\nos.system('curl x')\n", "uses os.system"),
        ("executor.py", "import os\nos.execvp('curl', ['curl'])\n", "uses os.execvp"),
        ("executor.py", "from os import posix_spawn\n", "uses os.posix_spawn"),
    ],
)
def test_each_payload_fails_for_its_own_reason(
    tmp_path: Path, module: str, body: str, names: str
) -> None:
    result = run_guard(tree(tmp_path, {module: CONTROL_SHELL.get(module, "") + body}))
    out = result.stdout + result.stderr
    assert result.returncode != 0, f"payload passed:\n{out}"
    assert MARKER in out, out
    assert names in out, out


def test_the_doors_are_honoured_and_only_for_their_own_rule(tmp_path: Path) -> None:
    root = tree(tmp_path, {
        "oracles/__init__.py": "import http.client\nimport subprocess\n",
        "r2.py": "import urllib.request\n",
        "laws/plugin.py": "import hypothesis\n",
    })
    result = run_guard(root)
    assert result.returncode == 0, result.stdout + result.stderr

    # The runner is a NETWORK door only: a process spawned from it is still refused.
    (root / "src" / "tannen" / "laws" / "plugin.py").write_text("import subprocess\n")
    result = run_guard(root)
    assert result.returncode != 0
    assert "tannen.laws.plugin imports subprocess" in result.stdout + result.stderr


def test_a_scan_over_nothing_is_refused(tmp_path: Path) -> None:
    result = run_guard(tmp_path)
    assert result.returncode != 0
    assert "a scan over nothing passes everything" in result.stdout + result.stderr


def test_the_derivation_sees_what_it_must_and_nothing_it_must_not() -> None:
    sys.path.insert(0, str(GUARD.parent))
    try:
        import check_doorway
    finally:
        sys.path.remove(str(GUARD.parent))
    for name in ("imaplib", "poplib", "socketserver", "xmlrpc.client", "http.client"):
        assert check_doorway.reaches_seed(name), name
    for name in ("os", "pathlib", "json", "hashlib", "tomllib", "subprocess"):
        assert not check_doorway.reaches_seed(name), name
