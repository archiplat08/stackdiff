"""Label tagging for diff entries — attach free-form key/value metadata to resources."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from stackdiff.diff import DiffEntry, DiffReport


@dataclass
class LabeledEntry:
    """A DiffEntry decorated with user-supplied labels."""
    entry: DiffEntry
    labels: Dict[str, str] = field(default_factory=dict)

    @property
    def address(self) -> str:
        return self.entry.address

    @property
    def action(self) -> str:
        return self.entry.action

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return self.labels.get(key, default)

    def has_label(self, key: str, value: Optional[str] = None) -> bool:
        if key not in self.labels:
            return False
        return value is None or self.labels[key] == value


@dataclass
class LabeledReport:
    entries: List[LabeledEntry] = field(default_factory=list)

    def filter_by_label(self, key: str, value: Optional[str] = None) -> "LabeledReport":
        return LabeledReport(
            entries=[e for e in self.entries if e.has_label(key, value)]
        )

    def all_label_keys(self) -> List[str]:
        keys: set = set()
        for e in self.entries:
            keys.update(e.labels.keys())
        return sorted(keys)


LabelMap = Dict[str, Dict[str, str]]  # address -> {key: value}


def apply_labels(report: DiffReport, label_map: LabelMap) -> LabeledReport:
    """Attach labels from *label_map* to every entry in *report*.

    Entries whose address is not present in *label_map* receive an empty label
    dict so they are still included in the result.
    """
    labeled: List[LabeledEntry] = []
    for entry in report.entries:
        labels = dict(label_map.get(entry.address, {}))
        labeled.append(LabeledEntry(entry=entry, labels=labels))
    return LabeledReport(entries=labeled)


def format_labeled_report(report: LabeledReport) -> str:
    """Return a human-readable string of labeled entries."""
    if not report.entries:
        return "(no entries)"
    lines: List[str] = []
    for e in report.entries:
        tag_str = ", ".join(f"{k}={v}" for k, v in sorted(e.labels.items()))
        tag_part = f"  [{tag_str}]" if tag_str else ""
        lines.append(f"  {e.action:10s} {e.address}{tag_part}")
    return "\n".join(lines)
