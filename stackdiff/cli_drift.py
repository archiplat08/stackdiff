"""CLI sub-command: stackdiff drift — detect drift between a snapshot and a plan."""

from __future__ import annotations

import argparse
import sys

from stackdiff.parser import parse_plan_text
from stackdiff.diff import build_report
from stackdiff.snapshot import load_snapshot
from stackdiff.drift import detect_drift, format_drift


def _add_drift_parser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "drift",
        help="Detect drift between a saved snapshot and a new plan file.",
    )
    p.add_argument("snapshot_name", help="Name of the saved snapshot to use as baseline.")
    p.add_argument("plan_file", help="Path to the new Terraform plan text file.")
    p.add_argument(
        "--snap-dir",
        default=".stackdiff/snapshots",
        help="Directory where snapshots are stored (default: .stackdiff/snapshots).",
    )
    p.add_argument(
        "--exit-code",
        action="store_true",
        help="Exit with code 1 when drift is detected.",
    )


def _cmd_drift(args: argparse.Namespace) -> int:
    snapshot = load_snapshot(args.snapshot_name, base_dir=args.snap_dir)
    if snapshot is None:
        print(f"Error: snapshot '{args.snapshot_name}' not found in {args.snap_dir}", file=sys.stderr)
        return 2

    try:
        plan_text = open(args.plan_file).read()
    except OSError as exc:
        print(f"Error reading plan file: {exc}", file=sys.stderr)
        return 2

    changes = parse_plan_text(plan_text)
    current_report = build_report(changes)
    drift_report = detect_drift(snapshot, current_report)

    print(format_drift(drift_report))

    if args.exit_code and drift_report.has_drift:
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stackdiff-drift")
    subs = parser.add_subparsers(dest="command")
    _add_drift_parser(subs)
    return parser


def main() -> None:  # pragma: no cover
    parser = build_parser()
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(0)
    sys.exit(_cmd_drift(args))
