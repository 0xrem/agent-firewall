"""Framework-specific integration adapters for AgentFirewall."""

from .langgraph import (
    LangGraphFirewallMiddleware,
    create_firewalled_langgraph_agent,
)

__all__ = [
    "LangGraphFirewallMiddleware",
    "create_firewalled_langgraph_agent",
]
