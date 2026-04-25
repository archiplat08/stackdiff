"""Map resource addresses to team/owner metadata and produce ownership reports."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from stackdiff.diff import DiffReport


@dataclass
class OwnershipEntry:
    address: str
    action: str
    owner: Optional[str]
    team: Optional[str]
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class OwnershipReport:
    entries: List[OwnershipEntry] = field(default_factory=list)

    def by_team(self) -> Dict[str, List[OwnershipEntry]]:
        result: Dict[str, List[OwnershipEntry]] = {}
        for e in self.entries:
            key = e.team or "(unowned)"
            result.setdefault(key, []).append(e)
        return result

    def unowned(self) -> List[OwnershipEntry]:
        return [e for e in self.entries if not e.owner and not e.team]


def build_ownership(
    report: DiffReport,
    ownership_map: Dict[str, Dict[str, str]],
) -> OwnershipReport:
    """Attach owner/team metadata from *ownership_map* to each diff entry.

    The map keys are resource addresses (or prefixes ending with ``*``).
    Each value is a dict that may contain ``owner``, ``team``, and arbitrary
    label keys.
    """
    entries: List[OwnershipEntry] = []
    for diff_entry in report.entries:
        addr = diff_entry.address
        meta = _lookup(addr, ownership_map)
        entries.append(
            OwnershipEntry(
                address=addr,
                action=diff_entry.action,
                owner=meta.get("owner"),
                team=meta.get("team"),
                labels={k: v for k, v in meta.items() if k not in ("owner", "team")},
            )
        )
    return OwnershipReport(entries=entries)


def _lookup(address: str, mapping: Dict[str, Dict[str, str]]) -> Dict[str, str]:
    """Return metadata for *address*, trying exact match then prefix wildcards."""
    if address in mapping:
        return mapping[address]
    for key, meta in mapping.items():
        if key.endswith("*") and address.startswith(key[:-1]):
            return meta
    return {}
