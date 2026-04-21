"""Integration tests for the remediation CLI sub-command."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture()
def plan_dir(tmp_path: Path) -> Path:
    return tmp_path


def _write(path: Path, content: str) -> Path:
    path.write_text(content)
    return path


_SAFE_PLAN = """
Terraform will perform the following actions:

  # aws_s3_bucket.logs will be created
  + resource "aws_s3_bucket" "logs" {
    }

Plan: 1 to add, 0 to change, 0 to destroy.
"""

_DESTROY_PLAN = """
Terraform will perform the following actions:

  # aws_db_instance.prod will be destroyed
  - resource "aws_db_instance" "prod" {
    }

Plan: 0 to add, 0 to change, 1 to destroy.
"""


def _run(plan_file: Path, *extra: str) -> subprocess.CompletedProcess:  # type: ignore[type-arg]
    return subprocess.run(
        [sys.executable, "-m", "stackdiff.cli_remediation", "remediation", str(plan_file), *extra],
        capture_output=True,
        text=True,
    )


def test_safe_plan_exits_zero(plan_dir: Path) -> None:
    f = _write(plan_dir / "safe.txt", _SAFE_PLAN)
    result = _run(f, "--exit-code")
    assert result.returncode == 0
    assert "safe" in result.stdout.lower()


def test_destroy_plan_produces_hints(plan_dir: Path) -> None:
    f = _write(plan_dir / "destroy.txt", _DESTROY_PLAN)
    result = _run(f)
    assert result.returncode == 0
    assert "prevent_destroy" in result.stdout or "delete" in result.stdout.lower()


def test_destroy_plan_exit_code_one_when_flag_set(plan_dir: Path) -> None:
    f = _write(plan_dir / "destroy2.txt", _DESTROY_PLAN)
    result = _run(f, "--exit-code")
    assert result.returncode == 1


def test_missing_plan_file_exits_two(plan_dir: Path) -> None:
    result = _run(plan_dir / "nonexistent.txt")
    assert result.returncode == 2
    assert "not found" in result.stderr


def test_no_command_prints_help(plan_dir: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "stackdiff.cli_remediation"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "remediation" in result.stdout
