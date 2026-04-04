"""Experimental MCP-oriented preview helpers for local loopback evaluation."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from .approval import ApprovalHandler
from .audit import AuditSink
from .config import FirewallConfig
from .enforcers import (
    GuardedFileAccess,
    GuardedHttpClient,
    GuardedResourceReader,
    GuardedSubprocessRunner,
)
from .events import EventContext
from .firewall import AgentFirewall
from .integrations.assembly import resolve_adapter_firewall
from .policy_packs import PolicyPackConfig
from .runtime_context import mcp_tool_runtime_context


def _default_tool_call_id(
    name: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> str:
    normalized_name = name or "tool"
    return f"call_{normalized_name}_{uuid4().hex[:12]}"


def _default_resource_call_id(uri: str, server_name: str | None = None) -> str:
    prefix = server_name or "resource"
    return f"read_{prefix}_{uuid4().hex[:12]}"


def _normalize_tool_kwargs(
    *,
    kwargs: Mapping[str, Any] | None,
    arguments: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if kwargs is not None and arguments is not None:
        raise TypeError("Pass either kwargs or arguments, not both.")
    if kwargs is not None:
        return dict(kwargs)
    if arguments is not None:
        return dict(arguments)
    return {}


@dataclass(slots=True)
class McpPreviewBundle:
    """Grouped preview bundle for MCP-oriented loopback flows."""

    firewall: AgentFirewall
    runtime: str
    direction: str
    source_prefix: str
    command_runner: GuardedSubprocessRunner
    http_client: GuardedHttpClient
    file_access: GuardedFileAccess
    resource_reader: GuardedResourceReader
    tools: dict[str, Callable[..., Any]] = field(default_factory=dict)
    tool_call_id_factory: Callable[[str, tuple[Any, ...], dict[str, Any]], str] = (
        _default_tool_call_id
    )
    resource_call_id_factory: Callable[[str, str | None], str] = _default_resource_call_id

    def register_tool(self, name: str, tool: Callable[..., Any]) -> None:
        self.tools[name] = tool

    def call_tool(
        self,
        name: str,
        *args: Any,
        server_name: str | None = None,
        arguments: Mapping[str, Any] | None = None,
        kwargs: Mapping[str, Any] | None = None,
        **tool_kwargs: Any,
    ) -> Any:
        if (arguments is not None or kwargs is not None) and tool_kwargs:
            raise TypeError(
                "Pass tool keyword arguments either directly or via kwargs/arguments, not both."
            )
        normalized_kwargs = _normalize_tool_kwargs(
            kwargs=kwargs,
            arguments=arguments,
        )
        if tool_kwargs:
            normalized_kwargs = dict(tool_kwargs)
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
            source=f"{self.source_prefix}.tool",
        )
        event.payload["tool_call_id"] = tool_call_id
        self.firewall.enforce(event)

        with mcp_tool_runtime_context(
            runtime=self.runtime,
            tool_name=name,
            tool_call_id=tool_call_id,
            tool_event_source=f"{self.source_prefix}.tool",
            mcp_direction=self.direction,
            mcp_server_name=server_name,
            mcp_operation="call_tool",
        ):
            if name not in self.tools:
                raise KeyError(f"Unknown tool: {name}")
            return self.tools[name](*normalized_args, **normalized_kwargs)

    def read_resource(
        self,
        uri: str,
        *,
        server_name: str | None = None,
        mime_type: str | None = None,
        **kwargs: Any,
    ) -> Any:
        tool_call_id = self.resource_call_id_factory(uri, server_name)
        with mcp_tool_runtime_context(
            runtime=self.runtime,
            tool_name="resource_read",
            tool_call_id=tool_call_id,
            tool_event_source=f"{self.source_prefix}.resource",
            mcp_direction=self.direction,
            mcp_server_name=server_name,
            mcp_resource_uri=uri,
            mcp_operation="read",
        ):
            return self.resource_reader.read(
                uri,
                server_name=server_name,
                mime_type=mime_type,
                **kwargs,
            )


def create_tool_wrapper(
    tool: Callable[..., Any],
    *,
    firewall: AgentFirewall,
    name: str,
    runtime: str,
    direction: str,
    source_prefix: str,
    server_name: str | None = None,
    tool_call_id_factory: Callable[[str, tuple[Any, ...], dict[str, Any]], str] = (
        _default_tool_call_id
    ),
) -> Callable[..., Any]:
    """Wrap one callable with MCP-flavored tool-call enforcement."""

    bundle = McpPreviewBundle(
        firewall=firewall,
        runtime=runtime,
        direction=direction,
        source_prefix=source_prefix,
        command_runner=GuardedSubprocessRunner(
            firewall=firewall,
            source=f"{source_prefix}.command",
        ),
        http_client=GuardedHttpClient(
            firewall=firewall,
            source=f"{source_prefix}.http",
        ),
        file_access=GuardedFileAccess(
            firewall=firewall,
            source=f"{source_prefix}.file",
        ),
        resource_reader=GuardedResourceReader(
            firewall=firewall,
            reader=lambda uri, **kwargs: None,
            source=f"{source_prefix}.resource",
        ),
        tool_call_id_factory=tool_call_id_factory,
    )
    bundle.register_tool(name, tool)

    def wrapped(*args: Any, **kwargs: Any) -> Any:
        return bundle.call_tool(name, *args, server_name=server_name, **kwargs)

    return wrapped


def create_resource_reader(
    reader: Callable[..., Any],
    *,
    firewall: AgentFirewall,
    runtime: str,
    direction: str,
    source_prefix: str,
    server_name: str | None = None,
    mime_type: str | None = None,
    resource_call_id_factory: Callable[[str, str | None], str] = _default_resource_call_id,
) -> Callable[[str], Any]:
    """Wrap one resource-reader callable with MCP-flavored resource enforcement."""

    guarded = GuardedResourceReader(
        firewall=firewall,
        reader=reader,
        source=f"{source_prefix}.resource",
    )

    def wrapped(uri: str, **kwargs: Any) -> Any:
        tool_call_id = resource_call_id_factory(uri, server_name)
        with mcp_tool_runtime_context(
            runtime=runtime,
            tool_name="resource_read",
            tool_call_id=tool_call_id,
            tool_event_source=f"{source_prefix}.resource",
            mcp_direction=direction,
            mcp_server_name=server_name,
            mcp_resource_uri=uri,
            mcp_operation="read",
        ):
            return guarded.read(
                uri,
                server_name=server_name,
                mime_type=mime_type,
                **kwargs,
            )

    return wrapped


def _create_preview_bundle(
    *,
    runtime: str,
    direction: str,
    source_prefix: str,
    firewall: AgentFirewall | None = None,
    config: FirewallConfig | None = None,
    policy_pack: str | PolicyPackConfig = "default",
    audit_sink: AuditSink | None = None,
    approval_handler: ApprovalHandler | None = None,
    tools: Mapping[str, Callable[..., Any]] | None = None,
    runner: Callable[..., Any] | None = None,
    http_opener: Callable[..., Any] | None = None,
    file_opener: Callable[..., Any] | None = None,
    resource_reader: Callable[..., Any] | None = None,
    tool_call_id_factory: Callable[[str, tuple[Any, ...], dict[str, Any]], str] = (
        _default_tool_call_id
    ),
    resource_call_id_factory: Callable[[str, str | None], str] = _default_resource_call_id,
) -> McpPreviewBundle:
    resolved_firewall = resolve_adapter_firewall(
        firewall=firewall,
        config=config,
        policy_pack=policy_pack,
        audit_sink=audit_sink,
        approval_handler=approval_handler,
    )
    command_runner = GuardedSubprocessRunner(
        firewall=resolved_firewall,
        source=f"{source_prefix}.command",
        **({"runner": runner} if runner is not None else {}),
    )
    http_client = GuardedHttpClient(
        firewall=resolved_firewall,
        source=f"{source_prefix}.http",
        **({"opener": http_opener} if http_opener is not None else {}),
    )
    file_access = GuardedFileAccess(
        firewall=resolved_firewall,
        source=f"{source_prefix}.file",
        **({"opener": file_opener} if file_opener is not None else {}),
    )
    guarded_resource_reader = GuardedResourceReader(
        firewall=resolved_firewall,
        reader=(
            resource_reader
            if resource_reader is not None
            else (lambda uri, **kwargs: None)
        ),
        source=f"{source_prefix}.resource",
    )
    bundle = McpPreviewBundle(
        firewall=resolved_firewall,
        runtime=runtime,
        direction=direction,
        source_prefix=source_prefix,
        command_runner=command_runner,
        http_client=http_client,
        file_access=file_access,
        resource_reader=guarded_resource_reader,
        tool_call_id_factory=tool_call_id_factory,
        resource_call_id_factory=resource_call_id_factory,
    )
    for name, tool in dict(tools or {}).items():
        bundle.register_tool(name, tool)
    return bundle


def create_client_bundle(
    *,
    firewall: AgentFirewall | None = None,
    config: FirewallConfig | None = None,
    policy_pack: str | PolicyPackConfig = "default",
    audit_sink: AuditSink | None = None,
    approval_handler: ApprovalHandler | None = None,
    tools: Mapping[str, Callable[..., Any]] | None = None,
    runner: Callable[..., Any] | None = None,
    http_opener: Callable[..., Any] | None = None,
    file_opener: Callable[..., Any] | None = None,
    resource_reader: Callable[..., Any] | None = None,
    tool_call_id_factory: Callable[[str, tuple[Any, ...], dict[str, Any]], str] = (
        _default_tool_call_id
    ),
    resource_call_id_factory: Callable[[str, str | None], str] = _default_resource_call_id,
) -> McpPreviewBundle:
    """Create an experimental MCP client preview bundle."""

    return _create_preview_bundle(
        runtime="mcp_client",
        direction="client",
        source_prefix="mcp.client",
        firewall=firewall,
        config=config,
        policy_pack=policy_pack,
        audit_sink=audit_sink,
        approval_handler=approval_handler,
        tools=tools,
        runner=runner,
        http_opener=http_opener,
        file_opener=file_opener,
        resource_reader=resource_reader,
        tool_call_id_factory=tool_call_id_factory,
        resource_call_id_factory=resource_call_id_factory,
    )


def create_server_bundle(
    *,
    firewall: AgentFirewall | None = None,
    config: FirewallConfig | None = None,
    policy_pack: str | PolicyPackConfig = "default",
    audit_sink: AuditSink | None = None,
    approval_handler: ApprovalHandler | None = None,
    tools: Mapping[str, Callable[..., Any]] | None = None,
    runner: Callable[..., Any] | None = None,
    http_opener: Callable[..., Any] | None = None,
    file_opener: Callable[..., Any] | None = None,
    resource_reader: Callable[..., Any] | None = None,
    tool_call_id_factory: Callable[[str, tuple[Any, ...], dict[str, Any]], str] = (
        _default_tool_call_id
    ),
    resource_call_id_factory: Callable[[str, str | None], str] = _default_resource_call_id,
) -> McpPreviewBundle:
    """Create an experimental MCP server preview bundle."""

    return _create_preview_bundle(
        runtime="mcp_server",
        direction="server",
        source_prefix="mcp.server",
        firewall=firewall,
        config=config,
        policy_pack=policy_pack,
        audit_sink=audit_sink,
        approval_handler=approval_handler,
        tools=tools,
        runner=runner,
        http_opener=http_opener,
        file_opener=file_opener,
        resource_reader=resource_reader,
        tool_call_id_factory=tool_call_id_factory,
        resource_call_id_factory=resource_call_id_factory,
    )


__all__ = [
    "McpPreviewBundle",
    "create_client_bundle",
    "create_resource_reader",
    "create_server_bundle",
    "create_tool_wrapper",
]
