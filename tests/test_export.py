"""Tests for stackdiff.export module."""
from __future__ import annotations

import csv
import io
import json

import pytest

from stackdiff.diff import DiffEntry, DiffReport
from stackdiff.export import report_to_dict, to_csv, to_json
from stackdiff.parser import ChangeAction


def _make_entry(
    address: str,
    action: ChangeAction,
    resource_type: str = "aws_instance",
    module: str | None = None,
) -> DiffEntry:
    return DiffEntry(
        address=address,
        short_address=address.split(".")[-1],
        resource_type=resource_type,
        module=module,
        action=action,
        before={"instance_type": "t2.micro"} if action != ChangeAction.CREATE else None,
        after={"instance_type": "t3.micro"} if action != ChangeAction.DESTROY else None,
    )


@pytest.fixture()
def sample_report() -> DiffReport:
    return DiffReport(
        entries=[
            _make_entry("aws_instance.web", ChangeAction.CREATE),
            _make_entry("aws_instance.db", ChangeAction.UPDATE),
            _make_entry("aws_instance.old", ChangeAction.DESTROY),
        ]
    )


def test_report_to_dict_structure(sample_report: DiffReport) -> None:
    result = report_to_dict(sample_report)
    assert "summary" in result
    assert "changes" in result
    assert result["summary"]["added"] == 1
    assert result["summary"]["removed"] == 1
    assert result["summary"]["changed"] == 1
    assert result["summary"]["total"] == 3
    assert result["summary"]["has_destructive"] is True


def test_to_json_valid(sample_report: DiffReport) -> None:
    output = to_json(sample_report)
    parsed = json.loads(output)
    assert len(parsed["changes"]) == 3
    actions = [c["action"] for c in parsed["changes"]]
    assert "create" in actions
    assert "update" in actions
    assert "destroy" in actions


def test_to_json_indent(sample_report: DiffReport) -> None:
    output = to_json(sample_report, indent=4)
    assert "    " in output  # 4-space indent present


def test_to_csv_valid(sample_report: DiffReport) -> None:
    output = to_csv(sample_report)
    reader = csv.DictReader(io.StringIO(output))
    rows = list(reader)
    assert len(rows) == 3
    addresses = [r["address"] for r in rows]
    assert "aws_instance.web" in addresses


def test_to_csv_fields(sample_report: DiffReport) -> None:
    output = to_csv(sample_report)
    reader = csv.DictReader(io.StringIO(output))
    assert reader.fieldnames == ["address", "short_address", "resource_type", "module", "action"]


def test_to_csv_empty_report() -> None:
    report = DiffReport(entries=[])
    output = to_csv(report)
    reader = csv.DictReader(io.StringIO(output))
    assert list(reader) == []
