"""Firewall orchestration and public helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, TypeVar

from .audit import AuditEntry, AuditSink, InMemoryAuditSink
from .config import FirewallConfig
from .events import EventContext
from .exceptions import FirewallViolation
from .policy import Decision, DecisionAction, PolicyEngine, Rule
T = TypeVar("T")


@dataclass(slots=True)
class AgentFirewall:
    """Core firewall object.

    This is an intentionally small skeleton. It keeps the initial package
    structure stable while the real enforcement model is implemented.
    """

    config: FirewallConfig = field(default_factory=FirewallConfig)
    policy: PolicyEngine = field(default_factory=PolicyEngine)
    audit_sink: AuditSink | None = field(default_factory=InMemoryAuditSink)

    def __post_init__(self) -> None:
        self.policy.default_action = self.config.default_action
        if not self.config.audit_enabled:
            self.audit_sink = None

    @property
    def rules(self) -> list[Rule]:
        return self.policy.rules

    def add_rule(self, rule: Rule) -> None:
        self.policy.add_rule(rule)

    def evaluate(self, event: EventContext) -> Decision:
        """Evaluate an event and record the resulting decision."""

        decision = self.policy.evaluate(event)
        effective_decision = self._apply_runtime_mode(decision)

        if self.audit_sink is not None:
            self.audit_sink.record(
                AuditEntry(event=event, decision=effective_decision)
            )

        return effective_decision

    def enforce(self, event: EventContext) -> Decision:
        """Evaluate an event and raise on blocked actions when configured."""

        decision = self.evaluate(event)
        if decision.action == DecisionAction.BLOCK and self.config.raise_on_block:
            raise FirewallViolation(decision, event)

        return decision

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

    def _apply_runtime_mode(self, decision: Decision) -> Decision:
        if not self.config.log_only:
            return decision

        if decision.action in {DecisionAction.BLOCK, DecisionAction.REVIEW}:
            metadata = dict(decision.metadata)
            metadata["original_action"] = decision.action.value
            return Decision.log(
                reason=decision.reason or "Rule matched in log-only mode.",
                rule=decision.rule,
                metadata=metadata,
            )

        return decision


def protect(
    agent: T,
    *,
    config: FirewallConfig | None = None,
    rules: Iterable[Rule] = (),
    audit_sink: AuditSink | None = None,
) -> T:
    """Compatibility helper that creates a firewall and wraps an agent."""

    resolved_config = config or FirewallConfig()
    firewall = AgentFirewall(
        config=resolved_config,
        policy=PolicyEngine(
            rules=list(rules),
            default_action=resolved_config.default_action,
        ),
        audit_sink=audit_sink if audit_sink is not None else InMemoryAuditSink(),
    )
    return firewall.wrap_agent(agent)
