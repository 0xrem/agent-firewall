"""Approval flow models and helpers for review-required runtime actions."""

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

__all__ = [
    "ApprovalHandler",
    "ApprovalOutcome",
    "ApprovalRequest",
    "ApprovalResponse",
    "StaticApprovalHandler",
    "TerminalApprovalHandler",
    "approve_all",
    "deny_all",
    "normalize_approval_response",
    "timeout_all",
]


@dataclass(slots=True)
class StaticApprovalHandler:
    """Deterministic approval handler for local demos, evals, and simple integrations.

    Matching order:

    1. exact tool name for `tool_call` events
    2. event kind name such as `prompt` or `http_request`
    3. the default outcome
    """

    default: ApprovalResponse | ApprovalOutcome | str | bool = ApprovalOutcome.TIMEOUT
    tool_outcomes: dict[str, ApprovalResponse | ApprovalOutcome | str | bool] = field(
        default_factory=dict
    )
    event_outcomes: dict[str, ApprovalResponse | ApprovalOutcome | str | bool] = field(
        default_factory=dict
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    def __call__(self, request: ApprovalRequest) -> ApprovalResponse:
        tool_name = str(request.event.payload.get("name", "")).lower()
        event_kind = request.event.kind.value

        if tool_name and tool_name in self.tool_outcomes:
            matched = "tool"
            selector = tool_name
            response = self.tool_outcomes[tool_name]
        elif event_kind in self.event_outcomes:
            matched = "event"
            selector = event_kind
            response = self.event_outcomes[event_kind]
        else:
            matched = "default"
            selector = "default"
            response = self.default

        normalized = normalize_approval_response(response)
        metadata = dict(self.metadata)
        metadata.update(normalized.metadata)
        metadata["approval_match_type"] = matched
        metadata["approval_match_value"] = selector
        return ApprovalResponse(
            outcome=normalized.outcome,
            reason=normalized.reason,
            metadata=metadata,
        )


def approve_all(
    *,
    reason: str = "Static approval handler approved the action.",
    metadata: dict[str, Any] | None = None,
) -> StaticApprovalHandler:
    """Return a handler that approves every review-required action."""

    return StaticApprovalHandler(
        default=ApprovalResponse.approve(reason=reason, metadata=metadata),
    )


def deny_all(
    *,
    reason: str = "Static approval handler denied the action.",
    metadata: dict[str, Any] | None = None,
) -> StaticApprovalHandler:
    """Return a handler that denies every review-required action."""

    return StaticApprovalHandler(
        default=ApprovalResponse.deny(reason=reason, metadata=metadata),
    )


def timeout_all(
    *,
    reason: str = "Static approval handler timed out.",
    metadata: dict[str, Any] | None = None,
) -> StaticApprovalHandler:
    """Return a handler that times out every review-required action."""

    return StaticApprovalHandler(
        default=ApprovalResponse.timeout(reason=reason, metadata=metadata),
    )


@dataclass(slots=True)
class TerminalApprovalHandler:
    """Interactive approval handler that prompts in the terminal.

    When a review decision is triggered, this handler prints the event details
    and asks the user to approve or deny the action in the terminal.

    This is the recommended handler for local development — it lets you see
    exactly what the agent is trying to do and decide in real-time.
    """

    default_deny: bool = True
    prompt_text: str = "  Allow? [y/N]: "
    metadata: dict[str, Any] = field(default_factory=dict)

    def __call__(self, request: ApprovalRequest) -> ApprovalResponse:
        import sys

        kind = request.event.kind.value
        rule = request.decision.rule or "unknown"
        reason = request.decision.reason or ""

        detail = ""
        if kind == "tool_call":
            tool = request.event.payload.get("name", "")
            detail = f"  Tool:   {tool}" if tool else ""
        elif kind == "file_access":
            path = request.event.payload.get("path", "")
            detail = f"  Path:   {path}" if path else ""
        elif kind == "http_request":
            host = request.event.payload.get("hostname", "")
            url = request.event.payload.get("url", "")
            detail = f"  Host:   {host}" if host else ""
            if url:
                detail += f"\n  URL:    {url}"
        elif kind == "command":
            cmd = request.event.payload.get("command_text", "")
            detail = f"  Cmd:    {cmd}" if cmd else ""

        print(f"--- AgentFirewall Review ---", file=sys.stderr)
        print(f"  Event:  {kind}", file=sys.stderr)
        if detail:
            print(detail, file=sys.stderr)
        print(f"  Rule:   {rule}", file=sys.stderr)
        if reason:
            print(f"  Reason: {reason}", file=sys.stderr)

        try:
            answer = input(self.prompt_text).strip().lower()
        except (EOFError, KeyboardInterrupt):
            answer = ""

        metadata = dict(self.metadata)
        metadata["approval_source"] = "terminal"

        if answer in ("y", "yes"):
            return ApprovalResponse.approve(
                reason="Approved by user in terminal.",
                metadata=metadata,
            )

        return ApprovalResponse.deny(
            reason="Denied by user in terminal.",
            metadata=metadata,
        )


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
