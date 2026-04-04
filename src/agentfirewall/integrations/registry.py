"""Registry helpers for official AgentFirewall runtime adapters."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from importlib.resources.abc import Traversable
from typing import Any

from ..evals.contracts import (
    EvalExpectationReport,
    EvalSuiteExpectations,
    validate_eval_summary_against_expectations,
)
from .conformance import ConformanceReport, validate_eval_summary
from .contracts import RuntimeAdapterSpec, capability_matrix_row
from .langgraph import get_langgraph_adapter_spec
from .openai_agents import get_openai_agents_adapter_spec


@dataclass(frozen=True, slots=True)
class OfficialAdapterDefinition:
    """Registry record for one official runtime adapter."""

    spec: RuntimeAdapterSpec
    eval_runner: str = ""
    eval_expectations: EvalSuiteExpectations | None = None

    @property
    def name(self) -> str:
        return self.spec.name

    def has_eval_suite(self) -> bool:
        return bool(self.eval_runner)

    def has_eval_expectations(self) -> bool:
        return self.eval_expectations is not None

    def run_eval_suite(
        self,
        path: str | Traversable | None = None,
    ) -> Any:
        """Run the adapter's packaged eval suite."""

        if not self.eval_runner:
            raise ValueError(
                f"Official adapter {self.name!r} does not declare an eval runner."
            )

        module_name, attribute = self.eval_runner.split(":", maxsplit=1)
        module = import_module(module_name)
        runner = getattr(module, attribute)
        if path is None:
            return runner()
        return runner(path)

    def validate_conformance(
        self,
        *,
        path: str | Traversable | None = None,
    ) -> ConformanceReport:
        """Run the packaged eval suite and validate it against the adapter contract."""

        summary = self.run_eval_suite(path=path)
        return validate_eval_summary(summary.to_dict(), self.spec)

    def validate_eval_expectations(
        self,
        *,
        path: str | Traversable | None = None,
    ) -> EvalExpectationReport:
        """Run the packaged eval suite and validate the release-gate expectations."""

        if self.eval_expectations is None:
            raise ValueError(
                f"Official adapter {self.name!r} does not declare eval expectations."
            )

        summary = self.run_eval_suite(path=path)
        return validate_eval_summary_against_expectations(
            summary.to_dict(),
            self.eval_expectations,
        )

    def resolve_eval_case_alias(self, alias: str) -> str:
        """Return the concrete eval-case name for one registered alias."""

        if self.eval_expectations is None:
            raise ValueError(
                f"Official adapter {self.name!r} does not declare eval expectations."
            )
        return self.eval_expectations.case_name(alias)

    def validate_release_gate(
        self,
        *,
        path: str | Traversable | None = None,
    ) -> "OfficialAdapterReleaseGateReport":
        """Run the packaged adapter release gate against one shared eval summary."""

        summary = self.run_eval_suite(path=path)
        payload = summary.to_dict()
        conformance = validate_eval_summary(payload, self.spec)
        eval_expectations = None
        if self.eval_expectations is not None:
            eval_expectations = validate_eval_summary_against_expectations(
                payload,
                self.eval_expectations,
            )
        return OfficialAdapterReleaseGateReport(
            adapter=self.name,
            conformance=conformance,
            eval_expectations=eval_expectations,
        )

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-friendly registry record for one official adapter."""

        payload = {
            "name": self.name,
            "spec": self.spec.to_dict(),
            "has_eval_suite": self.has_eval_suite(),
            "has_eval_expectations": self.has_eval_expectations(),
        }
        if self.eval_runner:
            payload["eval_runner"] = self.eval_runner
        if self.eval_expectations is not None:
            payload["eval_expectations"] = self.eval_expectations.to_dict()
        return payload


@dataclass(frozen=True, slots=True)
class OfficialAdapterReleaseGateReport:
    """Combined release-gate result for one official runtime adapter."""

    adapter: str
    conformance: ConformanceReport
    eval_expectations: EvalExpectationReport | None = None

    @property
    def ok(self) -> bool:
        return self.conformance.ok and (
            self.eval_expectations is None
            or self.eval_expectations.ok
        )

    def to_dict(self) -> dict[str, object]:
        payload = {
            "adapter": self.adapter,
            "ok": self.ok,
            "conformance": self.conformance.to_dict(),
        }
        if self.eval_expectations is not None:
            payload["eval_expectations"] = self.eval_expectations.to_dict()
        return payload


_OFFICIAL_ADAPTERS: dict[str, OfficialAdapterDefinition] = {
    "langgraph": OfficialAdapterDefinition(
        spec=get_langgraph_adapter_spec(),
        eval_runner="agentfirewall.evals:run_langgraph_eval_suite",
        eval_expectations=EvalSuiteExpectations(
            total=19,
            status_counts={
                "completed": 9,
                "blocked": 8,
                "review_required": 2,
            },
            task_counts={
                "incident_triage": 2,
                "secret_access": 2,
                "credential_injection": 1,
                "safe_file_write": 1,
            },
            named_cases={
                "safe_status_tool": "safe_status_tool",
                "review_required_tool": "shell_tool_review_without_handler",
                "safe_file_write": "guarded_file_write_allows_safe_path",
                "workflow_shell_then_http": "workflow_shell_approved_then_trusted_http",
                "workflow_shell_then_file_then_http": (
                    "workflow_shell_approved_then_safe_file_then_trusted_http"
                ),
                "log_only_workflow": "log_only_shell_then_blocked_http",
            },
        ),
    ),
    "openai_agents": OfficialAdapterDefinition(
        spec=get_openai_agents_adapter_spec(),
        eval_runner="agentfirewall.evals:run_openai_agents_eval_suite",
        eval_expectations=EvalSuiteExpectations(
            total=11,
            status_counts={
                "completed": 6,
                "blocked": 3,
                "review_required": 2,
            },
            task_counts={
                "benign_calculation": 1,
                "prompt_injection_attempt": 1,
                "shell_access": 1,
                "shell_access_approved": 1,
                "dangerous_command_attempt": 1,
                "sensitive_file_attempt": 1,
                "untrusted_host_attempt": 1,
                "log_only_demonstration": 1,
                "nested_side_effects_correlation": 1,
                "repo_triage": 1,
                "incident_triage": 1,
            },
            named_cases={
                "safe_function_tool": "safe_function_tool",
                "prompt_review": "prompt_injection_review",
                "shell_review": "shell_tool_review",
                "approved_shell": "shell_tool_approved",
                "blocked_command": "dangerous_command_blocked",
                "blocked_sensitive_read": "sensitive_file_access_blocked",
                "blocked_http": "untrusted_host_blocked",
                "log_only_workflow": "log_only_workflow",
                "nested_side_effects": "nested_side_effects",
                "workflow_repo_triage": "workflow_status_then_safe_file_then_trusted_http",
                "workflow_shell_then_file_then_http": (
                    "workflow_shell_approved_then_safe_file_then_trusted_http"
                ),
            },
        ),
    ),
}


def list_official_adapters() -> tuple[OfficialAdapterDefinition, ...]:
    """Return every official runtime-adapter registry entry."""

    return tuple(_OFFICIAL_ADAPTERS.values())


def list_official_adapter_specs() -> tuple[RuntimeAdapterSpec, ...]:
    """Return the declared contract for every official runtime adapter."""

    return tuple(adapter.spec for adapter in list_official_adapters())


def get_official_adapter(name: str) -> OfficialAdapterDefinition:
    """Return the registry record for one official runtime adapter."""

    try:
        return _OFFICIAL_ADAPTERS[name]
    except KeyError as exc:
        raise KeyError(f"Unknown official adapter: {name}") from exc


def get_official_adapter_spec(name: str) -> RuntimeAdapterSpec:
    """Return the declared contract for one official runtime adapter."""

    return get_official_adapter(name).spec


def export_official_adapter_matrix() -> list[dict[str, object]]:
    """Return the current official adapter capability matrix."""

    return [
        capability_matrix_row(adapter.spec)
        for adapter in list_official_adapters()
    ]


def export_official_adapter_inventory() -> list[dict[str, object]]:
    """Return the current official adapter registry as JSON-friendly records."""

    return [adapter.to_dict() for adapter in list_official_adapters()]


def run_official_adapter_eval_suite(
    name: str,
    *,
    path: str | Traversable | None = None,
) -> Any:
    """Run the packaged eval suite for one official adapter."""

    return get_official_adapter(name).run_eval_suite(path=path)


def validate_official_adapter_conformance(
    name: str,
    *,
    path: str | Traversable | None = None,
) -> ConformanceReport:
    """Run packaged eval evidence and validate it against the adapter contract."""

    return get_official_adapter(name).validate_conformance(path=path)


def validate_official_adapter_eval_expectations(
    name: str,
    *,
    path: str | Traversable | None = None,
) -> EvalExpectationReport:
    """Run packaged eval evidence and validate the adapter's release-gate expectations."""

    return get_official_adapter(name).validate_eval_expectations(path=path)


def validate_official_adapter_release_gate(
    name: str,
    *,
    path: str | Traversable | None = None,
) -> OfficialAdapterReleaseGateReport:
    """Run the shared release gate for one official runtime adapter."""

    return get_official_adapter(name).validate_release_gate(path=path)
