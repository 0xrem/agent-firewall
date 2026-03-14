"""Tool-dispatch helpers guarded by AgentFirewall."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from ..events import EventContext
from ..firewall import AgentFirewall
from ..runtime_context import tool_runtime_context


def _default_tool_call_id(
    name: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> str:
    normalized_name = name or "tool"
    return f"call_{normalized_name}_{uuid4().hex[:12]}"


@dataclass(slots=True)
class GuardedToolDispatcher:
    """Evaluate tool dispatch before invoking the underlying callable."""

    firewall: AgentFirewall
    tools: dict[str, Callable[..., Any]] = field(default_factory=dict)
    dispatcher: Callable[[str, tuple[Any, ...], dict[str, Any]], Any] | None = None
    source: str = "agent"
    runtime: str = "generic"
    tool_call_id_factory: Callable[[str, tuple[Any, ...], dict[str, Any]], str] = (
        _default_tool_call_id
    )

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
        tool_call_id = self.tool_call_id_factory(
            name,
            normalized_args,
            normalized_kwargs,
        )
        event = EventContext.tool_call(
            name,
            args=normalized_args,
            kwargs=normalized_kwargs,
            source=self.source,
        )
        event.payload["tool_call_id"] = tool_call_id
        self.firewall.enforce(event)

        with tool_runtime_context(
            runtime=self.runtime,
            tool_name=name,
            tool_call_id=tool_call_id,
            tool_event_source=self.source,
        ):
            if self.dispatcher is not None:
                return self.dispatcher(name, normalized_args, normalized_kwargs)

            if name not in self.tools:
                raise KeyError(f"Unknown tool: {name}")

            return self.tools[name](*normalized_args, **normalized_kwargs)
