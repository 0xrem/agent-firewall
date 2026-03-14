import io
import subprocess
import unittest

from agentfirewall import FirewallConfig, InMemoryAuditSink
from agentfirewall.approval import ApprovalResponse
from agentfirewall.generic import create_generic_runtime_bundle


class GenericRuntimeBundleTests(unittest.TestCase):
    def test_create_generic_runtime_bundle_builds_firewall_and_default_sources(self) -> None:
        audit_sink = InMemoryAuditSink()

        bundle = create_generic_runtime_bundle(
            config=FirewallConfig(name="generic-bundle", raise_on_review=False),
            audit_sink=audit_sink,
            approval_handler=lambda request: ApprovalResponse.approve(
                reason="Approved in test."
            ),
        )

        self.assertEqual(bundle.firewall.config.name, "generic-bundle")
        self.assertIs(bundle.firewall.audit_sink, audit_sink)
        self.assertEqual(bundle.tool_dispatcher.source, "generic.tool")
        self.assertEqual(bundle.tool_dispatcher.runtime, "generic")
        self.assertEqual(bundle.command_runner.source, "generic.command")
        self.assertEqual(bundle.http_client.source, "generic.http")
        self.assertEqual(bundle.file_access.source, "generic.file")

    def test_create_generic_runtime_bundle_rejects_mixed_firewall_inputs(self) -> None:
        bundle = create_generic_runtime_bundle()

        with self.assertRaises(TypeError):
            create_generic_runtime_bundle(
                firewall=bundle.firewall,
                config=FirewallConfig(name="conflict"),
            )

    def test_bundle_dispatch_propagates_runtime_context_to_nested_command(self) -> None:
        calls: list[tuple[object, bool, str | None]] = []
        audit_sink = InMemoryAuditSink()

        def fake_runner(command, *, shell=False, cwd=None, **kwargs):
            calls.append((command, shell, cwd))
            return subprocess.CompletedProcess(
                args=command,
                returncode=0,
                stdout="repo files\n",
            )

        bundle = create_generic_runtime_bundle(
            config=FirewallConfig(name="generic-bundle", raise_on_review=False),
            audit_sink=audit_sink,
            approval_handler=lambda request: ApprovalResponse.approve(
                reason="Approved in test."
            ),
            runner=fake_runner,
            tool_call_id_factory=lambda name, args, kwargs: "call_shell_bundle",
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

        result = bundle.dispatch("shell", command="ls")

        self.assertEqual(result, "repo files")
        self.assertEqual(calls, [("ls", True, None)])
        self.assertEqual(
            audit_sink.entries[-1].event.payload["runtime_context"],
            {
                "runtime": "generic",
                "tool_name": "shell",
                "tool_call_id": "call_shell_bundle",
                "tool_event_source": "generic.tool",
            },
        )

    def test_bundle_accepts_custom_source_prefix_and_registered_tools(self) -> None:
        bundle = create_generic_runtime_bundle(
            source_prefix="custom.preview",
            tools={"status": lambda message: f"status:{message}"},
            http_opener=lambda request, **kwargs: io.BytesIO(b"ok"),
        )

        result = bundle.dispatch("status", message="ready")

        self.assertEqual(result, "status:ready")
        self.assertEqual(bundle.tool_dispatcher.source, "custom.preview.tool")
        self.assertEqual(bundle.http_client.source, "custom.preview.http")
