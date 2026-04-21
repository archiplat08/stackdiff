"""Tests for stackdiff.drift and stackdiff.cli_drift."""

from __future__ import annotations

import json
import os
import textwrap
from pathlib import Path

import pytest

from stackdiff.diff import DiffReport, DiffEntry
from stackdiff.snapshot import Snapshot, save_snapshot
from stackdiff.drift import detect_drift, format_drift, DriftItem, DriftReport


def _entry(address: str, action: str) -> DiffEntry:
    return DiffEntry(address=address, action=action, change_type="resource")


def _report(*entries: DiffEntry) -> DiffReport:
    return DiffReport(entries=list(entries))


@pytest.fixture
def snap_dir(tmp_path: Path) -> str:
    return str(tmp_path / "snaps")


# --- unit tests for detect_drift ---

def test_no_drift_when_identical():
    base = _report(_entry("aws_s3_bucket.a", "create"))
    snap = Snapshot(name="s", report=base, created_at="2024-01-01T00:00:00")
    current = _report(_entry("aws_s3_bucket.a", "create"))
    result = detect_drift(snap, current)
    assert not result.has_drift
    assert result.items == []


def test_drift_action_changed():
    base = _report(_entry("aws_instance.web", "create"))
    snap = Snapshot(name="s", report=base, created_at="2024-01-01T00:00:00")
    current = _report(_entry("aws_instance.web", "delete"))
    result = detect_drift(snap, current)
    assert result.has_drift
    assert result.changed_count == 1
    assert result.items[0].is_changed


def test_drift_new_resource():
    base = _report()
    snap = Snapshot(name="s", report=base, created_at="2024-01-01T00:00:00")
    current = _report(_entry("aws_lambda_function.fn", "create"))
    result = detect_drift(snap, current)
    assert result.new_count == 1
    assert result.items[0].is_new


def test_drift_removed_resource():
    base = _report(_entry("aws_rds_cluster.db", "create"))
    snap = Snapshot(name="s", report=base, created_at="2024-01-01T00:00:00")
    current = _report()
    result = detect_drift(snap, current)
    assert result.removed_count == 1
    assert result.items[0].is_removed


def test_format_drift_no_drift():
    report = DriftReport(items=[])
    assert format_drift(report) == "No drift detected."


def test_format_drift_with_items():
    items = [
        DriftItem(address="aws_s3_bucket.x", baseline_action=None, current_action="create"),
        DriftItem(address="aws_instance.y", baseline_action="create", current_action=None),
        DriftItem(address="aws_iam_role.z", baseline_action="create", current_action="replace"),
    ]
    report = DriftReport(items=items)
    text = format_drift(report)
    assert "Drift detected: 3" in text
    assert "+" in text
    assert "-" in text
    assert "~" in text


# --- integration test via cli_drift ---

def test_cli_drift_no_drift(snap_dir, tmp_path):
    from stackdiff.cli_drift import _cmd_drift

    report = _report(_entry("aws_s3_bucket.b", "create"))
    save_snapshot("baseline", report, base_dir=snap_dir)

    plan_file = tmp_path / "plan.txt"
    plan_file.write_text(
        textwrap.dedent("""\
        Terraform will perform the following actions:

          # aws_s3_bucket.b will be created
          + resource "aws_s3_bucket" "b" {
            }

        Plan: 1 to add, 0 to change, 0 to destroy.
        """)
    )

    class Args:
        snapshot_name = "baseline"
        plan_file = str(plan_file)
        snap_dir = snap_dir
        exit_code = True

    rc = _cmd_drift(Args())
    assert rc == 0


def test_cli_drift_missing_snapshot(snap_dir, tmp_path, capsys):
    from stackdiff.cli_drift import _cmd_drift

    class Args:
        snapshot_name = "ghost"
        plan_file = str(tmp_path / "plan.txt")
        snap_dir = snap_dir
        exit_code = False

    rc = _cmd_drift(Args())
    assert rc == 2
    captured = capsys.readouterr()
    assert "ghost" in captured.err
