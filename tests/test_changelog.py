"""Tests for stackdiff.changelog and format_changelog."""
from __future__ import annotations

from datetime import datetime
from typing import List

import pytest

from stackdiff.changelog import (
    Changelog,
    ChangelogEntry,
    build_changelog_entry,
    format_changelog,
)
from stackdiff.diff import DiffEntry, DiffReport
from stackdiff.parser import ChangeAction, ResourceChange


def _rc(action: ChangeAction, address: str = "aws_instance.foo") -> ResourceChange:
    return ResourceChange(
        address=address,
        module=None,
        resource_type="aws_instance",
        action=action,
    )


def _entry(action: ChangeAction, address: str = "aws_instance.foo") -> DiffEntry:
    rc = _rc(action, address)
    return DiffEntry(before=None, after=rc)


def _report(*actions: ChangeAction) -> DiffReport:
    return DiffReport(entries=[_entry(a) for a in actions])


# --- build_changelog_entry ---

def test_build_entry_counts_creates():
    report = _report(ChangeAction.CREATE, ChangeAction.CREATE)
    entry = build_changelog_entry(report, stack="prod", timestamp=datetime(2024, 1, 1))
    assert entry.created == 2
    assert entry.updated == 0
    assert entry.stack == "prod"


def test_build_entry_flags_destructive():
    report = _report(ChangeAction.DELETE)
    entry = build_changelog_entry(report, stack="staging")
    assert entry.has_destructive is True


def test_build_entry_not_destructive_for_create():
    report = _report(ChangeAction.CREATE)
    entry = build_changelog_entry(report, stack="dev")
    assert entry.has_destructive is False


def test_build_entry_notes_attached():
    report = _report(ChangeAction.UPDATE)
    entry = build_changelog_entry(report, stack="dev", notes=["ticket-123"])
    assert "ticket-123" in entry.notes


def test_build_entry_default_timestamp_is_recent():
    before = datetime.utcnow()
    report = _report(ChangeAction.CREATE)
    entry = build_changelog_entry(report, stack="x")
    after = datetime.utcnow()
    assert before <= entry.timestamp <= after


# --- Changelog filtering ---

def _make_changelog() -> Changelog:
    entries = [
        ChangelogEntry(datetime(2024, 1, 1), "prod", 1, 0, 0, 0, False),
        ChangelogEntry(datetime(2024, 3, 1), "staging", 0, 1, 0, 0, False),
        ChangelogEntry(datetime(2024, 6, 1), "prod", 0, 0, 1, 0, True),
    ]
    return Changelog(entries=entries)


def test_changelog_len():
    cl = _make_changelog()
    assert len(cl) == 3


def test_since_filters_entries():
    cl = _make_changelog()
    result = cl.since(datetime(2024, 4, 1))
    assert len(result) == 1
    assert result.entries[0].stack == "prod"
    assert result.entries[0].has_destructive is True


def test_for_stack_filters_by_name():
    cl = _make_changelog()
    result = cl.for_stack("staging")
    assert len(result) == 1
    assert result.entries[0].stack == "staging"


# --- format_changelog ---

def test_format_empty_changelog():
    cl = Changelog(entries=[])
    out = format_changelog(cl)
    assert "No changelog" in out


def test_format_includes_stack_name():
    cl = _make_changelog()
    out = format_changelog(cl)
    assert "prod" in out
    assert "staging" in out


def test_format_marks_destructive():
    cl = _make_changelog()
    out = format_changelog(cl)
    assert "[DESTRUCTIVE]" in out


def test_format_stack_filter():
    cl = _make_changelog()
    out = format_changelog(cl, stack="staging")
    assert "staging" in out
    assert "prod" not in out
