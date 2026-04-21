"""Tests for stackdiff.policy evaluation."""
from __future__ import annotations

import pytest

from stackdiff.parser import ResourceChange, ChangeAction
from stackdiff.diff import DiffEntry, DiffReport
from stackdiff.policy import (
    NO_DESTROY,
    NO_REPLACE,
    WARN_ON_IAM,
    DEFAULT_RULES,
    PolicyRule,
    evaluate_policy,
)


def _make_entry(action: ChangeAction, rtype: str = "aws_instance", name: str = "web") -> DiffEntry:
    rc = ResourceChange(
        address=f"{rtype}.{name}",
        module=None,
        resource_type=rtype,
        name=name,
        action=action,
    )
    return DiffEntry(resource_change=rc)


def _report(*entries: DiffEntry) -> DiffReport:
    return DiffReport(entries=list(entries))


def test_no_violations_on_create():
    report = _report(_make_entry(ChangeAction.CREATE))
    result = evaluate_policy(report, [NO_DESTROY, NO_REPLACE])
    assert not result.violations
    assert not result.has_blocks
    assert not result.has_warnings


def test_no_destroy_blocks_delete():
    report = _report(_make_entry(ChangeAction.DELETE))
    result = evaluate_policy(report, [NO_DESTROY])
    assert len(result.violations) == 1
    assert result.violations[0].rule_name == "no-destroy"
    assert result.violations[0].severity == "block"
    assert result.has_blocks


def test_no_replace_blocks_replace():
    report = _report(_make_entry(ChangeAction.REPLACE))
    result = evaluate_policy(report, [NO_REPLACE])
    assert len(result.violations) == 1
    assert result.violations[0].rule_name == "no-replace"
    assert result.has_blocks


def test_warn_iam_on_update():
    report = _report(_make_entry(ChangeAction.UPDATE, rtype="aws_iam_role", name="deployer"))
    result = evaluate_policy(report, [WARN_ON_IAM])
    assert len(result.violations) == 1
    assert result.violations[0].severity == "warn"
    assert result.has_warnings
    assert not result.has_blocks


def test_warn_iam_not_triggered_for_non_iam():
    report = _report(_make_entry(ChangeAction.UPDATE, rtype="aws_s3_bucket"))
    result = evaluate_policy(report, [WARN_ON_IAM])
    assert not result.violations


def test_multiple_rules_multiple_violations():
    report = _report(
        _make_entry(ChangeAction.DELETE),
        _make_entry(ChangeAction.REPLACE),
    )
    result = evaluate_policy(report, DEFAULT_RULES)
    rule_names = {v.rule_name for v in result.violations}
    assert "no-destroy" in rule_names
    assert "no-replace" in rule_names
    assert result.has_blocks


def test_empty_report_no_violations():
    result = evaluate_policy(_report())
    assert not result.violations


def test_violation_message_format():
    report = _report(_make_entry(ChangeAction.DELETE, rtype="aws_db_instance", name="prod"))
    result = evaluate_policy(report, [NO_DESTROY])
    msg = result.violations[0].message
    assert "BLOCK" in msg
    assert "no-destroy" in msg
    assert "aws_db_instance.prod" in msg


def test_custom_rule():
    custom = PolicyRule(
        name="no-s3-delete",
        severity="block",
        match=lambda entry: (
            entry.resource_change.resource_type == "aws_s3_bucket"
            and entry.resource_change.action == ChangeAction.DELETE
        ),
    )
    report = _report(_make_entry(ChangeAction.DELETE, rtype="aws_s3_bucket", name="assets"))
    result = evaluate_policy(report, [custom])
    assert len(result.violations) == 1
    assert result.violations[0].rule_name == "no-s3-delete"
    assert result.has_blocks


def test_custom_rule_no_match():
    custom = PolicyRule(
        name="no-s3-delete",
        severity="block",
        match=lambda entry: (
            entry.resource_change.resource_type == "aws_s3_bucket"
            and entry.resource_change.action == ChangeAction.DELETE
        ),
    )
    report = _report(_make_entry(ChangeAction.CREATE, rtype="aws_s3_bucket", name="assets"))
    result = evaluate_policy(report, [custom])
    assert not result.violations
