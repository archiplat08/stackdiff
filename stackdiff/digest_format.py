"""Formatting helpers for DigestReport."""
from __future__ import annotations

from stackdiff.digest import DigestReport
from stackdiff.risk import level as risk_level


def format_digest(report: DigestReport, *, color: bool = True) -> str:
    _R = "\033[31m" if color else ""
    _Y = "\033[33m" if color else ""
    _G = "\033[32m" if color else ""
    _B = "\033[1m" if color else ""
    _RESET = "\033[0m" if color else ""

    p = report.period
    lines = [
        f"{_B}=== StackDiff Digest ({p.label.capitalize()}) ==={_RESET}",
        f"Period : {p.start.strftime('%Y-%m-%d %H:%M')} → {p.end.strftime('%Y-%m-%d %H:%M')} UTC",
        f"Plans  : {report.total_plans}",
        "",
        f"  Creates  : {_G}{report.total_creates}{_RESET}",
        f"  Updates  : {_Y}{report.total_updates}{_RESET}",
        f"  Deletes  : {_R}{report.total_deletes}{_RESET}",
        f"  Replaces : {_R}{report.total_replaces}{_RESET}",
        "",
        f"Destructive plans : {_R if report.destructive_plans else _G}{report.destructive_plans}{_RESET}",
        f"Top risk score    : {report.top_risk_score:.1f} ({risk_level(report.top_risk_score)})",
    ]
    if report.stacks:
        lines.append("")
        lines.append("Stacks involved:")
        for s in report.stacks:
            lines.append(f"  - {s}")
    return "\n".join(lines)


def digest_to_dict(report: DigestReport) -> dict:
    p = report.period
    return {
        "period": {
            "label": p.label,
            "start": p.start.isoformat(),
            "end": p.end.isoformat(),
        },
        "total_plans": report.total_plans,
        "total_creates": report.total_creates,
        "total_updates": report.total_updates,
        "total_deletes": report.total_deletes,
        "total_replaces": report.total_replaces,
        "destructive_plans": report.destructive_plans,
        "top_risk_score": report.top_risk_score,
        "stacks": report.stacks,
    }
