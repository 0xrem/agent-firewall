"""Filesystem helpers guarded by AgentFirewall."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from ..events import EventContext
from ..firewall import AgentFirewall
from ..runtime_context import attach_runtime_context


def _normalize_mode(mode: str) -> str:
    if any(flag in mode for flag in ("w", "a", "+", "x")):
        return "write"

    return "read"


@dataclass(slots=True)
class GuardedFileAccess:
    """Evaluate file access before delegating to a real opener."""

    firewall: AgentFirewall
    opener: Callable[..., Any] = field(default=open)
    source: str = "agent"

    def open(self, path: str, mode: str = "r", **kwargs: Any) -> Any:
        event = attach_runtime_context(
            EventContext.file_access(
                path,
                mode=_normalize_mode(mode),
                source=self.source,
            )
        )
        self.firewall.enforce(event)
        return self.opener(path, mode, **kwargs)
