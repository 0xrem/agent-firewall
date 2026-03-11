"""Core data models used by AgentFirewall."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class DecisionAction(str, Enum):
    """Supported outcomes for a policy decision."""

    ALLOW = "allow"
    BLOCK = "block"
    REVIEW = "review"
    LOG = "log"


@dataclass(slots=True)
class Decision:
    """Result returned after evaluating an event."""

    action: DecisionAction
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EventContext:
    """Normalized event payload passed through the firewall."""

    kind: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    source: str = "agent"
