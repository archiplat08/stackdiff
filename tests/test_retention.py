"""Tests for stackdiff.retention."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from stackdiff.retention import RetentionOptions, PruneResult, prune_directory


@pytest.fixture()
def tmp_dir(tmp_path: Path) -> Path:
    return tmp_path


def _touch(directory: Path, name: str, age_days: float = 0) -> Path:
    """Create a file and back-date its mtime."""
    p = directory / name
    p.write_text(name)
    if age_days:
        ts = time.time() - age_days * 86400
        import os
        os.utime(p, (ts, ts))
    return p


def test_prune_nonexistent_directory_returns_empty(tmp_path: Path) -> None:
    result = prune_directory(tmp_path / "ghost", RetentionOptions())
    assert result.total_removed == 0
    assert result.total_kept == 0


def test_no_options_keeps_all(tmp_dir: Path) -> None:
    for i in range(4):
        _touch(tmp_dir, f"file{i}.json")
    result = prune_directory(tmp_dir, RetentionOptions())
    assert result.total_removed == 0
    assert result.total_kept == 4


def test_max_count_keeps_newest(tmp_dir: Path) -> None:
    _touch(tmp_dir, "old.json", age_days=10)
    _touch(tmp_dir, "mid.json", age_days=5)
    _touch(tmp_dir, "new.json", age_days=0)
    result = prune_directory(tmp_dir, RetentionOptions(max_count=2))
    assert result.total_kept == 2
    assert result.total_removed == 1
    kept_names = {p.name for p in result.kept}
    assert "new.json" in kept_names
    assert "mid.json" in kept_names
    assert "old.json" not in kept_names
    assert not (tmp_dir / "old.json").exists()


def test_max_age_removes_old_files(tmp_dir: Path) -> None:
    _touch(tmp_dir, "ancient.json", age_days=40)
    _touch(tmp_dir, "recent.json", age_days=2)
    result = prune_directory(tmp_dir, RetentionOptions(max_age_days=30))
    assert result.total_removed == 1
    assert result.total_kept == 1
    assert not (tmp_dir / "ancient.json").exists()
    assert (tmp_dir / "recent.json").exists()


def test_combined_options_apply_both_filters(tmp_dir: Path) -> None:
    _touch(tmp_dir, "a.json", age_days=50)
    _touch(tmp_dir, "b.json", age_days=20)
    _touch(tmp_dir, "c.json", age_days=10)
    _touch(tmp_dir, "d.json", age_days=1)
    # max_age=30 removes 'a'; max_count=1 then keeps only newest of remaining
    result = prune_directory(tmp_dir, RetentionOptions(max_age_days=30, max_count=1))
    assert result.total_kept == 1
    assert result.kept[0].name == "d.json"


def test_prune_result_properties() -> None:
    r = PruneResult(removed=[Path("x"), Path("y")], kept=[Path("z")])
    assert r.total_removed == 2
    assert r.total_kept == 1
