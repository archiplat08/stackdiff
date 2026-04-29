"""Tests for stackdiff.exclusion."""
from __future__ import annotations

import pytest

from stackdiff.parser import ResourceChange, ChangeAction
from stackdiff.diff import DiffEntry, DiffReport
from stackdiff.exclusion import ExclusionRule, apply_exclusions


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _change(address: str, action: ChangeAction = ChangeAction.UPDATE) -> ResourceChange:
    return ResourceChange(address=address, action=action, before={}, after={})


def _entry(address: str, action: ChangeAction = ChangeAction.UPDATE) -> DiffEntry:
    return DiffEntry(change=_change(address, action))


def _report(*entries: DiffEntry) -> DiffReport:
    return DiffReport(entries=list(entries))


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------

def test_no_rules_keeps_all():
    report = _report(_entry("aws_s3_bucket.logs"), _entry("aws_iam_role.ci"))
    result = apply_exclusions(report, [])
    assert result.total_kept == 2
    assert result.total_excluded == 0
    assert result.is_clean


def test_exact_address_pattern_excludes_entry():
    report = _report(_entry("aws_s3_bucket.logs"), _entry("aws_iam_role.ci"))
    rules = [ExclusionRule(address_pattern="aws_s3_bucket.logs", reason="managed externally")]
    result = apply_exclusions(report, rules)
    assert result.total_excluded == 1
    assert result.total_kept == 1
    assert result.excluded[0].change.address == "aws_s3_bucket.logs"
    assert "managed externally" in result.rules_matched


def test_glob_pattern_excludes_multiple():
    report = _report(
        _entry("aws_s3_bucket.logs"),
        _entry("aws_s3_bucket.artifacts"),
        _entry("aws_iam_role.ci"),
    )
    rules = [ExclusionRule(address_pattern="aws_s3_bucket.*", reason="s3 skip")]
    result = apply_exclusions(report, rules)
    assert result.total_excluded == 2
    assert result.total_kept == 1
    assert result.kept[0].change.address == "aws_iam_role.ci"


def test_resource_type_exclusion():
    report = _report(
        _entry("aws_iam_role.ci"),
        _entry("aws_iam_policy.read"),
        _entry("aws_s3_bucket.data"),
    )
    rules = [ExclusionRule(resource_type="aws_iam_role", reason="iam exemption")]
    result = apply_exclusions(report, rules)
    assert result.total_excluded == 1
    assert result.excluded[0].change.address == "aws_iam_role.ci"


def test_multiple_rules_first_match_wins():
    entry = _entry("aws_s3_bucket.logs")
    report = _report(entry)
    rules = [
        ExclusionRule(address_pattern="aws_s3_bucket.logs", reason="rule-one"),
        ExclusionRule(address_pattern="aws_s3_bucket.*", reason="rule-two"),
    ]
    result = apply_exclusions(report, rules)
    assert result.total_excluded == 1
    # only the first matching reason should appear
    assert "rule-one" in result.rules_matched


def test_is_clean_false_when_something_excluded():
    report = _report(_entry("aws_s3_bucket.logs"))
    rules = [ExclusionRule(address_pattern="*")]
    result = apply_exclusions(report, rules)
    assert not result.is_clean


def test_empty_report_returns_empty_result():
    result = apply_exclusions(_report(), [ExclusionRule(address_pattern="*")])
    assert result.total_kept == 0
    assert result.total_excluded == 0
    assert result.is_clean
