"""CLI sub-command: stackdiff ownership — show resource ownership for a plan."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from stackdiff.parser import parse_plan_text
from stackdiff.diff import build_report
from stackdiff.ownership import build_ownership
from stackdiff.ownership_format import (
    format_ownership_text,
    ownership_to_json,
    ownership_to_markdown,
)


def _add_ownership_parser(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("ownership", help="Show resource ownership from a plan file")
    p.add_argument("plan", help="Path to Terraform plan text file")
    p.add_argument(
        "--map",
        dest="owner_map",
        default=None,
        help="JSON file mapping addresses to owner/team metadata",
    )
    p.add_argument(
        "--format",
        dest="fmt",
        choices=["text", "json", "markdown"],
        default="text",
    )
    p.add_argument(
        "--warn-unowned",
        action="store_true",
        help="Exit 1 if any resources have no owner",
    )
    p.set_defaults(func=_cmd_ownership)


def _cmd_ownership(args: argparse.Namespace) -> int:
    plan_text = Path(args.plan).read_text()
    changes = parse_plan_text(plan_text)
    report = build_report(changes)

    owner_map: dict = {}
    if args.owner_map:
        owner_map = json.loads(Path(args.owner_map).read_text())

    ownership = build_ownership(report, owner_map)

    if args.fmt == "json":
        print(ownership_to_json(ownership))
    elif args.fmt == "markdown":
        print(ownership_to_markdown(ownership))
    else:
        print(format_ownership_text(ownership))

    if args.warn_unowned and ownership.unowned():
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stackdiff-ownership")
    sub = parser.add_subparsers(dest="command")
    _add_ownership_parser(sub)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(0)
    sys.exit(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    main()
