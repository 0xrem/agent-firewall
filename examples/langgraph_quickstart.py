"""Minimal quick-start example for the supported LangGraph path."""

from __future__ import annotations

import subprocess

from agentfirewall import (
    FirewallConfig,
    ReviewRequired,
    create_firewall,
)
from agentfirewall.langgraph import create_agent, create_shell_tool

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


def _quickstart_firewall(name: str):
    return create_firewall(config=FirewallConfig(name=name))


def _fake_shell_runner(command, *, shell=False, cwd=None, **kwargs):
    return subprocess.CompletedProcess(
        args=command,
        returncode=0,
        stdout="repo files\n",
    )


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


def main() -> None:
    safe_firewall = _quickstart_firewall("quickstart-safe")
    safe_agent = create_agent(
        model=build_safe_model(),
        tools=[
            status,
            create_shell_tool(
                firewall=safe_firewall,
                runner=_fake_shell_runner,
            ),
        ],
        firewall=safe_firewall,
    )

    safe = safe_agent.invoke(
        {"messages": [{"role": "user", "content": "Check the system status."}]}
    )
    print(safe["messages"][-1].content)

    review_firewall = _quickstart_firewall("quickstart-review")
    review_agent = create_agent(
        model=build_review_model(),
        tools=[
            status,
            create_shell_tool(
                firewall=review_firewall,
                runner=_fake_shell_runner,
            ),
        ],
        firewall=review_firewall,
    )

    try:
        review_agent.invoke(
            {"messages": [{"role": "user", "content": "Open a shell and list files."}]}
        )
    except ReviewRequired as exc:
        print(f"review required: {exc}")


if __name__ == "__main__":
    main()
