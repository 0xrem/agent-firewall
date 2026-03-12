"""Audit models for runtime decisions."""

from __future__ import annotations

import json
from collections.abc import Mapping
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


@dataclass(slots=True)
class AuditSummary:
    """Aggregate counts for a group of audit entries."""

    total: int
    action_counts: dict[str, int]
    event_kind_counts: dict[str, int]
    rule_counts: dict[str, int]
    source_counts: dict[str, int]
    tool_name_counts: dict[str, int]

    def to_dict(self) -> dict[str, object]:
        return {
            "total": self.total,
            "action_counts": dict(self.action_counts),
            "event_kind_counts": dict(self.event_kind_counts),
            "rule_counts": dict(self.rule_counts),
            "source_counts": dict(self.source_counts),
            "tool_name_counts": dict(self.tool_name_counts),
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

    def summary(self) -> AuditSummary:
        action_counts: dict[str, int] = {}
        event_kind_counts: dict[str, int] = {}
        rule_counts: dict[str, int] = {}
        source_counts: dict[str, int] = {}
        tool_name_counts: dict[str, int] = {}

        for entry in self.entries:
            action = entry.decision.action.value
            kind = entry.event.kind.value
            rule = entry.decision.rule or "unknown"
            source = entry.event.source or "unknown"
            tool_name = ""
            if entry.event.kind.value == "tool_call":
                tool_name = str(entry.event.payload.get("name", "")).lower()
            else:
                runtime_context = entry.event.payload.get("runtime_context")
                if isinstance(runtime_context, Mapping):
                    tool_name = str(runtime_context.get("tool_name", "")).lower()

            action_counts[action] = action_counts.get(action, 0) + 1
            event_kind_counts[kind] = event_kind_counts.get(kind, 0) + 1
            rule_counts[rule] = rule_counts.get(rule, 0) + 1
            source_counts[source] = source_counts.get(source, 0) + 1
            if tool_name:
                tool_name_counts[tool_name] = tool_name_counts.get(tool_name, 0) + 1

        return AuditSummary(
            total=len(self.entries),
            action_counts=action_counts,
            event_kind_counts=event_kind_counts,
            rule_counts=rule_counts,
            source_counts=source_counts,
            tool_name_counts=tool_name_counts,
        )

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
