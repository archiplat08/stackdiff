"""Approval gate: determine whether a plan requires human approval before apply."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from stackdiff.diff import DiffReport
from stackdiff.risk import RiskScore, score_report
from stackdiff.policy import PolicyResult, evaluate
from stackdiff.annotate import annotate_report


@dataclass
class ApprovalOptions:
    """Thresholds that trigger an approval requirement."""
    require_on_destroy: bool = True
    require_on_replace: bool = True
    min_risk_score: Optional[int] = None   # require approval if score >= this
    require_on_policy_block: bool = True


@dataclass
class ApprovalResult:
    required: bool
    reasons: List[str] = field(default_factory=list)
    risk_score: int = 0
    policy_blocks: int = 0

    @property
    def summary(self) -> str:
        if not self.required:
            return "Approval not required — plan is safe to auto-apply."
        joined = "; ".join(self.reasons)
        return f"Approval REQUIRED: {joined}"


def check_approval(
    report: DiffReport,
    rules: Optional[list] = None,
    options: Optional[ApprovalOptions] = None,
) -> ApprovalResult:
    """Evaluate *report* against *options* and return an ApprovalResult."""
    if options is None:
        options = ApprovalOptions()
    if rules is None:
        rules = []

    reasons: List[str] = []

    # Risk scoring
    rs: RiskScore = score_report(report)
    if options.min_risk_score is not None and rs.total >= options.min_risk_score:
        reasons.append(
            f"risk score {rs.total} meets threshold {options.min_risk_score}"
        )

    # Policy blocks
    annotated = annotate_report(report, rules)
    policy_blocks = sum(
        1 for e in annotated.entries if e.has_violations and
        any(v.rule.severity == "block" for v in e.violations)
    )
    if options.require_on_policy_block and policy_blocks:
        reasons.append(f"{policy_blocks} policy block(s) violated")

    # Destructive / replace actions
    for entry in report.entries:
        action = entry.change.action.value if hasattr(entry.change.action, "value") else str(entry.change.action)
        if options.require_on_destroy and action in ("delete", "destroy"):
            reasons.append(f"destroy detected: {entry.change.address}")
            break
        if options.require_on_replace and action == "replace":
            reasons.append(f"replace detected: {entry.change.address}")
            break

    return ApprovalResult(
        required=bool(reasons),
        reasons=reasons,
        risk_score=rs.total,
        policy_blocks=policy_blocks,
    )
