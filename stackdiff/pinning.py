"""Resource pinning — mark specific resources as pinned so they are flagged
when a plan attempts to modify or destroy them."""
from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from typing import List, Optional

from stackdiff.diff import DiffReport, DiffEntry
from stackdiff.parser import ChangeAction


@dataclass
class PinnedRule:
    """A rule that pins one or more resources by address glob."""
    pattern: str
    reason: str = ""


@dataclass
class PinViolation:
    """A pinned resource that a plan wants to change or destroy."""
    entry: DiffEntry
    rule: PinnedRule

    @property
    def message(self) -> str:
        base = f"Pinned resource '{self.entry.address}' would be {self.entry.action.value}"
        if self.rule.reason:
            return f"{base}: {self.rule.reason}"
        return base


@dataclass
class PinResult:
    violations: List[PinViolation] = field(default_factory=list)
    checked: int = 0

    @property
    def clean(self) -> bool:
        return len(self.violations) == 0


_MUTABLE_ACTIONS = {ChangeAction.UPDATE, ChangeAction.DELETE, ChangeAction.REPLACE}


def _matches(entry: DiffEntry, rule: PinnedRule) -> bool:
    return fnmatch.fnmatch(entry.address, rule.pattern)


def check_pins(report: DiffReport, rules: List[PinnedRule]) -> PinResult:
    """Return a PinResult describing any pinned resources touched by *report*."""
    violations: List[PinViolation] = []
    for entry in report.entries:
        if entry.action not in _MUTABLE_ACTIONS:
            continue
        for rule in rules:
            if _matches(entry, rule):
                violations.append(PinViolation(entry=entry, rule=rule))
                break  # one violation per entry is enough
    return PinResult(violations=violations, checked=len(report.entries))


def format_pin_result(result: PinResult) -> str:
    """Return a human-readable summary of pin violations."""
    lines: List[str] = []
    if result.clean:
        lines.append("[pins] No pinned resources affected.")
    else:
        lines.append(f"[pins] {len(result.violations)} pinned resource(s) affected:")
        for v in result.violations:
            lines.append(f"  ! {v.message}")
    return "\n".join(lines)
