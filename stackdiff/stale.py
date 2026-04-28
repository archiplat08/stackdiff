"""Detect stale snapshots and audit entries that have not been updated recently."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from stackdiff.snapshot import Snapshot


@dataclass
class StaleEntry:
    name: str
    stack: Optional[str]
    created_at: datetime
    age_days: float
    is_stale: bool

    def age_str(self) -> str:
        d = int(self.age_days)
        if d == 1:
            return "1 day"
        return f"{d} days"


@dataclass
class StaleReport:
    entries: List[StaleEntry] = field(default_factory=list)
    threshold_days: int = 30

    @property
    def stale(self) -> List[StaleEntry]:
        return [e for e in self.entries if e.is_stale]

    @property
    def fresh(self) -> List[StaleEntry]:
        return [e for e in self.entries if not e.is_stale]

    @property
    def has_stale(self) -> bool:
        return bool(self.stale)


def _age_days(created_at: datetime) -> float:
    now = datetime.now(tz=timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return (now - created_at).total_seconds() / 86400.0


def check_stale(snapshots: List[Snapshot], threshold_days: int = 30) -> StaleReport:
    """Return a StaleReport for the given snapshots."""
    report = StaleReport(threshold_days=threshold_days)
    for snap in snapshots:
        age = _age_days(snap.created_at)
        report.entries.append(
            StaleEntry(
                name=snap.name,
                stack=snap.stack,
                created_at=snap.created_at,
                age_days=age,
                is_stale=age > threshold_days,
            )
        )
    return report


def format_stale_text(report: StaleReport) -> str:
    """Render a human-readable summary of the stale report."""
    lines: List[str] = [
        f"Stale snapshot check (threshold: {report.threshold_days} days)",
        f"  Total : {len(report.entries)}",
        f"  Stale : {len(report.stale)}",
        f"  Fresh : {len(report.fresh)}",
    ]
    if report.stale:
        lines.append("\nStale snapshots:")
        for e in report.stale:
            stack_tag = f" [{e.stack}]" if e.stack else ""
            lines.append(f"  {e.name}{stack_tag}  ({e.age_str()} old)")
    return "\n".join(lines)
