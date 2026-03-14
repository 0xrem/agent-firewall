"""Support-path inventory and evidence export for runtime adapters."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from enum import Enum
import json
from importlib import import_module
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import IO
from typing import Any
from datetime import datetime, timezone

from .evals.contracts import (
    EvalExpectationReport,
    EvalSuiteExpectations,
    find_eval_result,
    validate_eval_summary_against_expectations,
)
from .integrations.contracts import (
    AdapterCapability,
    AdapterSupportLevel,
    RuntimeAdapterSpec,
    capability_matrix_row,
    capability_set,
)
from .integrations.conformance import ConformanceReport, validate_eval_summary
from .integrations.openai_agents import get_openai_agents_adapter_spec
from .integrations.registry import (
    export_official_adapter_inventory,
    get_official_adapter,
    list_official_adapters,
)


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

    def validate_conformance(
        self,
        *,
        path: str | Traversable | None = None,
    ) -> ConformanceReport:
        """Validate packaged eval evidence against the preview runtime contract."""

        summary = self.run_eval_suite(path=path)
        return validate_eval_summary(summary.to_dict(), self.spec)

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


def get_openai_agents_preview_runtime_spec() -> RuntimeAdapterSpec:
    """Return the preview support contract for the OpenAI Agents SDK path."""

    adapter_spec = get_openai_agents_adapter_spec()
    return RuntimeAdapterSpec(
        name=adapter_spec.name,
        module=adapter_spec.module,
        support_level=adapter_spec.support_level,
        capabilities=capability_set(
            AdapterCapability.PROMPT_INSPECTION,
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
            "Preview OpenAI Agents SDK support path. Prompt and function_tool "
            "interception come from the adapter hooks, while shell, file, and "
            "HTTP enforcement are available through the official helper tool "
            "builders and runtime bundle. Hosted tools, MCP servers, and "
            "handoffs remain out of scope."
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
    "openai_agents": PreviewRuntimeDefinition(
        spec=get_openai_agents_preview_runtime_spec(),
        eval_runner="agentfirewall.evals:run_openai_agents_eval_suite",
        eval_expectations=EvalSuiteExpectations(
            total=9,
            status_counts={
                "completed": 4,
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


def validate_preview_runtime_conformance(
    name: str,
    *,
    path: str | Traversable | None = None,
) -> ConformanceReport:
    """Validate packaged eval evidence against one preview runtime contract."""

    return get_preview_runtime(name).validate_conformance(path=path)


def _support_path_evidence_payload(
    *,
    name: str,
    kind: RuntimeSupportKind,
    summary_digest: dict[str, object] | None = None,
    conformance: ConformanceReport | None = None,
    eval_expectations: EvalExpectationReport | None = None,
    error: Exception | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": name,
        "kind": kind.value,
        "evaluated": error is None and summary_digest is not None,
        "ok": None,
    }
    if summary_digest is not None:
        payload["summary"] = summary_digest
    if conformance is not None:
        payload["conformance"] = conformance.to_dict()
    if eval_expectations is not None:
        payload["eval_expectations"] = eval_expectations.to_dict()
    if error is not None:
        payload["error"] = f"{type(error).__name__}: {error}"
        return payload

    if conformance is None and eval_expectations is None:
        return payload

    payload["ok"] = (
        (conformance is None or conformance.ok)
        and (eval_expectations is None or eval_expectations.ok)
    )
    return payload


def _summary_digest(
    summary_payload: dict[str, Any],
    *,
    expectations: EvalSuiteExpectations | None = None,
) -> dict[str, object]:
    digest: dict[str, object] = {}
    for key in (
        "total",
        "passed",
        "failed",
        "unexpected_allows",
        "unexpected_blocks",
        "unexpected_reviews",
        "status_counts",
        "task_counts",
        "final_action_counts",
    ):
        value = summary_payload.get(key)
        if value is not None:
            digest[key] = value

    if expectations is not None and expectations.named_cases:
        named_cases: dict[str, object] = {}
        for alias, case_name in expectations.named_cases.items():
            result = find_eval_result(summary_payload, case_name)
            if result is None:
                named_cases[alias] = {
                    "name": case_name,
                    "missing": True,
                }
                continue
            named_cases[alias] = {
                "name": case_name,
                "status": result.get("status"),
                "matched": result.get("matched"),
                "observed_final_action": result.get("observed_final_action"),
            }
        digest["named_cases"] = named_cases
    return digest


def collect_official_adapter_evidence(
    name: str,
    *,
    path: str | Traversable | None = None,
) -> dict[str, object]:
    """Collect eval evidence for one official runtime adapter."""

    adapter = get_official_adapter(name)
    try:
        summary = adapter.run_eval_suite(path=path)
        payload = summary.to_dict()
        conformance = validate_eval_summary(payload, adapter.spec)
        eval_expectations = None
        if adapter.eval_expectations is not None:
            eval_expectations = validate_eval_summary_against_expectations(
                payload,
                adapter.eval_expectations,
            )
        return _support_path_evidence_payload(
            name=name,
            kind=RuntimeSupportKind.OFFICIAL_ADAPTER,
            summary_digest=_summary_digest(
                payload,
                expectations=adapter.eval_expectations,
            ),
            conformance=conformance,
            eval_expectations=eval_expectations,
        )
    except Exception as exc:  # pragma: no cover - exercised in dependency-gated envs
        return _support_path_evidence_payload(
            name=name,
            kind=RuntimeSupportKind.OFFICIAL_ADAPTER,
            error=exc,
        )


def collect_preview_runtime_evidence(
    name: str,
    *,
    path: str | Traversable | None = None,
) -> dict[str, object]:
    """Collect eval evidence for one preview runtime support path."""

    runtime = get_preview_runtime(name)
    try:
        summary = runtime.run_eval_suite(path=path)
        payload = summary.to_dict()
        conformance = validate_eval_summary(payload, runtime.spec)
        eval_expectations = None
        if runtime.eval_expectations is not None:
            eval_expectations = validate_eval_summary_against_expectations(
                payload,
                runtime.eval_expectations,
            )
        return _support_path_evidence_payload(
            name=name,
            kind=RuntimeSupportKind.PREVIEW_RUNTIME,
            summary_digest=_summary_digest(
                payload,
                expectations=runtime.eval_expectations,
            ),
            conformance=conformance,
            eval_expectations=eval_expectations,
        )
    except Exception as exc:  # pragma: no cover - exercised in dependency-gated envs
        return _support_path_evidence_payload(
            name=name,
            kind=RuntimeSupportKind.PREVIEW_RUNTIME,
            error=exc,
        )


def export_runtime_support_manifest(
    *,
    include_evidence: bool = False,
) -> dict[str, object]:
    """Export a JSON-friendly runtime support manifest for docs and websites."""

    manifest: dict[str, object] = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "official_adapters": export_official_adapter_inventory(),
        "preview_runtimes": export_preview_runtime_inventory(),
        "inventory": export_runtime_support_inventory(),
        "matrix": export_runtime_support_matrix(),
    }
    if include_evidence:
        manifest["evidence"] = {
            "official_adapters": [
                collect_official_adapter_evidence(adapter.name)
                for adapter in list_official_adapters()
            ],
            "preview_runtimes": [
                collect_preview_runtime_evidence(runtime.name)
                for runtime in list_preview_runtimes()
            ],
        }
    return manifest


def write_runtime_support_manifest(
    path: str | Path,
    *,
    include_evidence: bool = False,
) -> Path:
    """Write the runtime support manifest to one JSON file."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = export_runtime_support_manifest(include_evidence=include_evidence)
    target.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export AgentFirewall runtime support inventory and evidence as JSON."
        )
    )
    parser.add_argument(
        "--include-evidence",
        action="store_true",
        help="Run packaged eval suites and include conformance/evidence in the output.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write the manifest to this JSON file instead of stdout.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, *, stdout: IO[str] | None = None) -> int:
    """CLI entrypoint for exporting runtime support manifests."""

    args = _parse_args(argv)
    payload = export_runtime_support_manifest(include_evidence=args.include_evidence)
    output = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        write_runtime_support_manifest(
            args.output,
            include_evidence=args.include_evidence,
        )
        return 0
    stream = stdout if stdout is not None else None
    if stream is None:
        print(output, end="")
    else:
        stream.write(output)
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised via CLI
    raise SystemExit(main())


__all__ = [
    "PreviewRuntimeDefinition",
    "RuntimeSupportKind",
    "collect_official_adapter_evidence",
    "collect_preview_runtime_evidence",
    "export_preview_runtime_inventory",
    "export_runtime_support_manifest",
    "export_runtime_support_inventory",
    "export_runtime_support_matrix",
    "get_generic_preview_runtime_spec",
    "get_openai_agents_preview_runtime_spec",
    "get_preview_runtime",
    "list_preview_runtimes",
    "run_preview_runtime_eval_suite",
    "validate_preview_runtime_conformance",
    "validate_preview_runtime_eval_expectations",
    "write_runtime_support_manifest",
]
