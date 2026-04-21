"""Tests for stackdiff.threshold and cli_threshold."""
from __future__ import annotations

import textwrap
import pytest

from stackdiff.diff import DiffReport, DiffEntry
from stackdiff.parser import ChangeAction
from stackdiff.threshold import (
    ThresholdOptions,
    ThresholdViolation,
    check_thresholds,
    format_threshold_result,
)


def _entry(action: ChangeAction, rtype: str = "aws_instance", name: str = "web") -> DiffEntry:
    from stackdiff.parser import ResourceChange
    rc = ResourceChange(
        address=f"{rtype}.{name}",
        module=None,
        resource_type=rtype,
        name=name,
        action=action,
        before={"instance_type": "t2.micro"},
        after={"instance_type": "t3.micro"},
    )
    return DiffEntry(resource=rc)


def _report(*entries: DiffEntry) -> DiffReport:
    return DiffReport(entries=list(entries))


def test_no_violations_when_no_limits():
    report = _report(
        _entry(ChangeAction.DELETE),
        _entry(ChangeAction.DELETE, name="db"),
    )
    result = check_thresholds(report, ThresholdOptions())
    assert result.passed
    assert result.violations == []


def test_risk_score_violation():
    report = _report(
        _entry(ChangeAction.DELETE),
        _entry(ChangeAction.DELETE, name="db"),
    )
    result = check_thresholds(report, ThresholdOptions(max_risk_score=1))
    assert not result.passed
    fields = [v.field for v in result.violations]
    assert "risk_score" in fields


def test_destructive_violation():
    report = _report(
        _entry(ChangeAction.DELETE),
        _entry(ChangeAction.REPLACE, name="db"),
    )
    result = check_thresholds(report, ThresholdOptions(max_destructive=1))
    assert not result.passed
    fields = [v.field for v in result.violations]
    assert "destructive_changes" in fields
    v = next(x for x in result.violations if x.field == "destructive_changes")
    assert v.actual == 2
    assert v.limit == 1


def test_high_risk_violation():
    report = _report(
        _entry(ChangeAction.DELETE, rtype="aws_iam_role"),
        _entry(ChangeAction.DELETE, rtype="aws_iam_role", name="admin"),
    )
    result = check_thresholds(report, ThresholdOptions(max_high_risk=1))
    assert not result.passed
    fields = [v.field for v in result.violations]
    assert "high_risk_entries" in fields


def test_multiple_violations():
    report = _report(
        _entry(ChangeAction.DELETE, rtype="aws_iam_role"),
        _entry(ChangeAction.DELETE, rtype="aws_iam_role", name="admin"),
    )
    opts = ThresholdOptions(max_risk_score=1, max_destructive=1, max_high_risk=0)
    result = check_thresholds(report, opts)
    assert len(result.violations) == 3


def test_format_passed():
    result = check_thresholds(_report(), ThresholdOptions())
    assert format_threshold_result(result) == "All thresholds passed."


def test_format_violations():
    report = _report(_entry(ChangeAction.DELETE), _entry(ChangeAction.DELETE, name="db"))
    result = check_thresholds(report, ThresholdOptions(max_destructive=1))
    text = format_threshold_result(result)
    assert "Threshold violations:" in text
    assert "destructive_changes" in text
    assert "limit 1" in text


def test_violation_message():
    v = ThresholdViolation(field="risk_score", limit=5, actual=10)
    assert "risk_score" in v.message
    assert "10" in v.message
    assert "5" in v.message
