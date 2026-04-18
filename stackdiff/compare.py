"""Compare two DiffReports (e.g. current vs baseline) to detect regressions or improvements."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from stackdiff.diff import DiffReport, DiffEntry


@dataclass
class CompareResult:
    added: List[DiffEntry] = field(default_factory=list)    # in current, not in baseline
    removed: List[DiffEntry] = field(default_factory=list)  # in baseline, not in current
    unchanged: List[DiffEntry] = field(default_factory=list)

    @property
    def has_regressions(self) -> bool:
        """New destructive changes compared to baseline."""
        from stackdiff.diff import is_removed
        return any(is_removed(e) for e in self.added)

    @property
    def is_clean(self) -> bool:
        return not self.added and not self.removed


def _key(entry: DiffEntry) -> str:
    return f"{entry.resource.address}::{entry.resource.action.value}"


def compare_reports(current: DiffReport, baseline: DiffReport) -> CompareResult:
    """Diff two DiffReports by resource address + action."""
    baseline_keys = {_key(e): e for e in baseline.entries}
    current_keys = {_key(e): e for e in current.entries}

    added = [e for k, e in current_keys.items() if k not in baseline_keys]
    removed = [e for k, e in baseline_keys.items() if k not in current_keys]
    unchanged = [e for k, e in current_keys.items() if k in baseline_keys]

    return CompareResult(added=added, removed=removed, unchanged=unchanged)


def format_compare_result(result: CompareResult) -> str:
    lines: list[str] = []
    if result.is_clean:
        lines.append("No changes compared to baseline.")
        return "\n".join(lines)
    if result.added:
        lines.append(f"+ {len(result.added)} new change(s) vs baseline:")
        for e in result.added:
            lines.append(f"    {e.resource.action.value:10s} {e.resource.address}")
    if result.removed:
        lines.append(f"- {len(result.removed)} resolved change(s) vs baseline:")
        for e in result.removed:
            lines.append(f"    {e.resource.action.value:10s} {e.resource.address}")
    return "\n".join(lines)
