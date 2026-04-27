"""Tests for stackdiff.quarantine and stackdiff.cli_quarantine."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from stackdiff.annotate import AnnotatedEntry
from stackdiff.diff import ChangeAction
from stackdiff.quarantine import (
    QuarantineRule,
    QuarantineResult,
    _matches_rule,
    apply_quarantine,
    format_quarantine_text,
)
from stackdiff.risk import RiskScore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _annotated(address: str, action: str, risk_score: int) -> AnnotatedEntry:
    entry = MagicMock(spec=AnnotatedEntry)
    entry.address = address
    mock_action = MagicMock()
    mock_action.value = action
    entry.action = mock_action
    mock_risk = MagicMock(spec=RiskScore)
    mock_risk.score = risk_score
    entry.risk = mock_risk
    entry.violations = []
    return entry


# ---------------------------------------------------------------------------
# Unit tests — QuarantineResult
# ---------------------------------------------------------------------------

def test_result_is_clean_when_empty():
    r = QuarantineResult()
    assert r.is_clean
    assert r.total_quarantined == 0
    assert r.total_allowed == 0


def test_result_not_clean_with_quarantined():
    e = _annotated("aws_s3_bucket.b", "delete", 70)
    r = QuarantineResult(quarantined=[e])
    assert not r.is_clean
    assert r.total_quarantined == 1


# ---------------------------------------------------------------------------
# Unit tests — _matches_rule
# ---------------------------------------------------------------------------

def test_matches_rule_min_risk_pass():
    rule = QuarantineRule(min_risk_score=50)
    e = _annotated("aws_iam_role.r", "create", 60)
    assert _matches_rule(e, rule)


def test_matches_rule_min_risk_fail():
    rule = QuarantineRule(min_risk_score=80)
    e = _annotated("aws_iam_role.r", "create", 40)
    assert not _matches_rule(e, rule)


def test_matches_rule_action_match():
    rule = QuarantineRule(actions=["delete"])
    e = _annotated("aws_s3_bucket.b", "delete", 0)
    assert _matches_rule(e, rule)


def test_matches_rule_action_no_match():
    rule = QuarantineRule(actions=["delete"])
    e = _annotated("aws_s3_bucket.b", "create", 0)
    assert not _matches_rule(e, rule)


def test_matches_rule_combined_all_must_pass():
    rule = QuarantineRule(min_risk_score=50, actions=["delete"])
    e_ok = _annotated("aws_s3_bucket.b", "delete", 60)
    e_low_risk = _annotated("aws_s3_bucket.b", "delete", 10)
    e_wrong_action = _annotated("aws_s3_bucket.b", "create", 60)
    assert _matches_rule(e_ok, rule)
    assert not _matches_rule(e_low_risk, rule)
    assert not _matches_rule(e_wrong_action, rule)


# ---------------------------------------------------------------------------
# Unit tests — apply_quarantine
# ---------------------------------------------------------------------------

def test_apply_quarantine_empty_rules_allows_all():
    entries = [_annotated("aws_s3_bucket.b", "delete", 90)]
    result = apply_quarantine(entries, [])
    assert result.total_allowed == 1
    assert result.total_quarantined == 0


def test_apply_quarantine_partitions_correctly():
    safe = _annotated("aws_s3_bucket.safe", "create", 5)
    risky = _annotated("aws_iam_role.admin", "delete", 80)
    rule = QuarantineRule(min_risk_score=50)
    result = apply_quarantine([safe, risky], [rule])
    assert result.total_quarantined == 1
    assert result.total_allowed == 1
    assert result.quarantined[0].address == "aws_iam_role.admin"


# ---------------------------------------------------------------------------
# Unit tests — format_quarantine_text
# ---------------------------------------------------------------------------

def test_format_quarantine_text_clean():
    result = QuarantineResult(allowed=[_annotated("aws_s3_bucket.b", "create", 5)])
    text = format_quarantine_text(result)
    assert "0 quarantined" in text
    assert "1 allowed" in text


def test_format_quarantine_text_lists_quarantined():
    e = _annotated("aws_iam_role.admin", "delete", 90)
    result = QuarantineResult(quarantined=[e])
    text = format_quarantine_text(result)
    assert "aws_iam_role.admin" in text
    assert "delete" in text
    assert "risk=90" in text
