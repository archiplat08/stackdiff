"""Formatting helpers for suppression results."""
from __future__ import annotations

import json
from typing import Any, Dict, List

from stackdiff.suppression import SuppressionResult, SuppressionRule


def _rule_to_dict(rule: SuppressionRule) -> Dict[str, Any]:
    return {
        "address_pattern": rule.address_pattern,
        "action": rule.action,
        "reason": rule.reason,
    }


def _result_to_dict(result: SuppressionResult) -> Dict[str, Any]:
    return {
        "total_kept": result.total_kept,
        "total_suppressed": result.total_suppressed,
        "suppressed": [
            {
                "address": e.change.address,
                "action": e.change.action.value,
            }
            for e in result.suppressed
        ],
        "rules_applied": [_rule_to_dict(r) for r in result.rules_applied],
    }


def format_suppression_text(result: SuppressionResult) -> str:
    lines: List[str] = []
    lines.append(
        f"Suppression: {result.total_kept} kept, "
        f"{result.total_suppressed} suppressed"
    )
    if result.suppressed:
        lines.append("Suppressed entries:")
        for entry in result.suppressed:
            lines.append(
                f"  - {entry.change.address} [{entry.change.action.value}]"
            )
    if result.rules_applied:
        lines.append("Rules applied:")
        for rule in result.rules_applied:
            reason = f" ({rule.reason})" if rule.reason else ""
            action_str = rule.action or "any"
            lines.append(
                f"  * {rule.address_pattern} action={action_str}{reason}"
            )
    return "\n".join(lines)


def suppression_to_json(result: SuppressionResult, indent: int = 2) -> str:
    return json.dumps(_result_to_dict(result), indent=indent)
