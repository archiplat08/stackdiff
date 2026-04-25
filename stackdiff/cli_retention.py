"""CLI sub-command: stackdiff retention — prune snapshots / audit logs."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from stackdiff.retention import RetentionOptions, prune_directory


def _add_retention_parser(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("retention", help="Prune old snapshots or audit log files")
    p.add_argument("directory", help="Directory to prune (snapshots or audit log dir)")
    p.add_argument(
        "--max-age-days",
        type=int,
        default=None,
        metavar="N",
        help="Remove files older than N days",
    )
    p.add_argument(
        "--max-count",
        type=int,
        default=None,
        metavar="N",
        help="Keep only the N most recent files",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be removed without deleting",
    )


def _cmd_retention(args: argparse.Namespace) -> int:
    directory = Path(args.directory)
    if not directory.exists():
        print(f"error: directory not found: {directory}", file=sys.stderr)
        return 1

    options = RetentionOptions(
        max_age_days=args.max_age_days,
        max_count=args.max_count,
    )

    if args.dry_run:
        # Simulate without deleting
        from stackdiff.retention import _mtime
        from datetime import datetime, timedelta, timezone

        files = sorted(directory.iterdir(), key=_mtime, reverse=True)
        survivors = list(files)
        if options.max_age_days is not None:
            cutoff = datetime.now(tz=timezone.utc) - timedelta(days=options.max_age_days)
            survivors = [f for f in survivors if _mtime(f) >= cutoff]
        if options.max_count is not None:
            survivors = survivors[: options.max_count]
        to_remove = [f for f in files if f not in set(survivors)]
        for f in to_remove:
            print(f"[dry-run] would remove: {f}")
        print(f"[dry-run] {len(to_remove)} file(s) would be removed, {len(survivors)} kept")
        return 0

    result = prune_directory(directory, options)
    for f in result.removed:
        print(f"removed: {f}")
    print(f"{result.total_removed} file(s) removed, {result.total_kept} kept")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stackdiff-retention")
    sub = parser.add_subparsers(dest="command")
    _add_retention_parser(sub)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    sys.exit(_cmd_retention(args))
