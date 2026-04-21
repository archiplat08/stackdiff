"""Group diff report entries by a chosen dimension."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal

from stackdiff.diff import DiffReport, DiffEntry

GroupDimension = Literal["action", "resource_type", "module"]


@dataclass
class GroupedReport:
    dimension: GroupDimension
    groups: Dict[str, List[DiffEntry]] = field(default_factory=dict)

    def keys(self) -> List[str]:
        return sorted(self.groups.keys())

    def get(self, key: str) -> List[DiffEntry]:
        return self.groups.get(key, [])

    def total(self) -> int:
        return sum(len(v) for v in self.groups.values())


def _group_key(entry: DiffEntry, dimension: GroupDimension) -> str:
    if dimension == "action":
        return entry.change.action.value
    if dimension == "resource_type":
        addr = entry.change.address
        # e.g. module.vpc.aws_subnet.public -> aws_subnet
        parts = [p for p in addr.split(".") if not p.startswith("module")]
        return parts[0] if parts else addr
    if dimension == "module":
        addr = entry.change.address
        segments = addr.split(".")
        modules = []
        i = 0
        while i < len(segments) - 1:
            if segments[i] == "module":
                modules.append(f"module.{segments[i + 1]}")
                i += 2
            else:
                break
        return ".".join(modules) if modules else "(root)"
    raise ValueError(f"Unknown dimension: {dimension}")


def group_report(report: DiffReport, dimension: GroupDimension) -> GroupedReport:
    """Return a GroupedReport partitioning *report* entries by *dimension*."""
    groups: Dict[str, List[DiffEntry]] = {}
    for entry in report.entries:
        key = _group_key(entry, dimension)
        groups.setdefault(key, []).append(entry)
    return GroupedReport(dimension=dimension, groups=groups)


def format_grouped(grouped: GroupedReport) -> str:
    """Return a human-readable summary of a GroupedReport."""
    lines: List[str] = [f"Grouped by: {grouped.dimension}  (total {grouped.total()})", ""]
    for key in grouped.keys():
        entries = grouped.get(key)
        lines.append(f"  [{key}]  {len(entries)} resource(s)")
        for e in entries:
            lines.append(f"    - {e.change.address}")
    return "\n".join(lines)
