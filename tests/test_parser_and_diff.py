"""Tests for the parser and diff modules."""
from __future__ import annotations

import pytest

from stackdiff.diff import diff_plans
from stackdiff.parser import ChangeAction, ResourceChange, parse_plan_text

BASE_PLAN = """
  + aws_s3_bucket.logs
  ~ aws_instance.web
  - aws_security_group.old
"""

HEAD_PLAN = """
  + aws_s3_bucket.logs
  + aws_lambda_function.processor
  ~ aws_instance.web
"""


def test_parse_creates():
    changes = parse_plan_text("  + aws_s3_bucket.my_bucket")
    assert len(changes) == 1
    assert changes[0].action == ChangeAction.CREATE
    assert changes[0].resource_type == "aws_s3_bucket"
    assert changes[0].resource_name == "my_bucket"


def test_parse_update():
    changes = parse_plan_text("  ~ aws_instance.web")
    assert changes[0].action == ChangeAction.UPDATE


def test_parse_destroy():
    changes = parse_plan_text("  - aws_security_group.old")
    assert changes[0].action == ChangeAction.DESTROY


def test_parse_multiple_resources():
    changes = parse_plan_text(BASE_PLAN)
    assert len(changes) == 3


def test_parse_module_address():
    changes = parse_plan_text("  + module.networking.aws_vpc.main")
    assert changes[0].module == "module.networking"
    assert changes[0].resource_type == "aws_vpc"


def test_diff_added():
    base = parse_plan_text(BASE_PLAN)
    head = parse_plan_text(HEAD_PLAN)
    report = diff_plans(base, head)
    added_addresses = [e.address for e in report.added]
    assert "aws_lambda_function.processor" in added_addresses


def test_diff_removed():
    base = parse_plan_text(BASE_PLAN)
    head = parse_plan_text(HEAD_PLAN)
    report = diff_plans(base, head)
    removed_addresses = [e.address for e in report.removed]
    assert "aws_security_group.old" in removed_addresses


def test_diff_unchanged():
    base = parse_plan_text(BASE_PLAN)
    head = parse_plan_text(HEAD_PLAN)
    report = diff_plans(base, head)
    unchanged_addresses = [e.address for e in report.unchanged]
    assert "aws_s3_bucket.logs" in unchanged_addresses
    assert "aws_instance.web" in unchanged_addresses


def test_diff_no_changes():
    base = parse_plan_text(BASE_PLAN)
    report = diff_plans(base, base)
    assert not report.has_changes


def test_summary_format():
    base = parse_plan_text(BASE_PLAN)
    head = parse_plan_text(HEAD_PLAN)
    report = diff_plans(base, head)
    summary = report.summary()
    assert "+1 added" in summary
    assert "-1 removed" in summary
