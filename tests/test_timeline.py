"""Tests for stackdiff.timeline."""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from stackdiff.timeline import (
    TimelineEvent,
    TimelineReport,
    build_timeline,
    format_timeline,
)


def _audit_entry(stack: str, ts: datetime, changes: list) -> MagicMock:
    entry = MagicMock()
    entry.stack = stack
    entry.recorded_at = ts.isoformat()
    entry.report = {"entries": changes}
    return entry


BASE_TS = datetime(2024, 6, 1, 12, 0, 0)


def _change(action: str, address: str, risk: str = None, violations: list = None):
    return {
        "action": action,
        "address": address,
        "risk_level": risk,
        "violations": violations or [],
    }


def test_build_timeline_empty():
    report = build_timeline([])
    assert report.total == 0
    assert report.events == []


def test_build_timeline_single_entry():
    entry = _audit_entry("prod", BASE_TS, [_change("create", "aws_s3_bucket.x")])
    report = build_timeline([entry])
    assert report.total == 1
    ev = report.events[0]
    assert ev.stack == "prod"
    assert ev.action == "create"
    assert ev.address == "aws_s3_bucket.x"


def test_build_timeline_sorted_chronologically():
    e1 = _audit_entry("prod", BASE_TS + timedelta(hours=2), [_change("update", "aws_instance.b")])
    e2 = _audit_entry("staging", BASE_TS, [_change("create", "aws_instance.a")])
    report = build_timeline([e1, e2])
    assert report.events[0].address == "aws_instance.a"
    assert report.events[1].address == "aws_instance.b"


def test_by_stack_filters_correctly():
    e1 = _audit_entry("prod", BASE_TS, [_change("create", "res.a")])
    e2 = _audit_entry("dev", BASE_TS, [_change("delete", "res.b")])
    report = build_timeline([e1, e2])
    prod_events = report.by_stack("prod")
    assert len(prod_events) == 1
    assert prod_events[0].address == "res.a"


def test_in_range_filters_correctly():
    e1 = _audit_entry("prod", BASE_TS, [_change("create", "res.a")])
    e2 = _audit_entry("prod", BASE_TS + timedelta(days=2), [_change("delete", "res.b")])
    report = build_timeline([e1, e2])
    start = BASE_TS - timedelta(hours=1)
    end = BASE_TS + timedelta(hours=1)
    in_range = report.in_range(start, end)
    assert len(in_range) == 1
    assert in_range[0].address == "res.a"


def test_risky_returns_medium_and_above():
    e = _audit_entry("prod", BASE_TS, [
        _change("create", "res.a", risk="low"),
        _change("delete", "res.b", risk="critical"),
        _change("update", "res.c", risk="medium"),
    ])
    report = build_timeline([e])
    risky = report.risky()
    assert len(risky) == 2
    assert all(ev.risk_level in ("medium", "critical") for ev in risky)


def test_with_violations_filters_correctly():
    e = _audit_entry("prod", BASE_TS, [
        _change("create", "res.a", violations=[]),
        _change("delete", "res.b", violations=[{"rule": "no_delete"}]),
    ])
    report = build_timeline([e])
    violating = report.with_violations()
    assert len(violating) == 1
    assert violating[0].address == "res.b"


def test_format_timeline_empty():
    report = TimelineReport()
    output = format_timeline(report)
    assert "No timeline events" in output


def test_format_timeline_includes_headers():
    e = _audit_entry("prod", BASE_TS, [_change("create", "aws_s3_bucket.x", risk="low")])
    report = build_timeline([e])
    output = format_timeline(report)
    assert "Timestamp" in output
    assert "aws_s3_bucket.x" in output
    assert "low" in output


def test_format_timeline_truncates_at_max_rows():
    changes = [_change("create", f"res.{i}") for i in range(10)]
    e = _audit_entry("prod", BASE_TS, changes)
    report = build_timeline([e])
    output = format_timeline(report, max_rows=3)
    assert "7 more events" in output
