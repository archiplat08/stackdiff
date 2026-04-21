"""Tests for stackdiff.groupby and cli_groupby."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from stackdiff.parser import ResourceChange, ChangeAction
from stackdiff.diff import DiffEntry, DiffReport
from stackdiff.groupby import group_report, format_grouped, GroupedReport


def _entry(address: str, action: ChangeAction) -> DiffEntry:
    rc = ResourceChange(address=address, action=action)
    return DiffEntry(change=rc)


@pytest.fixture()
def sample_report() -> DiffReport:
    return DiffReport(
        entries=[
            _entry("aws_instance.web", ChangeAction.CREATE),
            _entry("aws_instance.db", ChangeAction.CREATE),
            _entry("module.vpc.aws_subnet.public", ChangeAction.UPDATE),
            _entry("module.vpc.aws_security_group.sg", ChangeAction.DELETE),
            _entry("module.iam.aws_iam_role.role", ChangeAction.CREATE),
        ]
    )


def test_group_by_action(sample_report: DiffReport) -> None:
    grouped = group_report(sample_report, "action")
    assert grouped.dimension == "action"
    assert len(grouped.get("create")) == 3
    assert len(grouped.get("update")) == 1
    assert len(grouped.get("delete")) == 1


def test_group_by_resource_type(sample_report: DiffReport) -> None:
    grouped = group_report(sample_report, "resource_type")
    assert len(grouped.get("aws_instance")) == 2
    assert len(grouped.get("aws_subnet")) == 1
    assert len(grouped.get("aws_security_group")) == 1
    assert len(grouped.get("aws_iam_role")) == 1


def test_group_by_module(sample_report: DiffReport) -> None:
    grouped = group_report(sample_report, "module")
    root = grouped.get("(root)")
    vpc = grouped.get("module.vpc")
    iam = grouped.get("module.iam")
    assert len(root) == 2
    assert len(vpc) == 2
    assert len(iam) == 1


def test_total(sample_report: DiffReport) -> None:
    grouped = group_report(sample_report, "action")
    assert grouped.total() == 5


def test_keys_sorted(sample_report: DiffReport) -> None:
    grouped = group_report(sample_report, "action")
    assert grouped.keys() == sorted(grouped.keys())


def test_format_grouped_contains_dimension(sample_report: DiffReport) -> None:
    grouped = group_report(sample_report, "resource_type")
    text = format_grouped(grouped)
    assert "resource_type" in text
    assert "aws_instance" in text


def test_empty_report() -> None:
    report = DiffReport(entries=[])
    grouped = group_report(report, "action")
    assert grouped.total() == 0
    assert grouped.keys() == []


# --- CLI integration ---

def test_cli_groupby_json(tmp_path: Path) -> None:
    from tests.test_cli_snapshot import _run  # reuse subprocess helper pattern
    plan = tmp_path / "plan.txt"
    # minimal terraform plan text with a create
    plan.write_text(
        "Terraform will perform the following actions:\n\n"
        "  # aws_s3_bucket.logs will be created\n"
        "  + resource \"aws_s3_bucket\" \"logs\" {\n"
        "    }\n\n"
        "Plan: 1 to add, 0 to change, 0 to destroy.\n"
    )
    from stackdiff.cli_groupby import _cmd_groupby
    import argparse

    ns = argparse.Namespace(plan=str(plan), dimension="action", json=True)
    # Should not raise
    ret = _cmd_groupby(ns)
    assert ret == 0


def test_cli_groupby_missing_file(tmp_path: Path) -> None:
    from stackdiff.cli_groupby import _cmd_groupby
    import argparse

    ns = argparse.Namespace(plan=str(tmp_path / "missing.txt"), dimension="action", json=False)
    ret = _cmd_groupby(ns)
    assert ret == 1
