"""Dependency graph analysis for Terraform plan resources."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set

from stackdiff.diff import DiffReport, DiffEntry


@dataclass
class DependencyNode:
    address: str
    action: str
    depends_on: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)


@dataclass
class DependencyGraph:
    nodes: Dict[str, DependencyNode] = field(default_factory=dict)

    def addresses(self) -> List[str]:
        return list(self.nodes.keys())

    def get(self, address: str) -> DependencyNode | None:
        return self.nodes.get(address)

    def upstream(self, address: str) -> List[str]:
        """Return all transitive dependencies of a node."""
        visited: Set[str] = set()
        stack = list(self.nodes.get(address, DependencyNode(address, "")).depends_on)
        while stack:
            dep = stack.pop()
            if dep in visited:
                continue
            visited.add(dep)
            node = self.nodes.get(dep)
            if node:
                stack.extend(node.depends_on)
        return sorted(visited)

    def downstream(self, address: str) -> List[str]:
        """Return all nodes that transitively depend on this node."""
        visited: Set[str] = set()
        stack = list(self.nodes.get(address, DependencyNode(address, "")).dependents)
        while stack:
            dep = stack.pop()
            if dep in visited:
                continue
            visited.add(dep)
            node = self.nodes.get(dep)
            if node:
                stack.extend(node.dependents)
        return sorted(visited)


def build_graph(report: DiffReport, dependency_map: Dict[str, List[str]] | None = None) -> DependencyGraph:
    """Build a dependency graph from a DiffReport and an optional dependency map.

    dependency_map maps resource address -> list of addresses it depends on.
    """
    dep_map: Dict[str, List[str]] = dependency_map or {}
    graph = DependencyGraph()

    for entry in report.entries:
        addr = entry.address
        deps = dep_map.get(addr, [])
        graph.nodes[addr] = DependencyNode(
            address=addr,
            action=entry.action,
            depends_on=list(deps),
        )

    # Wire dependents (reverse edges)
    for addr, node in graph.nodes.items():
        for dep in node.depends_on:
            if dep in graph.nodes:
                if addr not in graph.nodes[dep].dependents:
                    graph.nodes[dep].dependents.append(addr)

    return graph


def blast_radius(graph: DependencyGraph, address: str) -> List[str]:
    """Return all resources affected if `address` is changed/destroyed."""
    return graph.downstream(address)
