"""Tests for stackdiff.gate and stackdiff.cli_gate."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from stackdiff.diff import DiffReport, DiffEntry
from stackdiff.parser import ChangeAction, ResourceChange
from stackdiff.policy import PolicyRule
from stackdiff.threshold import ThresholdOptions
from stackdiff.gate import GateOptions, GateResult, evaluate_gate, format_gate_result


def _entry(action: ChangeAction, address: str = "aws_instance.web") -> DiffEntry:
    rc = ResourceChange(address=address, action=action, module=None, resource_type="aws_instance")
    return DiffEntry(change=rc)


def _report(*entries: DiffEntry) -> DiffReport:
    return DiffReport(entries=list(entries))


# ---------------------------------------------------------------------------
# Unit tests for evaluate_gate
# ---------------------------------------------------------------------------

def test_gate_passes_clean_plan():
    report = _report(_entry(ChangeAction.CREATE))
    result = evaluate_gate(report, GateOptions())
    assert result.passed
    assert result.exit_code == 0


def test_gate_blocks_destroy_when_rule_set():
    report = _report(_entry(ChangeAction.DELETE))
    rule = PolicyRule(name="no-destroy", action=ChangeAction.DELETE, blocking=True)
    result = evaluate_gate(report, GateOptions(rules=[rule]))
    assert not result.passed
    assert result.exit_code == 2


def test_gate_warns_on_threshold_violation():
    entries = [_entry(ChangeAction.DELETE, f"aws_instance.r{i}") for i in range(5)]
    report = _report(*entries)
    opts = GateOptions(thresholds=ThresholdOptions(max_deletes=3))
    result = evaluate_gate(report, opts)
    assert not result.passed
    assert result.exit_code == 1  # threshold = warn, not block
    assert not result.policy.has_blocks


def test_gate_fails_on_high_risk_score():
    entries = [_entry(ChangeAction.DELETE, f"aws_iam_role.r{i}") for i in range(4)]
    report = _report(*entries)
    result = evaluate_gate(report, GateOptions(max_risk_score=1.0))
    # With several IAM deletes the score should exceed 1.0
    assert result.risk.score > 1.0
    assert not result.passed


def test_gate_passes_when_risk_within_limit():
    report = _report(_entry(ChangeAction.CREATE))
    result = evaluate_gate(report, GateOptions(max_risk_score=100.0))
    assert result.passed


def test_format_gate_result_contains_status():
    report = _report(_entry(ChangeAction.CREATE))
    result = evaluate_gate(report, GateOptions())
    text = format_gate_result(result)
    assert "PASS" in text


def test_format_gate_result_shows_block():
    report = _report(_entry(ChangeAction.DELETE))
    rule = PolicyRule(name="no-destroy", action=ChangeAction.DELETE, blocking=True)
    result = evaluate_gate(report, GateOptions(rules=[rule]))
    text = format_gate_result(result)
    assert "BLOCK" in text


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------

CREATE_PLAN = """Terraform will perform the following actions:

  # aws_s3_bucket.logs will be created
  + resource "aws_s3_bucket" "logs" {
    }

Plan: 1 to add, 0 to change, 0 to destroy.
"""

DESTROY_PLAN = """Terraform will perform the following actions:

  # aws_s3_bucket.logs will be destroyed
  - resource "aws_s3_bucket" "logs" {
    }

Plan: 0 to add, 0 to change, 1 to destroy.
"""


@pytest.fixture()
def plan_dir(tmp_path: Path) -> Path:
    return tmp_path


def _run(plan_path: Path, *extra: str) -> subprocess.CompletedProcess:  # type: ignore[type-arg]
    return subprocess.run(
        [sys.executable, "-m", "stackdiff.cli_gate", "gate", str(plan_path), *extra],
        capture_output=True,
        text=True,
    )


def test_cli_gate_clean_plan_exits_zero(plan_dir: Path) -> None:
    p = plan_dir / "plan.txt"
    p.write_text(CREATE_PLAN)
    r = _run(p)
    assert r.returncode == 0


def test_cli_gate_destroy_blocked_exits_two(plan_dir: Path) -> None:
    p = plan_dir / "plan.txt"
    p.write_text(DESTROY_PLAN)
    r = _run(p, "--no-destroy")
    assert r.returncode == 2


def test_cli_gate_json_output(plan_dir: Path) -> None:
    p = plan_dir / "plan.txt"
    p.write_text(CREATE_PLAN)
    r = _run(p, "--format", "json")
    data = json.loads(r.stdout)
    assert "passed" in data
    assert "exit_code" in data
    assert "risk_score" in data


def test_cli_gate_missing_file_exits_one(plan_dir: Path) -> None:
    r = _run(plan_dir / "nonexistent.txt")
    assert r.returncode == 1
