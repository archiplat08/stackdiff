"""Build a timeline of changes across multiple audit log entries."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from stackdiff.audit import AuditEntry


@dataclass
class TimelineEvent:
    timestamp: datetime
    stack: str
    action: str
    address: str
    risk_level: Optional[str] = None
    has_violations: bool = False


@dataclass
class TimelineReport:
    events: List[TimelineEvent] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.events)

    def by_stack(self, stack: str) -> List[TimelineEvent]:
        return [e for e in self.events if e.stack == stack]

    def in_range(self, start: datetime, end: datetime) -> List[TimelineEvent]:
        return [e for e in self.events if start <= e.timestamp <= end]

    def risky(self) -> List[TimelineEvent]:
        return [e for e in self.events if e.risk_level in ("medium", "high", "critical")]

    def with_violations(self) -> List[TimelineEvent]:
        return [e for e in self.events if e.has_violations]


def _entry_to_event(entry: AuditEntry) -> List[TimelineEvent]:
    events: List[TimelineEvent] = []
    ts = entry.recorded_at
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts)
    for change in entry.report.get("entries", []):
        events.append(
            TimelineEvent(
                timestamp=ts,
                stack=entry.stack,
                action=change.get("action", "unknown"),
                address=change.get("address", ""),
                risk_level=change.get("risk_level"),
                has_violations=bool(change.get("violations")),
            )
        )
    return events


def build_timeline(entries: List[AuditEntry]) -> TimelineReport:
    """Convert a list of audit entries into a chronological timeline."""
    all_events: List[TimelineEvent] = []
    for entry in entries:
        all_events.extend(_entry_to_event(entry))
    all_events.sort(key=lambda e: e.timestamp)
    return TimelineReport(events=all_events)


def format_timeline(report: TimelineReport, max_rows: int = 50) -> str:
    if not report.events:
        return "No timeline events found."
    lines = [f"{'Timestamp':<26} {'Stack':<20} {'Action':<12} {'Address':<40} {'Risk':<10} Violations"]
    lines.append("-" * 120)
    for ev in report.events[:max_rows]:
        ts_str = ev.timestamp.strftime("%Y-%m-%dT%H:%M:%S")
        risk = ev.risk_level or "-"
        viol = "yes" if ev.has_violations else "no"
        lines.append(f"{ts_str:<26} {ev.stack:<20} {ev.action:<12} {ev.address:<40} {risk:<10} {viol}")
    if report.total > max_rows:
        lines.append(f"... ({report.total - max_rows} more events)")
    return "\n".join(lines)
