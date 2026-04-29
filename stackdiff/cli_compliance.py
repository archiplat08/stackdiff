"""CLI sub-command: stackdiff compliance — check a plan against a compliance framework."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from stackdiff.parser import parse_plan_text
from stackdiff.diff import build_report
from stackdiff.compliance import check_compliance, format_compliance, FRAMEWORKS


def _add_compliance_parser(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    p = subparsers.add_parser(
        "compliance",
        help="Check a Terraform plan against a named compliance framework.",
    )
    p.add_argument("plan", help="Path to terraform plan text output")
    p.add_argument(
        "--framework",
        required=True,
        choices=list(FRAMEWORKS.keys()),
        help="Compliance framework to evaluate against",
    )
    p.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        dest="fmt",
        help="Output format (default: text)",
    )
    p.set_defaults(func=_cmd_compliance)


def _cmd_compliance(args: argparse.Namespace) -> int:
    plan_path = Path(args.plan)
    if not plan_path.exists():
        print(f"error: plan file not found: {plan_path}", file=sys.stderr)
        return 1

    text = plan_path.read_text(encoding="utf-8")
    changes = parse_plan_text(text)
    report = build_report(changes)
    result = check_compliance(report, args.framework)

    if args.fmt == "json":
        import json
        payload = {
            "framework": result.framework,
            "passed": result.passed,
            "block_count": result.block_count,
            "warn_count": result.warn_count,
            "violations": [
                {"address": e.address, "action": e.action,
                 "violations": [{"severity": v.severity, "message": v.message} for v in e.violations]}
                for e in result.violations
            ],
        }
        print(json.dumps(payload, indent=2))
    else:
        print(format_compliance(result))

    return 0 if result.passed else 2


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="stackdiff-compliance")
    sub = p.add_subparsers(dest="command")
    _add_compliance_parser(sub)
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(0)
    sys.exit(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    main()
