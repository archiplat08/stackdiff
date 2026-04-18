"""Baseline management: save and load DiffReports for comparison across runs."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from stackdiff.export import report_to_dict
from stackdiff.diff import DiffReport, DiffEntry
from stackdiff.parser import ResourceChange, ChangeAction


DEFAULT_BASELINE_DIR = ".stackdiff"


def _entry_from_dict(d: dict) -> DiffEntry:
    rc = ResourceChange(
        address=d["address"],
        module=d.get("module"),
        resource_type=d["resource_type"],
        name=d["name"],
        action=ChangeAction(d["action"]),
        before=d.get("before"),
        after=d.get("after"),
    )
    from stackdiff.diff import DiffEntry
    return DiffEntry(resource=rc)


def save_baseline(report: DiffReport, label: str, baseline_dir: str = DEFAULT_BASELINE_DIR) -> Path:
    """Persist a DiffReport as a JSON baseline file."""
    os.makedirs(baseline_dir, exist_ok=True)
    path = Path(baseline_dir) / f"{label}.json"
    data = report_to_dict(report)
    path.write_text(json.dumps(data, indent=2))
    return path


def load_baseline(label: str, baseline_dir: str = DEFAULT_BASELINE_DIR) -> Optional[DiffReport]:
    """Load a previously saved baseline. Returns None if not found."""
    path = Path(baseline_dir) / f"{label}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    entries = [_entry_from_dict(e) for e in data.get("entries", [])]
    return DiffReport(entries=entries)


def list_baselines(baseline_dir: str = DEFAULT_BASELINE_DIR) -> list[str]:
    """Return available baseline labels."""
    d = Path(baseline_dir)
    if not d.exists():
        return []
    return [p.stem for p in sorted(d.glob("*.json"))]
