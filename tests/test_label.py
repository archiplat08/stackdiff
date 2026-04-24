"""Tests for stackdiff.label and stackdiff.cli_label."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from stackdiff.diff import DiffEntry, DiffReport
from stackdiff.label import (
    LabelMap,
    LabeledEntry,
    LabeledReport,
    apply_labels,
    format_labeled_report,
)


def _entry(address: str, action: str = "create") -> DiffEntry:
    return DiffEntry(address=address, action=action, before=None, after={})


def _report(*addresses_actions) -> DiffReport:
    entries = [_entry(a, act) for a, act in addresses_actions]
    return DiffReport(entries=entries)


# ---------------------------------------------------------------------------
# apply_labels
# ---------------------------------------------------------------------------

def test_apply_labels_empty_map():
    report = _report(("aws_s3_bucket.x", "create"))
    result = apply_labels(report, {})
    assert len(result.entries) == 1
    assert result.entries[0].labels == {}


def test_apply_labels_attaches_metadata():
    report = _report(("aws_s3_bucket.x", "create"), ("aws_iam_role.y", "delete"))
    lmap: LabelMap = {"aws_s3_bucket.x": {"team": "platform", "env": "prod"}}
    result = apply_labels(report, lmap)
    assert result.entries[0].get("team") == "platform"
    assert result.entries[0].get("env") == "prod"
    assert result.entries[1].labels == {}


def test_apply_labels_unknown_address_gets_empty():
    report = _report(("module.vpc.aws_vpc.main", "update"))
    result = apply_labels(report, {"other.resource": {"k": "v"}})
    assert result.entries[0].labels == {}


# ---------------------------------------------------------------------------
# LabeledEntry helpers
# ---------------------------------------------------------------------------

def test_has_label_key_only():
    e = LabeledEntry(entry=_entry("a"), labels={"team": "sre"})
    assert e.has_label("team") is True
    assert e.has_label("owner") is False


def test_has_label_key_and_value():
    e = LabeledEntry(entry=_entry("a"), labels={"env": "staging"})
    assert e.has_label("env", "staging") is True
    assert e.has_label("env", "prod") is False


# ---------------------------------------------------------------------------
# LabeledReport helpers
# ---------------------------------------------------------------------------

def test_filter_by_label_returns_matching():
    report = _report(("a", "create"), ("b", "delete"), ("c", "update"))
    lmap: LabelMap = {"a": {"critical": "true"}, "c": {"critical": "true"}}
    labeled = apply_labels(report, lmap)
    filtered = labeled.filter_by_label("critical", "true")
    assert len(filtered.entries) == 2
    assert {e.address for e in filtered.entries} == {"a", "c"}


def test_all_label_keys():
    report = _report(("a", "create"), ("b", "delete"))
    lmap: LabelMap = {"a": {"team": "x", "env": "prod"}, "b": {"team": "y"}}
    labeled = apply_labels(report, lmap)
    assert labeled.all_label_keys() == ["env", "team"]


# ---------------------------------------------------------------------------
# format_labeled_report
# ---------------------------------------------------------------------------

def test_format_empty_report():
    assert format_labeled_report(LabeledReport()) == "(no entries)"


def test_format_includes_address_and_action():
    report = _report(("aws_s3_bucket.logs", "create"))
    labeled = apply_labels(report, {})
    out = format_labeled_report(labeled)
    assert "aws_s3_bucket.logs" in out
    assert "create" in out


def test_format_includes_labels():
    report = _report(("aws_s3_bucket.logs", "create"))
    labeled = apply_labels(report, {"aws_s3_bucket.logs": {"env": "prod"}})
    out = format_labeled_report(labeled)
    assert "env=prod" in out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@pytest.fixture()
def plan_dir(tmp_path: Path) -> Path:
    return tmp_path


PLAN_TEXT = """
Terraform will perform the following actions:

  # aws_s3_bucket.data will be created
  + resource "aws_s3_bucket" "data" {
    }

Plan: 1 to add, 0 to change, 0 to destroy.
"""


def _run(args, capsys):
    from stackdiff.cli_label import _cmd_label, build_parser
    parser = build_parser()
    parsed = parser.parse_args(args)
    code = _cmd_label(parsed)
    return code, capsys.readouterr()


def test_cli_label_no_labels_exits_zero(plan_dir, capsys):
    plan_file = plan_dir / "plan.txt"
    plan_file.write_text(PLAN_TEXT)
    code, _ = _run(["label", str(plan_file)], capsys)
    assert code == 0


def test_cli_label_with_labels_file(plan_dir, capsys):
    plan_file = plan_dir / "plan.txt"
    plan_file.write_text(PLAN_TEXT)
    labels_file = plan_dir / "labels.json"
    labels_file.write_text(json.dumps({"aws_s3_bucket.data": {"team": "data-eng"}}))
    code, out = _run(["label", str(plan_file), "--labels", str(labels_file)], capsys)
    assert code == 0
    assert "team=data-eng" in out.out


def test_cli_label_invalid_labels_file(plan_dir, capsys):
    plan_file = plan_dir / "plan.txt"
    plan_file.write_text(PLAN_TEXT)
    labels_file = plan_dir / "labels.json"
    labels_file.write_text(json.dumps(["not", "a", "dict"]))
    code, _ = _run(["label", str(plan_file), "--labels", str(labels_file)], capsys)
    assert code == 1
