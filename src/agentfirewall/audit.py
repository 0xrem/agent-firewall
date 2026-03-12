"""Audit models for runtime decisions."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
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

    def to_dict(self) -> dict[str, object]:
        return {
            "created_at": self.created_at.isoformat(),
            "event": self.event.to_dict(),
            "decision": self.decision.to_dict(),
        }


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

    def export(self) -> list[dict[str, object]]:
        return [entry.to_dict() for entry in self.entries]

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.export(), indent=indent, sort_keys=True)


@dataclass(slots=True)
class JsonLinesAuditSink:
    """Append audit entries to a JSONL file for local inspection."""

    path: str | Path

    def record(self, entry: AuditEntry) -> None:
        target = Path(self.path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry.to_dict(), sort_keys=True))
            handle.write("\n")
