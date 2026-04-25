"""Integration tests for the ownership CLI sub-command."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


PLAN_TEXT = """
Terraform will perform the following actions:

  # aws_s3_bucket.logs will be created
  + resource "aws_s3_bucket" "logs" {
    }

  # aws_iam_role.ci will be created
  + resource "aws_iam_role" "ci" {
    }

Plan: 2 to add, 0 to change, 0 to destroy.
"""

OWNER_MAP = {
    "aws_s3_bucket.logs": {"owner": "alice", "team": "platform"},
    "aws_iam_role.*": {"team": "security"},
}


@pytest.fixture()
def plan_file(tmp_path: Path) -> Path:
    p = tmp_path / "plan.txt"
    p.write_text(PLAN_TEXT)
    return p


@pytest.fixture()
def owner_map_file(tmp_path: Path) -> Path:
    p = tmp_path / "owners.json"
    p.write_text(json.dumps(OWNER_MAP))
    return p


def _run(*args: str) -> subprocess.CompletedProcess:  # type: ignore[type-arg]
    return subprocess.run(
        [sys.executable, "-m", "stackdiff.cli_ownership", "ownership", *args],
        capture_output=True,
        text=True,
    )


def test_ownership_exits_zero(plan_file: Path, owner_map_file: Path) -> None:
    result = _run(str(plan_file), "--map", str(owner_map_file))
    assert result.returncode == 0


def test_ownership_text_output(plan_file: Path, owner_map_file: Path) -> None:
    result = _run(str(plan_file), "--map", str(owner_map_file), "--format", "text")
    assert "platform" in result.stdout
    assert "security" in result.stdout


def test_ownership_json_output(plan_file: Path, owner_map_file: Path) -> None:
    result = _run(str(plan_file), "--map", str(owner_map_file), "--format", "json")
    data = json.loads(result.stdout)
    addresses = {e["address"] for e in data}
    assert "aws_s3_bucket.logs" in addresses


def test_ownership_markdown_output(plan_file: Path, owner_map_file: Path) -> None:
    result = _run(str(plan_file), "--map", str(owner_map_file), "--format", "markdown")
    assert "| Address |" in result.stdout


def test_warn_unowned_exits_one_when_unowned(plan_file: Path) -> None:
    # No owner map provided — all resources are unowned.
    result = _run(str(plan_file), "--warn-unowned")
    assert result.returncode == 1


def test_warn_unowned_exits_zero_when_all_owned(
    plan_file: Path, owner_map_file: Path
) -> None:
    result = _run(
        str(plan_file), "--map", str(owner_map_file), "--warn-unowned"
    )
    # Both resources are covered by the map, so no unowned entries.
    assert result.returncode == 0
