"""Framework-specific integration adapters for AgentFirewall."""

from .contracts import (
    AdapterCapability,
    AdapterSupportLevel,
    RuntimeAdapterSpec,
)
from .langgraph import (
    LangGraphFirewallMiddleware,
    create_firewalled_langgraph_agent,
    create_guarded_langgraph_file_reader_tool,
    create_guarded_langgraph_file_writer_tool,
    create_guarded_langgraph_http_tool,
    create_guarded_langgraph_shell_tool,
    get_langgraph_adapter_spec,
)

__all__ = [
    "AdapterCapability",
    "AdapterSupportLevel",
    "LangGraphFirewallMiddleware",
    "RuntimeAdapterSpec",
    "create_firewalled_langgraph_agent",
    "create_guarded_langgraph_file_reader_tool",
    "create_guarded_langgraph_file_writer_tool",
    "create_guarded_langgraph_http_tool",
    "create_guarded_langgraph_shell_tool",
    "get_langgraph_adapter_spec",
]
