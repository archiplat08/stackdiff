"""Tests for stackdiff.impact and stackdiff.cli_impact."""
from __future__ import annotations

import json
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

from stackdiff.diff import DiffEntry, DiffReport
from stackdiff.parser import ChangeAction
from stackdiff.impact import classify_impact, format_impact, ImpactLevel


def _entry(action: ChangeAction, rtype: str = "aws_s3_bucket", name: str = "b") -> DiffEntry:
    from stackdiff.parser import ResourceChange
    rc = ResourceChange(
        address=f"{rtype}.{name}",
        module=None,
        resource_type=rtype,
        name=name,
        action=action,
    )
    return DiffEntry(resource=rc, before=None, after=None)


def _report(*entries: DiffEntry) -> DiffReport:
    return DiffReport(entries=list(entries))


# --- unit tests ---

def test_empty_report_is_none():
    result = classify_impact(_report())
    assert result.level == ImpactLevel.NONE
    assert result.total_changes == 0
    assert not result.destructive


def test_single_create_is_low():
    result = classify_impact(_report(_entry(ChangeAction.CREATE)))
    assert result.level == ImpactLevel.LOW
    assert not result.destructive


def test_single_destroy_is_medium():
    result = classify_impact(_report(_entry(ChangeAction.DELETE)))
    assert result.level in (ImpactLevel.MEDIUM, ImpactLevel.HIGH)
    assert result.destructive


def test_many_destroys_is_critical():
    entries = [_entry(ChangeAction.DELETE, name=str(i)) for i in range(6)]
    result = classify_impact(_report(*entries))
    assert result.level == ImpactLevel.CRITICAL


def test_replace_sensitive_resource_raises_level():
    entry = _entry(ChangeAction.REPLACE, rtype="aws_iam_role", name="admin")
    result = classify_impact(_report(entry))
    # sensitive resource + replace → at least HIGH
    assert result.level in (ImpactLevel.HIGH, ImpactLevel.CRITICAL)


def test_format_impact_contains_level():
    result = classify_impact(_report(_entry(ChangeAction.CREATE)))
    text = format_impact(result)
    assert "LOW" in text or "MEDIUM" in text or "HIGH" in text or "NONE" in text
    assert "risk_score" in text


# --- CLI tests ---

@pytest.fixture()
def plan_dir(tmp_path: Path) -> Path:
    return tmp_path


def _write(path: Path, content: str) -> Path:
    path.write_text(textwrap.dedent(content))
    return path


def _run(args: list[str]) -> int:
    from stackdiff.cli_impact import build_parser, _cmd_impact
    parser = build_parser()
    parsed = parser.parse_args(args)
    return _cmd_impact(parsed)


PLAN_CREATE = """\
  # aws_s3_bucket.example will be created
  + resource "aws_s3_bucket" "example" {
    }
Plan: 1 to add, 0 to change, 0 to destroy.
"""

PLAN_DESTROY = """\
  # aws_s3_bucket.example will be destroyed
  - resource "aws_s3_bucket" "example" {
    }
Plan: 0 to add, 0 to change, 1 to destroy.
"""


def test_impact_create_exits_zero(plan_dir: Path) -> None:
    f = _write(plan_dir / "plan.txt", PLAN_CREATE)
    assert _run(["impact", str(f)]) == 0


def test_impact_missing_file_exits_one(plan_dir: Path) -> None:
    assert _run(["impact", str(plan_dir / "missing.txt")]) == 1


def test_impact_min_level_triggers_exit_two(plan_dir: Path) -> None:
    f = _write(plan_dir / "plan.txt", PLAN_DESTROY)
    code = _run(["impact", str(f), "--min-level", "low"])
    assert code == 2


def test_impact_json_output(plan_dir: Path, capsys: pytest.CaptureFixture) -> None:
    f = _write(plan_dir / "plan.txt", PLAN_CREATE)
    _run(["impact", str(f), "--json"])
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "level" in data
    assert "risk_score" in data
    assert "total_changes" in data
