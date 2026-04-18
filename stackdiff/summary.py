"""Summary statistics for a DiffReport."""
from dataclasses import dataclass, field
from typing import Dict
from stackdiff.diff import DiffReport
from stackdiff.parser import ChangeAction


@dataclass
class DiffSummary:
    total: int = 0
    by_action: Dict[str, int] = field(default_factory=dict)
    by_resource_type: Dict[str, int] = field(default_factory=dict)

    def has_destructive(self) -> bool:
        return bool(
            self.by_action.get(ChangeAction.DELETE.value, 0)
            + self.by_action.get(ChangeAction.REPLACE.value, 0)
        )


def summarize(report: DiffReport) -> DiffSummary:
    summary = DiffSummary()
    for entry in report.entries:
        change = entry.change
        summary.total += 1

        action_key = change.action.value
        summary.by_action[action_key] = summary.by_action.get(action_key, 0) + 1

        # derive resource type from address
        parts = change.address.split(".")
        # strip module prefix segments (module.name)
        i = 0
        while i + 1 < len(parts) and parts[i] == "module":
            i += 2
        rtype = parts[i] if i < len(parts) else "unknown"
        summary.by_resource_type[rtype] = summary.by_resource_type.get(rtype, 0) + 1

    return summary


def format_summary(summary: DiffSummary) -> str:
    lines = [f"Total changes: {summary.total}"]
    if summary.by_action:
        lines.append("By action:")
        for action, count in sorted(summary.by_action.items()):
            lines.append(f"  {action}: {count}")
    if summary.by_resource_type:
        lines.append("By resource type:")
        for rtype, count in sorted(summary.by_resource_type.items()):
            lines.append(f"  {rtype}: {count}")
    if summary.has_destructive():
        lines.append("⚠  Report contains destructive changes.")
    return "\n".join(lines)
