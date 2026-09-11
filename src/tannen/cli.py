"""`tannen` — the command line. Effectful shell.

Two commands. `tannen laws report` (BRIEF §5.11) joined `make verify` at M0 per decision
D0012. `tannen run MODULE:CALLABLE --store PATH [--budget PATH] [--spend]` (docs/specs/m4.md
§1; BRIEF §5.10) imports MODULE (from the working directory too, as `python -m` would) and
calls CALLABLE with an invocation context over the store: replay-only unless `--spend` is
given, and `--spend` engages SpendGuard against the budget file named by `--budget` — with
none, it authorises nothing. WHICH budget a caller may name is not yet tied to the checked-in
`budget.yaml` or the policy envelope: frozen L4.4 spends against a budget of its own, so that
gap is a queued owner item (D0238), not a guarantee this command makes.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

from tannen.laws.discovery import find_root
from tannen.laws.report import build_report, render
from tannen.oracles import (
    REPLAY,
    SPEND,
    CaptureConflict,
    CaptureWriteFailed,
    NovelInvocationRefused,
    Oracles,
    SpendDenied,
    load_budget,
)
from tannen.store import Store

__all__ = ["REFUSALS", "main"]

#: What `tannen run` reports as exit 1 with the class name on stderr (docs/specs/m4.md §1).
#: Anything else is not a refusal, and propagates rather than hide inside an exit code.
REFUSALS = (NovelInvocationRefused, SpendDenied, CaptureWriteFailed, CaptureConflict)


def _target(text: str) -> tuple[str, str]:
    module, colon, attr = text.partition(":")
    if not (module and colon and attr):
        raise argparse.ArgumentTypeError(f"{text!r} is not MODULE:CALLABLE")
    return module, attr


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

    run = commands.add_parser(
        "run",
        help="call MODULE:CALLABLE with an oracle context — replay-only unless --spend",
    )
    run.add_argument("target", type=_target, metavar="MODULE:CALLABLE",
                     help="a callable taking a tannen.oracles.Oracles context")
    run.add_argument("--store", type=Path, required=True,
                     help="the store captures are read from and written to")
    run.add_argument("--budget", type=Path, default=None,
                     help="the budget file SpendGuard admits against (none authorises nothing)")
    run.add_argument("--spend", action="store_true",
                     help="allow novel oracle invocations, each admitted by SpendGuard")
    run.set_defaults(handler=_run)
    return parser


def _laws_report(args: argparse.Namespace) -> int:
    root = (args.root or find_root()).resolve()
    report = build_report(root, args.milestones)
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render(report))
    return 0 if report["ok"] else 1


def _run(args: argparse.Namespace) -> int:
    module, attr = args.target
    # A console script's sys.path[0] is its bin directory, not the working directory;
    # `tannen run pipeline:main` should find the `pipeline.py` it is run beside.
    here = str(Path.cwd())
    if "" not in sys.path and here not in sys.path:
        sys.path.insert(0, here)
    callable_ = getattr(importlib.import_module(module), attr)
    context = Oracles(
        Store(args.store),
        mode=SPEND if args.spend else REPLAY,
        budget=load_budget(args.budget) if args.budget is not None else None,
    )
    try:
        result = callable_(context)
    except REFUSALS as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    if isinstance(result, str):
        print(result)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
