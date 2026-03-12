"""Public package interface for AgentFirewall."""

from .audit import AuditEntry, InMemoryAuditSink, JsonLinesAuditSink
from .config import FirewallConfig
from .enforcers import (
    GuardedFileAccess,
    GuardedHttpClient,
    GuardedSubprocessRunner,
    GuardedToolDispatcher,
)
from .events import EventContext, EventKind
from .exceptions import AgentFirewallError, FirewallViolation, ReviewRequired
from .firewall import AgentFirewall, protect
from .policy import Decision, DecisionAction, PolicyEngine, Rule
from .policy_packs import (
    PolicyPackConfig,
    build_builtin_policy_engine,
    default_policy_pack,
    named_policy_pack,
    strict_policy_pack,
)
from .rules import default_runtime_rules

__all__ = [
    "AgentFirewall",
    "AgentFirewallError",
    "AuditEntry",
    "Decision",
    "DecisionAction",
    "EventContext",
    "EventKind",
    "FirewallConfig",
    "FirewallViolation",
    "GuardedFileAccess",
    "GuardedHttpClient",
    "GuardedSubprocessRunner",
    "GuardedToolDispatcher",
    "InMemoryAuditSink",
    "JsonLinesAuditSink",
    "PolicyEngine",
    "PolicyPackConfig",
    "ReviewRequired",
    "Rule",
    "build_builtin_policy_engine",
    "default_policy_pack",
    "default_runtime_rules",
    "named_policy_pack",
    "protect",
    "strict_policy_pack",
]
