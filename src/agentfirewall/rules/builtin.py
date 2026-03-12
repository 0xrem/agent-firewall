"""First-party rules for the initial AgentFirewall milestone."""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse

from ..events import EventContext, EventKind
from ..policy import Decision, Rule


def _matches_host(hostname: str, allowed_host: str) -> bool:
    if hostname == allowed_host:
        return True

    return hostname.endswith(f".{allowed_host}")


@dataclass(slots=True)
class ReviewPromptInjectionRule:
    """Review prompts that carry obvious override instructions."""

    name: str = "review_prompt_injection"
    suspicious_phrases: tuple[str, ...] = (
        "ignore previous instructions",
        "disregard all prior instructions",
        "reveal the system prompt",
    )

    def __call__(self, event: EventContext) -> Decision | None:
        if event.kind != EventKind.PROMPT:
            return None

        text = str(event.payload.get("text", "")).lower()
        for phrase in self.suspicious_phrases:
            if phrase in text:
                return Decision.review(
                    reason="Prompt contains an instruction-override pattern.",
                    metadata={"matched_phrase": phrase},
                )

        return None


@dataclass(slots=True)
class BlockDangerousCommandRule:
    """Block shell commands with clearly destructive intent."""

    name: str = "block_dangerous_command"
    blocked_patterns: tuple[str, ...] = (
        "rm -rf /",
        "rm -rf ~",
        "| sh",
        "| bash",
        "mkfs",
        "dd if=",
    )

    def __call__(self, event: EventContext) -> Decision | None:
        if event.kind != EventKind.COMMAND:
            return None

        command_text = str(event.payload.get("command_text", "")).lower()
        for pattern in self.blocked_patterns:
            if pattern in command_text:
                return Decision.block(
                    reason="Command matches a dangerous execution pattern.",
                    metadata={"matched_pattern": pattern},
                )

        return None


@dataclass(slots=True)
class BlockSensitiveFileAccessRule:
    """Block access to obviously sensitive local files."""

    name: str = "block_sensitive_file_access"
    sensitive_path_tokens: tuple[str, ...] = (
        ".env",
        ".aws/credentials",
        "id_rsa",
        "id_ed25519",
    )

    def __call__(self, event: EventContext) -> Decision | None:
        if event.kind != EventKind.FILE_ACCESS:
            return None

        path = str(event.payload.get("path", "")).lower()
        for token in self.sensitive_path_tokens:
            if token in path:
                return Decision.block(
                    reason="File path matches a sensitive-path rule.",
                    metadata={"matched_path_token": token},
                )

        return None


@dataclass(slots=True)
class BlockUntrustedHostRule:
    """Block outbound requests that do not match a trust list."""

    trusted_hosts: tuple[str, ...] = field(default_factory=tuple)
    name: str = "block_untrusted_host"

    def __call__(self, event: EventContext) -> Decision | None:
        if event.kind != EventKind.HTTP_REQUEST:
            return None

        url = str(event.payload.get("url", ""))
        hostname = (urlparse(url).hostname or "").lower()
        if not hostname or not self.trusted_hosts:
            return None

        for trusted_host in self.trusted_hosts:
            normalized = trusted_host.lower()
            if _matches_host(hostname, normalized):
                return None

        return Decision.block(
            reason="Outbound request host is not trusted.",
            metadata={"hostname": hostname},
        )


@dataclass(slots=True)
class ReviewSensitiveToolCallRule:
    """Review tool calls that should not run silently."""

    reviewed_tool_names: tuple[str, ...] = ()
    name: str = "review_sensitive_tool_call"

    def __call__(self, event: EventContext) -> Decision | None:
        if event.kind != EventKind.TOOL_CALL:
            return None

        tool_name = str(event.payload.get("name", "")).lower()
        for candidate in self.reviewed_tool_names:
            if tool_name == candidate.lower():
                return Decision.review(
                    reason="Tool call matches a reviewed-tool rule.",
                    metadata={"tool_name": tool_name},
                )

        return None


@dataclass(slots=True)
class BlockDisallowedToolRule:
    """Block tool calls that should never run under the current policy pack."""

    blocked_tool_names: tuple[str, ...] = ()
    name: str = "block_disallowed_tool"

    def __call__(self, event: EventContext) -> Decision | None:
        if event.kind != EventKind.TOOL_CALL:
            return None

        tool_name = str(event.payload.get("name", "")).lower()
        for candidate in self.blocked_tool_names:
            if tool_name == candidate.lower():
                return Decision.block(
                    reason="Tool call matches a blocked-tool rule.",
                    metadata={"tool_name": tool_name},
                )

        return None


def default_runtime_rules(
    *,
    trusted_hosts: tuple[str, ...] = ("localhost", "127.0.0.1", "api.openai.com"),
    reviewed_tool_names: tuple[str, ...] = (
        "shell",
        "terminal",
        "execute_command",
        "run_python",
    ),
    blocked_tool_names: tuple[str, ...] = (),
) -> list[Rule]:
    """Return a narrow default rule set for the first preview."""

    return [
        ReviewPromptInjectionRule(),
        ReviewSensitiveToolCallRule(reviewed_tool_names=reviewed_tool_names),
        BlockDisallowedToolRule(blocked_tool_names=blocked_tool_names),
        BlockDangerousCommandRule(),
        BlockSensitiveFileAccessRule(),
        BlockUntrustedHostRule(trusted_hosts=trusted_hosts),
    ]
