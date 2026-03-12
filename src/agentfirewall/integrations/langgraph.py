"""LangGraph runtime adapter helpers."""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Mapping, Sequence
from contextlib import nullcontext
from typing import Any

from ..approval import ApprovalHandler
from ..audit import AuditSink, InMemoryAuditSink
from ..config import FirewallConfig
from ..enforcers import (
    GuardedFileAccess,
    GuardedHttpClient,
    GuardedSubprocessRunner,
)
from ..events import EventContext
from ..firewall import AgentFirewall, create_firewall
from ..policy_packs import (
    PolicyPackConfig,
)
from ..runtime_context import runtime_event_context

try:
    from langchain.agents.middleware import AgentMiddleware
except ImportError:  # pragma: no cover - exercised when optional deps are absent.
    class AgentMiddleware:  # type: ignore[no-redef]
        """Fallback base class when LangGraph dependencies are unavailable."""

        pass


def _langgraph_tool_decorator(*, name: str, description: str):
    try:
        from langchain_core.tools import tool
    except ImportError as exc:  # pragma: no cover - exercised when optional deps are absent.
        raise ImportError(
            "LangGraph guarded tools require optional dependencies. "
            "Install with `pip install agentfirewall[langgraph]`."
        ) from exc

    return tool(
        name,
        description=description,
        parse_docstring=False,
    )


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


def _normalize_text_output(
    value: Any,
    *,
    encoding: str = "utf-8",
    strip_output: bool,
) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        text = value.decode(encoding, errors="replace")
    else:
        text = str(value)
    return text.strip() if strip_output else text


def _read_text_resource(
    resource: Any,
    *,
    encoding: str = "utf-8",
    max_chars: int | None = 4096,
    strip_output: bool = False,
) -> str:
    def _read(handle: Any) -> Any:
        if not hasattr(handle, "read"):
            return handle
        if max_chars is None:
            return handle.read()
        return handle.read(max_chars)

    if hasattr(resource, "__enter__") and hasattr(resource, "__exit__"):
        with resource as handle:
            payload = _read(handle)
    else:
        try:
            payload = _read(resource)
        finally:
            closer = getattr(resource, "close", None)
            if callable(closer):
                closer()

    return _normalize_text_output(
        payload,
        encoding=encoding,
        strip_output=strip_output,
    )


def _format_subprocess_result(
    result: Any,
    *,
    encoding: str = "utf-8",
    strip_output: bool = True,
) -> str:
    stdout = getattr(result, "stdout", None)
    if stdout not in (None, ""):
        return _normalize_text_output(
            stdout,
            encoding=encoding,
            strip_output=strip_output,
        )

    stderr = getattr(result, "stderr", None)
    if stderr not in (None, ""):
        return _normalize_text_output(
            stderr,
            encoding=encoding,
            strip_output=strip_output,
        )

    if isinstance(result, subprocess.CompletedProcess):
        return _normalize_text_output(
            result.returncode,
            encoding=encoding,
            strip_output=strip_output,
        )

    return _normalize_text_output(
        result,
        encoding=encoding,
        strip_output=strip_output,
    )


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
        event = self._tool_event(request.tool_call)
        self.firewall.enforce(event)
        with self._tool_execution_context(request.tool_call):
            return handler(request)

    async def awrap_tool_call(self, request: Any, handler: Any) -> Any:
        event = self._tool_event(request.tool_call)
        self.firewall.enforce(event)
        with self._tool_execution_context(request.tool_call):
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

    def _tool_execution_context(self, tool_call: Mapping[str, Any]) -> Any:
        tool_name = str(tool_call.get("name", "")).lower()
        tool_call_id = tool_call.get("id")
        if not tool_name and tool_call_id is None:
            return nullcontext()

        return runtime_event_context(
            runtime=self.source,
            tool_name=tool_name,
            tool_call_id=(
                str(tool_call_id)
                if tool_call_id is not None
                else None
            ),
            tool_event_source=f"{self.source}.tool",
        )


def create_firewalled_langgraph_agent(
    *,
    model: Any,
    tools: Sequence[Any] | None = None,
    firewall: AgentFirewall | None = None,
    config: FirewallConfig | None = None,
    policy_pack: str | PolicyPackConfig = "default",
    audit_sink: AuditSink | None = None,
    approval_handler: ApprovalHandler | None = None,
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

    if firewall is not None and (
        config is not None
        or audit_sink is not None
        or approval_handler is not None
        or policy_pack != "default"
    ):
        raise TypeError(
            "Pass either `firewall` or high-level firewall parameters, not both."
        )

    if firewall is None:
        resolved_firewall = create_firewall(
            config=config or FirewallConfig(),
            policy_pack=policy_pack,
            audit_sink=(
                audit_sink
                if audit_sink is not None
                else InMemoryAuditSink()
            ),
            approval_handler=approval_handler,
        )
    else:
        resolved_firewall = firewall

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


def create_guarded_langgraph_shell_tool(
    *,
    firewall: AgentFirewall,
    name: str = "shell",
    description: str = (
        "Run a shell command through AgentFirewall-guarded subprocess execution."
    ),
    source: str = "langgraph.shell",
    runner: Callable[..., Any] | None = None,
    shell: bool = True,
    run_kwargs: Mapping[str, Any] | None = None,
    encoding: str = "utf-8",
    strip_output: bool = True,
) -> Any:
    """Create a LangGraph tool that guards shell execution with AgentFirewall."""

    decorator = _langgraph_tool_decorator(name=name, description=description)
    runner_kwargs = {"capture_output": True, "text": True, "check": False}
    if run_kwargs is not None:
        runner_kwargs.update(dict(run_kwargs))

    guarded_runner_kwargs: dict[str, Any] = {
        "firewall": firewall,
        "source": f"{source}.command",
    }
    if runner is not None:
        guarded_runner_kwargs["runner"] = runner
    guarded_runner = GuardedSubprocessRunner(**guarded_runner_kwargs)

    @decorator
    def guarded_shell(command: str, cwd: str = "") -> str:
        """Run a shell command through AgentFirewall-guarded subprocess execution."""

        invocation_kwargs = dict(runner_kwargs)
        if cwd:
            invocation_kwargs["cwd"] = cwd
        result = guarded_runner.run(command, shell=shell, **invocation_kwargs)
        return _format_subprocess_result(
            result,
            encoding=encoding,
            strip_output=strip_output,
        )

    return guarded_shell


def create_guarded_langgraph_http_tool(
    *,
    firewall: AgentFirewall,
    name: str = "http_request",
    description: str = (
        "Send an outbound HTTP request through AgentFirewall-guarded network enforcement."
    ),
    source: str = "langgraph.http",
    opener: Callable[..., Any] | None = None,
    request_kwargs: Mapping[str, Any] | None = None,
    encoding: str = "utf-8",
    max_chars: int | None = 4096,
    strip_output: bool = False,
) -> Any:
    """Create a LangGraph tool that guards outbound HTTP requests."""

    decorator = _langgraph_tool_decorator(name=name, description=description)
    client_kwargs: dict[str, Any] = {
        "firewall": firewall,
        "source": f"{source}.request",
    }
    if opener is not None:
        client_kwargs["opener"] = opener
    guarded_client = GuardedHttpClient(**client_kwargs)
    resolved_request_kwargs = dict(request_kwargs or {})

    @decorator
    def guarded_http_request(url: str, method: str = "GET") -> str:
        """Send an outbound HTTP request through AgentFirewall-guarded network enforcement."""

        response = guarded_client.request(
            url,
            method=method,
            **dict(resolved_request_kwargs),
        )
        return _read_text_resource(
            response,
            encoding=encoding,
            max_chars=max_chars,
            strip_output=strip_output,
        )

    return guarded_http_request


def create_guarded_langgraph_file_reader_tool(
    *,
    firewall: AgentFirewall,
    name: str = "read_file",
    description: str = (
        "Read a local file through AgentFirewall-guarded filesystem enforcement."
    ),
    source: str = "langgraph.file",
    opener: Callable[..., Any] | None = None,
    read_kwargs: Mapping[str, Any] | None = None,
    encoding: str = "utf-8",
    max_chars: int | None = 4096,
    strip_output: bool = False,
) -> Any:
    """Create a LangGraph tool that guards local file reads."""

    decorator = _langgraph_tool_decorator(name=name, description=description)
    access_kwargs: dict[str, Any] = {
        "firewall": firewall,
        "source": f"{source}.file",
    }
    if opener is not None:
        access_kwargs["opener"] = opener
    file_access = GuardedFileAccess(**access_kwargs)

    @decorator
    def guarded_file_reader(path: str) -> str:
        """Read a local file through AgentFirewall-guarded filesystem enforcement."""

        open_kwargs = dict(read_kwargs or {})
        if "encoding" not in open_kwargs:
            open_kwargs["encoding"] = encoding
        handle = file_access.open(path, "r", **open_kwargs)
        return _read_text_resource(
            handle,
            encoding=encoding,
            max_chars=max_chars,
            strip_output=strip_output,
        )

    return guarded_file_reader
