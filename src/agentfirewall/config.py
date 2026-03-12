"""Configuration models for AgentFirewall."""

from __future__ import annotations

from dataclasses import dataclass

from .policy import DecisionAction


@dataclass(slots=True)
class FirewallConfig:
    """Base runtime configuration for the firewall."""

    name: str = "default"
    default_action: DecisionAction = DecisionAction.ALLOW
    audit_enabled: bool = True
    log_only: bool = False
    raise_on_block: bool = True
    raise_on_review: bool = True
