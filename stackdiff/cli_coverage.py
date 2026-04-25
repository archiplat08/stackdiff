"""CLI sub-command: coverage — report policy/ownership/risk coverage for a plan."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from stackdiff.annotate import annotate_report
from stackdiff.coverage import build_coverage, format_coverage
from stackdiff.parser import parse_plan_text
from stackdiff.diff import build_report
from stackdiff.policy import load_rules  # type: ignore[attr-defined]
from stackdiff.ownership import build_ownership


def _add_coverage_parser(sub: argparse._SubParsersAction) -> None:  # noqa: SLF001
    p = sub.add_parser("coverage", help="Report resource coverage across policy/ownership/risk")
    p.add_argument("plan", help="Path to terraform plan text output")
    p.add_argument("--owner-map", dest="owner_map", default=None,
                   help="JSON file mapping resource addresses to team owners")
    p.add_argument("--policy", dest="policy_file", default=None,
                   help="YAML/JSON policy rules file")
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--fail-under-owner", type=float, default=0.0,
                   metavar="PCT", help="Exit 1 if owner coverage below PCT")
    p.add_argument("--fail-under-policy", type=float, default=0.0,
                   metavar="PCT", help="Exit 1 if policy coverage below PCT")


def _cmd_coverage(args: argparse.Namespace) -> int:
    plan_text = Path(args.plan).read_text()
    changes = parse_plan_text(plan_text)
    report = build_report(changes)

    rules = []
    if args.policy_file:
        try:
            rules = load_rules(Path(args.policy_file).read_text())
        except Exception as exc:  # noqa: BLE001
            print(f"[coverage] warning: could not load policy: {exc}", file=sys.stderr)

    annotated = annotate_report(report, rules=rules)

    owner_map: dict = {}
    if args.owner_map:
        try:
            owner_map = json.loads(Path(args.owner_map).read_text())
        except Exception as exc:  # noqa: BLE001
            print(f"[coverage] warning: could not load owner map: {exc}", file=sys.stderr)

    result = build_coverage(annotated, owner_map=owner_map)

    if args.format == "json":
        print(json.dumps({
            "total": result.total,
            "with_owner": result.with_owner,
            "with_policy": result.with_policy,
            "with_risk": result.with_risk,
            "owner_pct": round(result.owner_pct, 2),
            "policy_pct": round(result.policy_pct, 2),
            "risk_pct": round(result.risk_pct, 2),
            "uncovered": result.uncovered_addresses,
        }, indent=2))
    else:
        print(format_coverage(result))

    exit_code = 0
    if result.owner_pct < args.fail_under_owner:
        exit_code = 1
    if result.policy_pct < args.fail_under_policy:
        exit_code = 1
    return exit_code


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="stackdiff-coverage")
    sub = p.add_subparsers(dest="cmd")
    _add_coverage_parser(sub)
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(_cmd_coverage(args))


if __name__ == "__main__":
    main()
