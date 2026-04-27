"""Suppression rules: allow known/accepted changes to be silenced from reports."""
from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from typing import List, Optional

from stackdiff.diff import DiffReport, DiffEntry


@dataclass
class SuppressionRule:
    """A single suppression rule."""
    address_pattern: str  # glob, e.g. "module.cache.*" or "aws_s3_bucket.logs"
    action: Optional[str] = None  # None means any action
    reason: str = ""


@dataclass
class SuppressionResult:
    kept: List[DiffEntry] = field(default_factory=list)
    suppressed: List[DiffEntry] = field(default_factory=list)
    rules_applied: List[SuppressionRule] = field(default_factory=list)

    @property
    def total_suppressed(self) -> int:
        return len(self.suppressed)

    @property
    def total_kept(self) -> int:
        return len(self.kept)


def _matches_rule(entry: DiffEntry, rule: SuppressionRule) -> bool:
    addr = entry.change.address
    if not fnmatch(addr, rule.address_pattern):
        return False
    if rule.action is not None and entry.change.action.value != rule.action:
        return False
    return True


def apply_suppressions(
    report: DiffReport,
    rules: List[SuppressionRule],
) -> SuppressionResult:
    """Filter a DiffReport by applying suppression rules.

    Entries matching any rule are moved to the suppressed list.
    Returns a SuppressionResult with kept and suppressed entries.
    """
    result = SuppressionResult()
    applied: set[int] = set()

    for entry in report.entries:
        suppressed = False
        for idx, rule in enumerate(rules):
            if _matches_rule(entry, rule):
                result.suppressed.append(entry)
                applied.add(idx)
                suppressed = True
                break
        if not suppressed:
            result.kept.append(entry)

    result.rules_applied = [rules[i] for i in sorted(applied)]
    return result


def to_filtered_report(result: SuppressionResult, original: DiffReport) -> DiffReport:
    """Return a new DiffReport containing only the kept entries."""
    return DiffReport(entries=result.kept, stack_name=original.stack_name)
