"""Tests for stackdiff.filter and stackdiff.summary."""
import pytest
from stackdiff.parser import ResourceChange, ChangeAction
from stackdiff.diff import DiffEntry, DiffReport
from stackdiff.filter import FilterOptions, filter_report
from stackdiff.summary import summarize, format_summary


def _make_report(*specs):
    """specs: list of (address, action_str)"""
    entries = []
    for address, action_str in specs:
        change = ResourceChange(
            address=address,
            action=ChangeAction(action_str),
            before={},
            after={},
        )
        entries.append(DiffEntry(change=change, before={}, after={}))
    return DiffReport(entries=entries)


def test_filter_by_action():
    report = _make_report(
        ("aws_instance.web", "create"),
        ("aws_s3_bucket.data", "delete"),
        ("aws_instance.db", "update"),
    )
    opts = FilterOptions(actions=["create"])
    result = filter_report(report, opts)
    assert len(result.entries) == 1
    assert result.entries[0].change.address == "aws_instance.web"


def test_filter_by_resource_type():
    report = _make_report(
        ("aws_instance.web", "create"),
        ("aws_s3_bucket.data", "create"),
    )
    opts = FilterOptions(resource_type="aws_instance")
    result = filter_report(report, opts)
    assert len(result.entries) == 1


def test_filter_by_module():
    report = _make_report(
        ("module.vpc.aws_subnet.pub", "create"),
        ("aws_instance.web", "create"),
    )
    opts = FilterOptions(module="module.vpc")
    result = filter_report(report, opts)
    assert len(result.entries) == 1
    assert "module.vpc" in result.entries[0].change.address


def test_filter_name_contains():
    report = _make_report(
        ("aws_instance.web_prod", "update"),
        ("aws_instance.web_staging", "update"),
        ("aws_instance.db", "update"),
    )
    opts = FilterOptions(name_contains="web")
    result = filter_report(report, opts)
    assert len(result.entries) == 2


def test_summarize_counts():
    report = _make_report(
        ("aws_instance.a", "create"),
        ("aws_instance.b", "delete"),
        ("aws_s3_bucket.x", "create"),
    )
    s = summarize(report)
    assert s.total == 3
    assert s.by_action["create"] == 2
    assert s.by_action["delete"] == 1
    assert s.by_resource_type["aws_instance"] == 2


def test_has_destructive_true():
    report = _make_report(("aws_instance.a", "delete"))
    s = summarize(report)
    assert s.has_destructive() is True


def test_has_destructive_false():
    report = _make_report(("aws_instance.a", "create"))
    s = summarize(report)
    assert s.has_destructive() is False


def test_format_summary_contains_warning():
    report = _make_report(("aws_instance.a", "replace"))
    s = summarize(report)
    text = format_summary(s)
    assert "destructive" in text
