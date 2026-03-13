import unittest

from agentfirewall import AgentFirewall, FirewallConfig, InMemoryAuditSink
from agentfirewall.integrations import resolve_adapter_firewall


class AdapterAssemblyTests(unittest.TestCase):
    def test_resolve_adapter_firewall_returns_existing_firewall(self) -> None:
        firewall = AgentFirewall()

        resolved = resolve_adapter_firewall(firewall=firewall)

        self.assertIs(resolved, firewall)

    def test_resolve_adapter_firewall_builds_firewall_from_high_level_options(self) -> None:
        audit_sink = InMemoryAuditSink()

        resolved = resolve_adapter_firewall(
            config=FirewallConfig(name="adapter-factory"),
            audit_sink=audit_sink,
            approval_handler=lambda request: True,
        )

        self.assertEqual(resolved.config.name, "adapter-factory")
        self.assertIs(resolved.audit_sink, audit_sink)
        self.assertIsNotNone(resolved.approval_handler)

    def test_resolve_adapter_firewall_rejects_mixed_existing_and_factory_options(self) -> None:
        firewall = AgentFirewall()

        with self.assertRaises(TypeError):
            resolve_adapter_firewall(
                firewall=firewall,
                config=FirewallConfig(name="conflict"),
            )
