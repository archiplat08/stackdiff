"""blame.py – attribute resource changes to their originating plan files.

Given a rollup report (multiple stacks) or a list of annotated entries,
BlameReport maps each resource address back to the stack/plan file that
introduced the change, making it easy to pinpoint *which* plan is
responsible for a risky or destructive modification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from stackdiff.annotate import AnnotatedEntry
from stackdiff.rollup import RollupReport, StackRollupEntry


@dataclass(frozen=True)
class BlameEntry:
    """A single resource change attributed to a specific stack."""

    address: str
    action: str
    stack_name: str
    plan_file: Optional[str]
    risk_level: str
    has_violations: bool


@dataclass
class BlameReport:
    """Collection of blame entries, indexed by resource address."""

    entries: List[BlameEntry] = field(default_factory=list)

    # ------------------------------------------------------------------ #
    # Convenience properties
    # ------------------------------------------------------------------ #

    @property
    def by_stack(self) -> Dict[str, List[BlameEntry]]:
        """Return entries grouped by stack name."""
        result: Dict[str, List[BlameEntry]] = {}
        for e in self.entries:
            result.setdefault(e.stack_name, []).append(e)
        return result

    @property
    def risky_entries(self) -> List[BlameEntry]:
        """Return entries whose risk level is not 'none'."""
        return [e for e in self.entries if e.risk_level != "none"]

    @property
    def violating_entries(self) -> List[BlameEntry]:
        """Return entries that have at least one policy violation."""
        return [e for e in self.entries if e.has_violations]


# --------------------------------------------------------------------------- #
# Builder
# --------------------------------------------------------------------------- #


def build_blame(
    rollup: RollupReport,
    annotated_map: Optional[Dict[str, List[AnnotatedEntry]]] = None,
) -> BlameReport:
    """Build a BlameReport from a RollupReport.

    Args:
        rollup: A RollupReport produced by ``stackdiff.rollup.build_rollup``.
        annotated_map: Optional mapping of *stack_name* → list of
            :class:`~stackdiff.annotate.AnnotatedEntry`.  When provided,
            risk and violation metadata are attached to each blame entry.

    Returns:
        A populated :class:`BlameReport`.
    """
    annotated_map = annotated_map or {}
    blame_entries: List[BlameEntry] = []

    for stack_entry in rollup.stacks:
        # Build a fast lookup: address → AnnotatedEntry for this stack
        ann_lookup: Dict[str, AnnotatedEntry] = {
            a.address: a
            for a in annotated_map.get(stack_entry.stack_name, [])
        }

        for diff_entry in stack_entry.entries:
            ann = ann_lookup.get(diff_entry.address)
            blame_entries.append(
                BlameEntry(
                    address=diff_entry.address,
                    action=diff_entry.action,
                    stack_name=stack_entry.stack_name,
                    plan_file=stack_entry.plan_file,
                    risk_level=ann.risk_level if ann else "none",
                    has_violations=ann.has_violations if ann else False,
                )
            )

    return BlameReport(entries=blame_entries)


# --------------------------------------------------------------------------- #
# Formatter
# --------------------------------------------------------------------------- #


def format_blame(report: BlameReport, *, color: bool = True) -> str:
    """Render a BlameReport as a human-readable string.

    Groups output by stack name and highlights risky / violating entries.
    """
    _RESET = "\033[0m" if color else ""
    _RED = "\033[31m" if color else ""
    _YELLOW = "\033[33m" if color else ""
    _CYAN = "\033[36m" if color else ""
    _BOLD = "\033[1m" if color else ""

    lines: List[str] = []
    by_stack = report.by_stack

    if not by_stack:
        return "(no blame entries)"

    for stack_name, entries in sorted(by_stack.items()):
        plan_file = entries[0].plan_file or "<unknown>"
        lines.append(f"{_BOLD}Stack: {stack_name}{_RESET}  ({plan_file})")
        for e in entries:
            risk_tag = ""
            if e.risk_level not in ("none", "low"):
                risk_tag = f" [{_YELLOW}{e.risk_level}{_RESET}]"
            violation_tag = f" {_RED}[VIOLATION]{_RESET}" if e.has_violations else ""
            lines.append(
                f"  {_CYAN}{e.action:<10}{_RESET} {e.address}{risk_tag}{violation_tag}"
            )
        lines.append("")

    return "\n".join(lines).rstrip()
