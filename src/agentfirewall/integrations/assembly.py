"""Shared assembly helpers for runtime adapters."""

from __future__ import annotations

from ..approval import ApprovalHandler
from ..audit import AuditSink
from ..config import FirewallConfig
from ..firewall import AgentFirewall, create_firewall
from ..policy_packs import PolicyPackConfig


def resolve_adapter_firewall(
    *,
    firewall: AgentFirewall | None = None,
    config: FirewallConfig | None = None,
    policy_pack: str | PolicyPackConfig = "default",
    audit_sink: AuditSink | None = None,
    approval_handler: ApprovalHandler | None = None,
) -> AgentFirewall:
    """Resolve an adapter firewall from either an existing object or high-level options."""

    if firewall is not None and (
        config is not None
        or audit_sink is not None
        or approval_handler is not None
        or policy_pack != "default"
    ):
        raise TypeError(
            "Pass either `firewall` or high-level firewall parameters, not both."
        )

    if firewall is not None:
        return firewall

    return create_firewall(
        config=config,
        policy_pack=policy_pack,
        audit_sink=audit_sink,
        approval_handler=approval_handler,
    )
