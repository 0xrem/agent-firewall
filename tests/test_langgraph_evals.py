import importlib.util
import unittest


LANGGRAPH_AVAILABLE = bool(importlib.util.find_spec("langchain")) and bool(
    importlib.util.find_spec("langgraph")
)


@unittest.skipUnless(LANGGRAPH_AVAILABLE, "LangGraph optional dependencies are not installed.")
class LangGraphEvalTests(unittest.TestCase):
    def test_default_langgraph_eval_suite_passes(self) -> None:
        from agentfirewall.evals import run_langgraph_eval_suite

        summary = run_langgraph_eval_suite()

        self.assertEqual(summary.failed, 0)
        self.assertEqual(summary.total, 19)
        self.assertEqual(summary.status_counts["completed"], 9)
        self.assertEqual(summary.status_counts["blocked"], 8)
        self.assertEqual(summary.status_counts["review_required"], 2)
        self.assertEqual(summary.task_counts["incident_triage"], 2)
        self.assertEqual(summary.task_counts["secret_access"], 2)
        self.assertEqual(summary.task_counts["credential_injection"], 1)
        self.assertEqual(summary.task_counts["safe_file_write"], 1)

    def test_langgraph_eval_summary_is_json_friendly(self) -> None:
        from agentfirewall.evals import run_langgraph_eval_suite

        summary = run_langgraph_eval_suite()
        payload = summary.to_dict()

        self.assertEqual(payload["failed"], 0)
        self.assertEqual(payload["unexpected_allows"], 0)
        self.assertEqual(payload["unexpected_blocks"], 0)
        self.assertEqual(payload["results"][0]["name"], "safe_status_tool")
        self.assertEqual(payload["results"][0]["task"], "operations_check")
        self.assertIn("workflow_goal", payload["results"][0])
        self.assertIn("task_counts", payload)
        self.assertIn("observed_event_kinds", payload["results"][0])
        self.assertIn("observed_actions", payload["results"][0])
        self.assertIn("audit_summary", payload["results"][0])
        self.assertIn("audit_trace", payload["results"][0])
        self.assertIn("event_kind_counts", payload["results"][0]["audit_summary"])
        self.assertIn("source_counts", payload["results"][0]["audit_summary"])
        self.assertIn("tool_name_counts", payload["results"][0]["audit_summary"])
        self.assertIn("event_operation", payload["results"][0]["audit_trace"][0])

    def test_langgraph_eval_trace_links_side_effects_to_tool_context(self) -> None:
        from agentfirewall.evals import run_langgraph_eval_suite

        summary = run_langgraph_eval_suite()
        workflow_result = next(
            result for result in summary.to_dict()["results"]
            if result["name"] == "workflow_shell_approved_then_trusted_http"
        )

        command_trace = next(
            item for item in workflow_result["audit_trace"]
            if item["event_kind"] == "command"
        )
        http_trace = next(
            item for item in workflow_result["audit_trace"]
            if item["event_kind"] == "http_request"
        )

        self.assertEqual(command_trace["runtime_context"]["tool_name"], "shell")
        self.assertEqual(
            command_trace["runtime_context"]["tool_call_id"],
            "call_shell_workflow",
        )
        self.assertEqual(http_trace["runtime_context"]["tool_name"], "http_request")
        self.assertEqual(
            http_trace["runtime_context"]["tool_call_id"],
            "call_http_after_shell_workflow",
        )

    def test_langgraph_eval_log_only_workflow_records_original_actions(self) -> None:
        from agentfirewall.evals import run_langgraph_eval_suite

        summary = run_langgraph_eval_suite()
        workflow_result = next(
            result for result in summary.to_dict()["results"]
            if result["name"] == "log_only_shell_then_blocked_http"
        )

        self.assertEqual(workflow_result["observed_final_action"], "log")
        original_actions = [
            item["decision_metadata"].get("original_action")
            for item in workflow_result["audit_trace"]
            if item["action"] == "log"
        ]
        self.assertIn("review", original_actions)
        self.assertIn("block", original_actions)

    def test_langgraph_eval_workflow_sequences_match_expected_trace(self) -> None:
        from agentfirewall.evals import run_langgraph_eval_suite

        summary = run_langgraph_eval_suite()
        workflow_result = next(
            result for result in summary.to_dict()["results"]
            if result["name"] == "workflow_shell_approved_then_safe_file_then_trusted_http"
        )

        self.assertEqual(
            workflow_result["observed_event_kinds"],
            workflow_result["expected_event_kinds"],
        )
        self.assertEqual(
            workflow_result["observed_actions"],
            workflow_result["expected_action_sequence"],
        )
