import unittest

from agentfirewall.evals import (
    load_mcp_client_eval_cases,
    load_mcp_server_eval_cases,
    run_mcp_client_eval_case,
    run_mcp_client_eval_suite,
    run_mcp_server_eval_case,
    run_mcp_server_eval_suite,
)


class McpPreviewEvalTests(unittest.TestCase):
    def test_mcp_client_eval_suite_matches_packaged_shape(self) -> None:
        summary = run_mcp_client_eval_suite()

        self.assertEqual(summary.total, 8)
        self.assertEqual(summary.passed, 8)
        self.assertEqual(summary.failed, 0)

    def test_mcp_server_eval_suite_matches_packaged_shape(self) -> None:
        summary = run_mcp_server_eval_suite()

        self.assertEqual(summary.total, 6)
        self.assertEqual(summary.passed, 6)
        self.assertEqual(summary.failed, 0)

    def test_mcp_client_resource_read_preserves_mcp_runtime_metadata(self) -> None:
        cases = {case.name: case for case in load_mcp_client_eval_cases()}
        result = run_mcp_client_eval_case(cases["allowed_resource_read"])

        self.assertTrue(result.matched, msg=result.detail)
        trace = next(
            item
            for item in result.audit_trace
            if item["event_kind"] == "resource_access"
        )
        self.assertEqual(
            trace["runtime_context"],
            {
                "runtime": "mcp_client",
                "tool_name": "resource_read",
                "tool_call_id": "call_eval_resource_read",
                "tool_event_source": "mcp.client.resource",
                "protocol": "mcp",
                "mcp_direction": "client",
                "mcp_server_name": "docs",
                "mcp_resource_uri": "mcp://docs/README.md",
                "mcp_operation": "read",
            },
        )

    def test_mcp_server_incident_triage_preserves_resource_and_http_steps(self) -> None:
        cases = {case.name: case for case in load_mcp_server_eval_cases()}
        result = run_mcp_server_eval_case(
            cases["workflow_shell_approved_then_resource_then_trusted_http"]
        )

        self.assertTrue(result.matched, msg=result.detail)
        self.assertEqual(
            result.observed_event_kinds,
            ["tool_call", "tool_call", "command", "resource_access", "tool_call", "http_request"],
        )
