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
    dispatcher: Callable[[str, tuple[Any, ...], dict[str, Any]], Any] | None = None
    source: str = "agent"

    def register(self, name: str, tool: Callable[..., Any]) -> None:
        self.tools[name] = tool

    def dispatch(
        self,
        name: str,
        *args: Any,
        arguments: Mapping[str, Any] | None = None,
        kwargs: Mapping[str, Any] | None = None,
        **tool_kwargs: Any,
    ) -> Any:
        if arguments is not None and kwargs is not None:
            raise TypeError("Pass either kwargs or arguments, not both.")
        if (arguments is not None or kwargs is not None) and tool_kwargs:
            raise TypeError(
                "Pass tool keyword arguments either directly or via kwargs/arguments, not both."
            )

        normalized_kwargs = dict(arguments or kwargs or tool_kwargs)
        normalized_args = tuple(args)
        event = EventContext.tool_call(
            name,
            args=normalized_args,
            kwargs=normalized_kwargs,
            source=self.source,
        )
        self.firewall.enforce(event)

        if self.dispatcher is not None:
            return self.dispatcher(name, normalized_args, normalized_kwargs)

        if name not in self.tools:
            raise KeyError(f"Unknown tool: {name}")

        return self.tools[name](*normalized_args, **normalized_kwargs)
