"""Registry helpers for official AgentFirewall runtime adapters."""

from __future__ import annotations

from .contracts import RuntimeAdapterSpec, capability_matrix_row
from .langgraph import get_langgraph_adapter_spec

_OFFICIAL_ADAPTER_SPECS: dict[str, RuntimeAdapterSpec] = {
    "langgraph": get_langgraph_adapter_spec(),
}


def list_official_adapter_specs() -> tuple[RuntimeAdapterSpec, ...]:
    """Return the declared contract for every official runtime adapter."""

    return tuple(_OFFICIAL_ADAPTER_SPECS.values())


def get_official_adapter_spec(name: str) -> RuntimeAdapterSpec:
    """Return the declared contract for one official runtime adapter."""

    try:
        return _OFFICIAL_ADAPTER_SPECS[name]
    except KeyError as exc:
        raise KeyError(f"Unknown official adapter: {name}") from exc


def export_official_adapter_matrix() -> list[dict[str, object]]:
    """Return the current official adapter capability matrix."""

    return [
        capability_matrix_row(spec)
        for spec in list_official_adapter_specs()
    ]
