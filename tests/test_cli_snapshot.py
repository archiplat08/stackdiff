"""Integration tests for cli_snapshot sub-commands."""
from __future__ import annotations

import json
import pytest

from stackdiff.cli_snapshot import build_parser, _cmd_snapshot


PLAN_TEXT = """
Terraform will perform the following actions:

  # aws_instance.web will be created
  + resource "aws_instance" "web" {
    }

  # aws_s3_bucket.logs will be destroyed
  - resource "aws_s3_bucket" "logs" {
    }

Plan: 1 to add, 0 to change, 1 to destroy.
"""


@pytest.fixture
def plan_file(tmp_path):
    p = tmp_path / "plan.txt"
    p.write_text(PLAN_TEXT)
    return str(p)


@pytest.fixture
def snap_dir(tmp_path):
    return str(tmp_path / "snaps")


def _run(args: list[str]):
    """Parse *args* and execute the corresponding snapshot sub-command.

    Returns the integer return-code produced by ``_cmd_snapshot``.
    """
    parser = build_parser()
    ns = parser.parse_args(args)
    return _cmd_snapshot(ns)


def test_save_exits_zero(plan_file, snap_dir):
    rc = _run(["snapshot", "save", "v1", plan_file, "--dir", snap_dir])
    assert rc == 0


def test_save_creates_snapshot_file(plan_file, snap_dir):
    _run(["snapshot", "save", "release-1", plan_file, "--dir", snap_dir])
    from stackdiff.snapshot import load_snapshot
    snap = load_snapshot("release-1", snap_dir)
    assert snap is not None
    assert len(snap.entries) == 2


def test_list_shows_saved_names(plan_file, snap_dir, capsys):
    _run(["snapshot", "save", "v1", plan_file, "--dir", snap_dir])
    _run(["snapshot", "save", "v2", plan_file, "--dir", snap_dir])
    rc = _run(["snapshot", "list", "--dir", snap_dir])
    assert rc == 0
    out = capsys.readouterr().out
    assert "v1" in out
    assert "v2" in out


def test_list_empty_dir_exits_zero(snap_dir, capsys):
    """Listing snapshots in an empty (or non-existent) directory should not error."""
    rc = _run(["snapshot", "list", "--dir", snap_dir])
    assert rc == 0


def test_show_exits_zero(plan_file, snap_dir, capsys):
    _run(["snapshot", "save", "v1", plan_file, "--dir", snap_dir])
    rc = _run(["snapshot", "show", "v1", "--dir", snap_dir])
    assert rc == 0


def test_show_missing_exits_one(snap_dir):
    rc = _run(["snapshot", "show", "ghost", "--dir", snap_dir])
    assert rc == 1


def test_diff_two_snapshots(plan_file, snap_dir, capsys):
    _run(["snapshot", "save", "base", plan_file, "--dir", snap_dir])
    _run(["snapshot", "save", "head", plan_file, "--dir", snap_dir])
    rc = _run(["snapshot", "diff", "base", "head", "--dir", snap_dir])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Added" in out


def test_delete_exits_zero(plan_file, snap_dir):
    _run(["snapshot", "save", "v1", plan_file, "--dir", snap_dir])
    rc = _run(["snapshot", "delete", "v1", "--dir", snap_dir])
    assert rc == 0


def test_delete_missing_exits_one(snap_dir):
    rc = _run(["snapshot", "delete", "ghost", "--dir", snap_dir])
    assert rc == 1


def test_delete_removes_snapshot(plan_file, snap_dir):
    """After deletion the snapshot should no longer appear in the list output."""
    _run(["snapshot", "save", "v1", plan_file, "--dir", snap_dir])
    _run(["snapshot", "delete", "v1", "--dir", snap_dir])
    from stackdiff.snapshot import load_snapshot
    assert load_snapshot("v1", snap_dir) is None
