"""Tests for stackdiff.coverage module."""
from __future__ import annotations

import pytest

from stackdiff.annotate import AnnotatedEntry
from stackdiff.coverage import build_coverage, format_coverage, CoverageResult
from stackdiff.diff import DiffEntry
from stackdiff.parser import ChangeAction, ResourceChange
from stackdiff.policy import PolicyViolation
from stackdiff.risk import RiskScore


def _change(address: str, action: ChangeAction = ChangeAction.CREATE) -> ResourceChange:
    return ResourceChange(address=address, action=action, before={}, after={})


def _entry(address: str, action: ChangeAction = ChangeAction.CREATE) -> DiffEntry:
    return DiffEntry(change=_change(address, action))


def _annotated(
    address: str,
    action: ChangeAction = ChangeAction.CREATE,
    violations: list | None = None,
    risk: RiskScore | None = None,
) -> AnnotatedEntry:
    entry = _entry(address, action)
    return AnnotatedEntry(
        _entry=entry,
        violations=violations or [],
        risk=risk or RiskScore(score=0, reasons=[]),
    )


def test_empty_returns_zero_totals():
    result = build_coverage([])
    assert result.total == 0
    assert result.with_owner == 0
    assert result.owner_pct == 0.0
    assert result.fully_covered is False


def test_owner_pct_with_exact_match():
    entries = [_annotated("aws_s3_bucket.foo"), _annotated("aws_iam_role.bar")]
    owner_map = {"aws_s3_bucket.foo": "team-a"}
    result = build_coverage(entries, owner_map=owner_map)
    assert result.with_owner == 1
    assert result.owner_pct == pytest.approx(50.0)


def test_owner_pct_with_wildcard_match():
    entries = [_annotated("module.vpc.aws_subnet.pub"), _annotated("aws_iam_role.bar")]
    owner_map = {"module.vpc.*": "net-team"}
    result = build_coverage(entries, owner_map=owner_map)
    assert result.with_owner == 1


def test_all_owned_marks_fully_covered_when_policy_covered():
    entries = [_annotated("aws_s3_bucket.x", violations=[])]
    owner_map = {"aws_s3_bucket.x": "team-x"}
    result = build_coverage(entries, owner_map=owner_map)
    assert result.fully_covered is True


def test_risk_counted_when_score_present():
    risk = RiskScore(score=5, reasons=["sensitive"])
    entries = [_annotated("aws_db_instance.prod", risk=risk)]
    result = build_coverage(entries)
    assert result.with_risk == 1
    assert result.risk_pct == pytest.approx(100.0)


def test_uncovered_addresses_listed():
    entries = [
        _annotated("aws_s3_bucket.a"),
        _annotated("aws_iam_role.b"),
    ]
    result = build_coverage(entries, owner_map={})
    assert "aws_s3_bucket.a" in result.uncovered_addresses
    assert "aws_iam_role.b" in result.uncovered_addresses


def test_format_coverage_includes_percentages():
    result = CoverageResult(
        total=4,
        with_owner=2,
        with_policy=4,
        with_risk=3,
        uncovered_addresses=["aws_s3_bucket.x"],
    )
    text = format_coverage(result)
    assert "50.0%" in text
    assert "100.0%" in text
    assert "aws_s3_bucket.x" in text
    assert "4 resources" in text
