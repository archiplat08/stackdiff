"""Digest module: produce a concise daily/weekly summary digest from audit logs."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from stackdiff.audit import AuditEntry
from stackdiff.summary import DiffSummary, summarize
from stackdiff.risk import RiskScore, score_report


@dataclass
class DigestPeriod:
    label: str          # e.g. "daily" or "weekly"
    start: datetime
    end: datetime


@dataclass
class DigestReport:
    period: DigestPeriod
    entries: List[AuditEntry] = field(default_factory=list)
    total_plans: int = 0
    total_creates: int = 0
    total_updates: int = 0
    total_deletes: int = 0
    total_replaces: int = 0
    destructive_plans: int = 0
    top_risk_score: float = 0.0
    stacks: List[str] = field(default_factory=list)


def _period_for(label: str, reference: Optional[datetime] = None) -> DigestPeriod:
    now = reference or datetime.now(tz=timezone.utc)
    if label == "daily":
        start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif label == "weekly":
        start = (now - timedelta(weeks=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        raise ValueError(f"Unknown period label: {label!r}")
    return DigestPeriod(label=label, start=start, end=end)


def build_digest(
    entries: List[AuditEntry],
    label: str = "daily",
    reference: Optional[datetime] = None,
) -> DigestReport:
    period = _period_for(label, reference)
    in_window = [
        e for e in entries
        if period.start <= e.recorded_at < period.end
    ]
    report = DigestReport(period=period, entries=in_window, total_plans=len(in_window))
    seen_stacks: set = set()
    for entry in in_window:
        s = summarize(entry.report)
        report.total_creates += s.creates
        report.total_updates += s.updates
        report.total_deletes += s.deletes
        report.total_replaces += s.replaces
        if s.has_destructive:
            report.destructive_plans += 1
        rs = score_report(entry.report)
        if rs.score > report.top_risk_score:
            report.top_risk_score = rs.score
        if entry.stack:
            seen_stacks.add(entry.stack)
    report.stacks = sorted(seen_stacks)
    return report
