"""CLI sub-commands for policy evaluation."""
from __future__ import annotations

import argparse
import sys

from stackdiff.parser import parse_plan_text
from stackdiff.diff import build_report
from stackdiff.policy import DEFAULT_RULES, evaluate_policy


def _add_policy_parser(subparsers: argparse.Action) -> None:
    p = subparsers.add_parser(
        "policy",
        help="Evaluate policy rules against a Terraform plan",
    )
    p.add_argument("plan_file", help="Path to terraform plan text output")
    p.add_argument(
        "--no-destroy",
        action="store_true",
        default=False,
        help="Enforce no-destroy rule (block)",
    )
    p.add_argument(
        "--no-replace",
        action="store_true",
        default=False,
        help="Enforce no-replace rule (block)",
    )
    p.add_argument(
        "--warn-iam",
        action="store_true",
        default=False,
        help="Warn on IAM resource changes",
    )
    p.add_argument(
        "--all-rules",
        action="store_true",
        default=False,
        help="Enable all built-in rules",
    )
    p.set_defaults(func=_cmd_policy)


def _cmd_policy(args: argparse.Namespace) -> int:
    from stackdiff.policy import NO_DESTROY, NO_REPLACE, WARN_ON_IAM

    with open(args.plan_file) as fh:
        text = fh.read()

    changes = parse_plan_text(text)
    report = build_report(changes)

    if args.all_rules:
        rules = DEFAULT_RULES
    else:
        rules = []
        if args.no_destroy:
            rules.append(NO_DESTROY)
        if args.no_replace:
            rules.append(NO_REPLACE)
        if args.warn_iam:
            rules.append(WARN_ON_IAM)
        if not rules:
            rules = DEFAULT_RULES

    result = evaluate_policy(report, rules)

    if not result.violations:
        print("policy: all checks passed")
        return 0

    for v in result.violations:
        print(v.message)

    if result.has_blocks:
        print("\npolicy: BLOCKED — destructive or disallowed changes detected")
        return 2

    print("\npolicy: warnings present")
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stackdiff-policy")
    subparsers = parser.add_subparsers(dest="command")
    _add_policy_parser(subparsers)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(0)
    sys.exit(args.func(args))
