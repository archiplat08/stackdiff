"""Generate human-readable changelogs from DiffReports across time."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from stackdiff.diff import DiffReport
from stackdiff.summary import summarize


@dataclass
class ChangelogEntry:
    timestamp: datetime
    stack: str
    created: int
    updated: int
    deleted: int
    replaced: int
    has_destructive: bool
    notes: List[str] = field(default_factory=list)


@dataclass
class Changelog:
    entries: List[ChangelogEntry] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.entries)

    def since(self, dt: datetime) -> "Changelog":
        return Changelog([e for e in self.entries if e.timestamp >= dt])

    def for_stack(self, stack: str) -> "Changelog":
        return Changelog([e for e in self.entries if e.stack == stack])


def build_changelog_entry(
    report: DiffReport,
    stack: str,
    timestamp: Optional[datetime] = None,
    notes: Optional[List[str]] = None,
) -> ChangelogEntry:
    summary = summarize(report)
    return ChangelogEntry(
        timestamp=timestamp or datetime.utcnow(),
        stack=stack,
        created=summary.creates,
        updated=summary.updates,
        deleted=summary.deletes,
        replaced=summary.replaces,
        has_destructive=summary.has_destructive,
        notes=notes or [],
    )


def format_changelog(changelog: Changelog, stack: Optional[str] = None) -> str:
    entries = changelog.for_stack(stack).entries if stack else changelog.entries
    if not entries:
        return "No changelog entries found."
    lines: List[str] = []
    for entry in sorted(entries, key=lambda e: e.timestamp, reverse=True):
        tag = " [DESTRUCTIVE]" if entry.has_destructive else ""
        lines.append(f"## {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')} — {entry.stack}{tag}")
        lines.append(
            f"  +{entry.created} created  ~{entry.updated} updated  "
            f"-{entry.deleted} deleted  >{entry.replaced} replaced"
        )
        for note in entry.notes:
            lines.append(f"  * {note}")
        lines.append("")
    return "\n".join(lines).rstrip()
