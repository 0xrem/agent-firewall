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

    def wrap_agent(self, agent: T) -> T:
        """Attach firewall state to an agent runtime."""

        try:
            setattr(agent, "__agentfirewall__", self)
        except AttributeError:
            pass

        return agent

    def protect(self, agent: T) -> T:
        """Backward-compatible shorthand for wrap_agent()."""

        return self.wrap_agent(agent)


def protect(
    agent: T,
    *,
    config: FirewallConfig | None = None,
    rules: Iterable[Rule] = (),
) -> T:
    """Compatibility helper that creates a firewall and wraps an agent."""

    firewall = AgentFirewall(
        config=config or FirewallConfig(),
        rules=list(rules),
    )
    return firewall.wrap_agent(agent)
