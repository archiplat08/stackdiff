"""Policy enforcement: define rules that flag or block certain diff patterns."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from stackdiff.diff import DiffReport, DiffEntry
from stackdiff.parser import ChangeAction


@dataclass
class PolicyRule:
    name: str
    description: str
    severity: str  # "warn" | "block"
    check: Callable[[DiffEntry], bool] = field(repr=False)


@dataclass
class PolicyViolation:
    rule_name: str
    severity: str
    entry: DiffEntry

    @property
    def message(self) -> str:
        addr = self.entry.resource_change.address
        return f"[{self.severity.upper()}] {self.rule_name}: {addr}"


@dataclass
class PolicyResult:
    violations: List[PolicyViolation] = field(default_factory=list)

    @property
    def has_blocks(self) -> bool:
        return any(v.severity == "block" for v in self.violations)

    @property
    def has_warnings(self) -> bool:
        return any(v.severity == "warn" for v in self.violations)


# Built-in rules
NO_DESTROY = PolicyRule(
    name="no-destroy",
    description="Disallow resource destruction",
    severity="block",
    check=lambda e: e.resource_change.action == ChangeAction.DELETE,
)

NO_REPLACE = PolicyRule(
    name="no-replace",
    description="Disallow resource replacement (destroy+create)",
    severity="block",
    check=lambda e: e.resource_change.action == ChangeAction.REPLACE,
)

WARN_ON_IAM = PolicyRule(
    name="warn-iam-change",
    description="Warn when IAM resources are modified",
    severity="warn",
    check=lambda e: "iam" in e.resource_change.resource_type.lower()
    and e.resource_change.action in (ChangeAction.UPDATE, ChangeAction.CREATE, ChangeAction.DELETE),
)

DEFAULT_RULES: List[PolicyRule] = [NO_DESTROY, NO_REPLACE, WARN_ON_IAM]


def evaluate_policy(
    report: DiffReport,
    rules: Optional[List[PolicyRule]] = None,
) -> PolicyResult:
    """Evaluate all rules against every entry in the report."""
    if rules is None:
        rules = DEFAULT_RULES
    result = PolicyResult()
    for entry in report.entries:
        for rule in rules:
            if rule.check(entry):
                result.violations.append(
                    PolicyViolation(rule_name=rule.name, severity=rule.severity, entry=entry)
                )
    return result
