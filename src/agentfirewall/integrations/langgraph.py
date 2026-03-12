"""LangGraph runtime adapter helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..events import EventContext
from ..firewall import AgentFirewall
from ..policy_packs import build_builtin_policy_engine, named_policy_pack

try:
    from langchain.agents.middleware import AgentMiddleware
except ImportError:  # pragma: no cover - exercised when optional deps are absent.
    class AgentMiddleware:  # type: ignore[no-redef]
        """Fallback base class when LangGraph dependencies are unavailable."""

        pass


def _message_role(message: Any) -> str:
    return str(
        getattr(
            message,
            "type",
            getattr(message, "role", ""),
        )
    ).lower()


def _message_text(content: Any) -> str:
    if isinstance(content, str):
        return content

    if isinstance(content, Sequence) and not isinstance(
        content,
        (str, bytes, bytearray),
    ):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, Mapping):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(part for part in parts if part)

    return ""


def _latest_user_text(messages: Sequence[Any]) -> str:
    if not messages:
        return ""

    last_message = messages[-1]
    if _message_role(last_message) not in {"human", "user"}:
        return ""

    return _message_text(getattr(last_message, "content", ""))


def _normalize_tool_payload(tool_call: Mapping[str, Any]) -> tuple[tuple[Any, ...], dict[str, Any]]:
    raw_args = tool_call.get("args")
    if raw_args is None:
        return (), {}
    if isinstance(raw_args, Mapping):
        return (), dict(raw_args)
    if isinstance(raw_args, Sequence) and not isinstance(
        raw_args,
        (str, bytes, bytearray),
    ):
        return tuple(raw_args), {}

    return (raw_args,), {}


class LangGraphFirewallMiddleware(AgentMiddleware):
    """Middleware that routes LangGraph runtime events through AgentFirewall."""

    def __init__(
        self,
        firewall: AgentFirewall,
        *,
        inspect_prompts: bool = True,
        source: str = "langgraph",
    ) -> None:
        self.firewall = firewall
        self.inspect_prompts = inspect_prompts
        self.source = source

    def before_model(self, state: Mapping[str, Any], runtime: Any) -> dict[str, Any] | None:
        if not self.inspect_prompts:
            return None

        messages = state.get("messages", ())
        if not isinstance(messages, Sequence):
            return None

        prompt_text = _latest_user_text(messages)
        if not prompt_text:
            return None

        self.firewall.enforce(
            EventContext.prompt(
                prompt_text,
                source=f"{self.source}.prompt",
            )
        )
        return None

    def wrap_tool_call(self, request: Any, handler: Any) -> Any:
        self.firewall.enforce(self._tool_event(request.tool_call))
        return handler(request)

    async def awrap_tool_call(self, request: Any, handler: Any) -> Any:
        self.firewall.enforce(self._tool_event(request.tool_call))
        return await handler(request)

    def _tool_event(self, tool_call: Mapping[str, Any]) -> EventContext:
        args, kwargs = _normalize_tool_payload(tool_call)
        event = EventContext.tool_call(
            str(tool_call.get("name", "")),
            args=args,
            kwargs=kwargs,
            source=f"{self.source}.tool",
        )
        tool_call_id = tool_call.get("id")
        if tool_call_id is not None:
            event.payload["tool_call_id"] = str(tool_call_id)
        return event


def create_firewalled_langgraph_agent(
    *,
    model: Any,
    tools: Sequence[Any] | None = None,
    firewall: AgentFirewall | None = None,
    middleware: Sequence[Any] = (),
    inspect_prompts: bool = True,
    source: str = "langgraph",
    **kwargs: Any,
) -> Any:
    """Create a LangGraph agent with AgentFirewall middleware attached."""

    try:
        from langchain.agents import create_agent
    except ImportError as exc:  # pragma: no cover - exercised when optional deps are absent.
        raise ImportError(
            "LangGraph integration requires optional dependencies. "
            "Install with `pip install agentfirewall[langgraph]`."
        ) from exc

    resolved_firewall = firewall or AgentFirewall(
        policy=build_builtin_policy_engine(named_policy_pack("default"))
    )
    adapter_middleware = LangGraphFirewallMiddleware(
        resolved_firewall,
        inspect_prompts=inspect_prompts,
        source=source,
    )
    agent = create_agent(
        model=model,
        tools=list(tools or ()),
        middleware=[adapter_middleware, *list(middleware)],
        **kwargs,
    )
    return resolved_firewall.wrap_agent(agent)
