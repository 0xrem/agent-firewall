"""Framework-specific integration adapters for AgentFirewall."""

from .assembly import resolve_adapter_firewall
from .contracts import (
    AdapterCapability,
    AdapterSupportLevel,
    OFFICIAL_ADAPTER_CAPABILITY_ORDER,
    RuntimeAdapterSpec,
    capability_matrix_row,
    capability_support_map,
)
from .conformance import (
    ConformanceIssue,
    ConformanceReport,
    validate_eval_summary,
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
from .openai_agents import (
    OpenAIAgentsEventTranslator,
    OpenAIAgentsFirewallHooks,
    OpenAIAgentsRuntimeBundle,
    create_firewalled_openai_agents_agent,
    create_openai_agents_runtime_bundle,
    create_guarded_openai_agents_function_tool,
    get_openai_agents_adapter_spec,
)
from .registry import (
    export_official_adapter_matrix,
    export_official_adapter_inventory,
    get_official_adapter,
    get_official_adapter_spec,
    list_official_adapters,
    list_official_adapter_specs,
    run_official_adapter_eval_suite,
    validate_official_adapter_conformance,
    validate_official_adapter_eval_expectations,
    validate_official_adapter_release_gate,
)

__all__ = [
    "AdapterCapability",
    "AdapterSupportLevel",
    "ConformanceIssue",
    "ConformanceReport",
    "LangGraphFirewallMiddleware",
    "OFFICIAL_ADAPTER_CAPABILITY_ORDER",
    "RuntimeAdapterSpec",
    "capability_matrix_row",
    "capability_support_map",
    "create_firewalled_langgraph_agent",
    "create_guarded_langgraph_file_reader_tool",
    "create_guarded_langgraph_file_writer_tool",
    "create_guarded_langgraph_http_tool",
    "create_guarded_langgraph_shell_tool",
    "create_firewalled_openai_agents_agent",
    "create_guarded_openai_agents_function_tool",
    "export_official_adapter_inventory",
    "export_official_adapter_matrix",
    "get_official_adapter",
    "get_official_adapter_spec",
    "get_langgraph_adapter_spec",
    "get_openai_agents_adapter_spec",
    "list_official_adapters",
    "list_official_adapter_specs",
    "OpenAIAgentsEventTranslator",
    "OpenAIAgentsFirewallHooks",
    "OpenAIAgentsRuntimeBundle",
    "create_openai_agents_runtime_bundle",
    "resolve_adapter_firewall",
    "run_official_adapter_eval_suite",
    "validate_eval_summary",
    "validate_official_adapter_conformance",
    "validate_official_adapter_eval_expectations",
    "validate_official_adapter_release_gate",
]
