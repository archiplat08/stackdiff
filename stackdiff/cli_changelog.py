"""CLI sub-command: changelog — show changelog across recorded audit entries."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from typing import List, Optional

from stackdiff.audit import load_audit_log
from stackdiff.changelog import Changelog, ChangelogEntry, format_changelog
from stackdiff.diff import DiffReport, DiffEntry
from stackdiff.parser import ChangeAction


def _add_changelog_parser(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("changelog", help="Show changelog of plan activity")
    p.add_argument("audit_log", help="Path to JSONL audit log")
    p.add_argument("--stack", default=None, help="Filter by stack name")
    p.add_argument("--since", default=None, help="ISO datetime lower bound (UTC)")


def _audit_entry_to_changelog(entry) -> Optional[ChangelogEntry]:  # type: ignore[return]
    """Convert an AuditEntry to a ChangelogEntry."""
    try:
        ts = datetime.fromisoformat(entry.recorded_at.replace("Z", "+00:00"))
        ts = ts.replace(tzinfo=None)  # naive UTC for comparison
    except Exception:
        ts = datetime.utcnow()

    # Reconstruct a minimal DiffReport from audit entry counts
    from stackdiff.changelog import build_changelog_entry
    from stackdiff.diff import DiffReport, DiffEntry
    from stackdiff.parser import ChangeAction, ResourceChange

    entries: List[DiffEntry] = []
    for action, count in [
        (ChangeAction.CREATE, entry.summary.get("creates", 0)),
        (ChangeAction.UPDATE, entry.summary.get("updates", 0)),
        (ChangeAction.DELETE, entry.summary.get("deletes", 0)),
        (ChangeAction.REPLACE, entry.summary.get("replaces", 0)),
    ]:
        for i in range(count):
            rc = ResourceChange(
                address=f"placeholder_{action.value}_{i}",
                module=None,
                resource_type="placeholder",
                action=action,
            )
            entries.append(DiffEntry(before=None, after=rc))

    report = DiffReport(entries=entries)
    return build_changelog_entry(report, stack=entry.stack or "default", timestamp=ts)


def _cmd_changelog(args: argparse.Namespace) -> int:
    audit_entries = load_audit_log(args.audit_log)
    if audit_entries is None:
        print(f"Error: audit log not found: {args.audit_log}", file=sys.stderr)
        return 1

    cl_entries = [e for e in (_audit_entry_to_changelog(a) for a in audit_entries) if e]
    changelog = Changelog(entries=cl_entries)

    if args.since:
        try:
            since_dt = datetime.fromisoformat(args.since)
        except ValueError:
            print(f"Invalid --since value: {args.since}", file=sys.stderr)
            return 1
        changelog = changelog.since(since_dt)

    print(format_changelog(changelog, stack=args.stack))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="stackdiff-changelog")
    sub = p.add_subparsers(dest="command")
    _add_changelog_parser(sub)
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(_cmd_changelog(args))
