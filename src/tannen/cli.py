"""`tannen` — the command line. Effectful shell.

Two commands. `tannen laws report` (BRIEF §5.11) joined `make verify` at M0 per decision
D0012. `tannen run MODULE:CALLABLE --store PATH [--budget PATH | --budget-override PATH]
[--spend]` (docs/specs/m5.md §6; BRIEF §5.10) imports MODULE (from the working directory too,
as `python -m` would) and calls CALLABLE with an invocation context over the store:
replay-only unless `--spend` is given, and `--spend` engages SpendGuard against a budget.

THE CLAMP (L5.1; owner ruling D0240 item (2), deferred here by D0241). WHICH budget a caller
may name is no longer the caller's to decide. Under `--spend` the default is the repository's
own checked-in `budget.yaml` at `find_root()`, and `--budget` may name that file and no other:
any other path is refused as `SpendDenied`, by name, before the pipeline is even imported and
with nothing written. `--budget-override PATH` is the one spelling that spends against a
budget this repository did not check in — the explicit act D0240 asks for, rather than a
flag whose shortest spelling quietly authorises a file nobody reviewed (BRIEF §5, the
correct-by-default catalogue). The two flags exclude each other. Without `--spend` neither is
consulted at all: replay-only refuses a novel invocation whatever they name.

A library enforces the authorisation it is handed and must not read the constitution (D0240,
D0243): SpendGuard still admits against whatever `Budget` it is given, and it is HERE — in
the shell, which is where a repository's own files may be read — that the checked-in budget
binds.
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
    Budget,
    CaptureConflict,
    CaptureWriteFailed,
    NovelInvocationRefused,
    Oracles,
    SpendDenied,
    load_budget,
)
from tannen.store import Store

__all__ = ["REFUSALS", "admitting_budget", "checked_in_budget", "main"]

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
    # Mutually exclusive, so naming both is argparse's usage error (exit 2) rather than a
    # precedence rule nobody would remember: they are two answers to one question.
    budgets = run.add_mutually_exclusive_group()
    budgets.add_argument("--budget", type=Path, default=None,
                         help="the checked-in budget.yaml, named explicitly; any other file is "
                              "refused (--budget-override spends against one)")
    budgets.add_argument("--budget-override", type=Path, default=None, dest="budget_override",
                         help="spend against a budget this repository did not check in — the "
                              "one spelling that may (D0240)")
    run.add_argument("--spend", action="store_true",
                     help="allow novel oracle invocations, each admitted by SpendGuard")
    run.set_defaults(handler=_run)
    return parser


def _laws_report(args: argparse.Namespace) -> int:
    root = (args.root or find_root()).resolve()
    report = build_report(root, args.milestones)
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render(report))
    return 0 if report["ok"] else 1


def checked_in_budget(start: Path | None = None) -> Path:
    """The repository's own budget file — the only one `--spend` admits against unless
    `--budget-override` names another (docs/specs/m5.md §6)."""
    return find_root(start) / "budget.yaml"


def admitting_budget(spend: bool, budget: Path | None, override: Path | None) -> Budget | None:
    """The `Budget` this invocation may spend against, or `None` when it may not spend at all.

    Without `--spend` neither flag is consulted — not read, not resolved, not validated: a
    replay refuses a novel invocation whatever they name, and a clamp that fired in replay mode
    would break L4.4's first node for a spend that was never possible.
    """
    if not spend:
        return None
    if override is not None:
        return load_budget(override)
    checked_in = checked_in_budget()
    if not (checked_in.parent / "MANIFEST.sha256").is_file():
        # find_root falls back to the cwd, so outside a checkout "checked-in" named any file (RT-M5-06).
        raise SpendDenied(
            f"{checked_in.parent} is not inside a tannen checkout (no MANIFEST.sha256 above it), "
            "so there is no checked-in budget; --budget-override names a budget from elsewhere"
        )
    if budget is not None and Path(budget).resolve() != checked_in.resolve():
        raise SpendDenied(
            f"--budget names {Path(budget)}, which is not this repository's checked-in budget "
            f"at {checked_in}; spending against another file is spelled --budget-override "
            "(docs/specs/m5.md §6, owner ruling D0240)"
        )
    if not checked_in.is_file():
        raise SpendDenied(
            f"there is no checked-in budget at {checked_in}, so nothing here authorises a "
            "spend; --budget-override names a budget from elsewhere"
        )
    return load_budget(checked_in)


def _refused(exc: BaseException) -> int:
    print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
    return 1


def _run(args: argparse.Namespace) -> int:
    module, attr = args.target
    # The clamp comes FIRST, before the pipeline is imported and before a store is opened:
    # a refusal that arrives after the module ran, or after anything was written, is a
    # refusal that already happened (L5.1's `calls` and `wrote` clauses).
    try:
        budget = admitting_budget(args.spend, args.budget, args.budget_override)
    except SpendDenied as exc:
        return _refused(exc)
    # A console script's sys.path[0] is its bin directory, not the working directory;
    # `tannen run pipeline:main` should find the `pipeline.py` it is run beside.
    here = str(Path.cwd())
    if "" not in sys.path and here not in sys.path:
        sys.path.insert(0, here)
    callable_ = getattr(importlib.import_module(module), attr)
    context = Oracles(
        Store(args.store),
        mode=SPEND if args.spend else REPLAY,
        budget=budget,
    )
    try:
        result = callable_(context)
    except REFUSALS as exc:
        return _refused(exc)
    if isinstance(result, str):
        print(result)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
