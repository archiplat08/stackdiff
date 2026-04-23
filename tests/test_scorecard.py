"""Tests for stackdiff.scorecard and cli_scorecard."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from stackdiff.diff import DiffEntry, DiffReport
from stackdiff.parser import ChangeAction
from stackdiff.risk import RiskScore, score_report
from stackdiff.policy import PolicyResult, PolicyViolation, PolicyRule
from stackdiff.threshold import ThresholdResult, ThresholdViolation
from stackdiff.impact import ImpactResult, ImpactLevel
from stackdiff.scorecard import build_scorecard, format_scorecard, ScorecardResult


def _entry(action: ChangeAction, rtype: str = "aws_instance", name: str = "web") -> DiffEntry:
    return DiffEntry(address=f"{rtype}.{name}", action=action, resource_type=rtype, module=None, before={}, after={})


def _report(*entries: DiffEntry) -> DiffReport:
    return DiffReport(entries=list(entries))


# --- unit tests for scorecard logic ---

def test_grade_a_for_clean_plan():
    risk = RiskScore(total=0, by_resource={})
    sc = build_scorecard(risk)
    assert sc.grade == "A"
    assert sc.healthy is True


def test_grade_degrades_with_high_risk():
    risk = RiskScore(total=80, by_resource={})
    sc = build_scorecard(risk)
    assert sc.grade in ("C", "D", "F")
    assert sc.healthy is False


def test_grade_f_for_critical_risk_and_policy_blocks():
    risk = RiskScore(total=120, by_resource={})
    rule = PolicyRule(name="no_destroy", severity="block", action="delete", resource_type=None)
    violation = PolicyViolation(rule=rule, entry=_entry(ChangeAction.DELETE))
    policy = PolicyResult(violations=[violation, violation])
    sc = build_scorecard(risk, policy=policy)
    assert sc.grade == "F"


def test_notes_include_policy_violations():
    risk = RiskScore(total=5, by_resource={})
    rule = PolicyRule(name="no_destroy", severity="block", action="delete", resource_type=None)
    violation = PolicyViolation(rule=rule, entry=_entry(ChangeAction.DELETE))
    policy = PolicyResult(violations=[violation])
    sc = build_scorecard(risk, policy=policy)
    assert any("policy" in n for n in sc.notes)


def test_notes_include_threshold_violations():
    risk = RiskScore(total=5, by_resource={})
    tv = ThresholdViolation(kind="risk_score", limit=10, actual=50)
    threshold = ThresholdResult(violations=[tv])
    sc = build_scorecard(risk, threshold=threshold)
    assert any("threshold" in n for n in sc.notes)


def test_format_scorecard_contains_grade():
    risk = RiskScore(total=0, by_resource={})
    sc = build_scorecard(risk)
    out = format_scorecard(sc)
    assert "Grade" in out
    assert "A" in out


def test_format_scorecard_shows_impact():
    risk = RiskScore(total=0, by_resource={})
    impact = ImpactResult(level=ImpactLevel.HIGH, reasons=["multiple destroys"])
    sc = build_scorecard(risk, impact=impact)
    out = format_scorecard(sc)
    assert "high" in out.lower()


# --- integration: CLI command ---

def test_cli_scorecard_exits_zero_for_safe_plan(tmp_path: Path):
    plan = tmp_path / "plan.txt"
    plan.write_text("No changes. Infrastructure is up-to-date.\n")
    from stackdiff.cli_scorecard import _cmd_scorecard
    args = MagicMock(plan=str(plan), policy=None, max_risk=None, max_deletes=None, json=False)
    rc = _cmd_scorecard(args)
    assert rc == 0


def test_cli_scorecard_returns_json(tmp_path: Path):
    plan = tmp_path / "plan.txt"
    plan.write_text("No changes. Infrastructure is up-to-date.\n")
    from stackdiff.cli_scorecard import _cmd_scorecard
    args = MagicMock(plan=str(plan), policy=None, max_risk=None, max_deletes=None, json=True)
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = _cmd_scorecard(args)
    data = json.loads(buf.getvalue())
    assert "grade" in data
    assert "healthy" in data


def test_cli_scorecard_missing_file_returns_one(tmp_path: Path):
    from stackdiff.cli_scorecard import _cmd_scorecard
    args = MagicMock(plan=str(tmp_path / "missing.txt"), policy=None, max_risk=None, max_deletes=None, json=False)
    rc = _cmd_scorecard(args)
    assert rc == 1
