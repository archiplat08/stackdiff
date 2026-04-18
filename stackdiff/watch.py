"""Watch a directory for new Terraform plan files and auto-diff them."""
from __future__ import annotations

import time
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from stackdiff.parser import parse_plan_text
from stackdiff.diff import build_report
from stackdiff.summary import summarize, format_summary


@dataclass
class WatchOptions:
    directory: Path
    interval: float = 2.0
    extension: str = ".tfplan.txt"
    on_change: Optional[Callable] = None


@dataclass
class WatchState:
    seen: set[str] = field(default_factory=set)
    last_report: object = None


def _scan(directory: Path, extension: str) -> list[Path]:
    return sorted(directory.glob(f"*{extension}"))


def _process_file(path: Path, state: WatchState, opts: WatchOptions) -> None:
    text = path.read_text()
    changes = parse_plan_text(text)
    report = build_report(changes)
    summary = summarize(report)

    print(f"\n[stackdiff watch] New plan detected: {path.name}")
    print(format_summary(summary))

    if opts.on_change:
        opts.on_change(path, report, summary)

    state.last_report = report


def watch(opts: WatchOptions, max_iterations: Optional[int] = None) -> None:
    """Poll directory for new plan files. Runs until interrupted."""
    state = WatchState()
    opts.directory.mkdir(parents=True, exist_ok=True)

    print(f"[stackdiff watch] Watching {opts.directory} (interval={opts.interval}s)")

    iterations = 0
    while True:
        for path in _scan(opts.directory, opts.extension):
            key = str(path)
            if key not in state.seen:
                state.seen.add(key)
                try:
                    _process_file(path, state, opts)
                except Exception as exc:  # noqa: BLE001
                    print(f"[stackdiff watch] Error processing {path.name}: {exc}")

        iterations += 1
        if max_iterations is not None and iterations >= max_iterations:
            break
        time.sleep(opts.interval)
