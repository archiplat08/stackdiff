"""Export diff reports to various formats (JSON, CSV)."""
from __future__ import annotations

import csv
import io
import json
from typing import Any

from stackdiff.diff import DiffReport
from stackdiff.summary import summarize


def report_to_dict(report: DiffReport) -> dict[str, Any]:
    """Serialize a DiffReport to a plain dictionary."""
    summary = summarize(report)
    return {
        "summary": {
            "added": summary.added,
            "removed": summary.removed,
            "changed": summary.changed,
            "total": summary.total,
            "has_destructive": summary.has_destructive,
        },
        "changes": [
            {
                "address": entry.address,
                "short_address": entry.short_address,
                "resource_type": entry.resource_type,
                "module": entry.module,
                "action": entry.action.value,
                "before": entry.before,
                "after": entry.after,
            }
            for entry in report.entries
        ],
    }


def to_json(report: DiffReport, indent: int = 2) -> str:
    """Export a DiffReport as a JSON string."""
    return json.dumps(report_to_dict(report), indent=indent, default=str)


def to_csv(report: DiffReport) -> str:
    """Export a DiffReport as a CSV string."""
    output = io.StringIO()
    fieldnames = ["address", "short_address", "resource_type", "module", "action"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for entry in report.entries:
        writer.writerow({
            "address": entry.address,
            "short_address": entry.short_address,
            "resource_type": entry.resource_type,
            "module": entry.module or "",
            "action": entry.action.value,
        })
    return output.getvalue()
