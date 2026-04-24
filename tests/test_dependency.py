"""Tests for stackdiff.dependency."""
from __future__ import annotations

import pytest

from stackdiff.diff import DiffReport, DiffEntry
from stackdiff.dependency import (
    DependencyNode,
    DependencyGraph,
    build_graph,
    blast_radius,
)


def _entry(address: str, action: str = "create") -> DiffEntry:
    from stackdiff.parser import ResourceChange, ChangeAction
    rc = ResourceChange(
        address=address,
        resource_type=address.split(".")[0] if "." in address else "aws_resource",
        name=address.split(".")[-1],
        action=ChangeAction(action),
        module=None,
    )
    return DiffEntry(resource=rc)


def _report(*entries: DiffEntry) -> DiffReport:
    return DiffReport(entries=list(entries))


# --- build_graph ---

def test_build_graph_empty():
    graph = build_graph(_report())
    assert graph.addresses() == []


def test_build_graph_nodes_created():
    r = _report(_entry("aws_vpc.main"), _entry("aws_subnet.pub"))
    graph = build_graph(r)
    assert set(graph.addresses()) == {"aws_vpc.main", "aws_subnet.pub"}


def test_build_graph_wires_dependents():
    r = _report(_entry("aws_vpc.main"), _entry("aws_subnet.pub"))
    dep_map = {"aws_subnet.pub": ["aws_vpc.main"]}
    graph = build_graph(r, dep_map)

    subnet = graph.get("aws_subnet.pub")
    assert subnet is not None
    assert "aws_vpc.main" in subnet.depends_on

    vpc = graph.get("aws_vpc.main")
    assert vpc is not None
    assert "aws_subnet.pub" in vpc.dependents


def test_build_graph_unknown_dep_not_in_graph():
    """Deps referencing addresses not in the report are stored but not wired."""
    r = _report(_entry("aws_subnet.pub"))
    dep_map = {"aws_subnet.pub": ["aws_vpc.main"]}  # aws_vpc.main not in report
    graph = build_graph(r, dep_map)
    subnet = graph.get("aws_subnet.pub")
    assert "aws_vpc.main" in subnet.depends_on
    # aws_vpc.main node should not exist
    assert graph.get("aws_vpc.main") is None


# --- upstream / downstream ---

def test_upstream_direct():
    r = _report(_entry("aws_vpc.main"), _entry("aws_subnet.pub"), _entry("aws_instance.web"))
    dep_map = {
        "aws_subnet.pub": ["aws_vpc.main"],
        "aws_instance.web": ["aws_subnet.pub"],
    }
    graph = build_graph(r, dep_map)
    ups = graph.upstream("aws_instance.web")
    assert "aws_subnet.pub" in ups
    assert "aws_vpc.main" in ups


def test_downstream_direct():
    r = _report(_entry("aws_vpc.main"), _entry("aws_subnet.pub"))
    dep_map = {"aws_subnet.pub": ["aws_vpc.main"]}
    graph = build_graph(r, dep_map)
    down = graph.downstream("aws_vpc.main")
    assert "aws_subnet.pub" in down


def test_upstream_empty_for_root():
    r = _report(_entry("aws_vpc.main"))
    graph = build_graph(r)
    assert graph.upstream("aws_vpc.main") == []


def test_downstream_empty_for_leaf():
    r = _report(_entry("aws_vpc.main"), _entry("aws_subnet.pub"))
    dep_map = {"aws_subnet.pub": ["aws_vpc.main"]}
    graph = build_graph(r, dep_map)
    assert graph.downstream("aws_subnet.pub") == []


# --- blast_radius ---

def test_blast_radius_returns_downstream():
    r = _report(_entry("aws_vpc.main"), _entry("aws_subnet.pub"), _entry("aws_instance.web"))
    dep_map = {
        "aws_subnet.pub": ["aws_vpc.main"],
        "aws_instance.web": ["aws_subnet.pub"],
    }
    graph = build_graph(r, dep_map)
    affected = blast_radius(graph, "aws_vpc.main")
    assert "aws_subnet.pub" in affected
    assert "aws_instance.web" in affected


def test_blast_radius_empty_for_unknown():
    r = _report(_entry("aws_vpc.main"))
    graph = build_graph(r)
    assert blast_radius(graph, "aws_nonexistent.x") == []
