"""Gate: evaluate a plan report against a combined policy + threshold + risk
criterion and return a single pass/fail/warn result suitable for CI pipelines."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from stackdiff.diff import DiffReport
from stackdiff.policy import PolicyResult, evaluate as evaluate_policy, PolicyRule
from stackdiff.threshold import ThresholdOptions, ThresholdResult, check as check_threshold
from stackdiff.risk import RiskScore, score_report


@dataclass
class GateOptions:
    rules: List[PolicyRule] = field(default_factory=list)
    thresholds: ThresholdOptions = field(default_factory=ThresholdOptions)
    max_risk_score: Optional[float] = None


@dataclass
class GateResult:
    policy: PolicyResult
    threshold: ThresholdResult
    risk: RiskScore
    max_risk_score: Optional[float]

    @property
    def passed(self) -> bool:
        return (
            not self.policy.has_blocks
            and self.threshold.passed
            and (
                self.max_risk_score is None
                or self.risk.score <= self.max_risk_score
            )
        )

    @property
    def warned(self) -> bool:
        """True when there are warnings but no hard failures."""
        return not self.passed and not self.policy.has_blocks

    @property
    def exit_code(self) -> int:
        """0 = pass, 1 = warn, 2 = block."""
        if self.passed:
            return 0
        if self.policy.has_blocks:
            return 2
        return 1


def evaluate_gate(report: DiffReport, options: GateOptions) -> GateResult:
    policy_result = evaluate_policy(report, options.rules)
    threshold_result = check_threshold(report, options.thresholds)
    risk = score_report(report)
    return GateResult(
        policy=policy_result,
        threshold=threshold_result,
        risk=risk,
        max_risk_score=options.max_risk_score,
    )


def format_gate_result(result: GateResult) -> str:
    lines: List[str] = []
    status = "PASS" if result.passed else ("BLOCK" if result.policy.has_blocks else "WARN")
    lines.append(f"Gate result: {status}")
    lines.append(f"  Risk score : {result.risk.score:.1f}  (level={result.risk.level}"  # noqa: E501
                 + (f", limit={result.max_risk_score}" if result.max_risk_score is not None else "") + ")")
    if not result.threshold.passed:
        for v in result.threshold.violations:
            lines.append(f"  [threshold] {v.message}")
    for v in result.policy.violations:
        tag = "BLOCK" if v.rule.blocking else "WARN"
        lines.append(f"  [policy/{tag}] {v.message}")
    return "\n".join(lines)
