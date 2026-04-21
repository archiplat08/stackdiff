"""Rollup: aggregate multiple DiffReports into a cross-stack summary."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from stackdiff.diff import DiffReport
from stackdiff.risk import RiskScore, score_report
from stackdiff.summary import DiffSummary, summarize


@dataclass
class StackRollupEntry:
    stack_name: str
    summary: DiffSummary
    risk: RiskScore


@dataclass
class RollupReport:
    entries: List[StackRollupEntry] = field(default_factory=list)

    @property
    def total_creates(self) -> int:
        return sum(e.summary.creates for e in self.entries)

    @property
    def total_updates(self) -> int:
        return sum(e.summary.updates for e in self.entries)

    @property
    def total_deletes(self) -> int:
        return sum(e.summary.deletes for e in self.entries)

    @property
    def total_replaces(self) -> int:
        return sum(e.summary.replaces for e in self.entries)

    @property
    def max_risk_score(self) -> int:
        if not self.entries:
            return 0
        return max(e.risk.score for e in self.entries)

    @property
    def any_destructive(self) -> bool:
        return any(e.summary.deletes > 0 or e.summary.replaces > 0 for e in self.entries)


def build_rollup(named_reports: Dict[str, DiffReport]) -> RollupReport:
    """Build a RollupReport from a mapping of stack_name -> DiffReport."""
    entries: List[StackRollupEntry] = []
    for stack_name, report in named_reports.items():
        summary = summarize(report)
        risk = score_report(report)
        entries.append(StackRollupEntry(stack_name=stack_name, summary=summary, risk=risk))
    return RollupReport(entries=entries)


def format_rollup(report: RollupReport) -> str:
    """Return a human-readable multi-stack rollup table."""
    if not report.entries:
        return "No stacks to roll up."

    lines = ["Stack Rollup Summary", "=" * 60]
    header = f"{'Stack':<30} {'Create':>7} {'Update':>7} {'Delete':>7} {'Replace':>7} {'Risk':>6}"
    lines.append(header)
    lines.append("-" * 60)
    for e in report.entries:
        s = e.summary
        lines.append(
            f"{e.stack_name:<30} {s.creates:>7} {s.updates:>7} {s.deletes:>7} {s.replaces:>7} {e.risk.score:>6}"
        )
    lines.append("=" * 60)
    lines.append(
        f"{'TOTAL':<30} {report.total_creates:>7} {report.total_updates:>7} "
        f"{report.total_deletes:>7} {report.total_replaces:>7} {report.max_risk_score:>6}"
    )
    if report.any_destructive:
        lines.append("\n[!] One or more stacks contain destructive changes.")
    return "\n".join(lines)
