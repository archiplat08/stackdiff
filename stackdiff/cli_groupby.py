"""CLI sub-command: stackdiff groupby."""
from __future__ import annotations

import argparse
import sys

from stackdiff.parser import parse_plan_text
from stackdiff.diff import build_report
from stackdiff.groupby import group_report, format_grouped, GroupDimension


def _add_groupby_parser(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("groupby", help="Group plan changes by action, resource_type, or module")
    p.add_argument("plan", help="Path to terraform plan text output")
    p.add_argument(
        "--by",
        dest="dimension",
        choices=["action", "resource_type", "module"],
        default="action",
        help="Dimension to group by (default: action)",
    )
    p.add_argument("--json", action="store_true", help="Emit JSON instead of text")


def _cmd_groupby(args: argparse.Namespace) -> int:
    try:
        text = open(args.plan).read()
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    changes = parse_plan_text(text)
    report = build_report(changes)
    dimension: GroupDimension = args.dimension  # type: ignore[assignment]
    grouped = group_report(report, dimension)

    if args.json:
        import json

        payload = {
            "dimension": grouped.dimension,
            "total": grouped.total(),
            "groups": {
                k: [e.change.address for e in v] for k, v in grouped.groups.items()
            },
        }
        print(json.dumps(payload, indent=2))
    else:
        print(format_grouped(grouped))

    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="stackdiff-groupby")
    sub = p.add_subparsers(dest="command")
    _add_groupby_parser(sub)
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(0)
    sys.exit(_cmd_groupby(args))


if __name__ == "__main__":  # pragma: no cover
    main()
