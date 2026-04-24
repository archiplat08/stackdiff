"""CLI subcommand: dependency — show dependency graph and blast radius."""
from __future__ import annotations

import argparse
import json
import sys

from stackdiff.parser import parse_plan_text
from stackdiff.diff import build_report
from stackdiff.dependency import build_graph, blast_radius


def _add_dependency_parser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "dependency",
        help="Analyse resource dependency graph from a plan file",
    )
    p.add_argument("plan", help="Path to terraform plan text file")
    p.add_argument(
        "--deps",
        metavar="JSON",
        help="JSON file mapping address -> [depends_on addresses]",
        default=None,
    )
    p.add_argument(
        "--blast-radius",
        metavar="ADDRESS",
        dest="blast_address",
        help="Show all resources impacted if ADDRESS changes",
        default=None,
    )
    p.add_argument(
        "--upstream",
        metavar="ADDRESS",
        help="Show all dependencies of ADDRESS",
        default=None,
    )
    p.add_argument("--json", action="store_true", help="Output as JSON")


def _cmd_dependency(args: argparse.Namespace) -> int:
    with open(args.plan) as fh:
        changes = parse_plan_text(fh.read())
    report = build_report(changes)

    dep_map = None
    if args.deps:
        with open(args.deps) as fh:
            dep_map = json.load(fh)

    graph = build_graph(report, dep_map)

    if args.blast_address:
        affected = blast_radius(graph, args.blast_address)
        if args.json:
            print(json.dumps({"blast_radius": affected}, indent=2))
        else:
            print(f"Blast radius for {args.blast_address}:")
            for addr in affected:
                print(f"  - {addr}")
            if not affected:
                print("  (no downstream dependents)")
        return 0

    if args.upstream:
        deps = graph.upstream(args.upstream)
        if args.json:
            print(json.dumps({"upstream": deps}, indent=2))
        else:
            print(f"Upstream dependencies of {args.upstream}:")
            for addr in deps:
                print(f"  - {addr}")
            if not deps:
                print("  (no upstream dependencies)")
        return 0

    # Default: list all nodes
    if args.json:
        data = [
            {"address": n.address, "action": n.action,
             "depends_on": n.depends_on, "dependents": n.dependents}
            for n in graph.nodes.values()
        ]
        print(json.dumps(data, indent=2))
    else:
        for n in graph.nodes.values():
            print(f"{n.address} [{n.action}]")
            if n.depends_on:
                print(f"  depends_on: {', '.join(n.depends_on)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="stackdiff-dependency")
    sub = p.add_subparsers(dest="command")
    _add_dependency_parser(sub)
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(_cmd_dependency(args))
