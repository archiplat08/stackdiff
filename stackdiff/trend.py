"""Trend analysis across multiple DiffReports over time."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from stackdiff.diff import DiffReport
from stackdiff.summary import summarize, DiffSummary


@dataclass
class TrendPoint:
    label: str
    total: int
    creates: int
    updates: int
    deletes: int
    replaces: int
    destructive: bool


@dataclass
class TrendReport:
    points: List[TrendPoint] = field(default_factory=list)

    @property
    def labels(self) -> List[str]:
        return [p.label for p in self.points]

    @property
    def total_series(self) -> List[int]:
        return [p.total for p in self.points]

    @property
    def destructive_count(self) -> int:
        return sum(1 for p in self.points if p.destructive)


def _point_from_summary(label: str, summary: DiffSummary) -> TrendPoint:
    return TrendPoint(
        label=label,
        total=summary.total,
        creates=summary.creates,
        updates=summary.updates,
        deletes=summary.deletes,
        replaces=summary.replaces,
        destructive=summary.has_destructive,
    )


def build_trend(labeled_reports: List[tuple[str, DiffReport]]) -> TrendReport:
    """Build a TrendReport from an ordered list of (label, DiffReport) pairs."""
    points = []
    for label, report in labeled_reports:
        summary = summarize(report)
        points.append(_point_from_summary(label, summary))
    return TrendReport(points=points)


def format_trend(trend: TrendReport) -> str:
    """Return a human-readable table of the trend report."""
    if not trend.points:
        return "No trend data available."

    header = f"{'Label':<20} {'Total':>6} {'Create':>7} {'Update':>7} {'Delete':>7} {'Replace':>8} {'Destructive':>12}"
    separator = "-" * len(header)
    rows = [header, separator]
    for p in trend.points:
        flag = "YES" if p.destructive else "no"
        rows.append(
            f"{p.label:<20} {p.total:>6} {p.creates:>7} {p.updates:>7}"
            f" {p.deletes:>7} {p.replaces:>8} {flag:>12}"
        )
    rows.append(separator)
    rows.append(f"Destructive snapshots: {trend.destructive_count}/{len(trend.points)}")
    return "\n".join(rows)
