"""Impact classification for diff reports.

Assigns a blast-radius label to an entire DiffReport based on the
combination of resource counts, risk scores, and destructive actions.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from stackdiff.diff import DiffReport

from stackdiff.risk import score_report, RiskScore
from stackdiff.summary import summarize, has_destructive


class ImpactLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Ordering used for comparisons (e.g. "is this at least HIGH?")
_LEVEL_ORDER = [
    ImpactLevel.NONE,
    ImpactLevel.LOW,
    ImpactLevel.MEDIUM,
    ImpactLevel.HIGH,
    ImpactLevel.CRITICAL,
]


@dataclass(frozen=True)
class ImpactResult:
    level: ImpactLevel
    risk_score: int
    total_changes: int
    destructive: bool
    reason: str

    def is_at_least(self, level: ImpactLevel) -> bool:
        """Return True if this result's level is >= *level* in severity."""
        return _LEVEL_ORDER.index(self.level) >= _LEVEL_ORDER.index(level)


def _label(level: ImpactLevel) -> str:
    colours = {
        ImpactLevel.NONE: "\033[90m",
        ImpactLevel.LOW: "\033[32m",
        ImpactLevel.MEDIUM: "\033[33m",
        ImpactLevel.HIGH: "\033[31m",
        ImpactLevel.CRITICAL: "\033[1;31m",
    }
    reset = "\033[0m"
    return f"{colours.get(level, '')}[{level.value.upper()}]{reset}"


def classify_impact(report: "DiffReport") -> ImpactResult:
    """Return an ImpactResult for *report*."""
    risk: RiskScore = score_report(report)
    summary = summarize(report)
    destructive = has_destructive(summary)
    total = summary.created + summary.updated + summary.destroyed + summary.replaced

    if total == 0:
        return ImpactResult(ImpactLevel.NONE, risk.score, total, False, "No changes detected.")

    if risk.score >= 80 or (destructive and summary.destroyed >= 5):
        level = ImpactLevel.CRITICAL
        reason = "Very high risk score or mass destruction."
    elif risk.score >= 50 or (destructive and summary.destroyed >= 2):
        level = ImpactLevel.HIGH
        reason = "High risk score or multiple destructive actions."
    elif risk.score >= 25 or destructive:
        level = ImpactLevel.MEDIUM
        reason = "Moderate risk or at least one destructive action."
    elif total >= 10:
        level = ImpactLevel.MEDIUM
        reason = "Large number of changes."
    elif total >= 1:
        level = ImpactLevel.LOW
        reason = "Small, non-destructive changes."
    else:
        level = ImpactLevel.NONE
        reason = "No significant changes."

    return ImpactResult(level, risk.score, total, destructive, reason)


def format_impact(result: ImpactResult) -> str:
    """Return a human-readable one-line summary of *result*."""
    label = _label(result.level)
    return (
        f"{label} risk_score={result.risk_score} "
        f"changes={result.total_changes} "
        f"destructive={result.destructive} "
        f"— {result.reason}"
    )
