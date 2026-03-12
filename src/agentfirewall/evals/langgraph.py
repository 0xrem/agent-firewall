"""Local LangGraph eval runner for AgentFirewall."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from importlib import resources
from importlib.resources.abc import Traversable
from typing import Any

from ..approval import ApprovalHandler, ApprovalOutcome, ApprovalResponse
from ..audit import InMemoryAuditSink
from ..config import FirewallConfig
from ..exceptions import FirewallViolation, ReviewRequired
from ..firewall import AgentFirewall
from ..integrations.langgraph import create_firewalled_langgraph_agent
from ..policy_packs import build_builtin_policy_engine, named_policy_pack

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
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    expected_status: EvalRunStatus | str = EvalRunStatus.COMPLETED
    expected_final_action: str = "allow"
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
    status: EvalRunStatus
    expected_status: EvalRunStatus
    matched: bool
    observed_actions: list[str]
    expected_final_action: str
    observed_final_action: str
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
            "unexpected_allows": self.unexpected_allows,
            "unexpected_blocks": self.unexpected_blocks,
            "unexpected_reviews": self.unexpected_reviews,
            "results": [
                {
                    "name": result.name,
                    "status": result.status.value,
                    "expected_status": result.expected_status.value,
                    "matched": result.matched,
                    "observed_actions": result.observed_actions,
                    "expected_final_action": result.expected_final_action,
                    "observed_final_action": result.observed_final_action,
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


def run_langgraph_eval_case(case: LangGraphEvalCase) -> EvaluationResult:
    """Run one LangGraph eval case locally."""

    @tool
    def status(message: str) -> str:
        """Return a status message."""

        return f"status:{message}"

    @tool
    def shell(command: str) -> str:
        """Run a shell command."""

        return f"shell:{command}"

    audit_sink = InMemoryAuditSink()
    firewall = AgentFirewall(
        config=FirewallConfig(
            name=f"eval:{case.name}",
            log_only=case.log_only,
        ),
        policy=build_builtin_policy_engine(named_policy_pack("default")),
        audit_sink=audit_sink,
        approval_handler=_make_approval_handler(case),
    )
    agent = create_firewalled_langgraph_agent(
        model=_build_model(case),
        tools=[status, shell],
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

    observed_actions = [entry.decision.action.value for entry in audit_sink.entries]
    observed_final_action = observed_actions[-1] if observed_actions else "none"
    matched = (
        status_value == case.expected_status
        and observed_final_action == case.expected_final_action
    )
    return EvaluationResult(
        name=case.name,
        status=status_value,
        expected_status=case.expected_status,
        matched=matched,
        observed_actions=observed_actions,
        expected_final_action=case.expected_final_action,
        observed_final_action=observed_final_action,
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
