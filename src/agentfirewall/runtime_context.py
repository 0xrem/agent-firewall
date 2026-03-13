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
