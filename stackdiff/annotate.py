"""Annotate a DiffReport with risk scores and policy violations."""
from dataclasses import dataclass, field
from typing import List, Optional

from stackdiff.diff import DiffReport, DiffEntry
from stackdiff.risk import RiskScore, score_report
from stackdiff.policy import PolicyResult, PolicyViolation, evaluate


@dataclass
class AnnotatedEntry:
    entry: DiffEntry
    risk: RiskScore
    violations: List[PolicyViolation] = field(default_factory=list)

    @property
    def address(self) -> str:
        return self.entry.address

    @property
    def action(self) -> str:
        return self.entry.action.value

    @property
    def risk_level(self) -> str:
        from stackdiff.risk import level
        return level(self.risk)

    @property
    def has_violations(self) -> bool:
        return bool(self.violations)

    @property
    def is_blocked(self) -> bool:
        from stackdiff.policy import Severity
        return any(v.severity == Severity.BLOCK for v in self.violations)


@dataclass
class AnnotatedReport:
    entries: List[AnnotatedEntry] = field(default_factory=list)

    @property
    def has_blocks(self) -> bool:
        return any(e.is_blocked for e in self.entries)

    @property
    def has_violations(self) -> bool:
        return any(e.has_violations for e in self.entries)

    @property
    def high_risk_entries(self) -> List[AnnotatedEntry]:
        return [e for e in self.entries if e.risk_level in ("high", "critical")]


def annotate(
    report: DiffReport,
    rules: Optional[list] = None,
) -> AnnotatedReport:
    """Combine risk scoring and policy evaluation into a single annotated report."""
    risk_report = score_report(report)
    risk_by_address = {rs.address: rs for rs in risk_report.scores}

    policy_result: PolicyResult = evaluate(report, rules or [])
    violations_by_address: dict = {}
    for v in policy_result.violations:
        violations_by_address.setdefault(v.address, []).append(v)

    annotated_entries: List[AnnotatedEntry] = []
    for entry in report.entries:
        addr = entry.address
        risk = risk_by_address.get(addr, RiskScore(address=addr, score=0))
        violations = violations_by_address.get(addr, [])
        annotated_entries.append(
            AnnotatedEntry(entry=entry, risk=risk, violations=violations)
        )

    return AnnotatedReport(entries=annotated_entries)


def format_annotated(report: AnnotatedReport) -> str:
    """Return a human-readable string for an AnnotatedReport."""
    lines = []
    for e in report.entries:
        tag = f"[{e.risk_level.upper()}]"
        violation_str = ""
        if e.violations:
            msgs = "; ".join(v.message for v in e.violations)
            violation_str = f" | violations: {msgs}"
        lines.append(f"  {tag} {e.address} ({e.action}){violation_str}")
    if not lines:
        lines.append("  (no changes)")
    return "\n".join(lines)
