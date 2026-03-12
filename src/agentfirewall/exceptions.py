"""Custom exceptions for AgentFirewall."""

from __future__ import annotations

from .events import EventContext
from .policy import Decision


class AgentFirewallError(Exception):
    """Base exception for the package."""


class FirewallViolation(AgentFirewallError):
    """Raised when a policy blocks an action."""

    def __init__(self, decision: Decision, event: EventContext):
        self.decision = decision
        self.event = event

        if decision.reason:
            message = decision.reason
        else:
            message = (
                f"AgentFirewall blocked {event.kind.value} during "
                f"{event.operation or 'execution'}."
            )

        super().__init__(message)
