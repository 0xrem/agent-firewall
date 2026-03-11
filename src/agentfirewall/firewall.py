"""Firewall orchestration and public helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, TypeVar

from .config import FirewallConfig
from .models import Decision, DecisionAction, EventContext

Rule = Callable[[EventContext], Decision | None]
T = TypeVar("T")


@dataclass(slots=True)
class AgentFirewall:
    """Core firewall object.

    This is an intentionally small skeleton. It keeps the initial package
    structure stable while the real enforcement model is implemented.
    """

    config: FirewallConfig = field(default_factory=FirewallConfig)
    rules: list[Rule] = field(default_factory=list)

    def evaluate(self, event: EventContext) -> Decision:
        """Return the first non-allow decision produced by the configured rules."""

        for rule in self.rules:
            decision = rule(event)
            if decision is None:
                continue
            if decision.action != DecisionAction.ALLOW:
                return decision

        return Decision(
            action=self.config.default_action,
            reason="No rule matched.",
        )

    def protect(self, agent: T) -> T:
        """Attach placeholder firewall state without altering agent behavior."""

        try:
            setattr(agent, "__agentfirewall__", self)
        except AttributeError:
            pass

        return agent


def protect(
    agent: T,
    *,
    config: FirewallConfig | None = None,
    rules: Iterable[Rule] = (),
) -> T:
    """Attach a firewall instance to an agent and return the original object."""

    firewall = AgentFirewall(
        config=config or FirewallConfig(),
        rules=list(rules),
    )
    return firewall.protect(agent)
