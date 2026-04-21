"""Suggest remediation hints for policy violations and high-risk changes."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from stackdiff.annotate import AnnotatedEntry, AnnotatedReport
from stackdiff.policy import PolicyViolation
from stackdiff.risk import RiskScore


@dataclass
class RemediationHint:
    address: str
    action: str
    risk_level: str
    suggestions: List[str] = field(default_factory=list)
    violation_messages: List[str] = field(default_factory=list)


_ACTION_HINTS = {
    "delete": [
        "Confirm the resource is no longer needed before applying.",
        "Consider using `prevent_destroy = true` lifecycle rule for critical resources.",
    ],
    "replace": [
        "A replace will destroy and re-create the resource; verify downstream dependencies.",
        "Check if a less disruptive change (e.g. in-place update) is possible.",
    ],
}

_RISK_HINTS = {
    "critical": ["Escalate to a senior engineer or security team before applying."],
    "high": ["Request a second review for this change."],
    "medium": ["Double-check the change in a staging environment first."],
}


def _build_hint(entry: AnnotatedEntry) -> Optional[RemediationHint]:
    suggestions: List[str] = []
    violation_msgs = [v.message for v in entry.violations]

    suggestions.extend(_ACTION_HINTS.get(entry.action, []))
    suggestions.extend(_RISK_HINTS.get(entry.risk_level, []))

    if not suggestions and not violation_msgs:
        return None

    return RemediationHint(
        address=entry.address,
        action=entry.action,
        risk_level=entry.risk_level,
        suggestions=suggestions,
        violation_messages=violation_msgs,
    )


def suggest(report: AnnotatedReport) -> List[RemediationHint]:
    """Return remediation hints for all entries that warrant attention."""
    hints: List[RemediationHint] = []
    for entry in report.entries:
        hint = _build_hint(entry)
        if hint is not None:
            hints.append(hint)
    return hints


def format_hints(hints: List[RemediationHint]) -> str:
    """Render hints as a human-readable string."""
    if not hints:
        return "No remediation hints — all changes look safe."

    lines: List[str] = []
    for h in hints:
        lines.append(f"[{h.risk_level.upper()}] {h.address} ({h.action})")
        for msg in h.violation_messages:
            lines.append(f"  ! Policy: {msg}")
        for s in h.suggestions:
            lines.append(f"  > {s}")
    return "\n".join(lines)
