"""Tests for stackdiff.heatmap and cli_heatmap."""
from __future__ import annotations

import pytest

from stackdiff.diff import DiffEntry, DiffReport
from stackdiff.heatmap import (
    HeatmapEntry,
    HeatmapReport,
    build_heatmap,
    format_heatmap,
)


def _entry(address: str, action: str = "create", rtype: str = "aws_s3_bucket") -> DiffEntry:
    return DiffEntry(address=address, resource_type=rtype, action=action, module=None)


def _report(*entries: DiffEntry) -> DiffReport:
    return DiffReport(entries=list(entries))


# ---------------------------------------------------------------------------
# build_heatmap
# ---------------------------------------------------------------------------

def test_build_heatmap_empty():
    result = build_heatmap([])
    assert result.entries == []


def test_build_heatmap_single_report():
    r = _report(_entry("aws_s3_bucket.a"), _entry("aws_s3_bucket.b", action="delete"))
    result = build_heatmap([r])
    assert len(result.entries) == 2
    addrs = {e.address for e in result.entries}
    assert "aws_s3_bucket.a" in addrs
    assert "aws_s3_bucket.b" in addrs


def test_build_heatmap_counts_across_reports():
    r1 = _report(_entry("aws_s3_bucket.x", action="create"))
    r2 = _report(_entry("aws_s3_bucket.x", action="update"))
    result = build_heatmap([r1, r2])
    assert len(result.entries) == 1
    entry = result.entries[0]
    assert entry.change_count == 2
    assert entry.action_counts == {"create": 1, "update": 1}


def test_build_heatmap_hot_resources():
    r1 = _report(_entry("aws_s3_bucket.x"))
    r2 = _report(_entry("aws_s3_bucket.x"), _entry("aws_s3_bucket.y"))
    result = build_heatmap([r1, r2])
    hot = result.hot_resources
    assert len(hot) == 1
    assert hot[0].address == "aws_s3_bucket.x"


def test_build_heatmap_top_sorted():
    r1 = _report(_entry("res.a"), _entry("res.b"), _entry("res.c"))
    r2 = _report(_entry("res.a"), _entry("res.c"))
    r3 = _report(_entry("res.a"))
    result = build_heatmap([r1, r2, r3])
    top = result.top
    assert top[0].address == "res.a"
    assert top[0].change_count == 3


def test_heatmap_entry_is_hot_false_for_single():
    e = HeatmapEntry(address="x", resource_type="t", change_count=1, action_counts={"create": 1})
    assert not e.is_hot


def test_heatmap_entry_is_hot_true_for_multiple():
    e = HeatmapEntry(address="x", resource_type="t", change_count=3, action_counts={"update": 3})
    assert e.is_hot


# ---------------------------------------------------------------------------
# format_heatmap
# ---------------------------------------------------------------------------

def test_format_heatmap_empty():
    report = HeatmapReport(entries=[])
    out = format_heatmap(report)
    assert "No changes" in out


def test_format_heatmap_contains_address():
    r = _report(_entry("aws_s3_bucket.main"))
    report = build_heatmap([r])
    out = format_heatmap(report)
    assert "aws_s3_bucket.main" in out


def test_format_heatmap_top_n_limits_output():
    entries = [_entry(f"res.r{i}") for i in range(20)]
    report = build_heatmap([_report(*entries)])
    out = format_heatmap(report, top_n=5)
    # Only 5 resource lines plus header lines
    resource_lines = [l for l in out.splitlines() if "res.r" in l]
    assert len(resource_lines) == 5


def test_format_heatmap_hot_marker_present():
    r1 = _report(_entry("res.hot"))
    r2 = _report(_entry("res.hot"))
    report = build_heatmap([r1, r2])
    out = format_heatmap(report)
    assert "\U0001f525" in out  # 🔥
