"""Threshold enforcement: fail if risk score or destructive count exceeds limits."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from stackdiff.risk import RiskScore, score_report
from stackdiff.diff import DiffReport
from stackdiff.summary import summarize


@dataclass
class ThresholdOptions:
    max_risk_score: Optional[int] = None   # total score ceiling
    max_destructive: Optional[int] = None  # destroy + replace ceiling
    max_high_risk: Optional[int] = None    # entries with level HIGH ceiling


@dataclass
class ThresholdViolation:
    field: str
    limit: int
    actual: int

    @property
    def message(self) -> str:
        return (
            f"threshold exceeded: {self.field} is {self.actual} "
            f"(limit {self.limit})"
        )


@dataclass
class ThresholdResult:
    violations: list[ThresholdViolation]

    @property
    def passed(self) -> bool:
        return len(self.violations) == 0


def check_thresholds(
    report: DiffReport,
    opts: ThresholdOptions,
) -> ThresholdResult:
    """Evaluate *report* against *opts* and return a ThresholdResult."""
    violations: list[ThresholdViolation] = []

    risk: RiskScore = score_report(report)
    summary = summarize(report)

    if opts.max_risk_score is not None and risk.total > opts.max_risk_score:
        violations.append(
            ThresholdViolation("risk_score", opts.max_risk_score, risk.total)
        )

    destructive = summary.destroys + summary.replaces
    if opts.max_destructive is not None and destructive > opts.max_destructive:
        violations.append(
            ThresholdViolation("destructive_changes", opts.max_destructive, destructive)
        )

    high_risk = sum(1 for e in risk.entries if e.level == "HIGH")
    if opts.max_high_risk is not None and high_risk > opts.max_high_risk:
        violations.append(
            ThresholdViolation("high_risk_entries", opts.max_high_risk, high_risk)
        )

    return ThresholdResult(violations=violations)


def format_threshold_result(result: ThresholdResult) -> str:
    if result.passed:
        return "All thresholds passed."
    lines = ["Threshold violations:"]
    for v in result.violations:
        lines.append(f"  - {v.message}")
    return "\n".join(lines)
