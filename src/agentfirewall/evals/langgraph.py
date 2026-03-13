"""Local LangGraph eval runner for AgentFirewall."""

from __future__ import annotations

import io
import json
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from importlib import resources
from importlib.resources.abc import Traversable
from typing import Any

from ..approval import ApprovalHandler, ApprovalOutcome, ApprovalResponse
from ..audit import InMemoryAuditSink
from ..config import FirewallConfig
from ..exceptions import FirewallViolation, ReviewRequired
from ..firewall import create_firewall
from ..langgraph import (
    create_agent,
    create_file_reader_tool,
    create_file_writer_tool,
    create_http_tool,
    create_shell_tool,
)

try:
    from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
    from langchain_core.messages import AIMessage
    from langchain_core.tools import tool
except ImportError as exc:  # pragma: no cover - optional dependency guard
    raise ImportError(
        "LangGraph evals require optional dependencies. "
        "Install with `pip install agentfirewall[langgraph]`."
    ) from exc


class ToolCallingFakeModel(GenericFakeChatModel):
    """Fake model that works with tool-calling agent tests and evals."""

    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        return self


class EvalRunStatus(str, Enum):
    """Top-level result state for an eval case."""

    COMPLETED = "completed"
    REVIEW_REQUIRED = "review_required"
    BLOCKED = "blocked"
    ERROR = "error"


@dataclass(slots=True)
class LangGraphEvalCase:
    """Serializable LangGraph eval case."""

    name: str
    prompt: str
    task: str = ""
    workflow_goal: str = ""
    model_messages: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    expected_status: EvalRunStatus | str = EvalRunStatus.COMPLETED
    expected_final_action: str = "allow"
    expected_event_kinds: list[str] = field(default_factory=list)
    expected_action_sequence: list[str] = field(default_factory=list)
    final_response: str = "done"
    approval_outcome: ApprovalOutcome | str | None = None
    approval_reason: str = ""
    log_only: bool = False

    def __post_init__(self) -> None:
        if isinstance(self.expected_status, str):
            self.expected_status = EvalRunStatus(self.expected_status)
        if isinstance(self.approval_outcome, str):
            self.approval_outcome = ApprovalOutcome(self.approval_outcome)


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


def _default_case_resource() -> Traversable:
    return resources.files("agentfirewall.evals").joinpath("cases/langgraph_cases.json")


def load_langgraph_eval_cases(path: str | Traversable | None = None) -> list[LangGraphEvalCase]:
    """Load LangGraph eval cases from JSON."""

    if path is None:
        payload = json.loads(_default_case_resource().read_text(encoding="utf-8"))
    else:
        target = path if hasattr(path, "read_text") else str(path)
        if hasattr(target, "read_text"):
            payload = json.loads(target.read_text(encoding="utf-8"))
        else:
            with open(target, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
    return [LangGraphEvalCase(**case) for case in payload]


def _build_model(case: LangGraphEvalCase) -> ToolCallingFakeModel:
    messages: list[AIMessage] = []
    if case.model_messages:
        for payload in case.model_messages:
            messages.append(
                AIMessage(
                    content=str(payload.get("content", "")),
                    tool_calls=list(payload.get("tool_calls", [])),
                )
            )
    else:
        if case.tool_calls:
            messages.append(AIMessage(content="", tool_calls=case.tool_calls))
        messages.append(AIMessage(content=case.final_response))
    return ToolCallingFakeModel(messages=iter(messages))


def _make_approval_handler(case: LangGraphEvalCase) -> ApprovalHandler | None:
    if case.approval_outcome is None:
        return None

    outcome = case.approval_outcome
    assert outcome is not None

    def handler(request) -> ApprovalResponse:
        metadata = {
            "eval_case": case.name,
            "approved_event_kind": request.event.kind.value,
        }
        if outcome == ApprovalOutcome.APPROVE:
            return ApprovalResponse.approve(
                reason=case.approval_reason or "Eval approval handler approved the action.",
                metadata=metadata,
            )
        if outcome == ApprovalOutcome.DENY:
            return ApprovalResponse.deny(
                reason=case.approval_reason or "Eval approval handler denied the action.",
                metadata=metadata,
            )
        return ApprovalResponse.timeout(
            reason=case.approval_reason or "Eval approval handler timed out.",
            metadata=metadata,
        )

    return handler


def _fake_shell_runner(command, *, shell=False, cwd=None, **kwargs):
    return subprocess.CompletedProcess(
        args=command,
        returncode=0,
        stdout="repo files\n",
    )


def _fake_http_opener(request, **kwargs):
    return io.BytesIO(b'{"status":"ok"}')


def _fake_file_opener(path, mode="r", **kwargs):
    return io.StringIO("README CONTENT")


def _fake_file_writer(path, content, **kwargs):
    return None


def run_langgraph_eval_case(case: LangGraphEvalCase) -> EvaluationResult:
    """Run one LangGraph eval case locally."""

    @tool
    def status(message: str) -> str:
        """Return a status message."""

        return f"status:{message}"

    audit_sink = InMemoryAuditSink()
    firewall = create_firewall(
        config=FirewallConfig(
            name=f"eval:{case.name}",
            log_only=case.log_only,
        ),
        audit_sink=audit_sink,
        approval_handler=_make_approval_handler(case),
    )
    agent = create_agent(
        model=_build_model(case),
        tools=[
            status,
            create_shell_tool(
                firewall=firewall,
                runner=_fake_shell_runner,
            ),
            create_http_tool(
                firewall=firewall,
                opener=_fake_http_opener,
            ),
            create_file_reader_tool(
                firewall=firewall,
                opener=_fake_file_opener,
            ),
            create_file_writer_tool(
                firewall=firewall,
                writer=_fake_file_writer,
            ),
        ],
        firewall=firewall,
    )

    status_value = EvalRunStatus.ERROR
    detail = ""
    try:
        agent.invoke({"messages": [{"role": "user", "content": case.prompt}]})
        status_value = EvalRunStatus.COMPLETED
    except ReviewRequired as exc:
        status_value = EvalRunStatus.REVIEW_REQUIRED
        detail = str(exc)
    except FirewallViolation as exc:
        status_value = EvalRunStatus.BLOCKED
        detail = str(exc)
    except Exception as exc:  # pragma: no cover - defensive path
        status_value = EvalRunStatus.ERROR
        detail = f"{type(exc).__name__}: {exc}"

    observed_event_kinds = [entry.event.kind.value for entry in audit_sink.entries]
    observed_actions = [entry.decision.action.value for entry in audit_sink.entries]
    observed_final_action = observed_actions[-1] if observed_actions else "none"
    matched = (
        status_value == case.expected_status
        and observed_final_action == case.expected_final_action
        and (
            not case.expected_event_kinds
            or observed_event_kinds == case.expected_event_kinds
        )
        and (
            not case.expected_action_sequence
            or observed_actions == case.expected_action_sequence
        )
    )
    if not matched and not detail:
        detail = (
            "Expected status/action/trace did not match. "
            f"observed_status={status_value.value}, "
            f"observed_final_action={observed_final_action}, "
            f"observed_event_kinds={observed_event_kinds}, "
            f"observed_actions={observed_actions}"
        )
    return EvaluationResult(
        name=case.name,
        task=case.task,
        workflow_goal=case.workflow_goal,
        status=status_value,
        expected_status=case.expected_status,
        matched=matched,
        observed_event_kinds=observed_event_kinds,
        observed_actions=observed_actions,
        expected_final_action=case.expected_final_action,
        observed_final_action=observed_final_action,
        expected_event_kinds=list(case.expected_event_kinds),
        expected_action_sequence=list(case.expected_action_sequence),
        audit_summary=audit_sink.summary().to_dict(),
        audit_trace=[
            {
                "event_kind": entry.event.kind.value,
                "event_operation": entry.event.operation,
                "action": entry.decision.action.value,
                "rule": entry.decision.rule,
                "source": entry.event.source,
                "decision_metadata": dict(entry.decision.metadata),
                "runtime_context": dict(
                    entry.event.payload.get("runtime_context", {})
                ),
            }
            for entry in audit_sink.entries
        ],
        detail=detail,
    )


def run_langgraph_eval_suite(
    path: str | Traversable | None = None,
) -> EvaluationSummary:
    """Run a LangGraph eval suite from a JSON file."""

    cases = load_langgraph_eval_cases(path)
    return EvaluationSummary(
        results=[run_langgraph_eval_case(case) for case in cases]
    )


def main() -> None:
    summary = run_langgraph_eval_suite()
    print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
