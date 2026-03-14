"""Preview low-level runtime bundle for unsupported tool-calling systems."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from .approval import ApprovalHandler
from .audit import AuditSink
from .config import FirewallConfig
from .enforcers import (
    GuardedFileAccess,
    GuardedHttpClient,
    GuardedSubprocessRunner,
    GuardedToolDispatcher,
)
from .firewall import AgentFirewall
from .integrations.assembly import resolve_adapter_firewall
from .policy_packs import PolicyPackConfig


@dataclass(frozen=True, slots=True)
class GenericRuntimeBundle:
    """Grouped low-level runtime surfaces for unsupported runtimes."""

    firewall: AgentFirewall
    tool_dispatcher: GuardedToolDispatcher
    command_runner: GuardedSubprocessRunner
    http_client: GuardedHttpClient
    file_access: GuardedFileAccess

    def register_tool(self, name: str, tool: Callable[..., Any]) -> None:
        self.tool_dispatcher.register(name, tool)

    def dispatch(
        self,
        name: str,
        *args: Any,
        arguments: Mapping[str, Any] | None = None,
        kwargs: Mapping[str, Any] | None = None,
        **tool_kwargs: Any,
    ) -> Any:
        return self.tool_dispatcher.dispatch(
            name,
            *args,
            arguments=arguments,
            kwargs=kwargs,
            **tool_kwargs,
        )


def create_generic_runtime_bundle(
    *,
    firewall: AgentFirewall | None = None,
    config: FirewallConfig | None = None,
    policy_pack: str | PolicyPackConfig = "default",
    audit_sink: AuditSink | None = None,
    approval_handler: ApprovalHandler | None = None,
    runtime: str = "generic",
    source_prefix: str = "generic",
    tools: Mapping[str, Callable[..., Any]] | None = None,
    dispatcher: Callable[[str, tuple[Any, ...], dict[str, Any]], Any] | None = None,
    runner: Callable[..., Any] | None = None,
    http_opener: Callable[..., Any] | None = None,
    file_opener: Callable[..., Any] | None = None,
    tool_call_id_factory: Callable[[str, tuple[Any, ...], dict[str, Any]], str] | None = None,
) -> GenericRuntimeBundle:
    """Create a grouped low-level runtime bundle on top of one firewall."""

    resolved_firewall = resolve_adapter_firewall(
        firewall=firewall,
        config=config,
        policy_pack=policy_pack,
        audit_sink=audit_sink,
        approval_handler=approval_handler,
    )

    tool_dispatcher_kwargs: dict[str, Any] = {
        "firewall": resolved_firewall,
        "tools": dict(tools or {}),
        "dispatcher": dispatcher,
        "source": f"{source_prefix}.tool",
        "runtime": runtime,
    }
    if tool_call_id_factory is not None:
        tool_dispatcher_kwargs["tool_call_id_factory"] = tool_call_id_factory

    command_runner_kwargs: dict[str, Any] = {
        "firewall": resolved_firewall,
        "source": f"{source_prefix}.command",
    }
    if runner is not None:
        command_runner_kwargs["runner"] = runner

    http_client_kwargs: dict[str, Any] = {
        "firewall": resolved_firewall,
        "source": f"{source_prefix}.http",
    }
    if http_opener is not None:
        http_client_kwargs["opener"] = http_opener

    file_access_kwargs: dict[str, Any] = {
        "firewall": resolved_firewall,
        "source": f"{source_prefix}.file",
    }
    if file_opener is not None:
        file_access_kwargs["opener"] = file_opener

    return GenericRuntimeBundle(
        firewall=resolved_firewall,
        tool_dispatcher=GuardedToolDispatcher(**tool_dispatcher_kwargs),
        command_runner=GuardedSubprocessRunner(**command_runner_kwargs),
        http_client=GuardedHttpClient(**http_client_kwargs),
        file_access=GuardedFileAccess(**file_access_kwargs),
    )


__all__ = [
    "GenericRuntimeBundle",
    "create_generic_runtime_bundle",
]
