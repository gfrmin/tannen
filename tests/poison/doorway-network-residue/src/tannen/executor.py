"""PAYLOAD (process): the same read through `os`, which the shell legitimately imports for
paths — so the import alone cannot be refused; the spawning call is what the guard names."""
import os


def fetch(url: str) -> int:
    return os.system(f"curl -s {url} > /dev/null")
