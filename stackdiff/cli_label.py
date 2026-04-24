"""CLI sub-command: stackdiff label — display a plan with resource labels applied."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from stackdiff.diff import build_report
from stackdiff.label import LabelMap, apply_labels, format_labeled_report
from stackdiff.parser import parse_plan_text


def _add_label_parser(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("label", help="Display plan with key/value labels applied to resources")
    p.add_argument("plan", help="Path to a Terraform plan text file")
    p.add_argument(
        "--labels",
        metavar="FILE",
        help="JSON file mapping resource address to label dict",
    )
    p.add_argument(
        "--filter-key",
        metavar="KEY",
        help="Only show entries that have this label key",
    )
    p.add_argument(
        "--filter-value",
        metavar="VALUE",
        help="Combined with --filter-key: only show entries where key=value",
    )


def _cmd_label(args: argparse.Namespace) -> int:
    plan_text = Path(args.plan).read_text()
    changes = parse_plan_text(plan_text)
    report = build_report(changes)

    label_map: LabelMap = {}
    if args.labels:
        raw = json.loads(Path(args.labels).read_text())
        if not isinstance(raw, dict):
            print("ERROR: labels file must be a JSON object", file=sys.stderr)
            return 1
        label_map = raw

    labeled = apply_labels(report, label_map)

    if args.filter_key:
        labeled = labeled.filter_by_label(args.filter_key, args.filter_value or None)

    print(format_labeled_report(labeled))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="stackdiff-label")
    sub = p.add_subparsers(dest="command")
    _add_label_parser(sub)
    return p


def main() -> None:  # pragma: no cover
    parser = build_parser()
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(0)
    sys.exit(_cmd_label(args))
