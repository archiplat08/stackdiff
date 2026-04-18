"""Notification hooks for watch events (stdout, webhook, file log)."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Optional

from stackdiff.export import report_to_dict
from stackdiff.summary import DiffSummary, has_destructive


def notify_stdout(path: Path, report, summary: DiffSummary) -> None:
    """Simple stdout notification (default hook)."""
    flag = " [DESTRUCTIVE]" if has_destructive(summary) else ""
    print(f"  -> {summary.total} change(s) in {path.name}{flag}")


def notify_file_log(log_path: Path):
    """Return a hook that appends JSON entries to a log file."""

    def _hook(path: Path, report, summary: DiffSummary) -> None:
        entry = {
            "file": str(path),
            "total": summary.total,
            "created": summary.created,
            "updated": summary.updated,
            "destroyed": summary.destroyed,
            "destructive": has_destructive(summary),
        }
        with log_path.open("a") as fh:
            fh.write(json.dumps(entry) + "\n")

    return _hook


def notify_webhook(url: str, timeout: float = 5.0):
    """Return a hook that POSTs a JSON payload to a webhook URL."""

    def _hook(path: Path, report, summary: DiffSummary) -> None:
        payload = {
            "file": path.name,
            "summary": {
                "total": summary.total,
                "created": summary.created,
                "updated": summary.updated,
                "destroyed": summary.destroyed,
                "destructive": has_destructive(summary),
            },
            "changes": report_to_dict(report)["entries"],
        }
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                print(f"[stackdiff notify] Webhook responded {resp.status}")
        except Exception as exc:  # noqa: BLE001
            print(f"[stackdiff notify] Webhook error: {exc}")

    return _hook
