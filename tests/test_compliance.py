"""Tests for stackdiff.compliance and stackdiff.cli_compliance."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from stackdiff.diff import DiffReport, DiffEntry
from stackdiff.parser import ResourceChange, ChangeAction
from stackdiff.compliance import (
    check_compliance,
    format_compliance,
    ComplianceResult,
    FRAMEWORKS,
)


def _entry(address: str, action: str) -> DiffEntry:
    rc = ResourceChange(
        address=address,
        module=None,
        resource_type=address.split(".")[0],
        name=address.split(".")[-1],
        action=ChangeAction(action),
    )
    return DiffEntry(change=rc)


def _report(*entries: DiffEntry) -> DiffReport:
    return DiffReport(entries=list(entries))


# ---------------------------------------------------------------------------
# check_compliance
# ---------------------------------------------------------------------------

def test_unknown_framework_raises():
    with pytest.raises(ValueError, match="Unknown compliance framework"):
        check_compliance(_report(), "hipaa")


def test_clean_plan_passes_cis():
    report = _report(_entry("aws_s3_bucket.logs", "create"))
    result = check_compliance(report, "cis")
    assert result.passed
    assert result.block_count == 0


def test_iam_delete_blocks_cis():
    report = _report(_entry("aws_iam_role.admin", "delete"))
    result = check_compliance(report, "cis")
    assert not result.passed
    assert result.block_count == 1


def test_security_group_replace_blocks_cis():
    report = _report(_entry("aws_security_group.web", "replace"))
    result = check_compliance(report, "cis")
    assert not result.passed


def test_kms_delete_blocks_pci():
    report = _report(_entry("aws_kms_key.main", "delete"))
    result = check_compliance(report, "pci")
    assert not result.passed
    assert result.block_count >= 1


def test_waf_replace_warns_pci():
    report = _report(_entry("aws_waf_rule.block_sql", "replace"))
    result = check_compliance(report, "pci")
    # warn only, not block
    assert result.passed
    assert result.warn_count >= 1


def test_s3_delete_blocks_soc2():
    report = _report(_entry("aws_s3_bucket.audit", "delete"))
    result = check_compliance(report, "soc2")
    assert not result.passed


def test_violations_list_populated():
    report = _report(_entry("aws_iam_role.ci", "delete"))
    result = check_compliance(report, "cis")
    assert len(result.violations) == 1


# ---------------------------------------------------------------------------
# format_compliance
# ---------------------------------------------------------------------------

def test_format_compliance_pass_contains_pass():
    result = ComplianceResult(framework="cis", entries=[])
    text = format_compliance(result)
    assert "PASS" in text
    assert "CIS" in text


def test_format_compliance_fail_contains_violation():
    report = _report(_entry("aws_iam_role.admin", "delete"))
    result = check_compliance(report, "cis")
    text = format_compliance(result)
    assert "FAIL" in text
    assert "aws_iam_role.admin" in text


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@pytest.fixture()
def plan_dir(tmp_path: Path) -> Path:
    return tmp_path


def _write(directory: Path, content: str) -> Path:
    p = directory / "plan.txt"
    p.write_text(content, encoding="utf-8")
    return p


PLAN_SAFE = """Terraform will perform the following actions:
  # aws_s3_bucket.data will be created
  + resource \"aws_s3_bucket\" \"data\" {
    }
Plan: 1 to add, 0 to change, 0 to destroy.
"""

PLAN_DESTROY_IAM = """Terraform will perform the following actions:
  # aws_iam_role.admin will be destroyed
  - resource \"aws_iam_role\" \"admin\" {
    }
Plan: 0 to add, 0 to change, 1 to destroy.
"""


def _run(argv: list[str]) -> int:
    from stackdiff.cli_compliance import build_parser
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


def test_compliance_clean_plan_exits_zero(plan_dir: Path):
    plan_file = _write(plan_dir, PLAN_SAFE)
    rc = _run(["compliance", str(plan_file), "--framework", "cis"])
    assert rc == 0


def test_compliance_destroy_iam_exits_two(plan_dir: Path):
    plan_file = _write(plan_dir, PLAN_DESTROY_IAM)
    rc = _run(["compliance", str(plan_file), "--framework", "cis"])
    assert rc == 2


def test_compliance_json_output(plan_dir: Path, capsys: pytest.CaptureFixture):
    plan_file = _write(plan_dir, PLAN_DESTROY_IAM)
    _run(["compliance", str(plan_file), "--framework", "cis", "--format", "json"])
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["framework"] == "cis"
    assert data["passed"] is False
    assert data["block_count"] >= 1


def test_compliance_missing_plan_exits_one(plan_dir: Path):
    rc = _run(["compliance", str(plan_dir / "nonexistent.txt"), "--framework", "pci"])
    assert rc == 1
