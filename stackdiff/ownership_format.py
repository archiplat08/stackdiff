"""Formatting helpers for OwnershipReport."""
from __future__ import annotations

import json
from typing import Any, Dict, List

from stackdiff.ownership import OwnershipEntry, OwnershipReport


def _entry_to_dict(e: OwnershipEntry) -> Dict[str, Any]:
    return {
        "address": e.address,
        "action": e.action,
        "owner": e.owner,
        "team": e.team,
        "labels": e.labels,
    }


def format_ownership_text(report: OwnershipReport) -> str:
    """Return a human-readable ownership table."""
    lines: List[str] = []
    by_team = report.by_team()
    for team, entries in sorted(by_team.items()):
        lines.append(f"[{team}]")
        for e in entries:
            owner_str = f" ({e.owner})" if e.owner else ""
            lines.append(f"  {e.action:<10} {e.address}{owner_str}")
    unowned = report.unowned()
    if unowned:
        lines.append(f"\nWARNING: {len(unowned)} resource(s) have no owner/team.")
    return "\n".join(lines)


def ownership_to_json(report: OwnershipReport, indent: int = 2) -> str:
    payload = [_entry_to_dict(e) for e in report.entries]
    return json.dumps(payload, indent=indent)


def ownership_to_markdown(report: OwnershipReport) -> str:
    lines = [
        "| Address | Action | Team | Owner |",
        "|---------|--------|------|-------|" ,
    ]
    for e in report.entries:
        lines.append(
            f"| {e.address} | {e.action} | {e.team or ''} | {e.owner or ''} |"
        )
    return "\n".join(lines)
