"""OpenAI Agents SDK runtime adapter helpers."""

from __future__ import annotations

import dataclasses
import inspect
import json
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from ..approval import ApprovalHandler
from ..audit import AuditSink
from ..config import FirewallConfig
from ..enforcers import (
    GuardedFileAccess,
    GuardedHttpClient,
    GuardedSubprocessRunner,
)
from ..events import EventContext
from ..firewall import AgentFirewall
from ..policy_packs import PolicyPackConfig
from ..runtime_context import (
    attach_runtime_context,
    build_tool_runtime_context,
    runtime_event_context,
)
from .assembly import resolve_adapter_firewall
from .contracts import (
    AdapterCapability,
    AdapterSupportLevel,
    RuntimeAdapterSpec,
    capability_set,
)

try:
    from agents import FunctionTool, function_tool
    from agents.lifecycle import AgentHooksBase
except ImportError:  # pragma: no cover - exercised when optional deps are absent.
    FunctionTool = Any  # type: ignore[assignment]

    def function_tool(*args: Any, **kwargs: Any) -> Any:  # type: ignore[no-redef]
        raise ImportError

    class AgentHooksBase:  # type: ignore[no-redef]
        """Fallback base class when OpenAI Agents dependencies are unavailable."""

        pass


OPENAI_AGENTS_ADAPTER_SPEC = RuntimeAdapterSpec(
    name="openai_agents",
    module="agentfirewall.openai_agents",
    support_level=AdapterSupportLevel.EXPERIMENTAL,
    capabilities=capability_set(
        AdapterCapability.PROMPT_INSPECTION,
        AdapterCapability.TOOL_CALL_INTERCEPTION,
        AdapterCapability.RUNTIME_CONTEXT_CORRELATION,
        AdapterCapability.REVIEW_SEMANTICS,
        AdapterCapability.LOG_ONLY_SEMANTICS,
    ),
    notes=(
        "Experimental OpenAI Agents SDK adapter. Current scope is "
        "function_tool-first and excludes hosted tools, MCP servers, and handoffs."
    ),
)


def get_openai_agents_adapter_spec() -> RuntimeAdapterSpec:
    """Return the internal adapter contract for the OpenAI Agents integration."""

    return OPENAI_AGENTS_ADAPTER_SPEC


def _require_openai_agents() -> None:
    try:
        function_tool  # type: ignore[misc]
    except NameError as exc:  # pragma: no cover - defensive path
        raise ImportError(
            "OpenAI Agents integration requires optional dependencies. "
            "Install with `pip install agentfirewall[openai-agents]`."
        ) from exc

    if FunctionTool is Any:
        raise ImportError(
            "OpenAI Agents integration requires optional dependencies. "
            "Install with `pip install agentfirewall[openai-agents]`."
        )


def _normalize_openai_input_text(content: Any) -> str:
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
                    continue
                nested_text = item.get("content")
                if isinstance(nested_text, str):
                    parts.append(nested_text)
        return "\n".join(part for part in parts if part)

    return ""


def _latest_user_input_text(input_items: str | Sequence[Any]) -> str:
    if isinstance(input_items, str):
        return input_items
    if not input_items:
        return ""

    last_item = input_items[-1]
    if not isinstance(last_item, Mapping):
        return ""
    role = str(last_item.get("role", "")).lower()
    if role != "user":
        return ""
    return _normalize_openai_input_text(last_item.get("content", ""))


def _normalize_tool_call_input(input_json: str) -> tuple[tuple[Any, ...], dict[str, Any]]:
    if not input_json:
        return (), {}

    try:
        payload = json.loads(input_json)
    except json.JSONDecodeError:
        return (input_json,), {}

    if isinstance(payload, Mapping):
        return (), dict(payload)
    if isinstance(payload, Sequence) and not isinstance(
        payload,
        (str, bytes, bytearray),
    ):
        return tuple(payload), {}

    return (payload,), {}


def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return value
    return None


@dataclasses.dataclass(frozen=True, slots=True)
class OpenAIAgentsEventTranslator:
    """Translate OpenAI Agents runtime hooks into shared AgentFirewall events."""

    source: str = "openai_agents"

    @property
    def prompt_source(self) -> str:
        return f"{self.source}.prompt"

    @property
    def tool_source(self) -> str:
        return f"{self.source}.tool"

    def prompt_event(
        self,
        input_items: str | Sequence[Any],
    ) -> EventContext | None:
        prompt_text = _latest_user_input_text(input_items)
        if not prompt_text:
            return None
        return EventContext.prompt(prompt_text, source=self.prompt_source)

    def tool_event(
        self,
        tool_name: str,
        input_json: str,
    ) -> EventContext:
        args, kwargs = _normalize_tool_call_input(input_json)
        return EventContext.tool_call(
            tool_name,
            args=args,
            kwargs=kwargs,
            source=self.tool_source,
        )

    def tool_runtime_metadata(
        self,
        context: Any,
    ) -> dict[str, Any]:
        tool_name = getattr(context, "tool_name", None)
        tool_call_id = getattr(context, "tool_call_id", None)
        if tool_name in (None, "") and tool_call_id in (None, ""):
            return {}

        return build_tool_runtime_context(
            runtime=self.source,
            tool_name=str(tool_name) if tool_name not in (None, "") else None,
            tool_call_id=(
                str(tool_call_id)
                if tool_call_id not in (None, "")
                else None
            ),
            tool_event_source=self.tool_source,
        )


class OpenAIAgentsFirewallHooks(AgentHooksBase):
    """Agent-scoped hooks that inspect prompts before the model runs."""

    def __init__(
        self,
        firewall: AgentFirewall,
        *,
        inspect_prompts: bool = True,
        source: str = "openai_agents",
        inner: Any = None,
    ) -> None:
        self.firewall = firewall
        self.inspect_prompts = inspect_prompts
        self.translator = OpenAIAgentsEventTranslator(source=source)
        self.inner = inner

    async def on_start(self, context: Any, agent: Any) -> None:
        if self.inner is not None and hasattr(self.inner, "on_start"):
            result = self.inner.on_start(context, agent)
            awaited = _maybe_await(result)
            if awaited is not None:
                await awaited

    async def on_end(self, context: Any, agent: Any, output: Any) -> None:
        if self.inner is not None and hasattr(self.inner, "on_end"):
            result = self.inner.on_end(context, agent, output)
            awaited = _maybe_await(result)
            if awaited is not None:
                await awaited

    async def on_handoff(self, context: Any, agent: Any, source: Any) -> None:
        if self.inner is not None and hasattr(self.inner, "on_handoff"):
            result = self.inner.on_handoff(context, agent, source)
            awaited = _maybe_await(result)
            if awaited is not None:
                await awaited

    async def on_tool_start(self, context: Any, agent: Any, tool: Any) -> None:
        if self.inner is not None and hasattr(self.inner, "on_tool_start"):
            result = self.inner.on_tool_start(context, agent, tool)
            awaited = _maybe_await(result)
            if awaited is not None:
                await awaited

    async def on_tool_end(self, context: Any, agent: Any, tool: Any, result_text: str) -> None:
        if self.inner is not None and hasattr(self.inner, "on_tool_end"):
            result = self.inner.on_tool_end(context, agent, tool, result_text)
            awaited = _maybe_await(result)
            if awaited is not None:
                await awaited

    async def on_llm_start(
        self,
        context: Any,
        agent: Any,
        system_prompt: str | None,
        input_items: str | list[Any],
    ) -> None:
        if self.inspect_prompts:
            event = self.translator.prompt_event(input_items)
            if event is not None:
                self.firewall.enforce(event)

        if self.inner is not None and hasattr(self.inner, "on_llm_start"):
            result = self.inner.on_llm_start(
                context,
                agent,
                system_prompt,
                input_items,
            )
            awaited = _maybe_await(result)
            if awaited is not None:
                await awaited

    async def on_llm_end(self, context: Any, agent: Any, response: Any) -> None:
        if self.inner is not None and hasattr(self.inner, "on_llm_end"):
            result = self.inner.on_llm_end(context, agent, response)
            awaited = _maybe_await(result)
            if awaited is not None:
                await awaited


def _coerce_function_tool(tool: Any) -> Any:
    if isinstance(tool, FunctionTool):
        return tool
    if not callable(tool):
        raise TypeError(
            "OpenAI Agents function-tool support expects a FunctionTool or callable."
        )
    return function_tool(tool, failure_error_function=None)


def _decorate_function_tool(
    *,
    name: str,
    description: str,
    func: Callable[..., Any],
) -> Any:
    tool_decorator = function_tool(
        name_override=name,
        description_override=description,
        failure_error_function=None,
    )
    return tool_decorator(func)


def _validate_supported_openai_agent(agent: Any) -> None:
    handoffs = getattr(agent, "handoffs", ())
    if handoffs:
        raise NotImplementedError(
            "OpenAI Agents support is currently function_tool-first and does not "
            "yet support handoffs."
        )

    mcp_servers = getattr(agent, "mcp_servers", ())
    if mcp_servers:
        raise NotImplementedError(
            "OpenAI Agents support is currently function_tool-first and does not "
            "yet support MCP servers."
        )

    unsupported_tools = [
        getattr(tool, "name", type(tool).__name__)
        for tool in getattr(agent, "tools", ())
        if not isinstance(tool, FunctionTool)
    ]
    if unsupported_tools:
        raise NotImplementedError(
            "OpenAI Agents support is currently function_tool-first and does not "
            "yet support hosted or non-function tools: "
            + ", ".join(str(name) for name in unsupported_tools)
        )


@dataclasses.dataclass(frozen=True, slots=True)
class OpenAIAgentsGuardedToolBuilder:
    """Build guarded tool surfaces for the OpenAI Agents adapter."""

    firewall: AgentFirewall
    source: str = "openai_agents"

    def _create_guarded_function_tool(
        self,
        *,
        name: str,
        description: str,
        func: Callable[..., Any],
    ) -> Any:
        _require_openai_agents()
        guarded_tool = _decorate_function_tool(
            name=name,
            description=description,
            func=func,
        )
        setattr(guarded_tool, "__agentfirewall__", self.firewall)
        return guarded_tool

    def create_shell_tool(
        self,
        *,
        name: str = "shell",
        description: str = (
            "Run a shell command through AgentFirewall-guarded subprocess execution."
        ),
        source: str = "openai_agents.shell",
        runner: Callable[..., Any] | None = None,
        shell: bool = True,
        run_kwargs: Mapping[str, Any] | None = None,
        encoding: str = "utf-8",
        strip_output: bool = True,
    ) -> Any:
        """Create a guarded shell tool for OpenAI Agents."""
        from ..integrations.langgraph import _format_subprocess_result

        guarded_runner_kwargs: dict[str, Any] = {
            "firewall": self.firewall,
            "source": f"{source}.command",
        }
        if runner is not None:
            guarded_runner_kwargs["runner"] = runner
        guarded_runner = GuardedSubprocessRunner(**guarded_runner_kwargs)

        runner_kwargs = {"capture_output": True, "text": True, "check": False}
        if run_kwargs is not None:
            runner_kwargs.update(dict(run_kwargs))

        def guarded_shell(command: str, cwd: str = "") -> str:
            invocation_kwargs = dict(runner_kwargs)
            if cwd:
                invocation_kwargs["cwd"] = cwd
            result = guarded_runner.run(command, shell=shell, **invocation_kwargs)
            return _format_subprocess_result(
                result,
                encoding=encoding,
                strip_output=strip_output,
            )

        return self._create_guarded_function_tool(
            name=name,
            description=description,
            func=guarded_shell,
        )

    def create_http_tool(
        self,
        *,
        name: str = "http_request",
        description: str = (
            "Send an outbound HTTP request through AgentFirewall-guarded network enforcement."
        ),
        source: str = "openai_agents.http",
        opener: Callable[..., Any] | None = None,
        request_kwargs: Mapping[str, Any] | None = None,
        encoding: str = "utf-8",
        max_chars: int | None = 4096,
        strip_output: bool = False,
    ) -> Any:
        """Create a guarded HTTP tool for OpenAI Agents."""
        from ..integrations.langgraph import _read_text_resource

        client_kwargs: dict[str, Any] = {
            "firewall": self.firewall,
            "source": f"{source}.request",
        }
        if opener is not None:
            client_kwargs["opener"] = opener
        guarded_client = GuardedHttpClient(**client_kwargs)
        resolved_request_kwargs = dict(request_kwargs or {})

        def guarded_http_request(url: str, method: str = "GET") -> str:
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

        return self._create_guarded_function_tool(
            name=name,
            description=description,
            func=guarded_http_request,
        )

    def create_file_reader_tool(
        self,
        *,
        name: str = "read_file",
        description: str = (
            "Read a local file through AgentFirewall-guarded filesystem enforcement."
        ),
        source: str = "openai_agents.file",
        opener: Callable[..., Any] | None = None,
        read_kwargs: Mapping[str, Any] | None = None,
        encoding: str = "utf-8",
        max_chars: int | None = 4096,
        strip_output: bool = False,
    ) -> Any:
        """Create a guarded file reader tool for OpenAI Agents."""
        from ..integrations.langgraph import _read_text_resource

        access_kwargs: dict[str, Any] = {
            "firewall": self.firewall,
            "source": f"{source}.file",
        }
        if opener is not None:
            access_kwargs["opener"] = opener
        file_access = GuardedFileAccess(**access_kwargs)

        def guarded_file_reader(path: str) -> str:
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

        return self._create_guarded_function_tool(
            name=name,
            description=description,
            func=guarded_file_reader,
        )

    def create_file_writer_tool(
        self,
        *,
        name: str = "write_file",
        description: str = (
            "Write content to a local file through AgentFirewall-guarded filesystem enforcement."
        ),
        source: str = "openai_agents.file",
        writer: Callable[..., Any] | None = None,
        encoding: str = "utf-8",
        write_kwargs: Mapping[str, Any] | None = None,
    ) -> Any:
        """Create a guarded file writer tool for OpenAI Agents."""
        file_source = f"{source}.file"
        file_access = None
        if writer is None:
            file_access = GuardedFileAccess(
                firewall=self.firewall,
                source=file_source,
            )

        def guarded_file_writer(path: str, content: str) -> str:
            if writer is None:
                assert file_access is not None
                open_kwargs = dict(write_kwargs or {})
                if "encoding" not in open_kwargs:
                    open_kwargs["encoding"] = encoding
                handle = file_access.open(path, "w", **open_kwargs)
                if hasattr(handle, "write"):
                    handle.write(content)
                    if hasattr(handle, "close"):
                        handle.close()
            else:
                event = attach_runtime_context(
                    EventContext.file_access(
                        path,
                        mode="write",
                        source=file_source,
                    )
                )
                self.firewall.enforce(event)
                writer(path, content, **dict(write_kwargs or {}))
            return f"wrote {len(content)} chars to {path}"

        return self._create_guarded_function_tool(
            name=name,
            description=description,
            func=guarded_file_writer,
        )


def create_guarded_openai_agents_function_tool(
    tool: Any,
    *,
    firewall: AgentFirewall | None = None,
    config: FirewallConfig | None = None,
    policy_pack: str | PolicyPackConfig = "default",
    audit_sink: AuditSink | None = None,
    approval_handler: ApprovalHandler | None = None,
    source: str = "openai_agents",
) -> Any:
    """Wrap one OpenAI Agents function tool with AgentFirewall enforcement."""

    _require_openai_agents()
    resolved_firewall = resolve_adapter_firewall(
        firewall=firewall,
        config=config,
        policy_pack=policy_pack,
        audit_sink=audit_sink,
        approval_handler=approval_handler,
    )
    original_tool = _coerce_function_tool(tool)
    if original_tool.needs_approval is not False:
        raise NotImplementedError(
            "OpenAI Agents function-tool support currently expects "
            "`needs_approval=False` and relies on AgentFirewall review semantics."
        )

    translator = OpenAIAgentsEventTranslator(source=source)
    original_invoke_tool = original_tool.on_invoke_tool

    async def guarded_invoke_tool(context: Any, input_json: str) -> Any:
        event = translator.tool_event(original_tool.name, input_json)
        resolved_firewall.enforce(event)
        metadata = translator.tool_runtime_metadata(context)
        with runtime_event_context(**metadata):
            return await original_invoke_tool(context, input_json)

    guarded_tool = dataclasses.replace(
        original_tool,
        on_invoke_tool=guarded_invoke_tool,
    )
    setattr(guarded_tool, "__agentfirewall__", resolved_firewall)
    return guarded_tool


def create_firewalled_openai_agents_agent(
    *,
    agent: Any,
    firewall: AgentFirewall | None = None,
    config: FirewallConfig | None = None,
    policy_pack: str | PolicyPackConfig = "default",
    audit_sink: AuditSink | None = None,
    approval_handler: ApprovalHandler | None = None,
    inspect_prompts: bool = True,
    source: str = "openai_agents",
) -> Any:
    """Return an OpenAI Agents SDK agent wrapped with AgentFirewall."""

    _require_openai_agents()
    _validate_supported_openai_agent(agent)
    resolved_firewall = resolve_adapter_firewall(
        firewall=firewall,
        config=config,
        policy_pack=policy_pack,
        audit_sink=audit_sink,
        approval_handler=approval_handler,
    )

    wrapped_tools = [
        create_guarded_openai_agents_function_tool(
            tool,
            firewall=resolved_firewall,
            source=source,
        )
        for tool in getattr(agent, "tools", ())
    ]
    wrapped_hooks = OpenAIAgentsFirewallHooks(
        resolved_firewall,
        inspect_prompts=inspect_prompts,
        source=source,
        inner=getattr(agent, "hooks", None),
    )

    firewalled_agent = dataclasses.replace(
        agent,
        tools=wrapped_tools,
        hooks=wrapped_hooks,
    )
    setattr(firewalled_agent, "__agentfirewall__", resolved_firewall)
    return firewalled_agent


def create_guarded_openai_agents_shell_tool(
    *,
    firewall: AgentFirewall,
    name: str = "shell",
    description: str = (
        "Run a shell command through AgentFirewall-guarded subprocess execution."
    ),
    source: str = "openai_agents.shell",
    runner: Callable[..., Any] | None = None,
    shell: bool = True,
    run_kwargs: Mapping[str, Any] | None = None,
    encoding: str = "utf-8",
    strip_output: bool = True,
) -> Any:
    """Create a guarded shell tool for OpenAI Agents."""
    return OpenAIAgentsGuardedToolBuilder(firewall=firewall).create_shell_tool(
        name=name,
        description=description,
        source=source,
        runner=runner,
        shell=shell,
        run_kwargs=run_kwargs,
        encoding=encoding,
        strip_output=strip_output,
    )


def create_guarded_openai_agents_http_tool(
    *,
    firewall: AgentFirewall,
    name: str = "http_request",
    description: str = (
        "Send an outbound HTTP request through AgentFirewall-guarded network enforcement."
    ),
    source: str = "openai_agents.http",
    opener: Callable[..., Any] | None = None,
    request_kwargs: Mapping[str, Any] | None = None,
    encoding: str = "utf-8",
    max_chars: int | None = 4096,
    strip_output: bool = False,
) -> Any:
    """Create a guarded HTTP tool for OpenAI Agents."""
    return OpenAIAgentsGuardedToolBuilder(firewall=firewall).create_http_tool(
        name=name,
        description=description,
        source=source,
        opener=opener,
        request_kwargs=request_kwargs,
        encoding=encoding,
        max_chars=max_chars,
        strip_output=strip_output,
    )


def create_guarded_openai_agents_file_reader_tool(
    *,
    firewall: AgentFirewall,
    name: str = "read_file",
    description: str = (
        "Read a local file through AgentFirewall-guarded filesystem enforcement."
    ),
    source: str = "openai_agents.file",
    opener: Callable[..., Any] | None = None,
    read_kwargs: Mapping[str, Any] | None = None,
    encoding: str = "utf-8",
    max_chars: int | None = 4096,
    strip_output: bool = False,
) -> Any:
    """Create a guarded file reader tool for OpenAI Agents."""
    return OpenAIAgentsGuardedToolBuilder(firewall=firewall).create_file_reader_tool(
        name=name,
        description=description,
        source=source,
        opener=opener,
        read_kwargs=read_kwargs,
        encoding=encoding,
        max_chars=max_chars,
        strip_output=strip_output,
    )


def create_guarded_openai_agents_file_writer_tool(
    *,
    firewall: AgentFirewall,
    name: str = "write_file",
    description: str = (
        "Write content to a local file through AgentFirewall-guarded filesystem enforcement."
    ),
    source: str = "openai_agents.file",
    writer: Callable[..., Any] | None = None,
    encoding: str = "utf-8",
    write_kwargs: Mapping[str, Any] | None = None,
) -> Any:
    """Create a guarded file writer tool for OpenAI Agents."""
    return OpenAIAgentsGuardedToolBuilder(firewall=firewall).create_file_writer_tool(
        name=name,
        description=description,
        source=source,
        writer=writer,
        encoding=encoding,
        write_kwargs=write_kwargs,
    )


__all__ = [
    "OpenAIAgentsEventTranslator",
    "OpenAIAgentsFirewallHooks",
    "OpenAIAgentsGuardedToolBuilder",
    "create_firewalled_openai_agents_agent",
    "create_guarded_openai_agents_function_tool",
    "create_guarded_openai_agents_shell_tool",
    "create_guarded_openai_agents_http_tool",
    "create_guarded_openai_agents_file_reader_tool",
    "create_guarded_openai_agents_file_writer_tool",
    "get_openai_agents_adapter_spec",
]
