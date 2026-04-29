"""Exclusion rules: skip specific addresses or resource types from a DiffReport."""
from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from typing import List, Sequence

from stackdiff.diff import DiffReport, DiffEntry


@dataclass
class ExclusionRule:
    """A single rule that can exclude a DiffEntry from further processing."""
    address_pattern: str = ""          # fnmatch glob against full address
    resource_type: str = ""            # exact match against resource type prefix
    reason: str = ""                   # human-readable explanation


@dataclass
class ExclusionResult:
    kept: List[DiffEntry] = field(default_factory=list)
    excluded: List[DiffEntry] = field(default_factory=list)
    rules_matched: List[str] = field(default_factory=list)  # reasons that fired

    @property
    def total_excluded(self) -> int:
        return len(self.excluded)

    @property
    def total_kept(self) -> int:
        return len(self.kept)

    @property
    def is_clean(self) -> bool:
        """True when nothing was excluded (all entries kept)."""
        return len(self.excluded) == 0


def _matches_rule(entry: DiffEntry, rule: ExclusionRule) -> bool:
    """Return True if *entry* is covered by *rule*."""
    if rule.address_pattern:
        address = getattr(entry, "address", None) or ""
        if not address:
            # fall back to change address
            address = entry.change.address if entry.change else ""
        if fnmatch.fnmatch(address, rule.address_pattern):
            return True
    if rule.resource_type:
        rtype = getattr(entry, "resource_type", None) or ""
        if not rtype and entry.change:
            # derive from address: module.x.aws_s3_bucket.name -> aws_s3_bucket
            parts = entry.change.address.split(".")
            rtype = parts[-2] if len(parts) >= 2 else ""
        if rtype == rule.resource_type:
            return True
    return False


def apply_exclusions(
    report: DiffReport,
    rules: Sequence[ExclusionRule],
) -> ExclusionResult:
    """Filter *report* entries against *rules*, returning an ExclusionResult."""
    result = ExclusionResult()
    fired_reasons: set[str] = set()

    for entry in report.entries:
        excluded = False
        for rule in rules:
            if _matches_rule(entry, rule):
                result.excluded.append(entry)
                if rule.reason:
                    fired_reasons.add(rule.reason)
                excluded = True
                break
        if not excluded:
            result.kept.append(entry)

    result.rules_matched = sorted(fired_reasons)
    return result
