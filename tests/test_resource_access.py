import unittest

from agentfirewall import FirewallConfig, InMemoryAuditSink
from agentfirewall.audit import export_audit_trace
from agentfirewall.enforcers import GuardedResourceReader
from agentfirewall.exceptions import FirewallViolation
from agentfirewall.firewall import AgentFirewall
from agentfirewall.policy import Decision, PolicyEngine
from agentfirewall.runtime_context import (
    build_mcp_runtime_context,
    mcp_tool_runtime_context,
    missing_runtime_context_fields,
)

from mcp_loopback import LoopbackResourceStore


def block_private_resource(event):
    if event.kind.value != "resource_access":
        return None
    if event.payload.get("uri") == "mcp://private/secrets":
        return Decision.block(
            reason="Private loopback resource is blocked.",
            rule="block_private_loopback_resource",
        )
    return None


class ResourceAccessTests(unittest.TestCase):
    def test_build_mcp_runtime_context_keeps_required_fields_and_optional_metadata(self) -> None:
        context = build_mcp_runtime_context(
            runtime="mcp_loopback",
            tool_name="resource_lookup",
            tool_call_id="call_resource_1",
            tool_event_source="mcp.loopback.tool",
            mcp_direction="client",
            mcp_server_name="docs",
            mcp_resource_uri="mcp://docs/README.md",
            mcp_operation="read",
        )

        self.assertEqual(
            context,
            {
                "runtime": "mcp_loopback",
                "tool_name": "resource_lookup",
                "tool_call_id": "call_resource_1",
                "tool_event_source": "mcp.loopback.tool",
                "protocol": "mcp",
                "mcp_direction": "client",
                "mcp_server_name": "docs",
                "mcp_resource_uri": "mcp://docs/README.md",
                "mcp_operation": "read",
            },
        )
        self.assertEqual(
            missing_runtime_context_fields(context),
            (),
        )

    def test_guarded_resource_reader_reads_loopback_resource_with_runtime_context(self) -> None:
        store = LoopbackResourceStore({"mcp://docs/README.md": "# docs"})
        audit_sink = InMemoryAuditSink()
        reader = GuardedResourceReader(
            firewall=AgentFirewall(
                config=FirewallConfig(name="loopback"),
                policy=PolicyEngine(),
                audit_sink=audit_sink,
            ),
            reader=store.read,
            source="mcp.loopback.resource",
        )

        with mcp_tool_runtime_context(
            runtime="mcp_loopback",
            tool_name="resource_lookup",
            tool_call_id="call_resource_1",
            tool_event_source="mcp.loopback.tool",
            mcp_direction="client",
            mcp_server_name="docs",
            mcp_resource_uri="mcp://docs/README.md",
            mcp_operation="read",
        ):
            content = reader.read(
                "mcp://docs/README.md",
                server_name="docs",
                mime_type="text/markdown",
            )

        self.assertEqual(content, "# docs")
        self.assertEqual(store.reads, ["mcp://docs/README.md"])
        self.assertEqual(len(audit_sink.entries), 1)
        event = audit_sink.entries[0].event
        self.assertEqual(event.kind.value, "resource_access")
        self.assertEqual(
            event.payload["runtime_context"],
            {
                "runtime": "mcp_loopback",
                "tool_name": "resource_lookup",
                "tool_call_id": "call_resource_1",
                "tool_event_source": "mcp.loopback.tool",
                "protocol": "mcp",
                "mcp_direction": "client",
                "mcp_server_name": "docs",
                "mcp_resource_uri": "mcp://docs/README.md",
                "mcp_operation": "read",
            },
        )
        self.assertEqual(event.payload["server_name"], "docs")
        self.assertEqual(event.payload["mime_type"], "text/markdown")
        self.assertEqual(event.payload["scheme"], "mcp")
        trace = export_audit_trace(audit_sink.entries)[0]
        self.assertEqual(trace["event_kind"], "resource_access")
        self.assertEqual(trace["event_operation"], "read")

    def test_guarded_resource_reader_blocks_private_loopback_uri_before_reader_runs(self) -> None:
        store = LoopbackResourceStore({"mcp://private/secrets": "top-secret"})
        reader = GuardedResourceReader(
            firewall=AgentFirewall(
                config=FirewallConfig(name="loopback"),
                policy=PolicyEngine(rules=[block_private_resource]),
                audit_sink=InMemoryAuditSink(),
            ),
            reader=store.read,
            source="mcp.loopback.resource",
        )

        with self.assertRaises(FirewallViolation):
            reader.read(
                "mcp://private/secrets",
                server_name="private",
                mime_type="application/json",
            )

        self.assertEqual(store.reads, [])
