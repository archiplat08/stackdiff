"""Render a human-readable summary of the audit log."""

from __future__ import annotations

from typing import List

from stackdiff.audit import AuditEntry


_HEADER = "{:<30} {:<40} {:>7} {:>7} {:>8}  {}"
_ROW = "{:<30} {:<40} {:>7} {:>7} {:>8}  {}"
_SEP = "-" * 100


def format_audit_log(entries: List[AuditEntry], show_tags: bool = False) -> str:
    """Return a formatted table of audit entries."""
    if not entries:
        return "No audit entries found."

    lines: List[str] = [
        _HEADER.format(
            "Timestamp", "Plan File", "Creates", "Updates", "Destroys", "Destructive"
        ),
        _SEP,
    ]

    for e in entries:
        s = e.summary
        tag_str = ""
        if show_tags and e.tags:
            tag_str = "  tags=" + ",".join(f"{k}={v}" for k, v in e.tags.items())
        lines.append(
            _ROW.format(
                e.timestamp[:26],
                e.plan_file[-40:] if len(e.plan_file) > 40 else e.plan_file,
                s.get("creates", 0),
                s.get("updates", 0),
                s.get("destroys", 0),
                "YES" if s.get("has_destructive") else "no",
            )
            + tag_str
        )

    lines.append(_SEP)
    lines.append(f"Total entries: {len(entries)}")
    return "\n".join(lines)


def destructive_entries(entries: List[AuditEntry]) -> List[AuditEntry]:
    """Filter entries that contain destructive changes."""
    return [e for e in entries if e.summary.get("has_destructive", False)]
