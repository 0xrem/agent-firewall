"""Tool-dispatch helpers guarded by AgentFirewall."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from ..events import EventContext
from ..firewall import AgentFirewall


@dataclass(slots=True)
class GuardedToolDispatcher:
    """Evaluate tool dispatch before invoking the underlying callable."""

    firewall: AgentFirewall
    tools: dict[str, Callable[..., Any]] = field(default_factory=dict)
    dispatcher: Callable[[str, dict[str, Any]], Any] | None = None
    source: str = "agent"

    def register(self, name: str, tool: Callable[..., Any]) -> None:
        self.tools[name] = tool

    def dispatch(
        self,
        name: str,
        *,
        arguments: Mapping[str, Any] | None = None,
    ) -> Any:
        normalized_arguments = dict(arguments or {})
        event = EventContext.tool_call(
            name,
            arguments=normalized_arguments,
            source=self.source,
        )
        self.firewall.enforce(event)

        if self.dispatcher is not None:
            return self.dispatcher(name, normalized_arguments)

        if name not in self.tools:
            raise KeyError(f"Unknown tool: {name}")

        return self.tools[name](**normalized_arguments)
