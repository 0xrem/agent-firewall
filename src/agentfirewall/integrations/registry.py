"""Registry helpers for official AgentFirewall runtime adapters."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from importlib.resources.abc import Traversable
from typing import Any

from .conformance import ConformanceReport, validate_eval_summary
from .contracts import RuntimeAdapterSpec, capability_matrix_row
from .langgraph import get_langgraph_adapter_spec


@dataclass(frozen=True, slots=True)
class OfficialAdapterDefinition:
    """Registry record for one official runtime adapter."""

    spec: RuntimeAdapterSpec
    eval_runner: str = ""

    @property
    def name(self) -> str:
        return self.spec.name

    def has_eval_suite(self) -> bool:
        return bool(self.eval_runner)

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

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-friendly registry record for one official adapter."""

        payload = {
            "name": self.name,
            "spec": self.spec.to_dict(),
            "has_eval_suite": self.has_eval_suite(),
        }
        if self.eval_runner:
            payload["eval_runner"] = self.eval_runner
        return payload


_OFFICIAL_ADAPTERS: dict[str, OfficialAdapterDefinition] = {
    "langgraph": OfficialAdapterDefinition(
        spec=get_langgraph_adapter_spec(),
        eval_runner="agentfirewall.evals:run_langgraph_eval_suite",
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
