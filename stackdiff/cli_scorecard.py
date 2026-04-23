"""CLI sub-command: scorecard — print a health grade for a plan file."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from stackdiff.parser import parse_plan_text
from stackdiff.diff import build_report
from stackdiff.risk import score_report
from stackdiff.policy import load_rules, evaluate
from stackdiff.threshold import ThresholdOptions, check_thresholds
from stackdiff.impact import classify_impact
from stackdiff.scorecard import build_scorecard, format_scorecard


def _add_scorecard_parser(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("scorecard", help="Print a health grade for a plan file")
    p.add_argument("plan", help="Path to terraform plan text file")
    p.add_argument("--policy", metavar="FILE", help="Policy rules YAML file")
    p.add_argument("--max-risk", type=int, default=None, metavar="N", help="Fail if total risk score exceeds N")
    p.add_argument("--max-deletes", type=int, default=None, metavar="N", help="Fail if destroy count exceeds N")
    p.add_argument("--json", action="store_true", help="Output JSON instead of text")


def _cmd_scorecard(args: argparse.Namespace) -> int:
    plan_path = Path(args.plan)
    if not plan_path.exists():
        print(f"error: plan file not found: {plan_path}", file=sys.stderr)
        return 1

    text = plan_path.read_text()
    changes = parse_plan_text(text)
    report = build_report(changes)

    risk = score_report(report)

    policy_result = None
    if args.policy:
        rules = load_rules(Path(args.policy))
        policy_result = evaluate(report, rules)

    threshold_result = None
    if args.max_risk is not None or args.max_deletes is not None:
        opts = ThresholdOptions(
            max_risk_score=args.max_risk,
            max_destructive=args.max_deletes,
        )
        threshold_result = check_thresholds(report, risk, opts)

    impact_result = classify_impact(report, risk)

    sc = build_scorecard(risk, policy_result, threshold_result, impact_result)

    if getattr(args, "json", False):
        import json
        data = {
            "grade": sc.grade,
            "healthy": sc.healthy,
            "risk_level": __import__("stackdiff.risk", fromlist=["level"]).level(risk),
            "risk_score": risk.total,
            "impact": sc.impact.level.value if sc.impact else None,
            "notes": sc.notes,
        }
        print(json.dumps(data, indent=2))
    else:
        print(format_scorecard(sc))

    return 0 if sc.healthy else 2


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="stackdiff-scorecard")
    sub = p.add_subparsers(dest="command")
    _add_scorecard_parser(sub)
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    sys.exit(_cmd_scorecard(args))


if __name__ == "__main__":
    main()
