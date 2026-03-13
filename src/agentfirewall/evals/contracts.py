"""Shared eval-summary helpers and release-gate expectations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class EvalSuiteExpectations:
    """Expected shape for one official adapter's packaged eval suite."""

    total: int
    failed: int = 0
    unexpected_allows: int = 0
    unexpected_blocks: int = 0
    unexpected_reviews: int = 0
    status_counts: dict[str, int] = field(default_factory=dict)
    task_counts: dict[str, int] = field(default_factory=dict)
    named_cases: dict[str, str] = field(default_factory=dict)

    def case_name(self, alias: str) -> str:
        """Return the concrete eval-case name for a scenario alias."""

        try:
            return self.named_cases[alias]
        except KeyError as exc:
            raise KeyError(f"Unknown eval-case alias: {alias}") from exc

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-friendly representation of the expectations."""

        return {
            "total": self.total,
            "failed": self.failed,
            "unexpected_allows": self.unexpected_allows,
            "unexpected_blocks": self.unexpected_blocks,
            "unexpected_reviews": self.unexpected_reviews,
            "status_counts": dict(self.status_counts),
            "task_counts": dict(self.task_counts),
            "named_cases": dict(self.named_cases),
        }


@dataclass(frozen=True, slots=True)
class EvalExpectationIssue:
    """One mismatch between a summary payload and the expected release gate."""

    check: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "check": self.check,
            "message": self.message,
        }


@dataclass(slots=True)
class EvalExpectationReport:
    """Collected result of validating one eval summary against expectations."""

    issues: list[EvalExpectationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues

    def add(self, check: str, message: str) -> None:
        self.issues.append(EvalExpectationIssue(check=check, message=message))

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def _results(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw_results = payload.get("results")
    if not isinstance(raw_results, Sequence):
        return []

    results: list[dict[str, Any]] = []
    for item in raw_results:
        if isinstance(item, Mapping):
            results.append(dict(item))
    return results


def find_eval_result(
    payload: Mapping[str, Any],
    case_name: str,
) -> dict[str, Any] | None:
    """Return one eval result by concrete case name."""

    for result in _results(payload):
        if result.get("name") == case_name:
            return result
    return None


def require_eval_result(
    payload: Mapping[str, Any],
    case_name: str,
) -> dict[str, Any]:
    """Return one eval result by concrete case name or raise."""

    result = find_eval_result(payload, case_name)
    if result is None:
        raise KeyError(f"Missing eval result: {case_name}")
    return result


def find_named_eval_result(
    payload: Mapping[str, Any],
    expectations: EvalSuiteExpectations,
    alias: str,
) -> dict[str, Any] | None:
    """Return one eval result by scenario alias."""

    return find_eval_result(payload, expectations.case_name(alias))


def require_named_eval_result(
    payload: Mapping[str, Any],
    expectations: EvalSuiteExpectations,
    alias: str,
) -> dict[str, Any]:
    """Return one eval result by scenario alias or raise."""

    return require_eval_result(payload, expectations.case_name(alias))


def find_eval_trace(
    result: Mapping[str, Any],
    *,
    event_kind: str,
    event_operation: str | None = None,
) -> dict[str, Any] | None:
    """Return one audit-trace item for a given event kind and optional operation."""

    traces = result.get("audit_trace")
    if not isinstance(traces, Sequence):
        return None

    for item in traces:
        if not isinstance(item, Mapping):
            continue
        trace = dict(item)
        if trace.get("event_kind") != event_kind:
            continue
        if event_operation is not None and trace.get("event_operation") != event_operation:
            continue
        return trace
    return None


def require_eval_trace(
    result: Mapping[str, Any],
    *,
    event_kind: str,
    event_operation: str | None = None,
) -> dict[str, Any]:
    """Return one audit-trace item or raise when the requested trace is missing."""

    trace = find_eval_trace(
        result,
        event_kind=event_kind,
        event_operation=event_operation,
    )
    if trace is None:
        detail = f"event_kind={event_kind}"
        if event_operation is not None:
            detail += f", event_operation={event_operation}"
        raise KeyError(f"Missing eval trace: {detail}")
    return trace


def validate_eval_summary_against_expectations(
    payload: Mapping[str, Any],
    expectations: EvalSuiteExpectations,
) -> EvalExpectationReport:
    """Validate one eval summary against a packaged release-gate expectation."""

    report = EvalExpectationReport()

    for key in (
        "total",
        "failed",
        "unexpected_allows",
        "unexpected_blocks",
        "unexpected_reviews",
    ):
        observed = payload.get(key)
        expected = getattr(expectations, key)
        if observed != expected:
            report.add(
                key,
                f"Expected {key}={expected!r}, observed {observed!r}.",
            )

    observed_status_counts = payload.get("status_counts")
    if not isinstance(observed_status_counts, Mapping):
        report.add("status_counts", "Eval summary is missing a status_counts mapping.")
    else:
        for key, expected in expectations.status_counts.items():
            observed = observed_status_counts.get(key)
            if observed != expected:
                report.add(
                    "status_counts",
                    f"Expected status_counts[{key!r}]={expected!r}, observed {observed!r}.",
                )

    observed_task_counts = payload.get("task_counts")
    if not isinstance(observed_task_counts, Mapping):
        report.add("task_counts", "Eval summary is missing a task_counts mapping.")
    else:
        for key, expected in expectations.task_counts.items():
            observed = observed_task_counts.get(key)
            if observed != expected:
                report.add(
                    "task_counts",
                    f"Expected task_counts[{key!r}]={expected!r}, observed {observed!r}.",
                )

    for alias, case_name in expectations.named_cases.items():
        if find_eval_result(payload, case_name) is not None:
            continue
        report.add(
            "named_cases",
            f"Expected named case {alias!r} -> {case_name!r} was missing from the eval summary.",
        )

    return report
