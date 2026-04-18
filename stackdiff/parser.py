"""Parse Terraform plan output into structured change objects."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class ChangeAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DESTROY = "destroy"
    REPLACE = "replace"
    NO_CHANGE = "no-change"


@dataclass
class ResourceChange:
    address: str
    action: ChangeAction
    resource_type: str
    resource_name: str
    module: Optional[str] = None
    attributes: dict = field(default_factory=dict)

    @property
    def short_address(self) -> str:
        return self.address.split(".")[-2] + "." + self.address.split(".")[-1]


# Symbols used in terraform plan text output
_ACTION_MAP = {
    "+": ChangeAction.CREATE,
    "-": ChangeAction.DESTROY,
    "~": ChangeAction.UPDATE,
    "-/+": ChangeAction.REPLACE,
    "+/-": ChangeAction.REPLACE,
}

_RESOURCE_RE = re.compile(
    r"^(?P<action>[+\-~]{1,3})\s+(?P<address>[\w.\[\]\"/-]+)", re.MULTILINE
)


def parse_plan_text(plan_text: str) -> List[ResourceChange]:
    """Extract resource changes from terraform plan stdout."""
    changes: List[ResourceChange] = []
    for match in _RESOURCE_RE.finditer(plan_text):
        raw_action = match.group("action").strip()
        action = _ACTION_MAP.get(raw_action, ChangeAction.NO_CHANGE)
        address = match.group("address")
        parts = address.split(".")
        if len(parts) < 2:
            continue
        resource_type = parts[-2]
        resource_name = parts[-1]
        module = ".".join(parts[:-2]) if len(parts) > 2 else None
        changes.append(
            ResourceChange(
                address=address,
                action=action,
                resource_type=resource_type,
                resource_name=resource_name,
                module=module,
            )
        )
    return changes
