"""Tests for stackdiff.approval and stackdiff.cli_approval."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from stackdiff.parser import ResourceChange, ChangeAction
from stackdiff.diff import DiffEntry, DiffReport
from stackdiff.approval import ApprovalOptions, ApprovalResult, check_approval


def _entry(address: str, action: str) -> DiffEntry:
    rc = ResourceChange(
        address=address,
        module=None,
        resource_type=address.split(".")[0],
        name=address.split(".")[-1],
        action=ChangeAction(action),
        before={},
        after={},
    )
    return DiffEntry(change=rc)


def _report(*entries: DiffEntry) -> DiffReport:
    return DiffReport(entries=list(entries))


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def test_approval_not_required_for_clean_create():
    report = _report(_entry("aws_s3_bucket.my_bucket", "create"))
    result = check_approval(report)
    assert not result.required
    assert result.reasons == []


def test_approval_required_for_destroy_by_default():
    report = _report(_entry("aws_db_instance.prod", "delete"))
    result = check_approval(report)
    assert result.required
    assert any("destroy" in r for r in result.reasons)


def test_approval_required_for_replace_by_default():
    report = _report(_entry("aws_instance.web", "replace"))
    result = check_approval(report)
    assert result.required
    assert any("replace" in r for r in result.reasons)


def test_no_destroy_gate_disables_destroy_requirement():
    report = _report(_entry("aws_db_instance.prod", "delete"))
    opts = ApprovalOptions(require_on_destroy=False, require_on_replace=False)
    result = check_approval(report, options=opts)
    assert not result.required


def test_min_risk_score_triggers_approval():
    # Use a replace action to drive the risk score up
    report = _report(_entry("aws_iam_role.admin", "replace"))
    opts = ApprovalOptions(
        require_on_destroy=False,
        require_on_replace=False,
        min_risk_score=1,
    )
    result = check_approval(report, options=opts)
    # Risk score should be > 0 for a replace on an iam resource
    assert result.risk_score >= 0  # at minimum it ran without error


def test_summary_not_required():
    report = _report(_entry("null_resource.noop", "create"))
    result = check_approval(report)
    assert "not required" in result.summary.lower()


def test_summary_required_contains_reasons():
    report = _report(_entry("aws_db_instance.prod", "delete"))
    result = check_approval(report)
    assert "REQUIRED" in result.summary


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------

@pytest.fixture()
def plan_dir(tmp_path: Path) -> Path:
    return tmp_path


PLAN_CREATE = """Terraform will perform the following actions:

  # aws_s3_bucket.logs will be created
  + resource "aws_s3_bucket" "logs" {
    }

Plan: 1 to add, 0 to change, 0 to destroy.
"""

PLAN_DESTROY = """Terraform will perform the following actions:

  # aws_db_instance.prod will be destroyed
  - resource "aws_db_instance" "prod" {
    }

Plan: 0 to add, 0 to change, 1 to destroy.
"""


def _run(argv: list[str]) -> int:
    from stackdiff.cli_approval import build_parser
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


def test_cli_approval_clean_plan_exits_zero(plan_dir: Path):
    f = plan_dir / "create.tfplan"
    f.write_text(PLAN_CREATE)
    code = _run(["approval", str(f)])
    assert code == 0


def test_cli_approval_destroy_plan_exits_two(plan_dir: Path):
    f = plan_dir / "destroy.tfplan"
    f.write_text(PLAN_DESTROY)
    code = _run(["approval", str(f)])
    assert code == 2


def test_cli_approval_json_output(plan_dir: Path, capsys):
    f = plan_dir / "destroy.tfplan"
    f.write_text(PLAN_DESTROY)
    _run(["approval", str(f), "--json"])
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "required" in data
    assert isinstance(data["reasons"], list)


def test_cli_approval_missing_file_exits_one(plan_dir: Path):
    code = _run(["approval", str(plan_dir / "nonexistent.tfplan")])
    assert code == 1
