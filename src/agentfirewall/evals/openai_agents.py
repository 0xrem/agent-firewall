"""Local OpenAI Agents SDK eval runner for AgentFirewall."""

from __future__ import annotations

import io
import json
import subprocess
from dataclasses import dataclass, field
from importlib import resources
from importlib.resources.abc import Traversable
from typing import Any

from ..approval import ApprovalHandler, ApprovalOutcome, ApprovalResponse
from ..audit import InMemoryAuditSink, export_audit_trace
from ..config import FirewallConfig
from ..exceptions import FirewallViolation, ReviewRequired
from ..firewall import create_firewall
from ..openai_agents import (
    create_agent,
    create_file_reader_tool,
    create_file_writer_tool,
    create_http_tool,
    create_shell_tool,
)
from ..policy_packs import named_policy_pack
from .models import EvalRunStatus, EvaluationResult, EvaluationSummary

try:
    from agents import Agent, Runner, function_tool
    from agents.items import ModelResponse
    from agents.models.interface import Model
    from agents.run_config import RunConfig
    from agents.usage import Usage
    from openai.types.responses import (
        ResponseFunctionToolCall,
        ResponseOutputMessage,
        ResponseOutputText,
    )
except ImportError:  # pragma: no cover - optional dependency guard
    OPENAI_AGENTS_AVAILABLE = False
else:
    OPENAI_AGENTS_AVAILABLE = True


@dataclass(slots=True)
class OpenAIAgentsEvalCase:
    """Serializable OpenAI Agents eval case."""

    name: str
    prompt: str
    task: str = ""
    workflow_goal: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    expected_status: EvalRunStatus | str = EvalRunStatus.COMPLETED
    expected_final_action: str = "allow"
    expected_event_kinds: list[str] = field(default_factory=list)
    expected_action_sequence: list[str] = field(default_factory=list)
    final_response: str | None = "done"
    approval_outcome: ApprovalOutcome | str | None = None
    approval_reason: str = ""
    log_only: bool = False

    def __post_init__(self) -> None:
        if isinstance(self.expected_status, str):
            self.expected_status = EvalRunStatus(self.expected_status)
        if isinstance(self.approval_outcome, str):
            self.approval_outcome = ApprovalOutcome(self.approval_outcome)


if OPENAI_AGENTS_AVAILABLE:

    class SequentialFakeModel(Model):
        """Minimal fake model for local tool-calling evals."""

        def __init__(self, outputs: list[ModelResponse]) -> None:
            self.outputs = list(outputs)
            self.calls = 0

        async def get_response(
            self,
            system_instructions,
            input,
            model_settings,
            tools,
            output_schema,
            handoffs,
            tracing,
            *,
            previous_response_id,
            conversation_id,
            prompt,
        ):
            output = self.outputs[self.calls]
            self.calls += 1
            return output

        def stream_response(self, *args, **kwargs):
            raise NotImplementedError


def _default_case_resource() -> Traversable:
    return resources.files("agentfirewall.evals").joinpath("cases/openai_agents_cases.json")


def load_openai_agents_eval_cases(
    path: str | Traversable | None = None,
) -> list[OpenAIAgentsEvalCase]:
    """Load OpenAI Agents eval cases from JSON."""

    if path is None:
        payload = json.loads(_default_case_resource().read_text(encoding="utf-8"))
    else:
        target = path if hasattr(path, "read_text") else str(path)
        if hasattr(target, "read_text"):
            payload = json.loads(target.read_text(encoding="utf-8"))
        else:
            with open(target, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
    return [OpenAIAgentsEvalCase(**case) for case in payload]


def _require_openai_agents() -> None:
    if not OPENAI_AGENTS_AVAILABLE:
        raise ImportError(
            "OpenAI Agents evals require optional dependencies. "
            "Install with `pip install agentfirewall[openai-agents]`."
        )


def _make_approval_handler(case: OpenAIAgentsEvalCase) -> ApprovalHandler | None:
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


def _tool_call_output(*, call_id: str, name: str, arguments: dict[str, Any]) -> ModelResponse:
    return ModelResponse(
        output=[
            ResponseFunctionToolCall(
                arguments=json.dumps(arguments),
                call_id=call_id,
                name=name,
                type="function_call",
            )
        ],
        usage=Usage(),
        response_id=f"resp_{call_id}",
    )


def _final_text_output(text: str) -> ModelResponse:
    return ModelResponse(
        output=[
            ResponseOutputMessage(
                id="msg_final",
                content=[
                    ResponseOutputText(
                        annotations=[],
                        text=text,
                        type="output_text",
                    )
                ],
                role="assistant",
                status="completed",
                type="message",
            )
        ],
        usage=Usage(),
        response_id="resp_final",
    )


def _build_model(case: OpenAIAgentsEvalCase) -> Any:
    _require_openai_agents()
    outputs = [
        _tool_call_output(
            call_id=str(tool_call["id"]),
            name=str(tool_call["name"]),
            arguments=dict(tool_call.get("args", {})),
        )
        for tool_call in case.tool_calls
    ]
    outputs.append(_final_text_output(case.final_response or "done"))
    return SequentialFakeModel(outputs)


def _fake_shell_runner(command, *, shell=False, cwd=None, **kwargs):
    rendered = command if isinstance(command, str) else " ".join(str(part) for part in command)
    if "pwd" in rendered:
        stdout = "/home/user\n"
    elif "ls" in rendered:
        stdout = "file1.txt\nfile2.txt\n"
    else:
        stdout = "done\n"
    return subprocess.CompletedProcess(
        args=command,
        returncode=0,
        stdout=stdout,
    )


def _build_file_helpers() -> tuple[dict[str, str], Any, Any]:
    file_store: dict[str, str] = {}

    def opener(path, mode="r", **kwargs):
        key = str(path)
        if any(flag in mode for flag in ("w", "a", "+", "x")):
            return io.StringIO()
        return io.StringIO(file_store.get(key, "README CONTENT"))

    def writer(path: str, content: str, **kwargs) -> None:
        file_store[str(path)] = content

    return file_store, opener, writer


def _fake_http_opener(request, **kwargs):
    url = getattr(request, "full_url", "")
    if not url and hasattr(request, "get_full_url"):
        url = request.get_full_url()
    if "trusted.com" in str(url):
        return io.BytesIO(b"uploaded successfully")
    return io.BytesIO(b'{"status":"ok"}')


def _build_tools_for_case(case: OpenAIAgentsEvalCase, firewall: Any) -> list[Any]:
    _require_openai_agents()
    tool_names = {str(tool_call.get("name", "")) for tool_call in case.tool_calls}
    file_store, file_opener, file_writer = _build_file_helpers()
    tools: list[Any] = []

    if "shell" in tool_names:
        tools.append(
            create_shell_tool(
                firewall=firewall,
                runner=_fake_shell_runner,
            )
        )
    if "http_request" in tool_names:
        tools.append(
            create_http_tool(
                firewall=firewall,
                opener=_fake_http_opener,
            )
        )
    if "read_file" in tool_names:
        tools.append(
            create_file_reader_tool(
                firewall=firewall,
                opener=file_opener,
            )
        )
    if "write_file" in tool_names:
        tools.append(
            create_file_writer_tool(
                firewall=firewall,
                writer=file_writer,
            )
        )
    if "calculator" in tool_names:

        @function_tool(
            name_override="calculator",
            description_override="Calculate a mathematical expression.",
            failure_error_function=None,
        )
        def calculator(expression: str) -> str:
            return str(eval(expression, {"__builtins__": {}}, {}))

        tools.append(calculator)

    return tools


def run_openai_agents_eval_case(case: OpenAIAgentsEvalCase) -> EvaluationResult:
    """Run one OpenAI Agents eval case locally."""

    _require_openai_agents()
    audit_sink = InMemoryAuditSink()
    firewall = create_firewall(
        config=FirewallConfig(
            name=f"eval:{case.name}",
            log_only=case.log_only,
        ),
        policy_pack=named_policy_pack("default", trusted_hosts=("api.trusted.com",)),
        audit_sink=audit_sink,
        approval_handler=_make_approval_handler(case),
    )
    agent = create_agent(
        agent=Agent(
            name=f"Eval Agent - {case.name}",
            instructions="You are a helpful assistant.",
            tools=_build_tools_for_case(case, firewall),
            model=_build_model(case),
        ),
        firewall=firewall,
        inspect_prompts=True,
    )

    status_value = EvalRunStatus.ERROR
    detail = ""
    try:
        Runner.run_sync(
            agent,
            case.prompt,
            run_config=RunConfig(tracing_disabled=True),
        )
        status_value = EvalRunStatus.COMPLETED
    except ReviewRequired as exc:
        status_value = EvalRunStatus.REVIEW_REQUIRED
        detail = str(exc)
    except FirewallViolation as exc:
        status_value = EvalRunStatus.BLOCKED
        detail = str(exc)
    except Exception as exc:  # pragma: no cover - defensive path
        detail = f"{type(exc).__name__}: {exc}"
        # OpenAI Agents may surface tool-call failures as UserError even when the
        # underlying firewall action was review/block. Keep eval status aligned
        # with the recorded audit evidence instead of the transport exception.
        if audit_sink.entries:
            last_action = audit_sink.entries[-1].decision.action.value
            if last_action == "review":
                status_value = EvalRunStatus.REVIEW_REQUIRED
            elif last_action == "block":
                status_value = EvalRunStatus.BLOCKED
            else:
                status_value = EvalRunStatus.ERROR
        else:
            status_value = EvalRunStatus.ERROR

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
        audit_trace=export_audit_trace(audit_sink.entries),
        detail=detail,
    )


def run_openai_agents_eval_suite(
    path: str | Traversable | None = None,
) -> EvaluationSummary:
    """Run the packaged OpenAI Agents eval suite."""

    cases = load_openai_agents_eval_cases(path)
    return EvaluationSummary(
        results=[run_openai_agents_eval_case(case) for case in cases]
    )


def main() -> None:
    if not OPENAI_AGENTS_AVAILABLE:
        print(
            "OpenAI Agents evals require optional dependencies. "
            "Install with `pip install agentfirewall[openai-agents]`."
        )
        return

    summary = run_openai_agents_eval_suite()
    print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
