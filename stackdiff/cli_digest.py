"""CLI entry-point for the digest subcommand."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from stackdiff.audit import load_audit_log
from stackdiff.digest import build_digest
from stackdiff.digest_format import format_digest, digest_to_dict


def _add_digest_parser(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("digest", help="Produce a summary digest from the audit log")
    p.add_argument("audit_log", help="Path to the JSONL audit log file")
    p.add_argument(
        "--period",
        choices=["daily", "weekly"],
        default="daily",
        help="Digest period (default: daily)",
    )
    p.add_argument(
        "--reference",
        metavar="ISO_DATETIME",
        default=None,
        help="Reference datetime for period end (ISO-8601, default: now)",
    )
    p.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        dest="fmt",
        help="Output format (default: text)",
    )
    p.add_argument("--no-color", action="store_true", help="Disable ANSI colors")


def _cmd_digest(args: argparse.Namespace) -> int:
    log_path = Path(args.audit_log)
    if not log_path.exists():
        print(f"error: audit log not found: {log_path}", file=sys.stderr)
        return 1

    entries = load_audit_log(log_path)
    reference: datetime | None = None
    if args.reference:
        try:
            reference = datetime.fromisoformat(args.reference).replace(tzinfo=timezone.utc)
        except ValueError as exc:
            print(f"error: invalid --reference value: {exc}", file=sys.stderr)
            return 1

    digest = build_digest(entries, label=args.period, reference=reference)

    if args.fmt == "json":
        print(json.dumps(digest_to_dict(digest), indent=2))
    else:
        print(format_digest(digest, color=not args.no_color))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stackdiff-digest")
    sub = parser.add_subparsers(dest="command")
    _add_digest_parser(sub)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    sys.exit(_cmd_digest(args))
