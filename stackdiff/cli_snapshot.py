"""CLI sub-commands for snapshot management."""
from __future__ import annotations

import argparse
import sys

from stackdiff.parser import parse_plan_text
from stackdiff.diff import build_report
from stackdiff.formatter import format_report
from stackdiff.snapshot import save_snapshot, load_snapshot, list_snapshots, delete_snapshot
from stackdiff.compare import compare_reports

DEFAULT_SNAPSHOTS_DIR = ".stackdiff/snapshots"


def _add_snapshot_parser(sub: argparse.Action) -> None:
    p = sub.add_parser("snapshot", help="Manage plan snapshots")
    cmds = p.add_subparsers(dest="snapshot_cmd", required=True)

    save_p = cmds.add_parser("save", help="Save a snapshot from a plan file")
    save_p.add_argument("name", help="Snapshot name")
    save_p.add_argument("plan_file", help="Path to Terraform plan text file")
    save_p.add_argument("--dir", default=DEFAULT_SNAPSHOTS_DIR, dest="snapshots_dir")

    cmds.add_parser("list", help="List saved snapshots").add_argument(
        "--dir", default=DEFAULT_SNAPSHOTS_DIR, dest="snapshots_dir"
    )

    show_p = cmds.add_parser("show", help="Show a snapshot")
    show_p.add_argument("name")
    show_p.add_argument("--dir", default=DEFAULT_SNAPSHOTS_DIR, dest="snapshots_dir")

    diff_p = cmds.add_parser("diff", help="Diff two snapshots")
    diff_p.add_argument("base", help="Base snapshot name")
    diff_p.add_argument("head", help="Head snapshot name")
    diff_p.add_argument("--dir", default=DEFAULT_SNAPSHOTS_DIR, dest="snapshots_dir")

    del_p = cmds.add_parser("delete", help="Delete a snapshot")
    del_p.add_argument("name")
    del_p.add_argument("--dir", default=DEFAULT_SNAPSHOTS_DIR, dest="snapshots_dir")


def _cmd_snapshot(args: argparse.Namespace) -> int:
    cmd = args.snapshot_cmd

    if cmd == "save":
        text = open(args.plan_file).read()
        changes = parse_plan_text(text)
        report = build_report(changes)
        path = save_snapshot(report, args.name, args.plan_file, args.snapshots_dir)
        print(f"Snapshot '{args.name}' saved to {path}")
        return 0

    if cmd == "list":
        names = list_snapshots(args.snapshots_dir)
        if not names:
            print("No snapshots found.")
        for n in names:
            print(n)
        return 0

    if cmd == "show":
        snap = load_snapshot(args.name, args.snapshots_dir)
        if snap is None:
            print(f"Snapshot '{args.name}' not found.", file=sys.stderr)
            return 1
        from stackdiff.diff import DiffReport
        report = DiffReport(entries=snap.entries)
        print(f"Snapshot: {snap.name}  created: {snap.created_at}  plan: {snap.plan_file}")
        print(format_report(report))
        return 0

    if cmd == "diff":
        base = load_snapshot(args.base, args.snapshots_dir)
        head = load_snapshot(args.head, args.snapshots_dir)
        if base is None or head is None:
            missing = args.base if base is None else args.head
            print(f"Snapshot '{missing}' not found.", file=sys.stderr)
            return 1
        from stackdiff.diff import DiffReport
        result = compare_reports(DiffReport(entries=base.entries), DiffReport(entries=head.entries))
        print(f"Added:   {len(result.added)}")
        print(f"Removed: {len(result.removed)}")
        print(f"Changed: {len(result.changed)}")
        return 0

    if cmd == "delete":
        ok = delete_snapshot(args.name, args.snapshots_dir)
        if not ok:
            print(f"Snapshot '{args.name}' not found.", file=sys.stderr)
            return 1
        print(f"Snapshot '{args.name}' deleted.")
        return 0

    return 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="stackdiff-snapshot")
    sub = p.add_subparsers(dest="cmd", required=True)
    _add_snapshot_parser(sub)
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(_cmd_snapshot(args))
