"""Tests for stackdiff.suppression and stackdiff.suppression_format."""
from __future__ import annotations

import json

import pytest

from stackdiff.diff import DiffEntry, DiffReport
from stackdiff.parser import ChangeAction, ResourceChange
from stackdiff.suppression import (
    SuppressionRule,
    apply_suppressions,
    to_filtered_report,
)
from stackdiff.suppression_format import format_suppression_text, suppression_to_json


def _entry(address: str, action: str = "create") -> DiffEntry:
    rc = ResourceChange(
        address=address,
        resource_type=address.split(".")[0],
        name=address.split(".")[-1],
        action=ChangeAction(action),
        module=None,
    )
    return DiffEntry(change=rc)


def _report(*entries: DiffEntry) -> DiffReport:
    return DiffReport(entries=list(entries), stack_name="test")


# --- apply_suppressions ---

def test_no_rules_keeps_all():
    r = _report(_entry("aws_s3_bucket.logs"), _entry("aws_iam_role.exec"))
    result = apply_suppressions(r, [])
    assert result.total_kept == 2
    assert result.total_suppressed == 0


def test_exact_address_suppressed():
    r = _report(_entry("aws_s3_bucket.logs"), _entry("aws_iam_role.exec"))
    rules = [SuppressionRule(address_pattern="aws_s3_bucket.logs", reason="known")]
    result = apply_suppressions(r, rules)
    assert result.total_suppressed == 1
    assert result.suppressed[0].change.address == "aws_s3_bucket.logs"
    assert result.total_kept == 1


def test_glob_pattern_suppresses_multiple():
    r = _report(
        _entry("module.cache.aws_elasticache_cluster.primary"),
        _entry("module.cache.aws_elasticache_cluster.replica"),
        _entry("aws_s3_bucket.data"),
    )
    rules = [SuppressionRule(address_pattern="module.cache.*")]
    result = apply_suppressions(r, rules)
    assert result.total_suppressed == 2
    assert result.total_kept == 1


def test_action_filter_only_suppresses_matching_action():
    r = _report(
        _entry("aws_instance.web", "create"),
        _entry("aws_instance.web", "delete"),
    )
    rules = [SuppressionRule(address_pattern="aws_instance.web", action="delete")]
    result = apply_suppressions(r, rules)
    assert result.total_suppressed == 1
    assert result.suppressed[0].change.action.value == "delete"
    assert result.total_kept == 1


def test_rules_applied_deduped():
    r = _report(_entry("aws_s3_bucket.a"), _entry("aws_s3_bucket.b"))
    rule = SuppressionRule(address_pattern="aws_s3_bucket.*")
    result = apply_suppressions(r, [rule])
    assert len(result.rules_applied) == 1


def test_to_filtered_report_returns_diff_report():
    r = _report(_entry("aws_s3_bucket.logs"), _entry("aws_iam_role.exec"))
    rules = [SuppressionRule(address_pattern="aws_s3_bucket.logs")]
    result = apply_suppressions(r, rules)
    filtered = to_filtered_report(result, r)
    assert len(filtered.entries) == 1
    assert filtered.stack_name == "test"


# --- format helpers ---

def test_format_suppression_text_no_suppressions():
    r = _report(_entry("aws_s3_bucket.a"))
    result = apply_suppressions(r, [])
    text = format_suppression_text(result)
    assert "1 kept" in text
    assert "0 suppressed" in text


def test_format_suppression_text_with_suppressed():
    r = _report(_entry("aws_s3_bucket.logs", "delete"))
    rules = [SuppressionRule(address_pattern="aws_s3_bucket.*", action="delete", reason="safe")]
    result = apply_suppressions(r, rules)
    text = format_suppression_text(result)
    assert "aws_s3_bucket.logs" in text
    assert "delete" in text
    assert "safe" in text


def test_suppression_to_json_valid():
    r = _report(_entry("aws_s3_bucket.logs"))
    rules = [SuppressionRule(address_pattern="aws_s3_bucket.*")]
    result = apply_suppressions(r, rules)
    data = json.loads(suppression_to_json(result))
    assert data["total_suppressed"] == 1
    assert data["total_kept"] == 0
    assert data["suppressed"][0]["address"] == "aws_s3_bucket.logs"
