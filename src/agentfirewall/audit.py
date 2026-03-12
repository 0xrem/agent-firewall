"""Audit models for runtime decisions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol

from .events import EventContext
from .policy import Decision


@dataclass(slots=True)
class AuditEntry:
    """Recorded decision for an evaluated runtime event."""

    event: EventContext
    decision: Decision
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class AuditSink(Protocol):
    """Minimal sink interface for audit destinations."""

    def record(self, entry: AuditEntry) -> None:
        """Record an audit entry."""


@dataclass(slots=True)
class InMemoryAuditSink:
    """Simple in-memory sink for tests, demos, and local development."""

    entries: list[AuditEntry] = field(default_factory=list)

    def record(self, entry: AuditEntry) -> None:
        self.entries.append(entry)

    def snapshot(self) -> list[AuditEntry]:
        return list(self.entries)
