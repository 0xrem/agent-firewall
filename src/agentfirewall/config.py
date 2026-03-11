"""Configuration models for AgentFirewall."""

from __future__ import annotations

from dataclasses import dataclass

from .models import DecisionAction


@dataclass(slots=True)
class FirewallConfig:
    """Base runtime configuration for the firewall."""

    name: str = "default"
    default_action: DecisionAction = DecisionAction.ALLOW
    audit_enabled: bool = True
