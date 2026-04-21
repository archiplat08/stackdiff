"""CLI sub-command: stackdiff threshold — check risk/destructive thresholds."""
from __future__ import annotations

import argparse
import sys

from stackdiff.parser import parse_plan_text
from stackdiff.diff import build_report
from stackdiff.threshold import (
    ThresholdOptions,
    check_thresholds,
    format_threshold_result,
)


def _add_threshold_parser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "threshold",
        help="Fail if risk score or destructive-change count exceeds limits.",
    )
    p.add_argument("plan", help="Path to terraform plan text output")
    p.add_argument(
        "--max-risk-score",
        type=int,
        default=None,
        metavar="N",
        help="Maximum allowed total risk score.",
    )
    p.add_argument(
        "--max-destructive",
        type=int,
        default=None,
        metavar="N",
        help="Maximum allowed destroys + replaces.",
    )
    p.add_argument(
        "--max-high-risk",
        type=int,
        default=None,
        metavar="N",
        help="Maximum allowed HIGH-risk entries.",
    )


def _cmd_threshold(args: argparse.Namespace) -> int:
    try:
        text = open(args.plan).read()
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    changes = parse_plan_text(text)
    report = build_report(changes)
    opts = ThresholdOptions(
        max_risk_score=args.max_risk_score,
        max_destructive=args.max_destructive,
        max_high_risk=args.max_high_risk,
    )
    result = check_thresholds(report, opts)
    print(format_threshold_result(result))
    return 0 if result.passed else 2


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="stackdiff-threshold")
    sub = p.add_subparsers(dest="command")
    _add_threshold_parser(sub)
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    sys.exit(_cmd_threshold(args))
