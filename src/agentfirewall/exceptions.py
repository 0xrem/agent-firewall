"""Custom exceptions for AgentFirewall."""


class AgentFirewallError(Exception):
    """Base exception for the package."""


class FirewallViolation(AgentFirewallError):
    """Raised when a policy blocks an action."""
