"""Tests for stackdiff.maturity."""
from __future__ import annotations

import pytest

from stackdiff.annotate import AnnotatedEntry
from stackdiff.diff import DiffEntry
from stackdiff.parser import ChangeAction, ResourceChange
from stackdiff.risk import RiskScore
from stackdiff.policy import PolicyViolation
from stackdiff.maturity import assess_maturity, format_maturity, _grade


def _rc(action: ChangeAction, rtype: str = "aws_s3_bucket", name: str = "b") -> ResourceChange:
    return ResourceChange(
        address=f"{rtype}.{name}",
        module=None,
        resource_type=rtype,
        name=name,
        action=action,
    )


def _entry(
    action: ChangeAction = ChangeAction.UPDATE,
    owner: str | None = "team-a",
    risk_level: str = "low",
    violations: int = 0,
) -> AnnotatedEntry:
    rc = _rc(action)
    diff = DiffEntry(before=None, after=rc, action=action)
    viols = [
        PolicyViolation(rule_id="r1", message="msg", severity="warn")
        for _ in range(violations)
    ]
    risk = RiskScore(score=5 if risk_level == "low" else 50, level=risk_level, reasons=[])
    return AnnotatedEntry(
        entry=diff,
        risk=risk,
        violations=viols,
        labels={},
        owner=owner,
    )


# ---------------------------------------------------------------------------
# _grade
# ---------------------------------------------------------------------------

def test_grade_a():
    assert _grade(95.0) == "A"

def test_grade_b():
    assert _grade(80.0) == "B"

def test_grade_c():
    assert _grade(65.0) == "C"

def test_grade_d():
    assert _grade(45.0) == "D"

def test_grade_f():
    assert _grade(30.0) == "F"


# ---------------------------------------------------------------------------
# assess_maturity – edge cases
# ---------------------------------------------------------------------------

def test_empty_entries_returns_perfect_score():
    result = assess_maturity([])
    assert result.score == 100.0
    assert result.grade == "A"
    assert result.total == 0


def test_fully_mature_entries():
    entries = [_entry(owner="team-a", risk_level="low", violations=0) for _ in range(4)]
    result = assess_maturity(entries)
    assert result.owned == 4
    assert result.violations == 0
    assert result.score >= 75.0
    assert result.grade in ("A", "B")


def test_no_owner_lowers_score():
    entries = [_entry(owner=None, risk_level="low", violations=0) for _ in range(4)]
    result = assess_maturity(entries)
    assert result.owned == 0
    assert result.score < 90.0
    assert "owner" in " ".join(result.notes).lower()


def test_violations_penalise_score():
    entries = [_entry(owner="team-a", risk_level="low", violations=3) for _ in range(4)]
    result = assess_maturity(entries)
    assert result.violations == 12
    assert result.score < 80.0


def test_high_risk_lowers_score():
    entries = [_entry(owner="team-a", risk_level="high", violations=0) for _ in range(4)]
    result = assess_maturity(entries)
    assert result.low_risk == 0
    assert result.score < 90.0


def test_score_clamped_to_zero_on_many_violations():
    entries = [_entry(owner=None, risk_level="high", violations=10) for _ in range(5)]
    result = assess_maturity(entries)
    assert result.score >= 0.0


# ---------------------------------------------------------------------------
# format_maturity
# ---------------------------------------------------------------------------

def test_format_maturity_contains_grade():
    result = assess_maturity([_entry()])
    text = format_maturity(result)
    assert result.grade in text


def test_format_maturity_contains_notes_when_present():
    entries = [_entry(owner=None, risk_level="high", violations=1)]
    result = assess_maturity(entries)
    text = format_maturity(result)
    assert "Notes:" in text
    assert "•" in text


def test_format_maturity_no_notes_section_when_clean():
    entries = [_entry(owner="team-a", risk_level="low", violations=0)]
    result = assess_maturity(entries)
    text = format_maturity(result)
    # notes list may be empty → no "Notes:" header
    if not result.notes:
        assert "Notes:" not in text
