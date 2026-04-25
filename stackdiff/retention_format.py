"""Format PruneResult for human-readable and JSON output."""
from __future__ import annotations

import json
from typing import Any, Dict, List

from stackdiff.retention import PruneResult


def _result_to_dict(result: PruneResult) -> Dict[str, Any]:
    return {
        "removed": [str(p) for p in result.removed],
        "kept": [str(p) for p in result.kept],
        "total_removed": result.total_removed,
        "total_kept": result.total_kept,
    }


def format_prune_text(result: PruneResult) -> str:
    """Return a human-readable summary of the prune operation."""
    lines: List[str] = []
    if result.removed:
        lines.append(f"Removed ({result.total_removed}):")
        for p in result.removed:
            lines.append(f"  - {p}")
    else:
        lines.append("No files removed.")
    lines.append(f"Kept: {result.total_kept} file(s)")
    return "\n".join(lines)


def prune_to_json(result: PruneResult, indent: int = 2) -> str:
    """Serialise the prune result to a JSON string."""
    return json.dumps(_result_to_dict(result), indent=indent)


def prune_to_markdown(result: PruneResult) -> str:
    """Return a Markdown-formatted summary table."""
    lines: List[str] = [
        "## Retention Prune Summary",
        "",
        f"| Metric | Count |",
        f"|--------|-------|",
        f"| Removed | {result.total_removed} |",
        f"| Kept | {result.total_kept} |",
    ]
    if result.removed:
        lines += ["", "### Removed Files", ""]
        for p in result.removed:
            lines.append(f"- `{p}`")
    return "\n".join(lines)
