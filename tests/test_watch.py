"""Tests for stackdiff.watch and stackdiff.notify."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from stackdiff.watch import WatchOptions, WatchState, _scan, watch
from stackdiff.notify import notify_stdout, notify_file_log, notify_webhook
from stackdiff.summary import DiffSummary


PLAN_TEXT = """Terraform will perform the following actions:

  # aws_instance.web will be created
  + resource "aws_instance" "web" {
    }

Plan: 1 to add, 0 to change, 0 to destroy.
"""


@pytest.fixture()
def plan_dir(tmp_path):
    return tmp_path / "plans"


def test_scan_finds_files(plan_dir):
    plan_dir.mkdir()
    (plan_dir / "a.tfplan.txt").write_text("x")
    (plan_dir / "b.tfplan.txt").write_text("x")
    (plan_dir / "ignore.json").write_text("x")
    found = _scan(plan_dir, ".tfplan.txt")
    assert len(found) == 2


def test_watch_calls_on_change(plan_dir):
    plan_dir.mkdir()
    callback = MagicMock()
    opts = WatchOptions(directory=plan_dir, interval=0, on_change=callback)
    (plan_dir / "plan1.tfplan.txt").write_text(PLAN_TEXT)
    watch(opts, max_iterations=1)
    callback.assert_called_once()
    args = callback.call_args[0]
    assert args[0].name == "plan1.tfplan.txt"


def test_watch_skips_already_seen(plan_dir):
    plan_dir.mkdir()
    callback = MagicMock()
    opts = WatchOptions(directory=plan_dir, interval=0, on_change=callback)
    (plan_dir / "plan1.tfplan.txt").write_text(PLAN_TEXT)
    watch(opts, max_iterations=2)
    assert callback.call_count == 1


def test_watch_picks_up_new_file(plan_dir):
    plan_dir.mkdir()
    callback = MagicMock()
    opts = WatchOptions(directory=plan_dir, interval=0, on_change=callback)
    (plan_dir / "plan1.tfplan.txt").write_text(PLAN_TEXT)

    iteration = [0]
    original_scan = __import__("stackdiff.watch", fromlist=["_scan"])._scan

    def fake_scan(d, ext):
        iteration[0] += 1
        if iteration[0] == 2:
            (plan_dir / "plan2.tfplan.txt").write_text(PLAN_TEXT)
        return original_scan(d, ext)

    with patch("stackdiff.watch._scan", side_effect=fake_scan):
        watch(opts, max_iterations=3)

    assert callback.call_count == 2


def test_notify_file_log(tmp_path):
    log = tmp_path / "watch.log"
    summary = DiffSummary(total=2, created=1, updated=1, destroyed=0)
    hook = notify_file_log(log)
    mock_report = MagicMock()
    hook(Path("plan.tfplan.txt"), mock_report, summary)
    entry = json.loads(log.read_text().strip())
    assert entry["total"] == 2
    assert entry["destructive"] is False


def test_notify_stdout_runs(capsys):
    summary = DiffSummary(total=1, created=0, updated=0, destroyed=1)
    notify_stdout(Path("x.tfplan.txt"), MagicMock(), summary)
    out = capsys.readouterr().out
    assert "DESTRUCTIVE" in out
