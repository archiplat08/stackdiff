"""Tests for stackdiff.remediation."""
from __future__ import annotations

from stackdiff.diff import DiffEntry, DiffReport
from stackdiff.parser import ChangeAction, ResourceChange
from stackdiff.policy import PolicyRule, PolicyViolation
from stackdiff.annotate import AnnotatedEntry, AnnotatedReport
from stackdiff.remediation import suggest, format_hints, RemediationHint


def _make_annotated(
    address: str,
    action: str,
    risk_level: str = "none",
    violations: list | None = None,
) -> AnnotatedEntry:
    rc = ResourceChange(
        address=address,
        resource_type=address.split(".")[0],
        name=address.split(".")[-1],
        action=ChangeAction(action),
        module=None,
    )
    entry = DiffEntry(change=rc, before={}, after={})
    return AnnotatedEntry(
        entry=entry,
        risk_score=0,
        risk_level=risk_level,
        violations=violations or [],
    )


def _report(*entries: AnnotatedEntry) -> AnnotatedReport:
    return AnnotatedReport(entries=list(entries))


def test_no_hints_for_safe_create():
    e = _make_annotated("aws_s3_bucket.logs", "create", "none")
    hints = suggest(_report(e))
    assert hints == []


def test_hint_for_delete():
    e = _make_annotated("aws_db_instance.prod", "delete", "high")
    hints = suggest(_report(e))
    assert len(hints) == 1
    h = hints[0]
    assert h.address == "aws_db_instance.prod"
    assert h.action == "delete"
    assert any("prevent_destroy" in s for s in h.suggestions)
    assert any("second review" in s for s in h.suggestions)


def test_hint_for_replace():
    e = _make_annotated("aws_instance.web", "replace", "medium")
    hints = suggest(_report(e))
    assert len(hints) == 1
    assert any("re-create" in s for s in hints[0].suggestions)
    assert any("staging" in s for s in hints[0].suggestions)


def test_hint_includes_violation_messages():
    v = PolicyViolation(
        rule_name="no_destroy",
        message="Destroy not allowed",
        severity="block",
    )
    e = _make_annotated("aws_iam_role.admin", "delete", "critical", violations=[v])
    hints = suggest(_report(e))
    assert len(hints) == 1
    assert "Destroy not allowed" in hints[0].violation_messages


def test_format_hints_empty():
    out = format_hints([])
    assert "safe" in out.lower()


def test_format_hints_renders_all_sections():
    v = PolicyViolation(rule_name="r", message="Blocked!", severity="block")
    e = _make_annotated("aws_rds_cluster.main", "replace", "high", violations=[v])
    hints = suggest(_report(e))
    rendered = format_hints(hints)
    assert "[HIGH]" in rendered
    assert "aws_rds_cluster.main" in rendered
    assert "Blocked!" in rendered
    assert ">" in rendered


def test_multiple_entries_only_actionable_ones():
    safe = _make_annotated("aws_s3_bucket.ok", "create", "none")
    risky = _make_annotated("aws_db_instance.prod", "delete", "critical")
    hints = suggest(_report(safe, risky))
    addresses = [h.address for h in hints]
    assert "aws_s3_bucket.ok" not in addresses
    assert "aws_db_instance.prod" in addresses
