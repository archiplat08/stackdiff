"""Tests for stackdiff.trend module."""
import pytest
from stackdiff.diff import DiffReport, DiffEntry
from stackdiff.parser import ChangeAction
from stackdiff.trend import build_trend, format_trend, TrendPoint, TrendReport


def _entry(action: ChangeAction, rtype: str = "aws_instance", name: str = "web") -> DiffEntry:
    from stackdiff.diff import DiffEntry
    return DiffEntry(
        address=f"{rtype}.{name}",
        module=None,
        resource_type=rtype,
        resource_name=name,
        action=action,
        before={},
        after={},
    )


def _report(*actions: ChangeAction) -> DiffReport:
    entries = [_entry(a, name=f"r{i}") for i, a in enumerate(actions)]
    return DiffReport(entries=entries)


def test_build_trend_empty():
    trend = build_trend([])
    assert trend.points == []
    assert trend.labels == []
    assert trend.total_series == []
    assert trend.destructive_count == 0


def test_build_trend_single_point():
    report = _report(ChangeAction.CREATE, ChangeAction.UPDATE)
    trend = build_trend([("v1", report)])
    assert len(trend.points) == 1
    p = trend.points[0]
    assert p.label == "v1"
    assert p.total == 2
    assert p.creates == 1
    assert p.updates == 1
    assert p.deletes == 0
    assert p.destructive is False


def test_build_trend_destructive_flagged():
    report = _report(ChangeAction.DELETE)
    trend = build_trend([("v2", report)])
    assert trend.points[0].destructive is True
    assert trend.destructive_count == 1


def test_build_trend_multiple_points():
    r1 = _report(ChangeAction.CREATE)
    r2 = _report(ChangeAction.DELETE, ChangeAction.REPLACE)
    r3 = _report(ChangeAction.UPDATE)
    trend = build_trend([("run-1", r1), ("run-2", r2), ("run-3", r3)])
    assert trend.labels == ["run-1", "run-2", "run-3"]
    assert trend.total_series == [1, 2, 1]
    assert trend.destructive_count == 1


def test_format_trend_empty():
    trend = TrendReport(points=[])
    output = format_trend(trend)
    assert "No trend data" in output


def test_format_trend_contains_labels():
    r1 = _report(ChangeAction.CREATE, ChangeAction.DELETE)
    r2 = _report(ChangeAction.UPDATE)
    trend = build_trend([("alpha", r1), ("beta", r2)])
    output = format_trend(trend)
    assert "alpha" in output
    assert "beta" in output


def test_format_trend_destructive_marker():
    report = _report(ChangeAction.DELETE)
    trend = build_trend([("snap", report)])
    output = format_trend(trend)
    assert "YES" in output


def test_format_trend_summary_line():
    r1 = _report(ChangeAction.CREATE)
    r2 = _report(ChangeAction.REPLACE)
    trend = build_trend([("a", r1), ("b", r2)])
    output = format_trend(trend)
    assert "1/2" in output
