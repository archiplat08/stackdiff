"""CLI sub-command: stackdiff quarantine — flag high-risk entries for review."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

from stackdiff.annotate import annotate_report
from stackdiff.diff import DiffReport
from stackdiff.parser import parse_plan_text
from stackdiff.policy import PolicyRule
from stackdiff.quarantine import (
    QuarantineRule,
    apply_quarantine,
    format_quarantine_text,
)


def _add_quarantine_parser(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("quarantine", help="Flag high-risk or policy-violating changes")
    p.add_argument("plan", help="Path to terraform plan text file")
    p.add_argument("--min-risk", type=int, default=None, metavar="SCORE",
                   help="Quarantine entries with risk score >= SCORE")
    p.add_argument("--actions", nargs="+", default=[],
                   metavar="ACTION", help="Quarantine specific actions (delete, replace, …)")
    p.add_argument("--resource-types", nargs="+", default=[],
                   metavar="TYPE", help="Quarantine specific resource types")
    p.add_argument("--format", choices=["text", "json"], default="text",
                   dest="fmt", help="Output format (default: text)")
    p.add_argument("--no-policy", action="store_true",
                   help="Skip default policy rules during annotation")


def _cmd_quarantine(args: argparse.Namespace) -> int:
    plan_path = Path(args.plan)
    if not plan_path.exists():
        print(f"error: plan file not found: {plan_path}", file=sys.stderr)
        return 1

    changes = parse_plan_text(plan_path.read_text())
    report = DiffReport(entries=[c for c in changes])

    policy_rules: List[PolicyRule] = []
    if not args.no_policy:
        policy_rules = [
            PolicyRule(name="no-destroy", action="delete", severity="block"),
            PolicyRule(name="no-replace", action="replace", severity="warn"),
        ]

    annotated = annotate_report(report, policy_rules=policy_rules)

    q_rules: List[QuarantineRule] = []
    if args.min_risk is not None or args.actions or args.resource_types:
        q_rules.append(
            QuarantineRule(
                min_risk_score=args.min_risk,
                actions=list(args.actions),
                resource_types=list(args.resource_types),
            )
        )
    else:
        # Default: quarantine anything with risk >= 50 or a block violation
        q_rules.append(QuarantineRule(min_risk_score=50))
        q_rules.append(QuarantineRule(actions=["delete", "replace"]))

    result = apply_quarantine(annotated, q_rules)

    if args.fmt == "json":
        payload = {
            "total_quarantined": result.total_quarantined,
            "total_allowed": result.total_allowed,
            "quarantined": [
                {
                    "address": e.address,
                    "action": e.action.value if hasattr(e.action, "value") else str(e.action),
                    "risk_score": e.risk.score,
                }
                for e in result.quarantined
            ],
        }
        print(json.dumps(payload, indent=2))
    else:
        print(format_quarantine_text(result))

    return 0 if result.is_clean else 2


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="stackdiff-quarantine")
    sub = p.add_subparsers(dest="cmd")
    _add_quarantine_parser(sub)
    return p


def main() -> None:  # pragma: no cover
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(_cmd_quarantine(args))
