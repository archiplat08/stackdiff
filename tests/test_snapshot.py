"""Tests for stackdiff.snapshot module."""
from __future__ import annotations

import json
import pytest

from stackdiff.diff import DiffReport, DiffEntry
from stackdiff.parser import ChangeAction
from stackdiff.snapshot import (
    save_snapshot,
    load_snapshot,
    list_snapshots,
    delete_snapshot,
)


def _entry(address: str, action: ChangeAction = ChangeAction.CREATE) -> DiffEntry:
    return DiffEntry(address=address, short_address=address.split(".")[-1], action=action)


@pytest.fixture
def snap_dir(tmp_path):
    return str(tmp_path / "snapshots")


@pytest.fixture
def sample_report():
    return DiffReport(entries=[
        _entry("aws_instance.web", ChangeAction.CREATE),
        _entry("aws_s3_bucket.data", ChangeAction.UPDATE),
    ])


def test_save_creates_file(snap_dir, sample_report):
    path = save_snapshot(sample_report, "v1", "plan.txt", snap_dir)
    assert path.exists()
    data = json.loads(path.read_text())
    assert data["name"] == "v1"
    assert data["plan_file"] == "plan.txt"
    assert len(data["entries"]) == 2


def test_save_stores_created_at(snap_dir, sample_report):
    save_snapshot(sample_report, "v1", "plan.txt", snap_dir)
    snap = load_snapshot("v1", snap_dir)
    assert snap.created_at is not None
    assert "T" in snap.created_at  # ISO format


def test_load_returns_snapshot(snap_dir, sample_report):
    save_snapshot(sample_report, "v1", "plan.txt", snap_dir)
    snap = load_snapshot("v1", snap_dir)
    assert snap is not None
    assert snap.name == "v1"
    assert len(snap.entries) == 2


def test_load_missing_returns_none(snap_dir):
    result = load_snapshot("nonexistent", snap_dir)
    assert result is None


def test_list_snapshots_empty(snap_dir):
    assert list_snapshots(snap_dir) == []


def test_list_snapshots_returns_names(snap_dir, sample_report):
    save_snapshot(sample_report, "alpha", "a.txt", snap_dir)
    save_snapshot(sample_report, "beta", "b.txt", snap_dir)
    names = list_snapshots(snap_dir)
    assert names == ["alpha", "beta"]


def test_delete_snapshot(snap_dir, sample_report):
    save_snapshot(sample_report, "v1", "plan.txt", snap_dir)
    assert delete_snapshot("v1", snap_dir) is True
    assert load_snapshot("v1", snap_dir) is None


def test_delete_missing_returns_false(snap_dir):
    assert delete_snapshot("ghost", snap_dir) is False


def test_snapshot_entries_have_correct_action(snap_dir):
    report = DiffReport(entries=[_entry("aws_db_instance.main", ChangeAction.DESTROY)])
    save_snapshot(report, "destroy-snap", "plan.txt", snap_dir)
    snap = load_snapshot("destroy-snap", snap_dir)
    assert snap.entries[0].action == ChangeAction.DESTROY
