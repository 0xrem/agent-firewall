"""Minimal quick-start example for the supported LangGraph path.

Shows ConsoleAuditSink printing every firewall decision to stderr in real-time,
and all four guarded tool types (shell, HTTP, file read, file write).
"""

from __future__ import annotations

import io
import subprocess

from agentfirewall import (
    ConsoleAuditSink,
    FirewallConfig,
    ReviewRequired,
    create_firewall,
)
from agentfirewall.exceptions import FirewallViolation
from agentfirewall.langgraph import (
    create_agent,
    create_file_reader_tool,
    create_file_writer_tool,
    create_http_tool,
    create_shell_tool,
)

try:
    from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
    from langchain_core.messages import AIMessage
    from langchain_core.tools import tool
except ImportError as exc:  # pragma: no cover - local usage guard
    raise SystemExit(
        "This example requires optional dependencies. "
        "Install with `pip install agentfirewall[langgraph]`."
    ) from exc


class ToolCallingFakeModel(GenericFakeChatModel):
    """Fake model for quick-start demos without external API calls."""

    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        return self


@tool
def status(message: str) -> str:
    """Return a status message."""

    return f"status:{message}"


def _fake_shell_runner(command, *, shell=False, cwd=None, **kwargs):
    return subprocess.CompletedProcess(args=command, returncode=0, stdout="repo files\n")


def _fake_http_opener(request, **kwargs):
    return io.BytesIO(b'{"status":"ok"}')


def _fake_file_opener(path, mode="r", **kwargs):
    return io.StringIO("README CONTENT")


def _fake_file_writer(path, data, **kwargs):
    pass


def build_safe_model() -> ToolCallingFakeModel:
    return ToolCallingFakeModel(
        messages=iter(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "call_status",
                            "name": "status",
                            "args": {"message": "ready"},
                            "type": "tool_call",
                        }
                    ],
                ),
                AIMessage(content="All set."),
            ]
        )
    )


def build_review_model() -> ToolCallingFakeModel:
    return ToolCallingFakeModel(
        messages=iter(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "call_shell",
                            "name": "shell",
                            "args": {"command": "ls"},
                            "type": "tool_call",
                        }
                    ],
                )
            ]
        )
    )


def build_file_write_model() -> ToolCallingFakeModel:
    return ToolCallingFakeModel(
        messages=iter(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "call_write",
                            "name": "write_file",
                            "args": {"path": ".env", "content": "SECRET=leaked"},
                            "type": "tool_call",
                        }
                    ],
                )
            ]
        )
    )


def main() -> None:
    # ConsoleAuditSink prints every decision to stderr in real-time
    firewall = create_firewall(
        config=FirewallConfig(name="quickstart"),
        audit_sink=ConsoleAuditSink(),
    )

    tools = [
        status,
        create_shell_tool(firewall=firewall, runner=_fake_shell_runner),
        create_http_tool(firewall=firewall, opener=_fake_http_opener),
        create_file_reader_tool(firewall=firewall, opener=_fake_file_opener),
        create_file_writer_tool(firewall=firewall, writer=_fake_file_writer),
    ]

    # 1. Safe flow — everything allowed
    print("== safe flow ==")
    safe_agent = create_agent(model=build_safe_model(), tools=tools, firewall=firewall)
    safe = safe_agent.invoke(
        {"messages": [{"role": "user", "content": "Check the system status."}]}
    )
    print(safe["messages"][-1].content)

    # 2. Shell tool triggers review
    print("\n== review-required shell flow ==")
    review_agent = create_agent(model=build_review_model(), tools=tools, firewall=firewall)
    try:
        review_agent.invoke(
            {"messages": [{"role": "user", "content": "Open a shell and list files."}]}
        )
    except ReviewRequired as exc:
        print(f"review required: {exc}")

    # 3. Writing to .env is blocked
    print("\n== blocked file write flow ==")
    write_agent = create_agent(model=build_file_write_model(), tools=tools, firewall=firewall)
    try:
        write_agent.invoke(
            {"messages": [{"role": "user", "content": "Write secrets to .env."}]}
        )
    except FirewallViolation as exc:
        print(f"blocked: {exc}")


if __name__ == "__main__":
    main()
