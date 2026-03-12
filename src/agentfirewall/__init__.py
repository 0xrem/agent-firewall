"""Public package interface for AgentFirewall."""

from __future__ import annotations

from importlib import import_module
import warnings
from typing import Any

from .approval import ApprovalResponse
from .audit import ConsoleAuditSink, InMemoryAuditSink, MultiAuditSink
from .config import FirewallConfig
from .exceptions import FirewallViolation, ReviewRequired
from .firewall import AgentFirewall, create_firewall

PUBLIC_API = (
    "AgentFirewall",
    "ApprovalResponse",
    "ConsoleAuditSink",
    "FirewallConfig",
    "FirewallViolation",
    "InMemoryAuditSink",
    "MultiAuditSink",
    "ReviewRequired",
    "create_firewall",
)

__all__ = list(PUBLIC_API)

_LEGACY_EXPORTS: dict[str, tuple[str, str, str]] = {
    "AgentFirewallError": (".exceptions", "AgentFirewallError", "agentfirewall.exceptions.AgentFirewallError"),
    "ApprovalHandler": (".approval", "ApprovalHandler", "agentfirewall.approval.ApprovalHandler"),
    "ApprovalOutcome": (".approval", "ApprovalOutcome", "agentfirewall.approval.ApprovalOutcome"),
    "ApprovalRequest": (".approval", "ApprovalRequest", "agentfirewall.approval.ApprovalRequest"),
    "AuditEntry": (".audit", "AuditEntry", "agentfirewall.audit.AuditEntry"),
    "AuditSummary": (".audit", "AuditSummary", "agentfirewall.audit.AuditSummary"),
    "Decision": (".policy", "Decision", "agentfirewall.policy.Decision"),
    "DecisionAction": (".policy", "DecisionAction", "agentfirewall.policy.DecisionAction"),
    "EventContext": (".events", "EventContext", "agentfirewall.events.EventContext"),
    "EventKind": (".events", "EventKind", "agentfirewall.events.EventKind"),
    "GuardedFileAccess": (".enforcers", "GuardedFileAccess", "agentfirewall.enforcers.GuardedFileAccess"),
    "GuardedHttpClient": (".enforcers", "GuardedHttpClient", "agentfirewall.enforcers.GuardedHttpClient"),
    "GuardedSubprocessRunner": (".enforcers", "GuardedSubprocessRunner", "agentfirewall.enforcers.GuardedSubprocessRunner"),
    "GuardedToolDispatcher": (".enforcers", "GuardedToolDispatcher", "agentfirewall.enforcers.GuardedToolDispatcher"),
    "JsonLinesAuditSink": (".audit", "JsonLinesAuditSink", "agentfirewall.audit.JsonLinesAuditSink"),
    "LangGraphFirewallMiddleware": (
        ".integrations.langgraph",
        "LangGraphFirewallMiddleware",
        "agentfirewall.integrations.langgraph.LangGraphFirewallMiddleware",
    ),
    "PolicyEngine": (".policy", "PolicyEngine", "agentfirewall.policy.PolicyEngine"),
    "PolicyPackConfig": (".policy_packs", "PolicyPackConfig", "agentfirewall.policy_packs.PolicyPackConfig"),
    "Rule": (".policy", "Rule", "agentfirewall.policy.Rule"),
    "build_builtin_policy_engine": (
        ".policy_packs",
        "build_builtin_policy_engine",
        "agentfirewall.policy_packs.build_builtin_policy_engine",
    ),
    "create_firewalled_langgraph_agent": (
        ".integrations.langgraph",
        "create_firewalled_langgraph_agent",
        "agentfirewall.langgraph.create_agent",
    ),
    "create_guarded_langgraph_file_reader_tool": (
        ".integrations.langgraph",
        "create_guarded_langgraph_file_reader_tool",
        "agentfirewall.langgraph.create_file_reader_tool",
    ),
    "create_guarded_langgraph_http_tool": (
        ".integrations.langgraph",
        "create_guarded_langgraph_http_tool",
        "agentfirewall.langgraph.create_http_tool",
    ),
    "create_guarded_langgraph_shell_tool": (
        ".integrations.langgraph",
        "create_guarded_langgraph_shell_tool",
        "agentfirewall.langgraph.create_shell_tool",
    ),
    "default_policy_pack": (
        ".policy_packs",
        "default_policy_pack",
        "agentfirewall.policy_packs.default_policy_pack",
    ),
    "default_runtime_rules": (
        ".rules",
        "default_runtime_rules",
        "agentfirewall.rules.default_runtime_rules",
    ),
    "named_policy_pack": (
        ".policy_packs",
        "named_policy_pack",
        "agentfirewall.policy_packs.named_policy_pack",
    ),
    "protect": (".firewall", "protect", "agentfirewall.firewall.protect"),
    "strict_policy_pack": (
        ".policy_packs",
        "strict_policy_pack",
        "agentfirewall.policy_packs.strict_policy_pack",
    ),
}


def __getattr__(name: str) -> Any:
    if name not in _LEGACY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attribute_name, guidance = _LEGACY_EXPORTS[name]
    warnings.warn(
        (
            f"`agentfirewall.{name}` is a legacy root import. "
            f"Import `{guidance}` instead. The root API is intentionally narrow."
        ),
        DeprecationWarning,
        stacklevel=2,
    )
    module = import_module(module_name, __name__)
    value = getattr(module, attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(_LEGACY_EXPORTS))
