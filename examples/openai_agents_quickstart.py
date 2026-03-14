"""
Quickstart example for OpenAI Agents SDK with AgentFirewall.

This is a minimal example to get started with AgentFirewall + OpenAI Agents.
Run this example without an API key to see the preview support path offline.

Run this example:
    python examples/openai_agents_quickstart.py
"""

from __future__ import annotations

from _openai_agents_fake_model import build_fake_model

from agentfirewall import (
    FirewallConfig,
    create_firewall,
    ConsoleAuditSink,
)
from agentfirewall.approval import approve_all

try:
    from agents import Agent, Runner
    from agents.run_config import RunConfig
    from agentfirewall.openai_agents import (
        create_agent as create_firewalled_agent,
    )
    from agentfirewall.openai_agents import (
        create_shell_tool,
    )
    OPENAI_AGENTS_AVAILABLE = True
except ImportError:
    OPENAI_AGENTS_AVAILABLE = False


def main():
    """Run a quick smoke test with OpenAI Agents + AgentFirewall."""
    print("=== OpenAI Agents Quickstart ===\n")

    if not OPENAI_AGENTS_AVAILABLE:
        print("OpenAI Agents SDK not available. Install with:")
        print("  pip install openai-agents")
        print("\nThis is expected if you haven't installed the optional dependency.")
        return

    firewall = create_firewall(
        config=FirewallConfig(name="quickstart"),
        audit_sink=ConsoleAuditSink(),
        approval_handler=approve_all(),
    )

    shell_tool = create_shell_tool(
        firewall=firewall,
        name="shell",
        description="Run a shell command",
    )
    model = build_fake_model(
        tool_calls=[
            {
                "id": "call_shell_quickstart",
                "name": "shell",
                "args": {"command": "echo 'Hello from AgentFirewall!'"},
            }
        ],
        final_text="Quickstart completed.",
    )

    agent = Agent(
        name="Quickstart Agent",
        instructions="You are a helpful assistant.",
        tools=[shell_tool],
        model=model,
    )

    firewalled_agent = create_firewalled_agent(
        agent=agent,
        firewall=firewall,
        inspect_prompts=True,
    )

    test_prompt = "Run the command: echo 'Hello from AgentFirewall!'"

    print(f"Prompt: {test_prompt}\n")
    try:
        result = Runner.run_sync(
            firewalled_agent,
            test_prompt,
            run_config=RunConfig(tracing_disabled=True),
        )
        print(f"\nResult: {result.final_output}")
    except Exception as exc:
        print(f"\nStopped by firewall: {exc}")


if __name__ == "__main__":
    main()
