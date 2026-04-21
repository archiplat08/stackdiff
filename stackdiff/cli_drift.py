"""CLI sub-command: drift — compare two snapshots to detect infrastructure drift."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from stackdiff.snapshot import load_snapshot, list_snapshots
from stackdiff.drift import build_drift_report, format_drift_report
from stackdiff.export import to_json


def _add_drift_parser(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    p = subparsers.add_parser(
        "drift",
        help="Detect drift between two saved snapshots.",
        description=(
            "Compare a baseline snapshot against a later snapshot and report "
            "resources that were added, removed, or whose action changed."
        ),
    )
    p.add_argument(
        "baseline",
        metavar="BASELINE",
        help="Name of the baseline snapshot (earlier state).",
    )
    p.add_argument(
        "current",
        metavar="CURRENT",
        help="Name of the current snapshot (later state).",
    )
    p.add_argument(
        "--snap-dir",
        default=".stackdiff/snapshots",
        metavar="DIR",
        help="Directory where snapshots are stored (default: .stackdiff/snapshots).",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Emit drift report as JSON instead of human-readable text.",
    )
    p.add_argument(
        "--list",
        action="store_true",
        help="List available snapshots in SNAP_DIR and exit.",
    )
    p.set_defaults(func=_cmd_drift)


def _cmd_drift(args: argparse.Namespace) -> int:
    snap_dir = Path(args.snap_dir)

    # --list: enumerate snapshots and exit
    if args.list:
        names = list_snapshots(snap_dir)
        if not names:
            print("No snapshots found in", snap_dir)
            return 0
        for name in sorted(names):
            print(name)
        return 0

    # Load baseline snapshot
    baseline_snap = load_snapshot(args.baseline, snap_dir)
    if baseline_snap is None:
        print(
            f"error: baseline snapshot '{args.baseline}' not found in {snap_dir}",
            file=sys.stderr,
        )
        return 1

    # Load current snapshot
    current_snap = load_snapshot(args.current, snap_dir)
    if current_snap is None:
        print(
            f"error: current snapshot '{args.current}' not found in {snap_dir}",
            file=sys.stderr,
        )
        return 1

    drift_report = build_drift_report(baseline_snap.report, current_snap.report)

    if args.json:
        # Serialise drift items as a JSON array
        import json

        items = [
            {
                "address": item.address,
                "drift_type": item.drift_type,
                "baseline_action": item.baseline_action,
                "current_action": item.current_action,
            }
            for item in drift_report.items
        ]
        print(json.dumps(items, indent=2))
    else:
        text = format_drift_report(drift_report)
        print(text)

    # Exit 1 when drift is detected so CI pipelines can react
    return 1 if drift_report.items else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stackdiff-drift",
        description="Detect infrastructure drift between snapshots.",
    )
    sub = parser.add_subparsers(dest="command")
    _add_drift_parser(sub)
    return parser


def main(argv: list[str] | None = None) -> None:  # pragma: no cover
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(0)
    sys.exit(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    main()
