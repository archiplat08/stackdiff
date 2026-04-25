"""Integration tests for the coverage CLI sub-command."""
from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


@pytest.fixture()
def plan_dir(tmp_path: Path) -> Path:
    return tmp_path


PLAN_CREATE = textwrap.dedent("""\
    Terraform will perform the following actions:

      # aws_s3_bucket.my_bucket will be created
      + resource "aws_s3_bucket" "my_bucket" {
          + bucket = "example"
        }

    Plan: 1 to add, 0 to change, 0 to destroy.
""")

PLAN_DESTROY = textwrap.dedent("""\
    Terraform will perform the following actions:

      # aws_iam_role.admin will be destroyed
      - resource "aws_iam_role" "admin" {
          - name = "admin"
        }

    Plan: 0 to add, 0 to change, 1 to destroy.
""")


def _write(path: Path, content: str) -> Path:
    path.write_text(content)
    return path


def _run(plan_path: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "stackdiff.cli_coverage", "coverage", str(plan_path), *extra],
        capture_output=True,
        text=True,
    )


def test_coverage_exits_zero(plan_dir: Path):
    plan = _write(plan_dir / "plan.txt", PLAN_CREATE)
    result = _run(plan)
    assert result.returncode == 0


def test_coverage_text_output(plan_dir: Path):
    plan = _write(plan_dir / "plan.txt", PLAN_CREATE)
    result = _run(plan)
    assert "Coverage Report" in result.stdout
    assert "%" in result.stdout


def test_coverage_json_output(plan_dir: Path):
    plan = _write(plan_dir / "plan.txt", PLAN_CREATE)
    result = _run(plan, "--format", "json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "total" in data
    assert "owner_pct" in data
    assert "uncovered" in data


def test_fail_under_owner_triggers_exit_one(plan_dir: Path):
    plan = _write(plan_dir / "plan.txt", PLAN_CREATE)
    # No owner map provided, so owner coverage is 0% — below 50%
    result = _run(plan, "--fail-under-owner", "50")
    assert result.returncode == 1


def test_fail_under_owner_passes_when_threshold_met(plan_dir: Path):
    plan = _write(plan_dir / "plan.txt", PLAN_CREATE)
    owner_map = plan.parent / "owners.json"
    owner_map.write_text(json.dumps({"aws_s3_bucket.my_bucket": "team-a"}))
    result = _run(plan, "--owner-map", str(owner_map), "--fail-under-owner", "100")
    assert result.returncode == 0
