"""Tests for stackdiff.cli_retention."""
from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from stackdiff.cli_retention import _cmd_retention, build_parser


@pytest.fixture()
def snap_dir(tmp_path: Path) -> Path:
    return tmp_path


def _touch(directory: Path, name: str, age_days: float = 0) -> Path:
    p = directory / name
    p.write_text(name)
    if age_days:
        ts = time.time() - age_days * 86400
        os.utime(p, (ts, ts))
    return p


def _run(args: list) -> int:
    parser = build_parser()
    parsed = parser.parse_args(["retention"] + args)
    return _cmd_retention(parsed)


def test_exits_zero_on_empty_dir(snap_dir: Path) -> None:
    code = _run([str(snap_dir)])
    assert code == 0


def test_missing_directory_exits_one(tmp_path: Path) -> None:
    code = _run([str(tmp_path / "ghost")])
    assert code == 1


def test_max_count_removes_excess(snap_dir: Path) -> None:
    for i in range(5):
        _touch(snap_dir, f"snap{i}.json", age_days=i)
    code = _run([str(snap_dir), "--max-count", "2"])
    assert code == 0
    remaining = list(snap_dir.iterdir())
    assert len(remaining) == 2


def test_max_age_removes_old(snap_dir: Path) -> None:
    _touch(snap_dir, "old.json", age_days=60)
    _touch(snap_dir, "new.json", age_days=1)
    code = _run([str(snap_dir), "--max-age-days", "30"])
    assert code == 0
    assert not (snap_dir / "old.json").exists()
    assert (snap_dir / "new.json").exists()


def test_dry_run_does_not_delete(snap_dir: Path, capsys) -> None:
    _touch(snap_dir, "a.json", age_days=90)
    _touch(snap_dir, "b.json", age_days=1)
    code = _run([str(snap_dir), "--max-count", "1", "--dry-run"])
    assert code == 0
    # both files still present
    assert (snap_dir / "a.json").exists()
    assert (snap_dir / "b.json").exists()
    captured = capsys.readouterr()
    assert "dry-run" in captured.out
    assert "would remove" in captured.out
