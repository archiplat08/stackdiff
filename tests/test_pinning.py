"""Tests for stackdiff.pinning and stackdiff.cli_pinning."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from stackdiff.diff import DiffEntry, DiffReport
from stackdiff.parser import ChangeAction, ResourceChange
from stackdiff.pinning import (
    PinnedRule,
    PinViolation,
    check_pins,
    format_pin_result,
)


def _entry(address: str, action: ChangeAction) -> DiffEntry:
    rc = ResourceChange(address=address, action=action, module=None, resource_type=address.split(".")[0])
    return DiffEntry(resource=rc)


def _report(*entries: DiffEntry) -> DiffReport:
    return DiffReport(entries=list(entries))


# ---------------------------------------------------------------------------
# check_pins
# ---------------------------------------------------------------------------

def test_no_rules_returns_clean():
    report = _report(_entry("aws_instance.web", ChangeAction.DELETE))
    result = check_pins(report, [])
    assert result.clean
    assert result.checked == 1


def test_create_action_not_flagged():
    rules = [PinnedRule(pattern="aws_instance.web")]
    report = _report(_entry("aws_instance.web", ChangeAction.CREATE))
    result = check_pins(report, rules)
    assert result.clean


def test_delete_on_pinned_resource_flagged():
    rules = [PinnedRule(pattern="aws_instance.web", reason="production DB")]
    report = _report(_entry("aws_instance.web", ChangeAction.DELETE))
    result = check_pins(report, rules)
    assert not result.clean
    assert len(result.violations) == 1
    assert "production DB" in result.violations[0].message


def test_update_on_pinned_resource_flagged():
    rules = [PinnedRule(pattern="aws_s3_bucket.assets")]
    report = _report(_entry("aws_s3_bucket.assets", ChangeAction.UPDATE))
    result = check_pins(report, rules)
    assert len(result.violations) == 1


def test_replace_on_pinned_resource_flagged():
    rules = [PinnedRule(pattern="aws_db_instance.main")]
    report = _report(_entry("aws_db_instance.main", ChangeAction.REPLACE))
    result = check_pins(report, rules)
    assert len(result.violations) == 1


def test_glob_pattern_matches_multiple():
    rules = [PinnedRule(pattern="aws_instance.*")]
    report = _report(
        _entry("aws_instance.web", ChangeAction.DELETE),
        _entry("aws_instance.api", ChangeAction.UPDATE),
        _entry("aws_s3_bucket.data", ChangeAction.DELETE),
    )
    result = check_pins(report, rules)
    assert len(result.violations) == 2


def test_only_first_matching_rule_produces_one_violation():
    rules = [
        PinnedRule(pattern="aws_instance.*"),
        PinnedRule(pattern="aws_instance.web"),
    ]
    report = _report(_entry("aws_instance.web", ChangeAction.DELETE))
    result = check_pins(report, rules)
    assert len(result.violations) == 1


# ---------------------------------------------------------------------------
# format_pin_result
# ---------------------------------------------------------------------------

def test_format_clean():
    report = _report(_entry("aws_instance.web", ChangeAction.CREATE))
    result = check_pins(report, [PinnedRule(pattern="aws_instance.web")])
    text = format_pin_result(result)
    assert "No pinned" in text


def test_format_violations_lists_messages():
    rules = [PinnedRule(pattern="aws_instance.web", reason="critical")]
    report = _report(_entry("aws_instance.web", ChangeAction.DELETE))
    result = check_pins(report, rules)
    text = format_pin_result(result)
    assert "1 pinned" in text
    assert "critical" in text


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@pytest.fixture()
def plan_dir(tmp_path: Path) -> Path:
    return tmp_path


PLAN_TEXT_CREATE = """
Terraform will perform the following actions:

  # aws_instance.web will be created
  + resource "aws_instance" "web" {}

Plan: 1 to add, 0 to change, 0 to destroy.
"""

PLAN_TEXT_DESTROY = """
Terraform will perform the following actions:

  # aws_instance.web will be destroyed
  - resource "aws_instance" "web" {}

Plan: 0 to add, 0 to change, 1 to destroy.
"""


def _run(args: list, plan_dir: Path) -> int:
    from stackdiff.cli_pinning import _cmd_pinning, build_parser
    parser = build_parser()
    parsed = parser.parse_args(["pins"] + args)
    return _cmd_pinning(parsed)


def test_clean_plan_exits_zero(plan_dir: Path):
    plan_file = plan_dir / "plan.txt"
    plan_file.write_text(PLAN_TEXT_CREATE)
    code = _run([str(plan_file), "--pin", "aws_instance.web"], plan_dir)
    assert code == 0


def test_destroy_pinned_exits_two(plan_dir: Path):
    plan_file = plan_dir / "plan.txt"
    plan_file.write_text(PLAN_TEXT_DESTROY)
    code = _run([str(plan_file), "--pin", "aws_instance.web"], plan_dir)
    assert code == 2


def test_no_rules_exits_zero(plan_dir: Path):
    plan_file = plan_dir / "plan.txt"
    plan_file.write_text(PLAN_TEXT_DESTROY)
    code = _run([str(plan_file)], plan_dir)
    assert code == 0


def test_pin_file_loaded(plan_dir: Path):
    plan_file = plan_dir / "plan.txt"
    plan_file.write_text(PLAN_TEXT_DESTROY)
    pin_file = plan_dir / "pins.json"
    pin_file.write_text(json.dumps([{"pattern": "aws_instance.*", "reason": "prod"}]))
    code = _run([str(plan_file), "--pin-file", str(pin_file)], plan_dir)
    assert code == 2


def test_json_output_structure(plan_dir: Path, capsys):
    plan_file = plan_dir / "plan.txt"
    plan_file.write_text(PLAN_TEXT_DESTROY)
    _run([str(plan_file), "--pin", "aws_instance.web", "--format", "json"], plan_dir)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "violations" in data
    assert data["clean"] is False
