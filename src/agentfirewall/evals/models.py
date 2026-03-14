"""Shared evaluation result models used by local runtime suites."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EvalRunStatus(str, Enum):
    """Top-level result state for an eval case."""

    COMPLETED = "completed"
    REVIEW_REQUIRED = "review_required"
    BLOCKED = "blocked"
    ERROR = "error"


@dataclass(slots=True)
class EvaluationResult:
    """Observed result for a single eval case."""

    name: str
    task: str
    workflow_goal: str
    status: EvalRunStatus
    expected_status: EvalRunStatus
    matched: bool
    observed_event_kinds: list[str]
    observed_actions: list[str]
    expected_final_action: str
    observed_final_action: str
    expected_event_kinds: list[str] = field(default_factory=list)
    expected_action_sequence: list[str] = field(default_factory=list)
    audit_summary: dict[str, Any] = field(default_factory=dict)
    audit_trace: list[dict[str, Any]] = field(default_factory=list)
    detail: str = ""


@dataclass(slots=True)
class EvaluationSummary:
    """Aggregate result for a group of eval cases."""

    results: list[EvaluationResult]

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for result in self.results if result.matched)

    @property
    def failed(self) -> int:
        return self.total - self.passed

    @property
    def status_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for result in self.results:
            key = result.status.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    @property
    def final_action_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for result in self.results:
            key = result.observed_final_action
            counts[key] = counts.get(key, 0) + 1
        return counts

    @property
    def task_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for result in self.results:
            key = result.task or "unlabeled"
            counts[key] = counts.get(key, 0) + 1
        return counts

    @property
    def unexpected_allows(self) -> int:
        return sum(
            1
            for result in self.results
            if not result.matched and result.observed_final_action == "allow"
        )

    @property
    def unexpected_blocks(self) -> int:
        return sum(
            1
            for result in self.results
            if not result.matched and result.observed_final_action == "block"
        )

    @property
    def unexpected_reviews(self) -> int:
        return sum(
            1
            for result in self.results
            if not result.matched and result.observed_final_action == "review"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "status_counts": self.status_counts,
            "final_action_counts": self.final_action_counts,
            "task_counts": self.task_counts,
            "unexpected_allows": self.unexpected_allows,
            "unexpected_blocks": self.unexpected_blocks,
            "unexpected_reviews": self.unexpected_reviews,
            "results": [
                {
                    "name": result.name,
                    "task": result.task,
                    "workflow_goal": result.workflow_goal,
                    "status": result.status.value,
                    "expected_status": result.expected_status.value,
                    "matched": result.matched,
                    "observed_event_kinds": result.observed_event_kinds,
                    "observed_actions": result.observed_actions,
                    "expected_final_action": result.expected_final_action,
                    "observed_final_action": result.observed_final_action,
                    "expected_event_kinds": result.expected_event_kinds,
                    "expected_action_sequence": result.expected_action_sequence,
                    "audit_summary": result.audit_summary,
                    "audit_trace": result.audit_trace,
                    "detail": result.detail,
                }
                for result in self.results
            ],
        }
