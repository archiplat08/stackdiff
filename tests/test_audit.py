"""Tests for stackdiff.audit and stackdiff.audit_report."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from stackdiff.audit import record, load_audit_log, AuditEntry
from stackdiff.audit_report import format_audit_log, destructive_entries
from stackdiff.diff import DiffReport, DiffEntry
from stackdiff.parser import ChangeAction, ResourceChange


def _make_entry(action: ChangeAction) -> DiffEntry:
    rc = ResourceChange(
        address=f"aws_instance.{action.value}",
        module=None,
        resource_type="aws_instance",
        name=action.value,
        action=action,
    )
    return DiffEntry(before=None, after=rc)


@pytest.fixture()
def tmp_audit(tmp_path: Path) -> Path:
    return tmp_path / "audit"


@pytest.fixture()
def sample_report() -> DiffReport:
    return DiffReport(
        entries=[
            _make_entry(ChangeAction.CREATE),
            _make_entry(ChangeAction.DESTROY),
        ]
    )


def test_record_creates_jsonl(tmp_audit: Path, sample_report: DiffReport) -> None:
    log_path = record(sample_report, "plan.txt", tmp_audit)
    assert log_path.exists()
    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["plan_file"] == "plan.txt"
    assert data["summary"]["creates"] == 1
    assert data["summary"]["destroys"] == 1
    assert data["summary"]["has_destructive"] is True


def test_record_appends(tmp_audit: Path, sample_report: DiffReport) -> None:
    record(sample_report, "plan1.txt", tmp_audit)
    record(sample_report, "plan2.txt", tmp_audit)
    log_path = tmp_audit / "audit.jsonl"
    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 2


def test_record_with_tags(tmp_audit: Path, sample_report: DiffReport) -> None:
    record(sample_report, "plan.txt", tmp_audit, tags={"env": "prod", "team": "infra"})
    entries = load_audit_log(tmp_audit)
    assert entries[0].tags == {"env": "prod", "team": "infra"}


def test_load_missing_returns_empty(tmp_audit: Path) -> None:
    assert load_audit_log(tmp_audit) == []


def test_load_audit_log(tmp_audit: Path, sample_report: DiffReport) -> None:
    record(sample_report, "a.txt", tmp_audit)
    record(sample_report, "b.txt", tmp_audit)
    entries = load_audit_log(tmp_audit)
    assert len(entries) == 2
    assert entries[0].plan_file == "a.txt"
    assert entries[1].plan_file == "b.txt"


def test_format_audit_log_empty() -> None:
    result = format_audit_log([])
    assert "No audit entries" in result


def test_format_audit_log_table(tmp_audit: Path, sample_report: DiffReport) -> None:
    record(sample_report, "plan.txt", tmp_audit)
    entries = load_audit_log(tmp_audit)
    table = format_audit_log(entries)
    assert "plan.txt" in table
    assert "YES" in table
    assert "Total entries: 1" in table


def test_destructive_entries_filter(tmp_audit: Path, sample_report: DiffReport) -> None:
    clean_report = DiffReport(entries=[_make_entry(ChangeAction.CREATE)])
    record(sample_report, "destructive.txt", tmp_audit)
    record(clean_report, "clean.txt", tmp_audit)
    entries = load_audit_log(tmp_audit)
    bad = destructive_entries(entries)
    assert len(bad) == 1
    assert bad[0].plan_file == "destructive.txt"
