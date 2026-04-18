"""CLI entry point for stackdiff."""
from __future__ import annotations

import sys
from pathlib import Path

import click

from stackdiff.diff import build_report
from stackdiff.export import to_csv, to_json
from stackdiff.filter import FilterOptions, filter_report
from stackdiff.formatter import format_report
from stackdiff.parser import parse_plan_text
from stackdiff.summary import format_summary, summarize


@click.command()
@click.argument("plan_file", type=click.Path(exists=True, dir_okay=False))
@click.option("--action", "actions", multiple=True, help="Filter by action (create/update/destroy).")
@click.option("--type", "resource_types", multiple=True, help="Filter by resource type.")
@click.option("--module", "modules", multiple=True, help="Filter by module prefix.")
@click.option("--summary", "show_summary", is_flag=True, default=False, help="Show summary only.")
@click.option("--output", "output_format", type=click.Choice(["text", "json", "csv"]), default="text", show_default=True, help="Output format.")
@click.option("--no-color", is_flag=True, default=False, help="Disable colored output.")
def main(
    plan_file: str,
    actions: tuple[str, ...],
    resource_types: tuple[str, ...],
    modules: tuple[str, ...],
    show_summary: bool,
    output_format: str,
    no_color: bool,
) -> None:
    """Diff and audit Terraform plan outputs."""
    text = Path(plan_file).read_text()
    changes = parse_plan_text(text)
    report = build_report(changes)

    opts = FilterOptions(
        actions=list(actions) or None,
        resource_types=list(resource_types) or None,
        modules=list(modules) or None,
    )
    report = filter_report(report, opts)

    if output_format == "json":
        click.echo(to_json(report))
    elif output_format == "csv":
        click.echo(to_csv(report), nl=False)
    else:
        if show_summary:
            click.echo(format_summary(summarize(report), color=not no_color))
        else:
            click.echo(format_report(report, color=not no_color))
            click.echo(format_summary(summarize(report), color=not no_color))


if __name__ == "__main__":
    main()
