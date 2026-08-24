"""`tannen` — the command line. Effectful shell.

M0 ships one command: `tannen laws report` (BRIEF §5.11), which joins `make verify` at
this milestone per decision D0012. `tannen run` and its SpendGuard arrive with the
oracles at M4; there is deliberately no command here that can spend anything.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tannen.laws.discovery import find_root
from tannen.laws.report import build_report, render

__all__ = ["main"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tannen", description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)

    laws = commands.add_parser("laws", help="executable laws and their recorded evidence")
    law_commands = laws.add_subparsers(dest="laws_command", required=True)

    report = law_commands.add_parser(
        "report",
        help="evidence freshness for the current descriptors; non-zero when any law lacks it",
    )
    report.add_argument("--root", type=Path, default=None, help="repo root (default: search upward)")
    report.add_argument(
        "--milestone", action="append", dest="milestones", metavar="M",
        help="restrict to a milestone (e.g. m0); repeatable, default all",
    )
    report.add_argument("--json", action="store_true", help="emit the report as JSON")
    report.set_defaults(handler=_laws_report)
    return parser


def _laws_report(args: argparse.Namespace) -> int:
    root = (args.root or find_root()).resolve()
    report = build_report(root, args.milestones)
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render(report))
    return 0 if report["ok"] else 1


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
