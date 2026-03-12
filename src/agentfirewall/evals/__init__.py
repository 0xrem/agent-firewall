"""Evaluation helpers for AgentFirewall."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "EvalRunStatus",
    "EvaluationResult",
    "EvaluationSummary",
    "LangGraphEvalCase",
    "load_langgraph_eval_cases",
    "run_langgraph_eval_case",
    "run_langgraph_eval_suite",
]


def __getattr__(name: str) -> Any:
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(".langgraph", __name__)
    return getattr(module, name)
