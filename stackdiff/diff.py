"""Compare two sets of ResourceChange lists to produce a diff report."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from stackdiff.parser import ChangeAction, ResourceChange


@dataclass
class DiffEntry:
    address: str
    before: Optional[ChangeAction]
    after: Optional[ChangeAction]

    @property
    def is_new(self) -> bool:
        return self.before is None and self.after is not None

    @property
    def is_removed(self) -> bool:
        return self.before is not None and self.after is None

    @property
    def is_changed(self) -> bool:
        return self.before != self.after and not self.is_new and not self.is_removed


@dataclass
class DiffReport:
    added: List[DiffEntry] = field(default_factory=list)
    removed: List[DiffEntry] = field(default_factory=list)
    changed: List[DiffEntry] = field(default_factory=list)
    unchanged: List[DiffEntry] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.removed or self.changed)

    def summary(self) -> str:
        return (
            f"+{len(self.added)} added, "
            f"-{len(self.removed)} removed, "
            f"~{len(self.changed)} changed, "
            f"{len(self.unchanged)} unchanged"
        )


def diff_plans(
    base: List[ResourceChange], head: List[ResourceChange]
) -> DiffReport:
    """Diff two plan outputs. base = before, head = after."""
    base_map: Dict[str, ChangeAction] = {r.address: r.action for r in base}
    head_map: Dict[str, ChangeAction] = {r.address: r.action for r in head}

    all_addresses = set(base_map) | set(head_map)
    report = DiffReport()

    for addr in sorted(all_addresses):
        entry = DiffEntry(
            address=addr,
            before=base_map.get(addr),
            after=head_map.get(addr),
        )
        if entry.is_new:
            report.added.append(entry)
        elif entry.is_removed:
            report.removed.append(entry)
        elif entry.is_changed:
            report.changed.append(entry)
        else:
            report.unchanged.append(entry)

    return report
