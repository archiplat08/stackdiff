"""Maturity scoring: assess how operationally mature a stack's change profile is."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from stackdiff.annotate import AnnotatedEntry
from stackdiff.risk import RiskScore


@dataclass(frozen=True)
class MaturityResult:
    total: int
    owned: int
    policy_checked: int
    risk_scored: int
    low_risk: int
    violations: int
    score: float  # 0.0 – 100.0
    grade: str
    notes: List[str] = field(default_factory=list)


def _grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 40:
        return "D"
    return "F"


def assess_maturity(entries: List[AnnotatedEntry]) -> MaturityResult:
    """Return a MaturityResult for the given annotated entries."""
    total = len(entries)
    if total == 0:
        return MaturityResult(
            total=0, owned=0, policy_checked=0, risk_scored=0,
            low_risk=0, violations=0, score=100.0, grade="A",
            notes=["No changes – nothing to assess."],
        )

    owned = sum(1 for e in entries if e.owner is not None)
    policy_checked = sum(1 for e in entries if e.violations is not None)
    risk_scored = sum(1 for e in entries if e.risk is not None)
    low_risk = sum(
        1 for e in entries
        if e.risk is not None and e.risk.level in ("none", "low")
    )
    violations = sum(
        len(e.violations) for e in entries if e.violations
    )

    ownership_pct = owned / total
    policy_pct = policy_checked / total
    risk_pct = risk_scored / total
    low_risk_pct = low_risk / max(risk_scored, 1)
    violation_penalty = min(violations * 5, 40)

    raw = (
        ownership_pct * 25
        + policy_pct * 25
        + risk_pct * 20
        + low_risk_pct * 30
        - violation_penalty
    )
    score = max(0.0, min(100.0, raw))

    notes: List[str] = []
    if ownership_pct < 0.5:
        notes.append("Less than 50 % of resources have an owner assigned.")
    if policy_pct < 1.0:
        notes.append("Not all resources have been evaluated against policy rules.")
    if violations > 0:
        notes.append(f"{violations} policy violation(s) detected – review before applying.")
    if low_risk_pct < 0.7 and risk_scored > 0:
        notes.append("Majority of changes carry medium or higher risk.")

    return MaturityResult(
        total=total,
        owned=owned,
        policy_checked=policy_checked,
        risk_scored=risk_scored,
        low_risk=low_risk,
        violations=violations,
        score=round(score, 1),
        grade=_grade(score),
        notes=notes,
    )


def format_maturity(result: MaturityResult) -> str:
    lines = [
        f"Maturity Score : {result.score:.1f} / 100  [{result.grade}]",
        f"  Total changes : {result.total}",
        f"  Owned         : {result.owned}",
        f"  Policy-checked: {result.policy_checked}",
        f"  Risk-scored   : {result.risk_scored}",
        f"  Low-risk      : {result.low_risk}",
        f"  Violations    : {result.violations}",
    ]
    if result.notes:
        lines.append("Notes:")
        for note in result.notes:
            lines.append(f"  • {note}")
    return "\n".join(lines)
