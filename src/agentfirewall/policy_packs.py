"""Config-driven policy pack builders for AgentFirewall."""

from __future__ import annotations

from dataclasses import dataclass, replace

from .policy import DecisionAction, PolicyEngine, Rule
from .rules.builtin import (
    BlockDangerousCommandRule,
    BlockDisallowedToolRule,
    BlockSensitiveFileAccessRule,
    BlockUntrustedHostRule,
    ReviewPromptInjectionRule,
    ReviewSensitiveToolCallRule,
)


@dataclass(slots=True)
class PolicyPackConfig:
    """Configuration for a built-in rule pack."""

    name: str = "default"
    suspicious_prompt_phrases: tuple[str, ...] = (
        "ignore previous instructions",
        "disregard all prior instructions",
        "reveal the system prompt",
    )
    dangerous_command_patterns: tuple[str, ...] = (
        "rm -rf /",
        "rm -rf ~",
        "| sh",
        "| bash",
        "mkfs",
        "dd if=",
    )
    sensitive_path_tokens: tuple[str, ...] = (
        ".env",
        ".aws/credentials",
        "id_rsa",
        "id_ed25519",
    )
    trusted_hosts: tuple[str, ...] = (
        "localhost",
        "127.0.0.1",
        "api.openai.com",
    )
    reviewed_tool_names: tuple[str, ...] = (
        "shell",
        "terminal",
        "execute_command",
        "run_python",
    )
    blocked_tool_names: tuple[str, ...] = ()


def default_policy_pack() -> PolicyPackConfig:
    """Return the default preview policy pack."""

    return PolicyPackConfig()


def strict_policy_pack() -> PolicyPackConfig:
    """Return a stricter built-in pack for local hardening trials."""

    return PolicyPackConfig(
        name="strict",
        blocked_tool_names=(
            "shell",
            "terminal",
            "execute_command",
            "run_python",
        ),
        reviewed_tool_names=(
            "read_file",
            "write_file",
            "http_request",
        ),
        trusted_hosts=(
            "localhost",
            "127.0.0.1",
            "api.openai.com",
        ),
    )


def named_policy_pack(name: str = "default", **overrides: object) -> PolicyPackConfig:
    """Return a named built-in pack with optional field overrides."""

    if name == "default":
        base = default_policy_pack()
    elif name == "strict":
        base = strict_policy_pack()
    else:
        raise ValueError(f"Unknown policy pack: {name}")

    valid_overrides = {
        key: value
        for key, value in overrides.items()
        if value is not None
    }
    return replace(base, **valid_overrides)


def builtin_policy_rules(config: PolicyPackConfig) -> list[Rule]:
    """Build the built-in rule list from explicit config."""

    return [
        ReviewPromptInjectionRule(
            suspicious_phrases=config.suspicious_prompt_phrases,
        ),
        ReviewSensitiveToolCallRule(
            reviewed_tool_names=config.reviewed_tool_names,
        ),
        BlockDisallowedToolRule(
            blocked_tool_names=config.blocked_tool_names,
        ),
        BlockDangerousCommandRule(
            blocked_patterns=config.dangerous_command_patterns,
        ),
        BlockSensitiveFileAccessRule(
            sensitive_path_tokens=config.sensitive_path_tokens,
        ),
        BlockUntrustedHostRule(
            trusted_hosts=config.trusted_hosts,
        ),
    ]


def build_builtin_policy_engine(
    config: PolicyPackConfig,
    *,
    default_action: DecisionAction = DecisionAction.ALLOW,
) -> PolicyEngine:
    """Create a policy engine from a named built-in pack."""

    return PolicyEngine(
        rules=list(builtin_policy_rules(config)),
        default_action=default_action,
    )
