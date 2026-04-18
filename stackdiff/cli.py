"""CLI entry point for stackdiff."""
from __future__ import annotations

import sys
from pathlib import Path

import click

from stackdiff.diff import diff_plans
from stackdiff.formatter import format_report
from stackdiff.parser import parse_plan_text


@click.command()
@click.argument("base_plan", type=click.Path(exists=True, dir_okay=False))
@click.argument("head_plan", type=click.Path(exists=True, dir_okay=False))
@click.option("--no-color", is_flag=True, default=False, help="Disable ANSI colors.")
@click.option(
    "--exit-code",
    is_flag=True,
    default=False,
    help="Exit with code 1 if changes are detected.",
)
def main(
    base_plan: str,
    head_plan: str,
    no_color: bool,
    exit_code: bool,
) -> None:
    """Diff two Terraform plan text outputs (BASE_PLAN vs HEAD_PLAN)."""
    base_text = Path(base_plan).read_text()
    head_text = Path(head_plan).read_text()

    base_changes = parse_plan_text(base_text)
    head_changes = parse_plan_text(head_text)

    report = diff_plans(base_changes, head_changes)
    click.echo(format_report(report, use_color=not no_color))

    if exit_code and report.has_changes:
        sys.exit(1)


if __name__ == "__main__":
    main()
