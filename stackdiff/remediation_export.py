"""Export remediation hints to JSON or Markdown."""
from __future__ import annotations

import json
from typing import Any, Dict, List

from stackdiff.remediation import RemediationHint


def hint_to_dict(hint: RemediationHint) -> Dict[str, Any]:
    return {
        "address": hint.address,
        "action": hint.action,
        "risk_level": hint.risk_level,
        "suggestions": hint.suggestions,
        "violation_messages": hint.violation_messages,
    }


def hints_to_json(hints: List[RemediationHint], indent: int = 2) -> str:
    """Serialise hints list to a JSON string."""
    return json.dumps([hint_to_dict(h) for h in hints], indent=indent)


def hints_to_markdown(hints: List[RemediationHint]) -> str:
    """Render hints as a Markdown document."""
    if not hints:
        return "## Remediation Hints\n\n_No hints — all changes look safe._\n"

    lines: List[str] = ["## Remediation Hints\n"]
    for h in hints:
        lines.append(f"### `{h.address}` — {h.action} (risk: {h.risk_level})\n")
        if h.violation_messages:
            lines.append("**Policy violations:**\n")
            for msg in h.violation_messages:
                lines.append(f"- {msg}")
            lines.append("")
        if h.suggestions:
            lines.append("**Suggestions:**\n")
            for s in h.suggestions:
                lines.append(f"- {s}")
            lines.append("")
    return "\n".join(lines)
