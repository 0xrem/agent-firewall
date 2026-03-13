"""Internal adapter-contract models for runtime integrations."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..runtime_context import REQUIRED_RUNTIME_CONTEXT_FIELDS


class AdapterSupportLevel(str, Enum):
    """Support levels for runtime adapters."""

    EXPERIMENTAL = "experimental"
    SUPPORTED = "supported"
    REFERENCE_ONLY = "reference_only"


class AdapterCapability(str, Enum):
    """Capabilities an adapter may declare."""

    PROMPT_INSPECTION = "prompt_inspection"
    TOOL_CALL_INTERCEPTION = "tool_call_interception"
    SHELL_ENFORCEMENT = "shell_enforcement"
    FILE_READ_ENFORCEMENT = "file_read_enforcement"
    FILE_WRITE_ENFORCEMENT = "file_write_enforcement"
    HTTP_ENFORCEMENT = "http_enforcement"
    RUNTIME_CONTEXT_CORRELATION = "runtime_context_correlation"
    REVIEW_SEMANTICS = "review_semantics"
    LOG_ONLY_SEMANTICS = "log_only_semantics"


OFFICIAL_ADAPTER_CAPABILITY_ORDER: tuple[AdapterCapability, ...] = (
    AdapterCapability.PROMPT_INSPECTION,
    AdapterCapability.TOOL_CALL_INTERCEPTION,
    AdapterCapability.SHELL_ENFORCEMENT,
    AdapterCapability.FILE_READ_ENFORCEMENT,
    AdapterCapability.FILE_WRITE_ENFORCEMENT,
    AdapterCapability.HTTP_ENFORCEMENT,
    AdapterCapability.RUNTIME_CONTEXT_CORRELATION,
    AdapterCapability.REVIEW_SEMANTICS,
    AdapterCapability.LOG_ONLY_SEMANTICS,
)


def capability_set(*capabilities: AdapterCapability) -> frozenset[AdapterCapability]:
    """Return a frozen capability set for adapter declarations."""

    return frozenset(capabilities)


@dataclass(frozen=True, slots=True)
class RuntimeAdapterSpec:
    """Declared contract for a runtime adapter."""

    name: str
    module: str
    support_level: AdapterSupportLevel = AdapterSupportLevel.EXPERIMENTAL
    capabilities: frozenset[AdapterCapability] = field(default_factory=frozenset)
    required_runtime_context_fields: tuple[str, ...] = REQUIRED_RUNTIME_CONTEXT_FIELDS
    notes: str = ""

    def supports(self, capability: AdapterCapability | str) -> bool:
        """Return whether the adapter declares support for a capability."""

        resolved = (
            capability
            if isinstance(capability, AdapterCapability)
            else AdapterCapability(capability)
        )
        return resolved in self.capabilities

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-friendly representation of the adapter contract."""

        return {
            "name": self.name,
            "module": self.module,
            "support_level": self.support_level.value,
            "capabilities": sorted(capability.value for capability in self.capabilities),
            "required_runtime_context_fields": list(self.required_runtime_context_fields),
            "notes": self.notes,
        }


def missing_declared_capabilities(
    spec: RuntimeAdapterSpec,
    required_capabilities: Mapping[str, AdapterCapability | str],
) -> dict[str, str]:
    """Return missing declared capabilities keyed by check name."""

    missing: dict[str, str] = {}
    for check_name, capability in required_capabilities.items():
        resolved = (
            capability
            if isinstance(capability, AdapterCapability)
            else AdapterCapability(capability)
        )
        if not spec.supports(resolved):
            missing[check_name] = resolved.value
    return missing


def capability_support_map(
    spec: RuntimeAdapterSpec,
    *,
    capability_order: tuple[AdapterCapability, ...] = OFFICIAL_ADAPTER_CAPABILITY_ORDER,
) -> dict[str, str]:
    """Return `supported`/`not_supported` values for the standard capability matrix."""

    return {
        capability.value: (
            "supported"
            if spec.supports(capability)
            else "not_supported"
        )
        for capability in capability_order
    }


def capability_matrix_row(
    spec: RuntimeAdapterSpec,
    *,
    capability_order: tuple[AdapterCapability, ...] = OFFICIAL_ADAPTER_CAPABILITY_ORDER,
) -> dict[str, object]:
    """Return a machine-readable capability-matrix row for one adapter."""

    row: dict[str, object] = {
        "name": spec.name,
        "module": spec.module,
        "support_level": spec.support_level.value,
        "notes": spec.notes,
    }
    row.update(capability_support_map(spec, capability_order=capability_order))
    return row
