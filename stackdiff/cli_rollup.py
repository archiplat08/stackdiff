"""CLI sub-command: rollup — aggregate multiple Terraform plan files."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from stackdiff.diff import build_report
from stackdiff.parser import parse_plan_text
from stackdiff.rollup import build_rollup, format_rollup


def _add_rollup_parser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser(
        "rollup",
        help="Aggregate multiple plan files into a cross-stack summary.",
    )
    p.add_argument(
        "plans",
        nargs="+",
        metavar="NAME=FILE",
        help="One or more stack=plan_file pairs, e.g. prod=plan.txt staging=plan2.txt",
    )
    p.add_argument(
        "--fail-on-destructive",
        action="store_true",
        default=False,
        help="Exit with code 2 if any stack has destructive changes.",
    )
    p.add_argument(
        "--max-risk",
        type=int,
        default=None,
        metavar="N",
        help="Exit with code 2 if max risk score across stacks exceeds N.",
    )
    p.set_defaults(func=_cmd_rollup)


def _cmd_rollup(args: argparse.Namespace) -> int:
    named_reports = {}
    for pair in args.plans:
        if "=" not in pair:
            print(f"ERROR: expected NAME=FILE, got: {pair}", file=sys.stderr)
            return 1
        name, path_str = pair.split("=", 1)
        path = Path(path_str)
        if not path.exists():
            print(f"ERROR: plan file not found: {path}", file=sys.stderr)
            return 1
        text = path.read_text()
        changes = parse_plan_text(text)
        named_reports[name] = build_report(changes)

    rollup = build_rollup(named_reports)
    print(format_rollup(rollup))

    if args.fail_on_destructive and rollup.any_destructive:
        return 2
    if args.max_risk is not None and rollup.max_risk_score > args.max_risk:
        return 2
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stackdiff-rollup")
    sub = parser.add_subparsers(dest="command")
    _add_rollup_parser(sub)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(0)
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
