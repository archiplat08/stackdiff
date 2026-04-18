"""Filtering utilities for DiffReport entries."""
from dataclasses import dataclass
from typing import Optional, List
from stackdiff.diff import DiffReport, DiffEntry
from stackdiff.parser import ChangeAction


@dataclass
class FilterOptions:
    actions: Optional[List[str]] = None  # e.g. ['create', 'delete']
    resource_type: Optional[str] = None  # e.g. 'aws_instance'
    module: Optional[str] = None         # e.g. 'module.vpc'
    name_contains: Optional[str] = None


def _matches(entry: DiffEntry, opts: FilterOptions) -> bool:
    change = entry.change

    if opts.actions:
        allowed = {ChangeAction(a) for a in opts.actions}
        if change.action not in allowed:
            return False

    address = change.address

    if opts.resource_type:
        # address format: [module.x.]resource_type.name
        bare = address.split(".")[-2] if "." in address else ""
        if bare != opts.resource_type:
            return False

    if opts.module:
        if not address.startswith(opts.module):
            return False

    if opts.name_contains:
        if opts.name_contains not in address:
            return False

    return True


def filter_report(report: DiffReport, opts: FilterOptions) -> DiffReport:
    """Return a new DiffReport containing only entries matching opts."""
    filtered = [e for e in report.entries if _matches(e, opts)]
    return DiffReport(entries=filtered)
