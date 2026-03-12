"""Public package interface for AgentFirewall."""

from .audit import AuditEntry, InMemoryAuditSink
from .config import FirewallConfig
from .enforcers import GuardedFileAccess, GuardedHttpClient, GuardedSubprocessRunner
from .events import EventContext, EventKind
from .exceptions import AgentFirewallError, FirewallViolation
from .firewall import AgentFirewall, protect
from .policy import Decision, DecisionAction, PolicyEngine, Rule
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
    "InMemoryAuditSink",
    "PolicyEngine",
    "Rule",
    "default_runtime_rules",
    "protect",
]
