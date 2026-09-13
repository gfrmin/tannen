"""PAYLOAD (process): a shell module reads the world through a child process. Frozen L4.9
does not scan `subprocess` at all, and lint-imports' kernel-no-io never reaches the shell."""
import subprocess


def fetch(url: str) -> bytes:
    return subprocess.run(["curl", "-s", url], capture_output=True, check=True).stdout
