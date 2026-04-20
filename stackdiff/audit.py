"""Audit log: record every diff report run with metadata for traceability."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from stackdiff.export import report_to_dict
from stackdiff.diff import DiffReport
from stackdiff.summary import summarize


@dataclass
class AuditEntry:
    timestamp: str
    plan_file: str
    summary: dict
    report: dict
    tags: dict = field(default_factory=dict)


def _entry_to_dict(entry: AuditEntry) -> dict:
    return {
        "timestamp": entry.timestamp,
        "plan_file": entry.plan_file,
        "summary": entry.summary,
        "report": entry.report,
        "tags": entry.tags,
    }


def record(
    report: DiffReport,
    plan_file: str,
    audit_dir: str | Path,
    tags: Optional[dict] = None,
) -> Path:
    """Append an audit entry for *report* and return the path written."""
    audit_dir = Path(audit_dir)
    audit_dir.mkdir(parents=True, exist_ok=True)

    s = summarize(report)
    entry = AuditEntry(
        timestamp=datetime.now(timezone.utc).isoformat(),
        plan_file=str(plan_file),
        summary={
            "creates": s.creates,
            "updates": s.updates,
            "destroys": s.destroys,
            "no_ops": s.no_ops,
            "has_destructive": s.has_destructive,
        },
        report=report_to_dict(report),
        tags=tags or {},
    )

    log_path = audit_dir / "audit.jsonl"
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(_entry_to_dict(entry)) + "\n")

    return log_path


def load_audit_log(audit_dir: str | Path) -> List[AuditEntry]:
    """Return all audit entries from *audit_dir*, oldest first."""
    log_path = Path(audit_dir) / "audit.jsonl"
    if not log_path.exists():
        return []
    entries: List[AuditEntry] = []
    with log_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            entries.append(
                AuditEntry(
                    timestamp=d["timestamp"],
                    plan_file=d["plan_file"],
                    summary=d["summary"],
                    report=d["report"],
                    tags=d.get("tags", {}),
                )
            )
    return entries
