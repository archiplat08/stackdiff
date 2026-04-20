"""Snapshot management: capture and compare named plan snapshots."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from stackdiff.diff import DiffReport
from stackdiff.export import report_to_dict
from stackdiff.baseline import _entry_from_dict


@dataclass
class Snapshot:
    name: str
    created_at: str
    plan_file: str
    entries: list = field(default_factory=list)


def _snapshot_path(snapshots_dir: str, name: str) -> Path:
    return Path(snapshots_dir) / f"{name}.snapshot.json"


def save_snapshot(report: DiffReport, name: str, plan_file: str, snapshots_dir: str) -> Path:
    """Persist a named snapshot of a DiffReport to disk."""
    path = _snapshot_path(snapshots_dir, name)
    Path(snapshots_dir).mkdir(parents=True, exist_ok=True)
    data = {
        "name": name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "plan_file": plan_file,
        "entries": report_to_dict(report)["entries"],
    }
    path.write_text(json.dumps(data, indent=2))
    return path


def load_snapshot(name: str, snapshots_dir: str) -> Optional[Snapshot]:
    """Load a named snapshot from disk. Returns None if not found."""
    path = _snapshot_path(snapshots_dir, name)
    if not path.exists():
        return None
    raw = json.loads(path.read_text())
    entries = [_entry_from_dict(e) for e in raw.get("entries", [])]
    return Snapshot(
        name=raw["name"],
        created_at=raw["created_at"],
        plan_file=raw["plan_file"],
        entries=entries,
    )


def list_snapshots(snapshots_dir: str) -> list[str]:
    """Return sorted list of snapshot names available in the directory."""
    d = Path(snapshots_dir)
    if not d.exists():
        return []
    return sorted(
        p.name.replace(".snapshot.json", "")
        for p in d.glob("*.snapshot.json")
    )


def delete_snapshot(name: str, snapshots_dir: str) -> bool:
    """Delete a snapshot by name. Returns True if deleted, False if not found."""
    path = _snapshot_path(snapshots_dir, name)
    if not path.exists():
        return False
    path.unlink()
    return True
