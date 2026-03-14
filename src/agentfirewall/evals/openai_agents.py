"""Local OpenAI Agents SDK eval runner for AgentFirewall."""

from __future__ import annotations

import json
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
    create_agent as create_firewalled_openai_agents_agent,
    create_file_reader_tool,
    create_file_writer_tool,
    create_http_tool,
    create_shell_tool,
)
from .models import EvalRunStatus, EvaluationResult, EvaluationSummary

try:
    from agents import Agent, Runner, function_tool
    OPENAI_AGENTS_AVAILABLE = True
except ImportError:
    OPENAI_AGENTS_AVAILABLE = False


@dataclass(slots=True)
class OpenAIAgentsEvalCase:
    """Serializable OpenAI Agents SDK eval case."""

    name: str
    prompt: str
    task: str = ""
    workflow_goal: str = ""
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


def _default_case_resource() -> Traversable:
    return resources.files("agentfirewall.evals").joinpath("cases/openai_agents_cases.json")


def load_openai_agents_eval_cases(path: str | Traversable | None = None) -> list[OpenAIAgentsEvalCase]:
    """Load OpenAI Agents SDK eval cases from JSON."""

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


def _build_tools_for_case(case: OpenAIAgentsEvalCase, firewall: Any) -> list[Any]:
    """Build guarded tools based on eval case requirements."""
    tools = []
    
    # Check what tools are needed based on tool_calls
    tool_names = {tc.get("name", "") for tc in case.tool_calls}
    
    if "shell" in tool_names:
        tools.append(create_shell_tool(firewall=firewall))
    if "http_request" in tool_names:
        tools.append(create_http_tool(firewall=firewall))
    if "read_file" in tool_names:
        tools.append(create_file_reader_tool(firewall=firewall))
    if "write_file" in tool_names:
        tools.append(create_file_writer_tool(firewall=firewall))
    
    # Add benign tools for safe cases
    if "calculator" in tool_names:
        @function_tool(name="calculator", description="Calculate a mathematical expression")
        def calculator(expression: str) -> str:
            try:
                result = eval(expression, {"__builtins__": {}}, {})
                return str(result)
            except Exception:
                return "error"
        tools.append(calculator)
    
    return tools


def run_openai_agents_eval_case(
    case: OpenAIAgentsEvalCase,
    *,
    approval_handler: ApprovalHandler | None = None,
    log_only: bool = False,
) -> EvaluationResult:
    """Run a single OpenAI Agents SDK eval case."""
    
    if not OPENAI_AGENTS_AVAILABLE:
        return EvaluationResult(
            case_name=case.name,
            status=EvalRunStatus.SKIPPED,
            error="OpenAI Agents SDK not available",
        )
    
    audit_sink = InMemoryAuditSink()
    firewall = create_firewall(
        config=FirewallConfig(name=f"eval-{case.name}"),
        audit_sink=audit_sink,
        approval_handler=approval_handler,
        log_only=log_only or case.log_only,
    )
    
    tools = _build_tools_for_case(case, firewall)
    
    agent = Agent(
        name=f"Eval Agent - {case.name}",
        instructions="You are a helpful assistant.",
        tools=tools,
    )
    
    firewalled_agent = create_firewalled_openai_agents_agent(
        agent=agent,
        firewall=firewall,
        inspect_prompts=True,
    )
    
    try:
        result = Runner.run_sync(firewalled_agent, case.prompt)
        actual_status = EvalRunStatus.COMPLETED
        actual_final_action = "allow"
        actual_response = result.final_output if hasattr(result, "final_output") else ""
    except ReviewRequired as exc:
        actual_status = EvalRunStatus.REVIEW_REQUIRED
        actual_final_action = "review"
        actual_response = None
    except FirewallViolation as exc:
        actual_status = EvalRunStatus.BLOCKED
        actual_final_action = "block"
        actual_response = None
    except Exception as exc:
        return EvaluationResult(
            case_name=case.name,
            status=EvalRunStatus.ERROR,
            error=str(exc),
        )
    
    audit_entries = list(audit_sink.entries)
    event_kinds = [entry.event.kind for entry in audit_entries]
    action_sequence = [entry.decision.action for entry in audit_entries]
    
    status_ok = actual_status == case.expected_status
    action_ok = actual_final_action == case.expected_final_action
    events_ok = event_kinds == case.expected_event_kinds if case.expected_event_kinds else True
    sequence_ok = action_sequence == case.expected_action_sequence if case.expected_action_sequence else True
    
    passed = status_ok and action_ok and (events_ok or not case.expected_event_kinds) and (sequence_ok or not case.expected_action_sequence)
    
    return EvaluationResult(
        case_name=case.name,
        status=actual_status,
        passed=passed,
        audit_entries=audit_entries,
        actual_final_action=actual_final_action,
        expected_final_action=case.expected_final_action,
        actual_event_kinds=event_kinds,
        expected_event_kinds=case.expected_event_kinds,
        actual_action_sequence=action_sequence,
        expected_action_sequence=case.expected_action_sequence,
        error=None,
    )


def run_openai_agents_evals(
    cases: list[OpenAIAgentsEvalCase] | None = None,
    *,
    approval_handler: ApprovalHandler | None = None,
) -> EvaluationSummary:
    """Run all OpenAI Agents SDK eval cases."""
    
    if not OPENAI_AGENTS_AVAILABLE:
        return EvaluationSummary(
            total=0,
            passed=0,
            failed=0,
            results=[],
            status_message="OpenAI Agents SDK not available",
        )
    
    if cases is None:
        cases = load_openai_agents_eval_cases()
    
    results: list[EvaluationResult] = []
    for case in cases:
        result = run_openai_agents_eval_case(case, approval_handler=approval_handler)
        results.append(result)
    
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    
    return EvaluationSummary(
        total=len(results),
        passed=passed,
        failed=failed,
        results=results,
        status_message=f"OpenAI Agents evals: {passed}/{len(results)} passed",
    )


def main() -> None:
    """CLI entrypoint for OpenAI Agents SDK evals."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run OpenAI Agents SDK evals")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()
    
    if not OPENAI_AGENTS_AVAILABLE:
        print("OpenAI Agents SDK not available. Install with:")
        print("  pip install openai-agents")
        return
    
    summary = run_openai_agents_evals()
    
    print(f"\n{'='*60}")
    print(f"OpenAI Agents SDK Eval Summary")
    print(f"{'='*60}")
    print(f"Total: {summary.total}")
    print(f"Passed: {summary.passed}")
    print(f"Failed: {summary.failed}")
    print(f"\nStatus: {summary.status_message}")
    
    if args.verbose and summary.results:
        print(f"\n{'='*60}")
        print("Detailed Results")
        print(f"{'='*60}")
        for result in summary.results:
            status_icon = "✅" if result.passed else "❌"
            print(f"\n{status_icon} {result.case_name}")
            print(f"  Status: {result.status.value}")
            print(f"  Action: {result.actual_final_action} (expected: {result.expected_final_action})")
            if result.error:
                print(f"  Error: {result.error}")
            if result.actual_event_kinds:
                print(f"  Events: {result.actual_event_kinds}")
            if result.actual_action_sequence:
                print(f"  Actions: {result.actual_action_sequence}")
    
    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()
