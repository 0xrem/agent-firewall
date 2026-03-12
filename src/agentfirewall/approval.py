"""Approval flow models for review-required runtime actions."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .events import EventContext
from .policy import Decision


class ApprovalOutcome(str, Enum):
    """Supported outcomes for a review-required runtime action."""

    APPROVE = "approve"
    DENY = "deny"
    TIMEOUT = "timeout"


@dataclass(slots=True)
class ApprovalRequest:
    """Context passed to an approval handler."""

    event: EventContext
    decision: Decision
    firewall_name: str = "default"


@dataclass(slots=True)
class ApprovalResponse:
    """Resolved outcome returned by an approval handler."""

    outcome: ApprovalOutcome | str
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.outcome, str):
            self.outcome = ApprovalOutcome(self.outcome)

    @classmethod
    def approve(
        cls,
        *,
        reason: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> "ApprovalResponse":
        return cls(
            outcome=ApprovalOutcome.APPROVE,
            reason=reason,
            metadata=metadata or {},
        )

    @classmethod
    def deny(
        cls,
        *,
        reason: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> "ApprovalResponse":
        return cls(
            outcome=ApprovalOutcome.DENY,
            reason=reason,
            metadata=metadata or {},
        )

    @classmethod
    def timeout(
        cls,
        *,
        reason: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> "ApprovalResponse":
        return cls(
            outcome=ApprovalOutcome.TIMEOUT,
            reason=reason,
            metadata=metadata or {},
        )


ApprovalHandler = Callable[
    [ApprovalRequest],
    ApprovalResponse | ApprovalOutcome | str | bool,
]


def normalize_approval_response(
    response: ApprovalResponse | ApprovalOutcome | str | bool,
) -> ApprovalResponse:
    """Normalize shorthand approval values into an explicit response object."""

    if isinstance(response, ApprovalResponse):
        return response
    if isinstance(response, bool):
        if response:
            return ApprovalResponse.approve()
        return ApprovalResponse.deny(reason="Approval handler denied the action.")
    if isinstance(response, ApprovalOutcome):
        return ApprovalResponse(outcome=response)
    return ApprovalResponse(outcome=response)
