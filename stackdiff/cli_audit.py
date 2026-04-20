"""CLI sub-commands for the audit log feature."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from stackdiff.audit import load_audit_log
from stackdiff.audit_report import format_audit_log, destructive_entries


def _add_audit_parser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("audit", help="View the audit log of past diff runs")
    p.add_argument(
        "--audit-dir",
        default=".stackdiff/audit",
        metavar="DIR",
        help="Directory containing audit.jsonl (default: .stackdiff/audit)",
    )
    p.add_argument(
        "--destructive-only",
        action="store_true",
        help="Show only entries that contained destructive changes",
    )
    p.add_argument(
        "--tags",
        action="store_true",
        help="Include tags column in output",
    )
    p.set_defaults(func=_cmd_audit)


def _cmd_audit(args: argparse.Namespace) -> int:
    entries = load_audit_log(args.audit_dir)
    if args.destructive_only:
        entries = destructive_entries(entries)
    print(format_audit_log(entries, show_tags=args.tags))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stackdiff-audit",
        description="Audit log viewer for stackdiff",
    )
    sub = parser.add_subparsers(dest="command")
    _add_audit_parser(sub)
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)
    sys.exit(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    main()
