"""CLI sub-command: stackdiff gate — CI gate for plan files."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from stackdiff.parser import parse_plan_text
from stackdiff.diff import build_report
from stackdiff.policy import PolicyRule
from stackdiff.threshold import ThresholdOptions
from stackdiff.gate import GateOptions, evaluate_gate, format_gate_result


def _add_gate_parser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("gate", help="CI gate: evaluate plan against policy, thresholds and risk")
    p.add_argument("plan", help="Terraform plan text file")
    p.add_argument("--no-destroy", action="store_true", help="Block any destroy actions")
    p.add_argument("--no-replace", action="store_true", help="Block any replace actions")
    p.add_argument("--max-risk", type=float, default=None, metavar="SCORE",
                   help="Fail if total risk score exceeds this value")
    p.add_argument("--max-deletes", type=int, default=None, metavar="N")
    p.add_argument("--max-changes", type=int, default=None, metavar="N")
    p.add_argument("--format", choices=["text", "json"], default="text")


def _cmd_gate(args: argparse.Namespace) -> int:
    path = Path(args.plan)
    if not path.exists():
        print(f"error: plan file not found: {path}", file=sys.stderr)
        return 1

    changes = parse_plan_text(path.read_text())
    report = build_report(changes)

    rules: list[PolicyRule] = []
    if args.no_destroy:
        from stackdiff.policy import PolicyRule, ChangeAction
        rules.append(PolicyRule(name="no-destroy", action=ChangeAction.DELETE, blocking=True))
    if args.no_replace:
        from stackdiff.policy import PolicyRule, ChangeAction
        rules.append(PolicyRule(name="no-replace", action=ChangeAction.REPLACE, blocking=True))

    thresholds = ThresholdOptions(
        max_deletes=args.max_deletes,
        max_changes=args.max_changes,
    )

    options = GateOptions(rules=rules, thresholds=thresholds, max_risk_score=args.max_risk)
    result = evaluate_gate(report, options)

    if args.format == "json":
        print(json.dumps({
            "passed": result.passed,
            "exit_code": result.exit_code,
            "risk_score": result.risk.score,
            "risk_level": result.risk.level,
            "policy_blocks": [v.message for v in result.policy.violations if v.rule.blocking],
            "policy_warns": [v.message for v in result.policy.violations if not v.rule.blocking],
            "threshold_violations": [v.message for v in result.threshold.violations],
        }, indent=2))
    else:
        print(format_gate_result(result))

    return result.exit_code


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="stackdiff-gate")
    sub = p.add_subparsers(dest="command")
    _add_gate_parser(sub)
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    sys.exit(_cmd_gate(args))
