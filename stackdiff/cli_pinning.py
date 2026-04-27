"""CLI entry-point for the pinning sub-command."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

from stackdiff.parser import parse_plan_text
from stackdiff.diff import build_report
from stackdiff.pinning import PinnedRule, check_pins, format_pin_result


def _add_pinning_parser(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("pins", help="Check whether a plan touches pinned resources")
    p.add_argument("plan", help="Path to terraform plan text output")
    p.add_argument(
        "--pin",
        metavar="PATTERN",
        action="append",
        default=[],
        dest="pins",
        help="Glob pattern for a pinned resource address (repeatable)",
    )
    p.add_argument(
        "--pin-file",
        metavar="FILE",
        help="JSON file containing [{pattern, reason}] pin rules",
    )
    p.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )


def _load_rules(pins: List[str], pin_file: str | None) -> List[PinnedRule]:
    rules: List[PinnedRule] = [PinnedRule(pattern=p) for p in pins]
    if pin_file:
        raw = json.loads(Path(pin_file).read_text())
        for item in raw:
            rules.append(PinnedRule(pattern=item["pattern"], reason=item.get("reason", "")))
    return rules


def _cmd_pinning(args: argparse.Namespace) -> int:
    text = Path(args.plan).read_text()
    changes = parse_plan_text(text)
    report = build_report(changes)
    rules = _load_rules(args.pins, args.pin_file)

    if not rules:
        print("[pins] No pin rules defined — nothing to check.", file=sys.stderr)
        return 0

    result = check_pins(report, rules)

    if args.format == "json":
        data = {
            "clean": result.clean,
            "checked": result.checked,
            "violations": [
                {"address": v.entry.address, "action": v.entry.action.value, "message": v.message}
                for v in result.violations
            ],
        }
        print(json.dumps(data, indent=2))
    else:
        print(format_pin_result(result))

    return 0 if result.clean else 2


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="stackdiff-pins")
    sub = p.add_subparsers(dest="cmd")
    _add_pinning_parser(sub)
    return p


def main() -> None:  # pragma: no cover
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(_cmd_pinning(args))
