"""CLI sub-command: heatmap — frequency analysis across plan files."""
from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path

from stackdiff.parser import parse_plan_text
from stackdiff.diff import build_report
from stackdiff.heatmap import build_heatmap, format_heatmap


def _add_heatmap_parser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser(
        "heatmap",
        help="Show change frequency across multiple Terraform plan files.",
    )
    p.add_argument(
        "plans",
        nargs="+",
        metavar="PLAN",
        help="Terraform plan text files (glob patterns accepted).",
    )
    p.add_argument(
        "--top",
        type=int,
        default=10,
        metavar="N",
        help="Show top N most-changed resources (default: 10).",
    )
    p.add_argument(
        "--hot-only",
        action="store_true",
        help="Only show resources that changed more than once.",
    )
    p.set_defaults(func=_cmd_heatmap)


def _cmd_heatmap(args: argparse.Namespace) -> int:
    paths: list[Path] = []
    for pattern in args.plans:
        matched = glob.glob(pattern, recursive=True)
        if not matched:
            print(f"Warning: no files matched '{pattern}'", file=sys.stderr)
        paths.extend(Path(m) for m in matched)

    if not paths:
        print("Error: no plan files found.", file=sys.stderr)
        return 1

    reports = []
    for path in paths:
        try:
            text = path.read_text()
        except OSError as exc:
            print(f"Warning: cannot read {path}: {exc}", file=sys.stderr)
            continue
        changes = parse_plan_text(text)
        reports.append(build_report(changes))

    heatmap = build_heatmap(reports)

    if args.hot_only:
        from stackdiff.heatmap import HeatmapReport
        heatmap = HeatmapReport(entries=heatmap.hot_resources)

    print(format_heatmap(heatmap, top_n=args.top))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stackdiff-heatmap")
    sub = parser.add_subparsers(dest="command")
    _add_heatmap_parser(sub)
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
