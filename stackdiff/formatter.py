"""Format a DiffReport for terminal output."""
from __future__ import annotations

from stackdiff.diff import DiffReport

RESET = "\033[0m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BOLD = "\033[1m"
DIM = "\033[2m"


def _color(text: str, code: str, use_color: bool) -> str:
    return f"{code}{text}{RESET}" if use_color else text


def format_report(report: DiffReport, use_color: bool = True) -> str:
    lines: list[str] = []

    if not report.has_changes:
        lines.append(_color("No changes detected between plans.", DIM, use_color))
        return "\n".join(lines)

    if report.added:
        lines.append(_color("Added:", BOLD, use_color))
        for e in report.added:
            lines.append(
                _color(f"  + {e.address}", GREEN, use_color)
                + _color(f" ({e.after})", DIM, use_color)
            )

    if report.removed:
        lines.append(_color("Removed:", BOLD, use_color))
        for e in report.removed:
            lines.append(
                _color(f"  - {e.address}", RED, use_color)
                + _color(f" ({e.before})", DIM, use_color)
            )

    if report.changed:
        lines.append(_color("Changed:", BOLD, use_color))
        for e in report.changed:
            lines.append(
                _color(f"  ~ {e.address}", YELLOW, use_color)
                + _color(f" ({e.before} -> {e.after})", DIM, use_color)
            )

    lines.append("")
    lines.append(_color(report.summary(), BOLD, use_color))
    return "\n".join(lines)
