"""Normalized runtime event models used by AgentFirewall."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable

from .serialization import to_jsonable


class EventKind(str, Enum):
    """Runtime surfaces that the firewall can evaluate."""

    PROMPT = "prompt"
    TOOL_CALL = "tool_call"
    COMMAND = "command"
    FILE_ACCESS = "file_access"
    HTTP_REQUEST = "http_request"


def _command_to_text(command: str | Iterable[str]) -> str:
    if isinstance(command, str):
        return command

    return " ".join(str(part) for part in command)


@dataclass(slots=True)
class EventContext:
    """Normalized event payload passed through the firewall."""

    kind: EventKind | str
    operation: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    source: str = "agent"
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if isinstance(self.kind, str):
            self.kind = EventKind(self.kind)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "operation": self.operation,
            "payload": to_jsonable(self.payload),
            "source": self.source,
            "tags": list(self.tags),
        }

    @classmethod
    def prompt(cls, text: str, *, source: str = "agent") -> "EventContext":
        return cls(
            kind=EventKind.PROMPT,
            operation="inspect",
            payload={"text": text},
            source=source,
        )

    @classmethod
    def tool_call(
        cls,
        name: str,
        *,
        arguments: dict[str, Any] | None = None,
        source: str = "agent",
    ) -> "EventContext":
        return cls(
            kind=EventKind.TOOL_CALL,
            operation="dispatch",
            payload={"name": name, "arguments": arguments or {}},
            source=source,
        )

    @classmethod
    def command(
        cls,
        command: str | Iterable[str],
        *,
        shell: bool = False,
        cwd: str | None = None,
        source: str = "agent",
    ) -> "EventContext":
        return cls(
            kind=EventKind.COMMAND,
            operation="execute",
            payload={
                "command": command,
                "command_text": _command_to_text(command),
                "shell": shell,
                "cwd": cwd,
            },
            source=source,
        )

    @classmethod
    def file_access(
        cls,
        path: str,
        *,
        mode: str,
        source: str = "agent",
    ) -> "EventContext":
        return cls(
            kind=EventKind.FILE_ACCESS,
            operation=mode,
            payload={"path": path, "mode": mode},
            source=source,
        )

    @classmethod
    def http_request(
        cls,
        url: str,
        *,
        method: str = "GET",
        source: str = "agent",
    ) -> "EventContext":
        normalized_method = method.upper()
        return cls(
            kind=EventKind.HTTP_REQUEST,
            operation=normalized_method,
            payload={"url": url, "method": normalized_method},
            source=source,
        )
