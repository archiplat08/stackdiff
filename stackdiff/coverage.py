"""Coverage analysis: measure what fraction of plan resources have policy rules,
ownership assignments, and risk scores applied."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from stackdiff.annotate import AnnotatedEntry
from stackdiff.diff import DiffReport


@dataclass
class CoverageResult:
    total: int
    with_owner: int
    with_policy: int
    with_risk: int
    uncovered_addresses: List[str] = field(default_factory=list)

    @property
    def owner_pct(self) -> float:
        return (self.with_owner / self.total * 100) if self.total else 0.0

    @property
    def policy_pct(self) -> float:
        return (self.with_policy / self.total * 100) if self.total else 0.0

    @property
    def risk_pct(self) -> float:
        return (self.with_risk / self.total * 100) if self.total else 0.0

    @property
    def fully_covered(self) -> bool:
        return self.total > 0 and self.with_owner == self.total and self.with_policy == self.total


def build_coverage(
    annotated: List[AnnotatedEntry],
    owner_map: Optional[dict] = None,
) -> CoverageResult:
    """Compute coverage metrics from a list of AnnotatedEntry objects."""
    total = len(annotated)
    with_owner = 0
    with_policy = 0
    with_risk = 0
    uncovered: List[str] = []

    owner_map = owner_map or {}

    for entry in annotated:
        addr = entry.address
        has_owner = bool(owner_map.get(addr) or any(
            addr.startswith(k.rstrip("*")) for k in owner_map if k.endswith("*")
        ))
        has_policy = entry.has_violations or entry.violations == []
        has_risk = entry.risk_level is not None

        if has_owner:
            with_owner += 1
        if has_policy:
            with_policy += 1
        if has_risk:
            with_risk += 1
        if not has_owner or not has_policy:
            uncovered.append(addr)

    return CoverageResult(
        total=total,
        with_owner=with_owner,
        with_policy=with_policy,
        with_risk=with_risk,
        uncovered_addresses=uncovered,
    )


def format_coverage(result: CoverageResult) -> str:
    lines = [
        f"Coverage Report ({result.total} resources)",
        f"  Ownership : {result.with_owner}/{result.total} ({result.owner_pct:.1f}%)",
        f"  Policy    : {result.with_policy}/{result.total} ({result.policy_pct:.1f}%)",
        f"  Risk      : {result.with_risk}/{result.total} ({result.risk_pct:.1f}%)",
    ]
    if result.uncovered_addresses:
        lines.append("  Uncovered resources:")
        for addr in result.uncovered_addresses:
            lines.append(f"    - {addr}")
    return "\n".join(lines)
