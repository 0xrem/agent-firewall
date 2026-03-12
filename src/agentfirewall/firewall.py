"""Firewall orchestration and public helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, TypeVar

from .approval import (
    ApprovalHandler,
    ApprovalOutcome,
    ApprovalRequest,
    normalize_approval_response,
)
from .audit import AuditEntry, AuditSink, InMemoryAuditSink
from .config import FirewallConfig
from .events import EventContext
from .exceptions import FirewallViolation, ReviewRequired
from .policy import Decision, DecisionAction, PolicyEngine, Rule
from .policy_packs import (
    PolicyPackConfig,
    build_builtin_policy_engine,
    named_policy_pack,
)
T = TypeVar("T")


@dataclass(slots=True)
class AgentFirewall:
    """Core firewall object.

    Evaluates runtime events through a policy engine, records audit entries,
    and enforces block/review/allow decisions on the agent execution path.
    """

    config: FirewallConfig = field(default_factory=FirewallConfig)
    policy: PolicyEngine = field(default_factory=PolicyEngine)
    audit_sink: AuditSink | None = field(default_factory=InMemoryAuditSink)
    approval_handler: ApprovalHandler | None = None

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
        self._record_decision(event, effective_decision)

        return effective_decision

    def enforce(self, event: EventContext) -> Decision:
        """Evaluate an event and interrupt execution when configured."""

        decision = self.evaluate(event)
        if decision.action == DecisionAction.BLOCK and self.config.raise_on_block:
            raise FirewallViolation(decision, event)
        if decision.action == DecisionAction.REVIEW and self.approval_handler is not None:
            resolved_decision = self._resolve_review(event, decision)
            if resolved_decision.action == DecisionAction.BLOCK and self.config.raise_on_block:
                raise FirewallViolation(resolved_decision, event)
            return resolved_decision
        if decision.action == DecisionAction.REVIEW and self.config.raise_on_review:
            resolved_decision = self._resolve_review(event, decision)
            if resolved_decision.action == DecisionAction.BLOCK and self.config.raise_on_block:
                raise FirewallViolation(resolved_decision, event)
            return resolved_decision

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

    def _resolve_review(self, event: EventContext, decision: Decision) -> Decision:
        if self.approval_handler is None:
            raise ReviewRequired(decision, event)

        request = ApprovalRequest(
            event=event,
            decision=decision,
            firewall_name=self.config.name,
        )
        response = normalize_approval_response(self.approval_handler(request))
        metadata = dict(decision.metadata)
        metadata.update(response.metadata)
        metadata["original_action"] = decision.action.value
        metadata["approval_outcome"] = response.outcome.value

        if response.outcome == ApprovalOutcome.APPROVE:
            resolved = Decision.allow(
                reason=response.reason or "Review approved by approval handler.",
                rule=decision.rule,
                metadata=metadata,
            )
        elif response.outcome == ApprovalOutcome.DENY:
            resolved = Decision.block(
                reason=response.reason or "Review denied by approval handler.",
                rule=decision.rule,
                metadata=metadata,
            )
        else:
            resolved = Decision.block(
                reason=response.reason or "Review timed out before approval.",
                rule=decision.rule,
                metadata=metadata,
            )

        self._record_decision(event, resolved)
        return resolved

    def _record_decision(self, event: EventContext, decision: Decision) -> None:
        if self.audit_sink is not None:
            self.audit_sink.record(AuditEntry(event=event, decision=decision))


def protect(
    agent: T,
    *,
    config: FirewallConfig | None = None,
    rules: Iterable[Rule] = (),
    audit_sink: AuditSink | None = None,
    approval_handler: ApprovalHandler | None = None,
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
        approval_handler=approval_handler,
    )
    return firewall.wrap_agent(agent)


def create_firewall(
    *,
    config: FirewallConfig | None = None,
    policy_pack: str | PolicyPackConfig = "default",
    audit_sink: AuditSink | None = None,
    approval_handler: ApprovalHandler | None = None,
) -> AgentFirewall:
    """Create a firewall using the supported built-in policy-pack path."""

    resolved_config = config or FirewallConfig()
    resolved_policy_pack = (
        named_policy_pack(policy_pack)
        if isinstance(policy_pack, str)
        else policy_pack
    )
    return AgentFirewall(
        config=resolved_config,
        policy=build_builtin_policy_engine(
            resolved_policy_pack,
            default_action=resolved_config.default_action,
        ),
        audit_sink=(
            audit_sink
            if audit_sink is not None
            else InMemoryAuditSink()
        ),
        approval_handler=approval_handler,
    )
