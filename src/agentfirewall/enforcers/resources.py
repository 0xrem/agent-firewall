"""Resource-access helpers guarded by AgentFirewall."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from ..events import EventContext
from ..firewall import AgentFirewall
from ..runtime_context import attach_runtime_context


@dataclass(slots=True)
class GuardedResourceReader:
    """Evaluate resource reads before delegating to a reader callable."""

    firewall: AgentFirewall
    reader: Callable[..., Any]
    source: str = "agent"

    def read(
        self,
        uri: str,
        *,
        server_name: str | None = None,
        mime_type: str | None = None,
        **kwargs: Any,
    ) -> Any:
        event = attach_runtime_context(
            EventContext.resource_access(
                uri,
                server_name=server_name,
                mime_type=mime_type,
                source=self.source,
            )
        )
        self.firewall.enforce(event)
        return self.reader(uri, **kwargs)
