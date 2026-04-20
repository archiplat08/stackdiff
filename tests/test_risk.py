"""Tests for stackdiff.risk module."""
import pytest

from stackdiff.diff import DiffReport, DiffEntry
from stackdiff.parser import ChangeAction
from stackdiff.risk import RiskScore, score_report, format_risk, _score_entry


def _entry(address: str, action: ChangeAction, resource_type: str = "aws_instance") -> DiffEntry:
    return DiffEntry(address=address, action=action, resource_type=resource_type, before={}, after={})


def _report(*entries: DiffEntry) -> DiffReport:
    return DiffReport(entries=list(entries))


# --- RiskScore.level ---

def test_level_none():
    assert RiskScore(total=0).level == "none"


def test_level_low():
    assert RiskScore(total=4).level == "low"


def test_level_medium():
    assert RiskScore(total=15).level == "medium"


def test_level_high():
    assert RiskScore(total=40).level == "high"


def test_level_critical():
    assert RiskScore(total=51).level == "critical"


# --- _score_entry ---

def test_score_create_normal():
    e = _entry("aws_instance.web", ChangeAction.CREATE, "aws_instance")
    assert _score_entry(e) == 1


def test_score_destroy_normal():
    e = _entry("aws_instance.web", ChangeAction.DESTROY, "aws_instance")
    assert _score_entry(e) == 10


def test_score_sensitive_doubles():
    e = _entry("aws_iam_role.admin", ChangeAction.UPDATE, "aws_iam_role")
    assert _score_entry(e) == 6  # 3 * 2


def test_score_sensitive_destroy():
    e = _entry("aws_kms_key.main", ChangeAction.DESTROY, "aws_kms_key")
    assert _score_entry(e) == 20  # 10 * 2


def test_score_noop_is_zero():
    e = _entry("aws_s3_bucket.logs", ChangeAction.NO_OP, "aws_s3_bucket")
    assert _score_entry(e) == 0


# --- score_report ---

def test_empty_report_zero_score():
    risk = score_report(_report())
    assert risk.total == 0
    assert risk.level == "none"
    assert risk.per_entry == []


def test_score_report_accumulates():
    report = _report(
        _entry("aws_instance.a", ChangeAction.CREATE, "aws_instance"),   # 1
        _entry("aws_instance.b", ChangeAction.DESTROY, "aws_instance"),  # 10
    )
    risk = score_report(report)
    assert risk.total == 11
    assert risk.level == "medium"


def test_score_report_per_entry_structure():
    report = _report(_entry("aws_iam_role.r", ChangeAction.REPLACE, "aws_iam_role"))
    risk = score_report(report)
    assert len(risk.per_entry) == 1
    item = risk.per_entry[0]
    assert item["address"] == "aws_iam_role.r"
    assert item["action"] == "replace"
    assert item["sensitive"] is True
    assert item["score"] == 14  # 7 * 2


# --- format_risk ---

def test_format_risk_contains_level():
    risk = RiskScore(total=5, per_entry=[{"address": "a.b", "action": "create", "score": 5, "sensitive": False}])
    out = format_risk(risk)
    assert "LOW" in out
    assert "a.b" in out
    assert "score=5" in out


def test_format_risk_sensitive_flag():
    risk = RiskScore(total=20, per_entry=[{"address": "aws_kms_key.k", "action": "destroy", "score": 20, "sensitive": True}])
    out = format_risk(risk)
    assert "[sensitive]" in out
