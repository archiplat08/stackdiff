"""Integration tests for the digest CLI subcommand."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from stackdiff.audit import AuditEntry, record
from stackdiff.diff import DiffReport, DiffEntry
from stackdiff.parser import ChangeAction, ResourceChange
from stackdiff.cli_digest import build_parser, _cmd_digest


def _rc(action: ChangeAction, addr: str) -> ResourceChange:
    return ResourceChange(address=addr, action=action, module=None)


def _report(action: ChangeAction, addr: str) -> DiffReport:
    return DiffReport(entries=[DiffEntry(change=_rc(action, addr))])


@pytest.fixture()
def audit_log(tmp_path: Path) -> Path:
    log = tmp_path / "audit.jsonl"
    ts = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
    record(
        log,
        stack="mystack",
        plan_file="plan.txt",
        report=_report(ChangeAction.CREATE, "aws_s3_bucket.x"),
        now=ts,
    )
    record(
        log,
        stack="mystack",
        plan_file="plan.txt",
        report=_report(ChangeAction.DELETE, "aws_db_instance.prod"),
        now=ts,
    )
    return log


def _run(audit_log: Path, *extra: str) -> tuple[int, str]:
    import io, contextlib
    parser = build_parser()
    args = parser.parse_args(["digest", str(audit_log), "--reference", "2024-06-16T00:00:00", *extra])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = _cmd_digest(args)
    return code, buf.getvalue()


def test_digest_exits_zero(audit_log: Path):
    code, _ = _run(audit_log)
    assert code == 0


def test_digest_text_contains_summary(audit_log: Path):
    _, out = _run(audit_log)
    assert "Plans" in out
    assert "Destructive" in out


def test_digest_json_valid(audit_log: Path):
    _, out = _run(audit_log, "--format", "json")
    data = json.loads(out)
    assert data["total_plans"] == 2
    assert data["destructive_plans"] == 1
    assert "mystack" in data["stacks"]


def test_digest_missing_log_exits_one(tmp_path: Path):
    parser = build_parser()
    args = parser.parse_args(["digest", str(tmp_path / "nope.jsonl")])
    assert _cmd_digest(args) == 1


def test_digest_weekly_period(audit_log: Path):
    _, out = _run(audit_log, "--period", "weekly", "--format", "json")
    data = json.loads(out)
    assert data["period"]["label"] == "weekly"
    assert data["total_plans"] == 2
