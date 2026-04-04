"""Evaluation helpers for AgentFirewall."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "EvalExpectationIssue",
    "EvalExpectationReport",
    "EvalRunStatus",
    "EvalSuiteExpectations",
    "EvaluationResult",
    "EvaluationSummary",
    "GenericEvalCase",
    "LangGraphEvalCase",
    "McpClientEvalCase",
    "McpServerEvalCase",
    "OpenAIAgentsEvalCase",
    "find_eval_result",
    "find_eval_trace",
    "find_named_eval_result",
    "load_generic_eval_cases",
    "load_langgraph_eval_cases",
    "load_mcp_client_eval_cases",
    "load_mcp_server_eval_cases",
    "load_openai_agents_eval_cases",
    "require_eval_result",
    "require_eval_trace",
    "require_named_eval_result",
    "run_generic_eval_case",
    "run_generic_eval_suite",
    "run_langgraph_eval_case",
    "run_langgraph_eval_suite",
    "run_mcp_client_eval_case",
    "run_mcp_client_eval_suite",
    "run_mcp_server_eval_case",
    "run_mcp_server_eval_suite",
    "run_openai_agents_eval_case",
    "run_openai_agents_eval_suite",
    "validate_eval_summary_against_expectations",
]

_MODULE_EXPORTS: dict[str, str] = {
    "EvalExpectationIssue": ".contracts",
    "EvalExpectationReport": ".contracts",
    "EvalSuiteExpectations": ".contracts",
    "find_eval_result": ".contracts",
    "find_eval_trace": ".contracts",
    "find_named_eval_result": ".contracts",
    "require_eval_result": ".contracts",
    "require_eval_trace": ".contracts",
    "require_named_eval_result": ".contracts",
    "validate_eval_summary_against_expectations": ".contracts",
    "EvalRunStatus": ".models",
    "EvaluationResult": ".models",
    "EvaluationSummary": ".models",
    "GenericEvalCase": ".generic",
    "load_generic_eval_cases": ".generic",
    "run_generic_eval_case": ".generic",
    "run_generic_eval_suite": ".generic",
    "LangGraphEvalCase": ".langgraph",
    "load_langgraph_eval_cases": ".langgraph",
    "run_langgraph_eval_case": ".langgraph",
    "run_langgraph_eval_suite": ".langgraph",
    "McpClientEvalCase": ".mcp_client",
    "load_mcp_client_eval_cases": ".mcp_client",
    "run_mcp_client_eval_case": ".mcp_client",
    "run_mcp_client_eval_suite": ".mcp_client",
    "McpServerEvalCase": ".mcp_server",
    "load_mcp_server_eval_cases": ".mcp_server",
    "run_mcp_server_eval_case": ".mcp_server",
    "run_mcp_server_eval_suite": ".mcp_server",
    "OpenAIAgentsEvalCase": ".openai_agents",
    "load_openai_agents_eval_cases": ".openai_agents",
    "run_openai_agents_eval_case": ".openai_agents",
    "run_openai_agents_eval_suite": ".openai_agents",
}


def __getattr__(name: str) -> Any:
    if name not in _MODULE_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(_MODULE_EXPORTS[name], __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
