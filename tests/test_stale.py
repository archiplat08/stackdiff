"""Tests for stackdiff.stale."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from stackdiff.diff import DiffReport
from stackdiff.snapshot import Snapshot
from stackdiff.stale import (
    StaleEntry,
    StaleReport,
    check_stale,
    format_stale_text,
)


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _snap(name: str, age_days: float, stack: str | None = None) -> Snapshot:
    created_at = _now() - timedelta(days=age_days)
    return Snapshot(
        name=name,
        stack=stack,
        created_at=created_at,
        report=DiffReport(entries=[]),
    )


# ---------------------------------------------------------------------------
# StaleReport helpers
# ---------------------------------------------------------------------------

def test_stale_report_stale_property():
    report = StaleReport(
        entries=[
            StaleEntry("a", None, _now(), 5.0, False),
            StaleEntry("b", None, _now(), 40.0, True),
        ],
        threshold_days=30,
    )
    assert len(report.stale) == 1
    assert report.stale[0].name == "b"


def test_stale_report_fresh_property():
    report = StaleReport(
        entries=[
            StaleEntry("a", None, _now(), 5.0, False),
            StaleEntry("b", None, _now(), 40.0, True),
        ],
    )
    assert len(report.fresh) == 1
    assert report.fresh[0].name == "a"


def test_has_stale_false_when_all_fresh():
    report = StaleReport(
        entries=[StaleEntry("a", None, _now(), 2.0, False)]
    )
    assert not report.has_stale


def test_has_stale_true_when_any_stale():
    report = StaleReport(
        entries=[StaleEntry("old", None, _now(), 60.0, True)]
    )
    assert report.has_stale


# ---------------------------------------------------------------------------
# check_stale
# ---------------------------------------------------------------------------

def test_check_stale_empty():
    report = check_stale([])
    assert report.entries == []
    assert not report.has_stale


def test_check_stale_marks_old_snapshot():
    snaps = [_snap("old", 45), _snap("new", 5)]
    report = check_stale(snaps, threshold_days=30)
    assert report.has_stale
    stale_names = {e.name for e in report.stale}
    assert "old" in stale_names
    assert "new" not in stale_names


def test_check_stale_custom_threshold():
    snaps = [_snap("snap", 10)]
    report = check_stale(snaps, threshold_days=7)
    assert report.has_stale


def test_check_stale_preserves_stack():
    snaps = [_snap("snap", 50, stack="prod")]
    report = check_stale(snaps)
    assert report.entries[0].stack == "prod"


# ---------------------------------------------------------------------------
# format_stale_text
# ---------------------------------------------------------------------------

def test_format_stale_text_contains_counts():
    snaps = [_snap("old", 40), _snap("new", 2)]
    report = check_stale(snaps, threshold_days=30)
    text = format_stale_text(report)
    assert "Total : 2" in text
    assert "Stale : 1" in text
    assert "Fresh : 1" in text


def test_format_stale_text_lists_stale_names():
    snaps = [_snap("legacy-snap", 90, stack="staging")]
    report = check_stale(snaps, threshold_days=30)
    text = format_stale_text(report)
    assert "legacy-snap" in text
    assert "staging" in text


def test_format_stale_text_no_stale_section_when_all_fresh():
    snaps = [_snap("fresh", 1)]
    report = check_stale(snaps, threshold_days=30)
    text = format_stale_text(report)
    assert "Stale snapshots:" not in text
