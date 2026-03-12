"""Policy and decision models used by AgentFirewall."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .events import EventContext
from .serialization import to_jsonable


class DecisionAction(str, Enum):
    """Supported outcomes for a policy decision."""

    ALLOW = "allow"
    BLOCK = "block"
    REVIEW = "review"
    LOG = "log"


@dataclass(slots=True)
class Decision:
    """Result returned after evaluating an event."""

    action: DecisionAction | str
    reason: str = ""
    rule: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.action, str):
            self.action = DecisionAction(self.action)

    @property
    def is_blocking(self) -> bool:
        return self.action == DecisionAction.BLOCK

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action.value,
            "reason": self.reason,
            "rule": self.rule,
            "metadata": to_jsonable(self.metadata),
        }

    @classmethod
    def allow(
        cls,
        *,
        reason: str = "",
        rule: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "Decision":
        return cls(
            action=DecisionAction.ALLOW,
            reason=reason,
            rule=rule,
            metadata=metadata or {},
        )

    @classmethod
    def block(
        cls,
        *,
        reason: str,
        rule: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "Decision":
        return cls(
            action=DecisionAction.BLOCK,
            reason=reason,
            rule=rule,
            metadata=metadata or {},
        )

    @classmethod
    def review(
        cls,
        *,
        reason: str,
        rule: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "Decision":
        return cls(
            action=DecisionAction.REVIEW,
            reason=reason,
            rule=rule,
            metadata=metadata or {},
        )

    @classmethod
    def log(
        cls,
        *,
        reason: str,
        rule: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "Decision":
        return cls(
            action=DecisionAction.LOG,
            reason=reason,
            rule=rule,
            metadata=metadata or {},
        )


Rule = Callable[[EventContext], Decision | None]


@dataclass(slots=True)
class PolicyEngine:
    """Ordered rule engine used by the runtime firewall."""

    rules: list[Rule] = field(default_factory=list)
    default_action: DecisionAction = DecisionAction.ALLOW

    def evaluate(self, event: EventContext) -> Decision:
        for rule in self.rules:
            decision = rule(event)
            if decision is None:
                continue

            if decision.rule is None:
                decision.rule = getattr(
                    rule,
                    "name",
                    getattr(rule, "__name__", rule.__class__.__name__),
                )
            return decision

        return Decision(
            action=self.default_action,
            reason="No rule matched.",
            rule="default",
        )

    def add_rule(self, rule: Rule) -> None:
        self.rules.append(rule)
