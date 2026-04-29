"""Compliance checking: evaluate a report against a named compliance framework."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from stackdiff.diff import DiffReport
from stackdiff.annotate import AnnotatedEntry, annotate_report
from stackdiff.policy import PolicyRule


FRAMEWORKS: dict[str, List[PolicyRule]] = {
    "cis": [
        PolicyRule(id="cis-1", description="No IAM resource deletions", action="delete", resource_type_pattern="aws_iam_*", severity="block"),
        PolicyRule(id="cis-2", description="No security group replacements", action="replace", resource_type_pattern="aws_security_group*", severity="block"),
    ],
    "pci": [
        PolicyRule(id="pci-1", description="No deletion of encryption resources", action="delete", resource_type_pattern="aws_kms_*", severity="block"),
        PolicyRule(id="pci-2", description="No deletion of audit log resources", action="delete", resource_type_pattern="aws_cloudtrail*", severity="block"),
        PolicyRule(id="pci-3", description="Warn on WAF changes", action="replace", resource_type_pattern="aws_waf*", severity="warn"),
    ],
    "soc2": [
        PolicyRule(id="soc2-1", description="No deletion of logging resources", action="delete", resource_type_pattern="aws_cloudwatch_log*", severity="block"),
        PolicyRule(id="soc2-2", description="No deletion of S3 buckets", action="delete", resource_type_pattern="aws_s3_bucket", severity="block"),
    ],
}


@dataclass
class ComplianceResult:
    framework: str
    entries: List[AnnotatedEntry] = field(default_factory=list)

    @property
    def violations(self) -> List[AnnotatedEntry]:
        return [e for e in self.entries if e.has_violations]

    @property
    def passed(self) -> bool:
        return all(not e.blocks for e in self.entries)

    @property
    def block_count(self) -> int:
        return sum(1 for e in self.entries if e.blocks)

    @property
    def warn_count(self) -> int:
        return sum(1 for e in self.entries if e.warns and not e.blocks)


def check_compliance(report: DiffReport, framework: str) -> ComplianceResult:
    """Evaluate *report* against the named compliance *framework*."""
    framework_lower = framework.lower()
    rules = FRAMEWORKS.get(framework_lower)
    if rules is None:
        raise ValueError(f"Unknown compliance framework: {framework!r}. Available: {list(FRAMEWORKS)}")
    annotated = annotate_report(report, rules)
    return ComplianceResult(framework=framework_lower, entries=annotated)


def format_compliance(result: ComplianceResult) -> str:
    """Return a human-readable compliance report."""
    lines: List[str] = [
        f"Compliance Framework : {result.framework.upper()}",
        f"Status               : {'PASS' if result.passed else 'FAIL'}",
        f"Blocks               : {result.block_count}",
        f"Warnings             : {result.warn_count}",
    ]
    if result.violations:
        lines.append("\nViolations:")
        for entry in result.violations:
            for v in entry.violations:
                lines.append(f"  [{v.severity.upper()}] {entry.address}  —  {v.message}")
    return "\n".join(lines)
