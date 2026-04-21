"""CLI sub-command: stackdiff remediation — show remediation hints for a plan."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from stackdiff.parser import parse_plan_text
from stackdiff.diff import build_report
from stackdiff.policy import load_rules, evaluate
from stackdiff.annotate import annotate_report
from stackdiff.remediation import suggest, format_hints


def _add_remediation_parser(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("remediation", help="Show remediation hints for a plan file")
    p.add_argument("plan", help="Path to terraform plan text output")
    p.add_argument(
        "--policy",
        metavar="FILE",
        help="Optional YAML policy file",
        default=None,
    )
    p.add_argument(
        "--exit-code",
        action="store_true",
        help="Exit 1 when any hint is produced",
    )


def _cmd_remediation(args: argparse.Namespace) -> int:
    plan_path = Path(args.plan)
    if not plan_path.exists():
        print(f"error: plan file not found: {plan_path}", file=sys.stderr)
        return 2

    text = plan_path.read_text()
    changes = parse_plan_text(text)
    report = build_report(changes)

    rules = load_rules(args.policy) if args.policy else []
    annotated = annotate_report(report, rules)

    hints = suggest(annotated)
    print(format_hints(hints))

    if args.exit_code and hints:
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stackdiff")
    sub = parser.add_subparsers(dest="command")
    _add_remediation_parser(sub)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(0)
    sys.exit(_cmd_remediation(args))


if __name__ == "__main__":
    main()
