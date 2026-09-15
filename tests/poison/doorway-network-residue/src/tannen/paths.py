"""CONTROL (must pass): legitimate shell IO — reading the filesystem is not reading the world."""
import os.path
from pathlib import Path


def exists(p: str) -> bool:
    return os.path.exists(p) and Path(p).is_file()
