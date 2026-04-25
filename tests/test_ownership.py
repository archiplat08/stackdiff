"""Tests for stackdiff.ownership and stackdiff.ownership_format."""
from __future__ import annotations

import json
import pytest

from stackdiff.diff import DiffEntry, DiffReport
from stackdiff.ownership import build_ownership, OwnershipReport
from stackdiff.ownership_format import (
    format_ownership_text,
    ownership_to_json,
    ownership_to_markdown,
)


def _entry(address: str, action: str = "create") -> DiffEntry:
    from stackdiff.parser import ResourceChange, ChangeAction
    rc = ResourceChange(
        address=address,
        resource_type=address.split(".")[0] if "." in address else "aws_instance",
        name=address.split(".")[-1],
        module=None,
        action=ChangeAction(action),
    )
    return DiffEntry(change=rc)


def _report(*addresses_actions) -> DiffReport:
    entries = [_entry(a, act) for a, act in addresses_actions]
    return DiffReport(entries=entries)


OWNER_MAP = {
    "aws_s3_bucket.logs": {"owner": "alice", "team": "platform"},
    "aws_iam_role.*": {"team": "security"},
}


def test_build_ownership_exact_match():
    report = _report(("aws_s3_bucket.logs", "create"))
    result = build_ownership(report, OWNER_MAP)
    assert len(result.entries) == 1
    e = result.entries[0]
    assert e.owner == "alice"
    assert e.team == "platform"


def test_build_ownership_wildcard_match():
    report = _report(("aws_iam_role.deployer", "create"))
    result = build_ownership(report, OWNER_MAP)
    e = result.entries[0]
    assert e.team == "security"
    assert e.owner is None


def test_build_ownership_no_match():
    report = _report(("aws_lambda_function.handler", "update"))
    result = build_ownership(report, OWNER_MAP)
    e = result.entries[0]
    assert e.owner is None
    assert e.team is None


def test_unowned_returns_entries_without_team_or_owner():
    report = _report(
        ("aws_s3_bucket.logs", "create"),
        ("aws_lambda_function.handler", "create"),
    )
    result = build_ownership(report, OWNER_MAP)
    unowned = result.unowned()
    assert len(unowned) == 1
    assert unowned[0].address == "aws_lambda_function.handler"


def test_by_team_groups_correctly():
    report = _report(
        ("aws_s3_bucket.logs", "create"),
        ("aws_iam_role.ci", "create"),
        ("aws_lambda_function.fn", "create"),
    )
    result = build_ownership(report, OWNER_MAP)
    by_team = result.by_team()
    assert "platform" in by_team
    assert "security" in by_team
    assert "(unowned)" in by_team


def test_format_text_contains_team_header():
    report = _report(("aws_s3_bucket.logs", "create"))
    result = build_ownership(report, OWNER_MAP)
    text = format_ownership_text(result)
    assert "[platform]" in text
    assert "aws_s3_bucket.logs" in text


def test_ownership_to_json_valid():
    report = _report(("aws_s3_bucket.logs", "create"))
    result = build_ownership(report, OWNER_MAP)
    data = json.loads(ownership_to_json(result))
    assert isinstance(data, list)
    assert data[0]["address"] == "aws_s3_bucket.logs"
    assert data[0]["team"] == "platform"


def test_ownership_to_markdown_has_table():
    report = _report(("aws_s3_bucket.logs", "create"))
    result = build_ownership(report, OWNER_MAP)
    md = ownership_to_markdown(result)
    assert "| Address |" in md
    assert "aws_s3_bucket.logs" in md


def test_empty_report_produces_empty_ownership():
    result = build_ownership(DiffReport(entries=[]), OWNER_MAP)
    assert result.entries == []
    assert result.unowned() == []
    assert result.by_team() == {}
