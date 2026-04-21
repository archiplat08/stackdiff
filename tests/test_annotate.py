"""Tests for stackdiff.annotate."""
import pytest
from stackdiff.diff import DiffReport, DiffEntry
from stackdiff.parser import ChangeAction
from stackdiff.policy import PolicyRule, Severity
from stackdiff.annotate import annotate, format_annotated, AnnotatedReport


def _entry(address: str, action: ChangeAction) -> DiffEntry:
    return DiffEntry(
        address=address,
        action=action,
        before={},
        after={},
    )


def _report(*entries: DiffEntry) -> DiffReport:
    return DiffReport(entries=list(entries))


# ---------------------------------------------------------------------------
# annotate() basics
# ---------------------------------------------------------------------------

def test_annotate_empty_report():
    report = _report()
    result = annotate(report, rules=[])
    assert isinstance(result, AnnotatedReport)
    assert result.entries == []


def test_annotate_preserves_all_entries():
    report = _report(
        _entry("aws_s3_bucket.data", ChangeAction.CREATE),
        _entry("aws_instance.web", ChangeAction.UPDATE),
    )
    result = annotate(report, rules=[])
    assert len(result.entries) == 2
    addresses = [e.address for e in result.entries]
    assert "aws_s3_bucket.data" in addresses
    assert "aws_instance.web" in addresses


def test_annotate_no_violations_when_no_rules():
    report = _report(_entry("aws_iam_role.admin", ChangeAction.CREATE))
    result = annotate(report, rules=[])
    assert not result.has_violations
    for e in result.entries:
        assert e.violations == []


def test_annotate_detects_block_violation():
    rule = PolicyRule(
        name="no_destroy",
        action=ChangeAction.DELETE,
        severity=Severity.BLOCK,
        resource_type_pattern="*",
    )
    report = _report(_entry("aws_db_instance.prod", ChangeAction.DELETE))
    result = annotate(report, rules=[rule])
    assert result.has_violations
    assert result.has_blocks
    entry = result.entries[0]
    assert entry.is_blocked


def test_annotate_warn_does_not_block():
    rule = PolicyRule(
        name="warn_iam",
        action=ChangeAction.CREATE,
        severity=Severity.WARN,
        resource_type_pattern="aws_iam_*",
    )
    report = _report(_entry("aws_iam_policy.read", ChangeAction.CREATE))
    result = annotate(report, rules=[rule])
    assert result.has_violations
    assert not result.has_blocks


# ---------------------------------------------------------------------------
# Risk integration
# ---------------------------------------------------------------------------

def test_annotate_assigns_risk_level():
    report = _report(_entry("aws_iam_role.admin", ChangeAction.DELETE))
    result = annotate(report, rules=[])
    entry = result.entries[0]
    assert entry.risk_level in ("none", "low", "medium", "high", "critical")


def test_annotate_high_risk_entries_filtered():
    report = _report(
        _entry("aws_iam_role.admin", ChangeAction.DELETE),
        _entry("aws_s3_bucket.logs", ChangeAction.CREATE),
    )
    result = annotate(report, rules=[])
    # high_risk_entries should only include entries with high/critical risk
    for e in result.high_risk_entries:
        assert e.risk_level in ("high", "critical")


# ---------------------------------------------------------------------------
# format_annotated()
# ---------------------------------------------------------------------------

def test_format_annotated_empty():
    result = annotate(_report(), rules=[])
    output = format_annotated(result)
    assert "(no changes)" in output


def test_format_annotated_contains_address():
    report = _report(_entry("aws_lambda_function.handler", ChangeAction.UPDATE))
    result = annotate(report, rules=[])
    output = format_annotated(result)
    assert "aws_lambda_function.handler" in output


def test_format_annotated_shows_violation_message():
    rule = PolicyRule(
        name="no_destroy",
        action=ChangeAction.DELETE,
        severity=Severity.BLOCK,
        resource_type_pattern="*",
    )
    report = _report(_entry("aws_rds_cluster.main", ChangeAction.DELETE))
    result = annotate(report, rules=[rule])
    output = format_annotated(result)
    assert "violations" in output
