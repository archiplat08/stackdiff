"""Retention policy: prune old snapshots and audit entries by age or count."""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional


@dataclass
class RetentionOptions:
    max_age_days: Optional[int] = None   # delete entries older than N days
    max_count: Optional[int] = None      # keep only the N most recent entries


@dataclass
class PruneResult:
    removed: List[Path]
    kept: List[Path]

    @property
    def total_removed(self) -> int:
        return len(self.removed)

    @property
    def total_kept(self) -> int:
        return len(self.kept)


def _mtime(p: Path) -> datetime:
    return datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)


def prune_directory(directory: Path, options: RetentionOptions) -> PruneResult:
    """Apply retention policy to all files in *directory*.

    Files are sorted newest-first; the policy is applied in two passes:
    1. Drop anything older than *max_age_days*.
    2. Drop anything beyond the *max_count* most-recent survivors.
    """
    if not directory.exists():
        return PruneResult(removed=[], kept=[])

    files = sorted(directory.iterdir(), key=_mtime, reverse=True)
    survivors: List[Path] = list(files)

    if options.max_age_days is not None:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=options.max_age_days)
        survivors = [f for f in survivors if _mtime(f) >= cutoff]

    if options.max_count is not None:
        survivors = survivors[: options.max_count]

    survivor_set = set(survivors)
    removed: List[Path] = []
    for f in files:
        if f not in survivor_set:
            f.unlink(missing_ok=True)
            removed.append(f)

    return PruneResult(removed=removed, kept=survivors)
