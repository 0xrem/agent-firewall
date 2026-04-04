"""Internal runtime-context helpers for correlating workflow events."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from .events import EventContext


_RUNTIME_CONTEXT: ContextVar[dict[str, Any] | None] = ContextVar(
    "agentfirewall_runtime_context",
    default=None,
)

REQUIRED_RUNTIME_CONTEXT_FIELDS: tuple[str, ...] = (
    "runtime",
    "tool_name",
    "tool_call_id",
    "tool_event_source",
)

SIDE_EFFECT_RUNTIME_EVENT_KINDS: tuple[str, ...] = (
    "command",
    "file_access",
    "http_request",
    "resource_access",
)


def current_runtime_context() -> dict[str, Any]:
    """Return the current correlated runtime context, if any."""

    current = _RUNTIME_CONTEXT.get()
    return dict(current) if current else {}


def missing_runtime_context_fields(
    metadata: Mapping[str, Any] | None,
    *,
    required_fields: tuple[str, ...] = REQUIRED_RUNTIME_CONTEXT_FIELDS,
) -> tuple[str, ...]:
    """Return the required runtime-context fields missing from metadata."""

    if not isinstance(metadata, Mapping):
        return required_fields

    missing: list[str] = []
    for field in required_fields:
        value = metadata.get(field)
        if value in (None, "", (), [], {}):
            missing.append(field)
    return tuple(missing)


def build_tool_runtime_context(
    *,
    runtime: str,
    tool_name: str | None = None,
    tool_call_id: str | None = None,
    tool_event_source: str | None = None,
    **metadata: Any,
) -> dict[str, Any]:
    """Build a normalized runtime-context payload for a tool-triggered flow."""

    context: dict[str, Any] = {}
    declared = {
        "runtime": runtime,
        "tool_name": tool_name,
        "tool_call_id": tool_call_id,
        "tool_event_source": tool_event_source,
    }
    declared.update(metadata)

    for key, value in declared.items():
        if value in (None, "", (), [], {}):
            continue
        context[key] = value
    return context


@contextmanager
def tool_runtime_context(
    *,
    runtime: str,
    tool_name: str | None = None,
    tool_call_id: str | None = None,
    tool_event_source: str | None = None,
    **metadata: Any,
) -> Iterator[None]:
    """Apply normalized runtime-context metadata for a tool-triggered flow."""

    context = build_tool_runtime_context(
        runtime=runtime,
        tool_name=tool_name,
        tool_call_id=tool_call_id,
        tool_event_source=tool_event_source,
        **metadata,
    )
    with runtime_event_context(**context):
        yield


def build_mcp_runtime_context(
    *,
    runtime: str,
    tool_name: str | None = None,
    tool_call_id: str | None = None,
    tool_event_source: str | None = None,
    protocol: str = "mcp",
    mcp_direction: str | None = None,
    mcp_server_name: str | None = None,
    mcp_resource_uri: str | None = None,
    mcp_operation: str | None = None,
    **metadata: Any,
) -> dict[str, Any]:
    """Build runtime context enriched with optional MCP metadata."""

    return build_tool_runtime_context(
        runtime=runtime,
        tool_name=tool_name,
        tool_call_id=tool_call_id,
        tool_event_source=tool_event_source,
        protocol=protocol,
        mcp_direction=mcp_direction,
        mcp_server_name=mcp_server_name,
        mcp_resource_uri=mcp_resource_uri,
        mcp_operation=mcp_operation,
        **metadata,
    )


@contextmanager
def mcp_tool_runtime_context(
    *,
    runtime: str,
    tool_name: str | None = None,
    tool_call_id: str | None = None,
    tool_event_source: str | None = None,
    protocol: str = "mcp",
    mcp_direction: str | None = None,
    mcp_server_name: str | None = None,
    mcp_resource_uri: str | None = None,
    mcp_operation: str | None = None,
    **metadata: Any,
) -> Iterator[None]:
    """Apply tool runtime context enriched with optional MCP metadata."""

    context = build_mcp_runtime_context(
        runtime=runtime,
        tool_name=tool_name,
        tool_call_id=tool_call_id,
        tool_event_source=tool_event_source,
        protocol=protocol,
        mcp_direction=mcp_direction,
        mcp_server_name=mcp_server_name,
        mcp_resource_uri=mcp_resource_uri,
        mcp_operation=mcp_operation,
        **metadata,
    )
    with runtime_event_context(**context):
        yield


@contextmanager
def runtime_event_context(**metadata: Any) -> Iterator[None]:
    """Temporarily enrich nested runtime events with correlation metadata."""

    current = current_runtime_context()
    for key, value in metadata.items():
        if value in (None, "", (), [], {}):
            continue
        current[key] = value

    token = _RUNTIME_CONTEXT.set(current or None)
    try:
        yield
    finally:
        _RUNTIME_CONTEXT.reset(token)


def attach_runtime_context(event: EventContext) -> EventContext:
    """Attach the active runtime context to an event payload if present."""

    metadata = current_runtime_context()
    if not metadata:
        return event

    payload = dict(event.payload)
    existing = payload.get("runtime_context")
    if isinstance(existing, Mapping):
        merged = dict(existing)
        merged.update(metadata)
    else:
        merged = metadata
    payload["runtime_context"] = merged
    event.payload = payload
    return event
