"""Tests for stackdiff.digest and stackdiff.digest_format."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from stackdiff.diff import DiffReport, DiffEntry
from stackdiff.parser import ChangeAction, ResourceChange
from stackdiff.audit import AuditEntry
from stackdiff.digest import build_digest, _period_for, DigestReport
from stackdiff.digest_format import format_digest, digest_to_dict


def _rc(action: ChangeAction, addr: str) -> ResourceChange:
    return ResourceChange(address=addr, action=action, module=None)


def _entry(
    action: ChangeAction,
    addr: str,
    stack: str = "stack-a",
    recorded_at: datetime | None = None,
) -> AuditEntry:
    rc = _rc(action, addr)
    report = DiffReport(entries=[DiffEntry(change=rc)])
    ts = recorded_at or datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    return AuditEntry(stack=stack, plan_file="plan.txt", report=report, recorded_at=ts)


REF = datetime(2024, 6, 16, 0, 0, 0, tzinfo=timezone.utc)


def test_period_daily_boundaries():
    p = _period_for("daily", REF)
    assert p.start == datetime(2024, 6, 15, 0, 0, 0, tzinfo=timezone.utc)
    assert p.end == datetime(2024, 6, 16, 0, 0, 0, tzinfo=timezone.utc)


def test_period_weekly_boundaries():
    p = _period_for("weekly", REF)
    assert p.start == datetime(2024, 6, 9, 0, 0, 0, tzinfo=timezone.utc)
    assert p.end == datetime(2024, 6, 16, 0, 0, 0, tzinfo=timezone.utc)


def test_period_unknown_raises():
    with pytest.raises(ValueError, match="Unknown period"):
        _period_for("monthly", REF)


def test_build_digest_empty():
    digest = build_digest([], label="daily", reference=REF)
    assert digest.total_plans == 0
    assert digest.total_creates == 0
    assert digest.destructive_plans == 0
    assert digest.stacks == []


def test_build_digest_filters_outside_window():
    outside = _entry(
        ChangeAction.CREATE, "aws_s3_bucket.old",
        recorded_at=datetime(2024, 6, 13, 10, 0, 0, tzinfo=timezone.utc),
    )
    digest = build_digest([outside], label="daily", reference=REF)
    assert digest.total_plans == 0


def test_build_digest_counts_creates():
    e = _entry(ChangeAction.CREATE, "aws_s3_bucket.b",
               recorded_at=datetime(2024, 6, 15, 8, 0, 0, tzinfo=timezone.utc))
    digest = build_digest([e], label="daily", reference=REF)
    assert digest.total_plans == 1
    assert digest.total_creates == 1
    assert digest.total_deletes == 0


def test_build_digest_destructive_flagged():
    e = _entry(ChangeAction.DELETE, "aws_db_instance.prod",
               recorded_at=datetime(2024, 6, 15, 9, 0, 0, tzinfo=timezone.utc))
    digest = build_digest([e], label="daily", reference=REF)
    assert digest.destructive_plans == 1


def test_build_digest_collects_stacks():
    e1 = _entry(ChangeAction.CREATE, "r.a", stack="alpha",
                recorded_at=datetime(2024, 6, 15, 1, 0, 0, tzinfo=timezone.utc))
    e2 = _entry(ChangeAction.UPDATE, "r.b", stack="beta",
                recorded_at=datetime(2024, 6, 15, 2, 0, 0, tzinfo=timezone.utc))
    digest = build_digest([e1, e2], label="daily", reference=REF)
    assert sorted(digest.stacks) == ["alpha", "beta"]


def test_format_digest_contains_period_label():
    digest = build_digest([], label="weekly", reference=REF)
    text = format_digest(digest, color=False)
    assert "Weekly" in text


def test_digest_to_dict_structure():
    e = _entry(ChangeAction.CREATE, "aws_instance.web",
               recorded_at=datetime(2024, 6, 15, 6, 0, 0, tzinfo=timezone.utc))
    digest = build_digest([e], label="daily", reference=REF)
    d = digest_to_dict(digest)
    assert d["period"]["label"] == "daily"
    assert d["total_plans"] == 1
    assert "top_risk_score" in d
