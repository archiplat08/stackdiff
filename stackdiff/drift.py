"""Drift detection: compare a saved snapshot against a new plan report."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from stackdiff.diff import DiffReport, DiffEntry
from stackdiff.snapshot import Snapshot


@dataclass
class DriftItem:
    address: str
    baseline_action: Optional[str]  # None means resource was absent
    current_action: Optional[str]   # None means resource is now absent

    @property
    def is_new(self) -> bool:
        return self.baseline_action is None and self.current_action is not None

    @property
    def is_removed(self) -> bool:
        return self.baseline_action is not None and self.current_action is None

    @property
    def is_changed(self) -> bool:
        return (
            self.baseline_action is not None
            and self.current_action is not None
            and self.baseline_action != self.current_action
        )


@dataclass
class DriftReport:
    items: List[DriftItem] = field(default_factory=list)

    @property
    def has_drift(self) -> bool:
        return len(self.items) > 0

    @property
    def new_count(self) -> int:
        return sum(1 for i in self.items if i.is_new)

    @property
    def removed_count(self) -> int:
        return sum(1 for i in self.items if i.is_removed)

    @property
    def changed_count(self) -> int:
        return sum(1 for i in self.items if i.is_changed)


def _index(report: DiffReport) -> dict[str, str]:
    """Return {address: action} mapping for a report."""
    return {e.address: e.action for e in report.entries}


def detect_drift(snapshot: Snapshot, current: DiffReport) -> DriftReport:
    """Compare *snapshot* (baseline) against *current* plan report.

    Returns a DriftReport listing every resource whose action differs,
    appeared, or disappeared between the two.
    """
    baseline_idx = _index(snapshot.report)
    current_idx = _index(current)

    all_addresses = set(baseline_idx) | set(current_idx)
    items: List[DriftItem] = []

    for addr in sorted(all_addresses):
        b_action = baseline_idx.get(addr)
        c_action = current_idx.get(addr)
        if b_action != c_action:
            items.append(DriftItem(address=addr, baseline_action=b_action, current_action=c_action))

    return DriftReport(items=items)


def format_drift(report: DriftReport) -> str:
    """Return a human-readable summary of drift."""
    if not report.has_drift:
        return "No drift detected."

    lines = [f"Drift detected: {len(report.items)} change(s)"]
    for item in report.items:
        if item.is_new:
            lines.append(f"  + {item.address}  (new: {item.current_action})")
        elif item.is_removed:
            lines.append(f"  - {item.address}  (was: {item.baseline_action})")
        else:
            lines.append(f"  ~ {item.address}  ({item.baseline_action} -> {item.current_action})")
    return "\n".join(lines)
