"""Support-path inventory for official adapters and preview runtimes."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from importlib import import_module
from importlib.resources.abc import Traversable
from typing import Any

from .evals.contracts import (
    EvalExpectationReport,
    EvalSuiteExpectations,
    validate_eval_summary_against_expectations,
)
from .integrations.contracts import (
    AdapterCapability,
    AdapterSupportLevel,
    RuntimeAdapterSpec,
    capability_matrix_row,
    capability_set,
)
from .integrations.registry import list_official_adapters


class RuntimeSupportKind(str, Enum):
    """High-level classification for runtime support paths."""

    OFFICIAL_ADAPTER = "official_adapter"
    PREVIEW_RUNTIME = "preview_runtime"


@dataclass(frozen=True, slots=True)
class PreviewRuntimeDefinition:
    """Registry record for one non-official runtime support path."""

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
        """Run the preview runtime's packaged local eval suite."""

        if not self.eval_runner:
            raise ValueError(
                f"Preview runtime {self.name!r} does not declare an eval runner."
            )

        module_name, attribute = self.eval_runner.split(":", maxsplit=1)
        module = import_module(module_name)
        runner = getattr(module, attribute)
        if path is None:
            return runner()
        return runner(path)

    def validate_eval_expectations(
        self,
        *,
        path: str | Traversable | None = None,
    ) -> EvalExpectationReport:
        """Validate packaged eval evidence for the preview runtime."""

        if self.eval_expectations is None:
            raise ValueError(
                f"Preview runtime {self.name!r} does not declare eval expectations."
            )

        summary = self.run_eval_suite(path=path)
        return validate_eval_summary_against_expectations(
            summary.to_dict(),
            self.eval_expectations,
        )

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-friendly representation of the preview runtime."""

        payload = {
            "name": self.name,
            "kind": RuntimeSupportKind.PREVIEW_RUNTIME.value,
            "spec": self.spec.to_dict(),
            "has_eval_suite": self.has_eval_suite(),
            "has_eval_expectations": self.has_eval_expectations(),
        }
        if self.eval_runner:
            payload["eval_runner"] = self.eval_runner
        if self.eval_expectations is not None:
            payload["eval_expectations"] = self.eval_expectations.to_dict()
        return payload


def get_generic_preview_runtime_spec() -> RuntimeAdapterSpec:
    """Return the declared support contract for the generic wrapper path."""

    return RuntimeAdapterSpec(
        name="generic_wrappers",
        module="agentfirewall.generic",
        support_level=AdapterSupportLevel.EXPERIMENTAL,
        capabilities=capability_set(
            AdapterCapability.TOOL_CALL_INTERCEPTION,
            AdapterCapability.SHELL_ENFORCEMENT,
            AdapterCapability.FILE_READ_ENFORCEMENT,
            AdapterCapability.FILE_WRITE_ENFORCEMENT,
            AdapterCapability.HTTP_ENFORCEMENT,
            AdapterCapability.RUNTIME_CONTEXT_CORRELATION,
            AdapterCapability.REVIEW_SEMANTICS,
            AdapterCapability.LOG_ONLY_SEMANTICS,
        ),
        notes=(
            "Preview low-level guarded wrapper path for unsupported "
            "tool-calling runtimes. Prompt inspection is not provided."
        ),
    )


_PREVIEW_RUNTIMES: dict[str, PreviewRuntimeDefinition] = {
    "generic_wrappers": PreviewRuntimeDefinition(
        spec=get_generic_preview_runtime_spec(),
        eval_runner="agentfirewall.evals:run_generic_eval_suite",
        eval_expectations=EvalSuiteExpectations(
            total=7,
            status_counts={
                "blocked": 3,
                "completed": 3,
                "review_required": 1,
            },
            task_counts={
                "shell_access": 2,
                "data_exfiltration": 1,
                "secret_access": 1,
                "credential_injection": 1,
                "log_only_observability": 1,
            },
            named_cases={
                "safe_status_tool": "safe_status_tool",
                "review_required_tool": "shell_tool_review_without_handler",
                "approved_shell_tool": "shell_tool_approved",
                "blocked_http": "guarded_http_blocks_untrusted_host",
                "blocked_sensitive_read": "guarded_file_blocks_sensitive_read",
                "blocked_sensitive_write": "guarded_file_write_blocks_sensitive_path",
                "log_only_workflow": "log_only_shell_then_blocked_http",
            },
        ),
    ),
}


def list_preview_runtimes() -> tuple[PreviewRuntimeDefinition, ...]:
    """Return every preview runtime support path."""

    return tuple(_PREVIEW_RUNTIMES.values())


def get_preview_runtime(name: str) -> PreviewRuntimeDefinition:
    """Return one preview runtime support path."""

    try:
        return _PREVIEW_RUNTIMES[name]
    except KeyError as exc:
        raise KeyError(f"Unknown preview runtime: {name}") from exc


def export_preview_runtime_inventory() -> list[dict[str, object]]:
    """Return JSON-friendly records for preview runtime support paths."""

    return [runtime.to_dict() for runtime in list_preview_runtimes()]


def export_runtime_support_inventory() -> list[dict[str, object]]:
    """Return inventory rows for both official adapters and preview runtimes."""

    inventory: list[dict[str, object]] = []
    for adapter in list_official_adapters():
        row = adapter.to_dict()
        row["kind"] = RuntimeSupportKind.OFFICIAL_ADAPTER.value
        inventory.append(row)
    inventory.extend(export_preview_runtime_inventory())
    return inventory


def export_runtime_support_matrix() -> list[dict[str, object]]:
    """Return a combined capability matrix for support-path inventory."""

    rows: list[dict[str, object]] = []
    for adapter in list_official_adapters():
        row = capability_matrix_row(adapter.spec)
        row["kind"] = RuntimeSupportKind.OFFICIAL_ADAPTER.value
        rows.append(row)
    for runtime in list_preview_runtimes():
        row = capability_matrix_row(runtime.spec)
        row["kind"] = RuntimeSupportKind.PREVIEW_RUNTIME.value
        rows.append(row)
    return rows


def run_preview_runtime_eval_suite(
    name: str,
    *,
    path: str | Traversable | None = None,
) -> Any:
    """Run the packaged eval suite for one preview runtime."""

    return get_preview_runtime(name).run_eval_suite(path=path)


def validate_preview_runtime_eval_expectations(
    name: str,
    *,
    path: str | Traversable | None = None,
) -> EvalExpectationReport:
    """Validate packaged eval evidence for one preview runtime."""

    return get_preview_runtime(name).validate_eval_expectations(path=path)


__all__ = [
    "PreviewRuntimeDefinition",
    "RuntimeSupportKind",
    "export_preview_runtime_inventory",
    "export_runtime_support_inventory",
    "export_runtime_support_matrix",
    "get_generic_preview_runtime_spec",
    "get_preview_runtime",
    "list_preview_runtimes",
    "run_preview_runtime_eval_suite",
    "validate_preview_runtime_eval_expectations",
]
