"""Evaluation helpers for AgentFirewall."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from .contracts import (
    EvalExpectationIssue,
    EvalExpectationReport,
    EvalSuiteExpectations,
    find_eval_result,
    find_eval_trace,
    find_named_eval_result,
    require_eval_result,
    require_eval_trace,
    require_named_eval_result,
    validate_eval_summary_against_expectations,
)

__all__ = [
    "EvalExpectationIssue",
    "EvalExpectationReport",
    "EvalRunStatus",
    "EvalSuiteExpectations",
    "EvaluationResult",
    "EvaluationSummary",
    "GenericEvalCase",
    "LangGraphEvalCase",
    "find_eval_result",
    "find_eval_trace",
    "find_named_eval_result",
    "load_generic_eval_cases",
    "load_langgraph_eval_cases",
    "require_eval_result",
    "require_eval_trace",
    "require_named_eval_result",
    "run_generic_eval_case",
    "run_generic_eval_suite",
    "run_langgraph_eval_case",
    "run_langgraph_eval_suite",
    "validate_eval_summary_against_expectations",
]


def __getattr__(name: str) -> Any:
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    if name in {
        "EvalRunStatus",
        "EvaluationResult",
        "EvaluationSummary",
    }:
        module = import_module(".models", __name__)
        return getattr(module, name)

    if name in {
        "LangGraphEvalCase",
        "load_langgraph_eval_cases",
        "run_langgraph_eval_case",
        "run_langgraph_eval_suite",
    }:
        module = import_module(".langgraph", __name__)
        return getattr(module, name)

    if name in {
        "GenericEvalCase",
        "load_generic_eval_cases",
        "run_generic_eval_case",
        "run_generic_eval_suite",
    }:
        module = import_module(".generic", __name__)
        return getattr(module, name)

    module = import_module(".contracts", __name__)
    return getattr(module, name)
