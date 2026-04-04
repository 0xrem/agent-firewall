"""Reusable adapter-conformance validators."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from ..runtime_context import (
    SIDE_EFFECT_RUNTIME_EVENT_KINDS,
    missing_runtime_context_fields,
)
from .contracts import AdapterCapability, RuntimeAdapterSpec

REQUIRED_AUDIT_SUMMARY_KEYS: tuple[str, ...] = (
    "action_counts",
    "event_kind_counts",
    "rule_counts",
    "source_counts",
    "tool_name_counts",
)


@dataclass(frozen=True, slots=True)
class ConformanceIssue:
    """One adapter-conformance gap."""

    check: str
    message: str
    result_name: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "check": self.check,
            "message": self.message,
            "result_name": self.result_name,
        }


@dataclass(slots=True)
class ConformanceReport:
    """Collected result of validating one adapter against a summary payload."""

    adapter: str
    issues: list[ConformanceIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues

    def add(self, check: str, message: str, *, result_name: str = "") -> None:
        self.issues.append(
            ConformanceIssue(
                check=check,
                message=message,
                result_name=result_name,
            )
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "adapter": self.adapter,
            "ok": self.ok,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def _iter_result_traces(payload: Mapping[str, Any]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    results = payload.get("results")
    if not isinstance(results, Sequence):
        return []

    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for raw_result in results:
        if not isinstance(raw_result, Mapping):
            continue
        result = dict(raw_result)
        traces = result.get("audit_trace")
        if not isinstance(traces, Sequence):
            continue
        for raw_trace in traces:
            if isinstance(raw_trace, Mapping):
                pairs.append((result, dict(raw_trace)))
    return pairs


def _has_trace(
    payload: Mapping[str, Any],
    *,
    event_kind: str,
    event_operation: str | None = None,
) -> bool:
    for _, trace in _iter_result_traces(payload):
        if trace.get("event_kind") != event_kind:
            continue
        if event_operation is not None and trace.get("event_operation") != event_operation:
            continue
        return True
    return False


def _validate_declared_capability_coverage(
    payload: Mapping[str, Any],
    spec: RuntimeAdapterSpec,
    report: ConformanceReport,
) -> None:
    checks: tuple[tuple[AdapterCapability, str, str, str | None], ...] = (
        (AdapterCapability.PROMPT_INSPECTION, "prompt_coverage", "prompt", None),
        (AdapterCapability.TOOL_CALL_INTERCEPTION, "tool_call_coverage", "tool_call", None),
        (AdapterCapability.SHELL_ENFORCEMENT, "shell_coverage", "command", None),
        (AdapterCapability.FILE_READ_ENFORCEMENT, "file_read_coverage", "file_access", "read"),
        (AdapterCapability.FILE_WRITE_ENFORCEMENT, "file_write_coverage", "file_access", "write"),
        (AdapterCapability.HTTP_ENFORCEMENT, "http_coverage", "http_request", None),
        (
            AdapterCapability.RESOURCE_READ_INTERCEPTION,
            "resource_read_coverage",
            "resource_access",
            "read",
        ),
    )
    for capability, check_name, event_kind, event_operation in checks:
        if not spec.supports(capability):
            continue
        if _has_trace(payload, event_kind=event_kind, event_operation=event_operation):
            continue
        detail = f"event_kind={event_kind}"
        if event_operation is not None:
            detail += f", event_operation={event_operation}"
        report.add(
            check_name,
            f"Declared capability {capability.value!r} has no conformance evidence ({detail}).",
        )


def _validate_audit_summary_shape(
    payload: Mapping[str, Any],
    report: ConformanceReport,
) -> None:
    results = payload.get("results")
    if not isinstance(results, Sequence):
        report.add("results_payload", "Eval summary payload is missing a results sequence.")
        return

    for raw_result in results:
        if not isinstance(raw_result, Mapping):
            continue
        result = dict(raw_result)
        audit_summary = result.get("audit_summary")
        if not isinstance(audit_summary, Mapping):
            report.add(
                "audit_summary_shape",
                "Result is missing an audit_summary mapping.",
                result_name=str(result.get("name", "")),
            )
            continue
        for key in REQUIRED_AUDIT_SUMMARY_KEYS:
            if key not in audit_summary:
                report.add(
                    "audit_summary_shape",
                    f"Result audit_summary is missing required key {key!r}.",
                    result_name=str(result.get("name", "")),
                )


def _validate_runtime_context(
    payload: Mapping[str, Any],
    spec: RuntimeAdapterSpec,
    report: ConformanceReport,
) -> None:
    if not spec.supports(AdapterCapability.RUNTIME_CONTEXT_CORRELATION):
        return

    for result, trace in _iter_result_traces(payload):
        if trace.get("event_kind") not in SIDE_EFFECT_RUNTIME_EVENT_KINDS:
            continue
        missing = missing_runtime_context_fields(
            trace.get("runtime_context"),
            required_fields=spec.required_runtime_context_fields,
        )
        if not missing:
            continue
        report.add(
            "runtime_context_required_fields",
            f"Trace is missing required runtime_context fields: {missing}.",
            result_name=str(result.get("name", "")),
        )


def _validate_review_semantics(
    payload: Mapping[str, Any],
    spec: RuntimeAdapterSpec,
    report: ConformanceReport,
) -> None:
    if not spec.supports(AdapterCapability.REVIEW_SEMANTICS):
        return

    results = payload.get("results")
    if not isinstance(results, Sequence):
        return

    for raw_result in results:
        if not isinstance(raw_result, Mapping):
            continue
        status = raw_result.get("status")
        action = raw_result.get("observed_final_action")
        if status == "review_required" or action == "review":
            return

    report.add(
        "review_semantics",
        "Declared review semantics but no review-required or final review result was observed.",
    )


def _validate_log_only_semantics(
    payload: Mapping[str, Any],
    spec: RuntimeAdapterSpec,
    report: ConformanceReport,
) -> None:
    if not spec.supports(AdapterCapability.LOG_ONLY_SEMANTICS):
        return

    log_found = False
    for result, trace in _iter_result_traces(payload):
        if trace.get("action") != "log":
            continue
        log_found = True
        metadata = trace.get("decision_metadata")
        if not isinstance(metadata, Mapping) or metadata.get("original_action") in (None, ""):
            report.add(
                "log_only_semantics",
                "Log-only trace is missing decision_metadata.original_action.",
                result_name=str(result.get("name", "")),
            )
    if not log_found:
        report.add(
            "log_only_semantics",
            "Declared log-only semantics but no log action was observed in the eval summary.",
        )


def validate_eval_summary(
    payload: Mapping[str, Any],
    spec: RuntimeAdapterSpec,
) -> ConformanceReport:
    """Validate an eval-summary payload against an adapter contract."""

    report = ConformanceReport(adapter=spec.name)
    _validate_audit_summary_shape(payload, report)
    _validate_declared_capability_coverage(payload, spec, report)
    _validate_runtime_context(payload, spec, report)
    _validate_review_semantics(payload, spec, report)
    _validate_log_only_semantics(payload, spec, report)
    return report
