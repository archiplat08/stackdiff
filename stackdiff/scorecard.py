"""Scorecard: aggregate risk, policy, threshold, and drift signals into a single health score."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from stackdiff.risk import RiskScore, level as risk_level
from stackdiff.policy import PolicyResult
from stackdiff.threshold import ThresholdResult
from stackdiff.impact import ImpactResult, ImpactLevel


@dataclass
class ScorecardResult:
    risk: RiskScore
    policy: Optional[PolicyResult]
    threshold: Optional[ThresholdResult]
    impact: Optional[ImpactResult]
    notes: List[str] = field(default_factory=list)

    @property
    def grade(self) -> str:
        """Return A-F letter grade based on combined signals."""
        penalty = 0

        lv = risk_level(self.risk)
        if lv == "critical":
            penalty += 40
        elif lv == "high":
            penalty += 25
        elif lv == "medium":
            penalty += 10
        elif lv == "low":
            penalty += 5

        if self.policy and not self.policy.passed:
            blocks = sum(1 for v in self.policy.violations if v.rule.severity == "block")
            warns = sum(1 for v in self.policy.violations if v.rule.severity == "warn")
            penalty += blocks * 20 + warns * 5

        if self.threshold and not self.threshold.passed:
            penalty += len(self.threshold.violations) * 15

        if self.impact:
            if self.impact.level == ImpactLevel.CRITICAL:
                penalty += 30
            elif self.impact.level == ImpactLevel.HIGH:
                penalty += 15

        if penalty == 0:
            return "A"
        if penalty <= 10:
            return "B"
        if penalty <= 25:
            return "C"
        if penalty <= 45:
            return "D"
        return "F"

    @property
    def healthy(self) -> bool:
        return self.grade in ("A", "B")


def build_scorecard(
    risk: RiskScore,
    policy: Optional[PolicyResult] = None,
    threshold: Optional[ThresholdResult] = None,
    impact: Optional[ImpactResult] = None,
) -> ScorecardResult:
    notes: List[str] = []
    if policy and not policy.passed:
        notes.append(f"{len(policy.violations)} policy violation(s)")
    if threshold and not threshold.passed:
        notes.append(f"{len(threshold.violations)} threshold violation(s)")
    lv = risk_level(risk)
    if lv in ("high", "critical"):
        notes.append(f"risk level: {lv} (score={risk.total})")
    return ScorecardResult(risk=risk, policy=policy, threshold=threshold, impact=impact, notes=notes)


def format_scorecard(sc: ScorecardResult) -> str:
    lines = [
        f"Grade : {sc.grade}",
        f"Healthy: {sc.healthy}",
        f"Risk   : {risk_level(sc.risk)} ({sc.risk.total})",
    ]
    if sc.impact:
        lines.append(f"Impact : {sc.impact.level.value}")
    if sc.notes:
        lines.append("Notes  :")
        for n in sc.notes:
            lines.append(f"  - {n}")
    return "\n".join(lines)
