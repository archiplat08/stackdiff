"""CLI sub-command: stackdiff approval — check whether a plan needs approval."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from stackdiff.parser import parse_plan_text
from stackdiff.diff import build_report
from stackdiff.policy import load_rules
from stackdiff.approval import ApprovalOptions, check_approval


def _add_approval_parser(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("approval", help="Check whether a plan requires human approval")
    p.add_argument("plan", help="Path to terraform plan text file")
    p.add_argument("--policy", metavar="FILE", help="YAML policy rules file")
    p.add_argument("--min-risk", type=int, default=None, metavar="N",
                   help="Require approval when risk score >= N")
    p.add_argument("--no-destroy-gate", action="store_true",
                   help="Do not require approval for destroy actions")
    p.add_argument("--no-replace-gate", action="store_true",
                   help="Do not require approval for replace actions")
    p.add_argument("--json", dest="as_json", action="store_true",
                   help="Emit result as JSON")
    p.set_defaults(func=_cmd_approval)


def _cmd_approval(args: argparse.Namespace) -> int:
    plan_path = Path(args.plan)
    if not plan_path.exists():
        print(f"error: plan file not found: {plan_path}", file=sys.stderr)
        return 1

    changes = parse_plan_text(plan_path.read_text())
    report = build_report(changes)

    rules = []
    if args.policy:
        policy_path = Path(args.policy)
        if not policy_path.exists():
            print(f"error: policy file not found: {policy_path}", file=sys.stderr)
            return 1
        rules = load_rules(policy_path)

    opts = ApprovalOptions(
        require_on_destroy=not args.no_destroy_gate,
        require_on_replace=not args.no_replace_gate,
        min_risk_score=args.min_risk,
    )

    result = check_approval(report, rules=rules, options=opts)

    if args.as_json:
        print(json.dumps({
            "required": result.required,
            "reasons": result.reasons,
            "risk_score": result.risk_score,
            "policy_blocks": result.policy_blocks,
        }, indent=2))
    else:
        print(result.summary)
        if result.required and result.reasons:
            for r in result.reasons:
                print(f"  • {r}")

    return 2 if result.required else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="stackdiff-approval")
    sub = p.add_subparsers(dest="command")
    _add_approval_parser(sub)
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
