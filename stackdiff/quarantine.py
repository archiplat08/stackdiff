"""Quarantine module: flag and isolate high-risk or policy-violating entries."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from stackdiff.annotate import AnnotatedEntry
from stackdiff.risk import RiskScore


@dataclass(frozen=True)
class QuarantineRule:
    """A rule that triggers quarantine for matching entries."""
    min_risk_score: Optional[int] = None  # inclusive lower bound
    actions: List[str] = field(default_factory=list)  # e.g. ["delete", "replace"]
    resource_types: List[str] = field(default_factory=list)  # e.g. ["aws_iam_role"]


@dataclass
class QuarantineResult:
    """Outcome of applying quarantine rules to an annotated report."""
    quarantined: List[AnnotatedEntry] = field(default_factory=list)
    allowed: List[AnnotatedEntry] = field(default_factory=list)

    @property
    def total_quarantined(self) -> int:
        return len(self.quarantined)

    @property
    def total_allowed(self) -> int:
        return len(self.allowed)

    @property
    def is_clean(self) -> bool:
        return self.total_quarantined == 0


def _matches_rule(entry: AnnotatedEntry, rule: QuarantineRule) -> bool:
    """Return True if the entry triggers the given quarantine rule."""
    if rule.min_risk_score is not None:
        score: RiskScore = entry.risk
        if score.score < rule.min_risk_score:
            return False

    if rule.actions:
        action_str = entry.action.value if hasattr(entry.action, "value") else str(entry.action)
        if action_str not in rule.actions:
            return False

    if rule.resource_types:
        resource_type = entry.address.split(".")[-2] if "." in entry.address else ""
        if not any(entry.address.startswith(rt) or resource_type == rt for rt in rule.resource_types):
            return False

    return True


def apply_quarantine(
    entries: List[AnnotatedEntry],
    rules: List[QuarantineRule],
) -> QuarantineResult:
    """Partition entries into quarantined and allowed based on rules."""
    result = QuarantineResult()
    for entry in entries:
        if any(_matches_rule(entry, rule) for rule in rules):
            result.quarantined.append(entry)
        else:
            result.allowed.append(entry)
    return result


def format_quarantine_text(result: QuarantineResult) -> str:
    """Return a human-readable summary of quarantine results."""
    lines: List[str] = []
    lines.append(f"Quarantine: {result.total_quarantined} quarantined, {result.total_allowed} allowed")
    if result.quarantined:
        lines.append("\nQuarantined entries:")
        for e in result.quarantined:
            action_str = e.action.value if hasattr(e.action, "value") else str(e.action)
            lines.append(f"  [{action_str}] {e.address}  risk={e.risk.score}")
    return "\n".join(lines)
