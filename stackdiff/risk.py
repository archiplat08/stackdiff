"""Risk scoring for diff reports based on resource changes."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from stackdiff.diff import DiffReport, DiffEntry
from stackdiff.parser import ChangeAction

# Base scores per action
_ACTION_SCORES: Dict[ChangeAction, int] = {
    ChangeAction.CREATE: 1,
    ChangeAction.UPDATE: 3,
    ChangeAction.REPLACE: 7,
    ChangeAction.DESTROY: 10,
    ChangeAction.NO_OP: 0,
}

# Multiplier applied when resource type matches a sensitive pattern
_SENSITIVE_TYPES = (
    "aws_iam",
    "aws_security_group",
    "aws_kms",
    "aws_s3_bucket",
    "google_iam",
    "azurerm_role",
)

_SENSITIVE_MULTIPLIER = 2


@dataclass
class RiskScore:
    total: int
    per_entry: List[Dict] = field(default_factory=list)

    @property
    def level(self) -> str:
        if self.total == 0:
            return "none"
        if self.total <= 5:
            return "low"
        if self.total <= 20:
            return "medium"
        if self.total <= 50:
            return "high"
        return "critical"

    def top_risks(self, n: int = 3) -> List[Dict]:
        """Return the *n* highest-scoring entries, sorted descending by score."""
        return sorted(self.per_entry, key=lambda x: x["score"], reverse=True)[:n]


def _is_sensitive(resource_type: str) -> bool:
    return any(resource_type.startswith(p) for p in _SENSITIVE_TYPES)


def _score_entry(entry: DiffEntry) -> int:
    base = _ACTION_SCORES.get(entry.action, 0)
    if _is_sensitive(entry.resource_type):
        return base * _SENSITIVE_MULTIPLIER
    return base


def score_report(report: DiffReport) -> RiskScore:
    """Compute a risk score for the entire diff report."""
    total = 0
    per_entry = []
    for entry in report.entries:
        s = _score_entry(entry)
        total += s
        per_entry.append(
            {
                "address": entry.address,
                "action": entry.action.value,
                "score": s,
                "sensitive": _is_sensitive(entry.resource_type),
            }
        )
    return RiskScore(total=total, per_entry=per_entry)


def format_risk(risk: RiskScore) -> str:
    """Return a human-readable risk summary string."""
    lines = [f"Risk level : {risk.level.upper()}  (score={risk.total})"]
    for item in risk.per_entry:
        flag = " [sensitive]" if item["sensitive"] else ""
        lines.append(f"  {item['address']}  action={item['action']}  score={item['score']}{flag}")
    return "\n".join(lines)
