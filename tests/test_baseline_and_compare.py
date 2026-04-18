"""Tests for baseline persistence and report comparison."""

import pytest
from pathlib import Path

from stackdiff.diff import DiffReport, DiffEntry
from stackdiff.parser import ResourceChange, ChangeAction
from stackdiff.baseline import save_baseline, load_baseline, list_baselines
from stackdiff.compare import compare_reports, format_compare_result, CompareResult


def _entry(address: str, action: ChangeAction) -> DiffEntry:
    parts = address.split(".")
    rtype, name = parts[-2], parts[-1]
    rc = ResourceChange(
        address=address, module=None, resource_type=rtype,
        name=name, action=action, before=None, after=None,
    )
    return DiffEntry(resource=rc)


@pytest.fixture
def tmp_baseline_dir(tmp_path):
    return str(tmp_path / "baselines")


def _report(*entries):
    return DiffReport(entries=list(entries))


def test_save_and_load_baseline(tmp_baseline_dir):
    report = _report(_entry("aws_s3_bucket.my_bucket", ChangeAction.CREATE))
    path = save_baseline(report, "run1", tmp_baseline_dir)
    assert path.exists()
    loaded = load_baseline("run1", tmp_baseline_dir)
    assert loaded is not None
    assert len(loaded.entries) == 1
    assert loaded.entries[0].resource.address == "aws_s3_bucket.my_bucket"
    assert loaded.entries[0].resource.action == ChangeAction.CREATE


def test_load_missing_baseline_returns_none(tmp_baseline_dir):
    result = load_baseline("nonexistent", tmp_baseline_dir)
    assert result is None


def test_list_baselines(tmp_baseline_dir):
    r = _report(_entry("aws_instance.web", ChangeAction.UPDATE))
    save_baseline(r, "alpha", tmp_baseline_dir)
    save_baseline(r, "beta", tmp_baseline_dir)
    labels = list_baselines(tmp_baseline_dir)
    assert labels == ["alpha", "beta"]


def test_compare_identical_reports():
    e = _entry("aws_instance.web", ChangeAction.UPDATE)
    r = _report(e)
    result = compare_reports(r, r)
    assert result.is_clean
    assert not result.added
    assert not result.removed


def test_compare_added_entry():
    base = _report(_entry("aws_instance.web", ChangeAction.UPDATE))
    current = _report(
        _entry("aws_instance.web", ChangeAction.UPDATE),
        _entry("aws_s3_bucket.logs", ChangeAction.CREATE),
    )
    result = compare_reports(current, base)
    assert len(result.added) == 1
    assert result.added[0].resource.address == "aws_s3_bucket.logs"
    assert not result.removed


def test_compare_removed_entry():
    base = _report(
        _entry("aws_instance.web", ChangeAction.UPDATE),
        _entry("aws_s3_bucket.logs", ChangeAction.CREATE),
    )
    current = _report(_entry("aws_instance.web", ChangeAction.UPDATE))
    result = compare_reports(current, base)
    assert len(result.removed) == 1
    assert not result.added


def test_has_regressions_destructive():
    base = _report()
    current = _report(_entry("aws_instance.web", ChangeAction.DESTROY))
    result = compare_reports(current, base)
    assert result.has_regressions


def test_format_compare_clean():
    r = _report()
    result = compare_reports(r, r)
    assert "No changes" in format_compare_result(result)


def test_format_compare_with_changes():
    base = _report()
    current = _report(_entry("aws_instance.web", ChangeAction.CREATE))
    result = compare_reports(current, base)
    text = format_compare_result(result)
    assert "new change" in text
    assert "aws_instance.web" in text
