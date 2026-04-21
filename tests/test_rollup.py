"""Tests for stackdiff.rollup and stackdiff.cli_rollup."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from stackdiff.diff import DiffReport, DiffEntry
from stackdiff.parser import ChangeAction, ResourceChange
from stackdiff.rollup import build_rollup, format_rollup, RollupReport


def _entry(action: ChangeAction, rtype: str = "aws_instance", name: str = "main") -> DiffEntry:
    rc = ResourceChange(
        address=f"{rtype}.{name}",
        module=None,
        resource_type=rtype,
        resource_name=name,
        action=action,
        before={},
        after={},
    )
    return DiffEntry(resource=rc)


def _report(*actions: ChangeAction) -> DiffReport:
    entries = [_entry(a, name=f"r{i}") for i, a in enumerate(actions)]
    return DiffReport(entries=entries)


# ---------------------------------------------------------------------------
# build_rollup
# ---------------------------------------------------------------------------

def test_build_rollup_empty():
    rollup = build_rollup({})
    assert rollup.entries == []
    assert rollup.total_creates == 0
    assert rollup.max_risk_score == 0
    assert rollup.any_destructive is False


def test_build_rollup_single_stack():
    rollup = build_rollup({"prod": _report(ChangeAction.CREATE)})
    assert len(rollup.entries) == 1
    assert rollup.entries[0].stack_name == "prod"
    assert rollup.total_creates == 1
    assert rollup.total_deletes == 0


def test_build_rollup_aggregates_totals():
    reports = {
        "prod": _report(ChangeAction.CREATE, ChangeAction.DELETE),
        "staging": _report(ChangeAction.UPDATE, ChangeAction.CREATE),
    }
    rollup = build_rollup(reports)
    assert rollup.total_creates == 2
    assert rollup.total_updates == 1
    assert rollup.total_deletes == 1


def test_build_rollup_any_destructive_true():
    reports = {
        "safe": _report(ChangeAction.CREATE),
        "risky": _report(ChangeAction.DELETE),
    }
    rollup = build_rollup(reports)
    assert rollup.any_destructive is True


def test_build_rollup_any_destructive_false():
    reports = {"safe": _report(ChangeAction.CREATE, ChangeAction.UPDATE)}
    rollup = build_rollup(reports)
    assert rollup.any_destructive is False


def test_max_risk_score_is_maximum_across_stacks():
    reports = {
        "low": _report(ChangeAction.CREATE),
        "high": _report(ChangeAction.DELETE, ChangeAction.REPLACE),
    }
    rollup = build_rollup(reports)
    assert rollup.max_risk_score >= rollup.entries[0].risk.score


# ---------------------------------------------------------------------------
# format_rollup
# ---------------------------------------------------------------------------

def test_format_rollup_empty():
    result = format_rollup(RollupReport())
    assert "No stacks" in result


def test_format_rollup_contains_stack_name():
    rollup = build_rollup({"my-stack": _report(ChangeAction.CREATE)})
    output = format_rollup(rollup)
    assert "my-stack" in output


def test_format_rollup_contains_total_row():
    rollup = build_rollup({"a": _report(ChangeAction.CREATE), "b": _report(ChangeAction.UPDATE)})
    output = format_rollup(rollup)
    assert "TOTAL" in output


def test_format_rollup_destructive_warning():
    rollup = build_rollup({"x": _report(ChangeAction.DELETE)})
    output = format_rollup(rollup)
    assert "destructive" in output.lower()


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------

PLAN_CREATE = textwrap.dedent("""\
    Terraform will perform the following actions:

      # aws_instance.web will be created
      + resource "aws_instance" "web" {
        }

    Plan: 1 to add, 0 to change, 0 to destroy.
""")

PLAN_DELETE = textwrap.dedent("""\
    Terraform will perform the following actions:

      # aws_s3_bucket.data will be destroyed
      - resource "aws_s3_bucket" "data" {
        }

    Plan: 0 to add, 0 to change, 1 to destroy.
""")


def test_cli_rollup_exits_zero(tmp_path: Path):
    from stackdiff.cli_rollup import _cmd_rollup
    import argparse

    f = tmp_path / "plan.txt"
    f.write_text(PLAN_CREATE)
    args = argparse.Namespace(plans=[f"prod={f}"], fail_on_destructive=False, max_risk=None)
    assert _cmd_rollup(args) == 0


def test_cli_rollup_fail_on_destructive(tmp_path: Path):
    from stackdiff.cli_rollup import _cmd_rollup
    import argparse

    f = tmp_path / "plan.txt"
    f.write_text(PLAN_DELETE)
    args = argparse.Namespace(plans=[f"prod={f}"], fail_on_destructive=True, max_risk=None)
    assert _cmd_rollup(args) == 2


def test_cli_rollup_bad_pair_returns_one(tmp_path: Path):
    from stackdiff.cli_rollup import _cmd_rollup
    import argparse

    args = argparse.Namespace(plans=["noequalssign"], fail_on_destructive=False, max_risk=None)
    assert _cmd_rollup(args) == 1


def test_cli_rollup_missing_file_returns_one(tmp_path: Path):
    from stackdiff.cli_rollup import _cmd_rollup
    import argparse

    args = argparse.Namespace(
        plans=["prod=/nonexistent/path/plan.txt"], fail_on_destructive=False, max_risk=None
    )
    assert _cmd_rollup(args) == 1
