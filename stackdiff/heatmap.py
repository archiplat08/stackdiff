"""Resource change heatmap: frequency analysis across multiple reports."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Sequence

from stackdiff.diff import DiffReport


@dataclass
class HeatmapEntry:
    address: str
    resource_type: str
    change_count: int
    action_counts: Dict[str, int] = field(default_factory=dict)

    @property
    def is_hot(self) -> bool:
        """True when this resource changed more than once."""
        return self.change_count > 1

    @property
    def dominant_action(self) -> str:
        """Return the most frequently occurring action for this resource."""
        if not self.action_counts:
            return "unknown"
        return max(self.action_counts, key=lambda a: self.action_counts[a])


@dataclass
class HeatmapReport:
    entries: List[HeatmapEntry] = field(default_factory=list)

    @property
    def hot_resources(self) -> List[HeatmapEntry]:
        return [e for e in self.entries if e.is_hot]

    @property
    def top(self) -> List[HeatmapEntry]:
        return sorted(self.entries, key=lambda e: e.change_count, reverse=True)


def build_heatmap(reports: Sequence[DiffReport]) -> HeatmapReport:
    """Aggregate change frequency across *reports*."""
    total: Counter[str] = Counter()
    action_map: Dict[str, Counter[str]] = {}
    type_map: Dict[str, str] = {}

    for report in reports:
        for entry in report.entries:
            addr = entry.address
            total[addr] += 1
            action_map.setdefault(addr, Counter())[entry.action] += 1
            type_map.setdefault(addr, entry.resource_type)

    entries = [
        HeatmapEntry(
            address=addr,
            resource_type=type_map[addr],
            change_count=count,
            action_counts=dict(action_map[addr]),
        )
        for addr, count in total.items()
    ]
    return HeatmapReport(entries=entries)


def format_heatmap(report: HeatmapReport, top_n: int = 10) -> str:
    """Return a human-readable heatmap table."""
    if not report.entries:
        return "No changes recorded."

    lines: List[str] = ["Resource Change Heatmap", "=" * 50]
    for entry in report.top[:top_n]:
        heat = "🔥" if entry.is_hot else "  "
        actions = ", ".join(f"{a}:{c}" for a, c in sorted(entry.action_counts.items()))
        lines.append(f"{heat} {entry.address} ({entry.change_count}x) [{actions}]")
    return "\n".join(lines)
