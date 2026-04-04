"""Local MCP server preview eval runner for AgentFirewall."""

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
from ..mcp import create_server_bundle
from ..policy import Decision
from ..policy_packs import named_policy_pack
from .models import EvalRunStatus, EvaluationResult, EvaluationSummary


def _resource_rule(event):
    if event.kind.value != "resource_access":
        return None
    uri = str(event.payload.get("uri", ""))
    if uri.startswith("mcp://private/"):
        return Decision.block(
            reason="Private MCP resource is blocked in the loopback preview.",
            rule="block_private_mcp_resource",
            metadata={"mcp_resource_uri": uri},
        )
    return None


@dataclass(slots=True)
class McpServerEvalCase:
    name: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    task: str = ""
    workflow_goal: str = ""
    expected_status: EvalRunStatus | str = EvalRunStatus.COMPLETED
    expected_final_action: str = "allow"
    expected_event_kinds: list[str] = field(default_factory=list)
    expected_action_sequence: list[str] = field(default_factory=list)
    approval_outcome: ApprovalOutcome | str | None = None
    approval_reason: str = ""
    log_only: bool = False

    def __post_init__(self) -> None:
        if isinstance(self.expected_status, str):
            self.expected_status = EvalRunStatus(self.expected_status)
        if isinstance(self.approval_outcome, str):
            self.approval_outcome = ApprovalOutcome(self.approval_outcome)


def _default_case_resource() -> Traversable:
    return resources.files("agentfirewall.evals").joinpath("cases/mcp_server_cases.json")


def load_mcp_server_eval_cases(path: str | Traversable | None = None) -> list[McpServerEvalCase]:
    if path is None:
        payload = json.loads(_default_case_resource().read_text(encoding="utf-8"))
    else:
        target = path if hasattr(path, "read_text") else str(path)
        if hasattr(target, "read_text"):
            payload = json.loads(target.read_text(encoding="utf-8"))
        else:
            with open(target, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
    return [McpServerEvalCase(**case) for case in payload]


def _make_approval_handler(case: McpServerEvalCase) -> ApprovalHandler | None:
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
    return subprocess.CompletedProcess(args=command, returncode=0, stdout="repo files\n")


def _fake_http_opener(request, **kwargs):
    url = getattr(request, "full_url", "")
    if "trusted.local" in str(url):
        return io.BytesIO(b'{"status":"trusted"}')
    return io.BytesIO(b'{"status":"ok"}')


def _fake_file_opener(path, mode="r", **kwargs):
    return io.StringIO("README CONTENT")


def _fake_resource_reader(uri: str, **kwargs):
    resources_map = {
        "mcp://docs/README.md": "# repo docs",
        "mcp://private/secrets": "TOP-SECRET",
    }
    return resources_map[uri]


def _register_tools(bundle) -> None:
    bundle.register_tool("status", lambda message: f"status:{message}")
    bundle.register_tool(
        "shell",
        lambda command: bundle.command_runner.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip(),
    )
    bundle.register_tool(
        "http_request",
        lambda url, method="GET": bundle.http_client.request(url, method=method).read(),
    )
    bundle.register_tool(
        "read_file",
        lambda path: bundle.file_access.open(path, "r").read(),
    )
    bundle.register_tool(
        "write_file",
        lambda path, content: bundle.file_access.open(path, "w").write(content),
    )


def run_mcp_server_eval_case(case: McpServerEvalCase) -> EvaluationResult:
    audit_sink = InMemoryAuditSink()
    bundle = create_server_bundle(
        config=FirewallConfig(name=f"eval:{case.name}", log_only=case.log_only),
        policy_pack=named_policy_pack("default", trusted_hosts=("api.openai.com", "trusted.local")),
        audit_sink=audit_sink,
        approval_handler=_make_approval_handler(case),
        runner=_fake_shell_runner,
        http_opener=_fake_http_opener,
        file_opener=_fake_file_opener,
        resource_reader=_fake_resource_reader,
        tool_call_id_factory=lambda name, args, kwargs: f"call_eval_{name}",
        resource_call_id_factory=lambda uri, server_name=None: "call_eval_resource_read",
    )
    bundle.firewall.add_rule(_resource_rule)
    _register_tools(bundle)

    status_value = EvalRunStatus.ERROR
    detail = ""
    try:
        for step in case.steps:
            kind = str(step["kind"])
            if kind == "tool_call":
                bundle.call_tool(
                    str(step["name"]),
                    *tuple(step.get("args", ())),
                    server_name=step.get("server_name"),
                    kwargs=dict(step.get("kwargs", {})),
                )
            elif kind == "resource_read":
                bundle.read_resource(
                    str(step["uri"]),
                    server_name=step.get("server_name"),
                    mime_type=step.get("mime_type"),
                )
            else:
                raise AssertionError(f"Unsupported step kind: {kind}")
        status_value = EvalRunStatus.COMPLETED
    except ReviewRequired as exc:
        status_value = EvalRunStatus.REVIEW_REQUIRED
        detail = str(exc)
    except FirewallViolation as exc:
        status_value = EvalRunStatus.BLOCKED
        detail = str(exc)
    except Exception as exc:  # pragma: no cover
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
        audit_trace=export_audit_trace(audit_sink.entries),
        detail=detail,
    )


def run_mcp_server_eval_suite(path: str | Traversable | None = None) -> EvaluationSummary:
    cases = load_mcp_server_eval_cases(path)
    return EvaluationSummary(results=[run_mcp_server_eval_case(case) for case in cases])


def main() -> None:
    summary = run_mcp_server_eval_suite()
    print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
