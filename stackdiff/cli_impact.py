"""CLI sub-command: stackdiff impact <plan-file>

Prints an impact classification for the given Terraform plan output.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from stackdiff.parser import parse_plan_text
from stackdiff.diff import build_report
from stackdiff.impact import classify_impact, format_impact, ImpactLevel


def _add_impact_parser(subparsers: argparse.Action) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser(
        "impact",
        help="Classify the blast radius of a Terraform plan.",
    )
    p.add_argument("plan", help="Path to terraform plan text output.")
    p.add_argument(
        "--min-level",
        choices=[l.value for l in ImpactLevel],
        default=None,
        help="Exit non-zero when impact is at or above this level.",
    )
    p.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    p.set_defaults(func=_cmd_impact)


_LEVEL_ORDER = [
    ImpactLevel.NONE,
    ImpactLevel.LOW,
    ImpactLevel.MEDIUM,
    ImpactLevel.HIGH,
    ImpactLevel.CRITICAL,
]


def _cmd_impact(args: argparse.Namespace) -> int:
    plan_path = Path(args.plan)
    if not plan_path.exists():
        print(f"error: plan file not found: {plan_path}", file=sys.stderr)
        return 1

    text = plan_path.read_text()
    changes = parse_plan_text(text)
    report = build_report(changes)
    result = classify_impact(report)

    if getattr(args, "json", False):
        import json
        print(json.dumps({
            "level": result.level.value,
            "risk_score": result.risk_score,
            "total_changes": result.total_changes,
            "destructive": result.destructive,
            "reason": result.reason,
        }))
    else:
        print(format_impact(result))

    if args.min_level:
        threshold = ImpactLevel(args.min_level)
        if _LEVEL_ORDER.index(result.level) >= _LEVEL_ORDER.index(threshold):
            return 2

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stackdiff-impact")
    subs = parser.add_subparsers(dest="command")
    _add_impact_parser(subs)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
