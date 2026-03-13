import importlib.util
import unittest

from agentfirewall.evals import (
    require_eval_trace,
    require_named_eval_result,
)
from agentfirewall.integrations import (
    get_official_adapter,
    run_official_adapter_eval_suite,
    validate_official_adapter_eval_expectations,
)


LANGGRAPH_AVAILABLE = bool(importlib.util.find_spec("langchain")) and bool(
    importlib.util.find_spec("langgraph")
)


@unittest.skipUnless(LANGGRAPH_AVAILABLE, "LangGraph optional dependencies are not installed.")
class LangGraphEvalTests(unittest.TestCase):
    def test_default_langgraph_eval_suite_passes(self) -> None:
        summary = run_official_adapter_eval_suite("langgraph")
        report = validate_official_adapter_eval_expectations("langgraph")

        self.assertEqual(summary.failed, 0)
        self.assertEqual(summary.total, 19)
        self.assertTrue(report.ok, msg=report.to_dict())

    def test_langgraph_eval_summary_is_json_friendly(self) -> None:
        summary = run_official_adapter_eval_suite("langgraph")
        payload = summary.to_dict()
        adapter = get_official_adapter("langgraph")
        first_result = require_named_eval_result(
            payload,
            adapter.eval_expectations,
            "safe_status_tool",
        )

        self.assertEqual(payload["failed"], 0)
        self.assertEqual(payload["unexpected_allows"], 0)
        self.assertEqual(payload["unexpected_blocks"], 0)
        self.assertEqual(first_result["name"], "safe_status_tool")
        self.assertEqual(first_result["task"], "operations_check")
        self.assertIn("workflow_goal", first_result)
        self.assertIn("task_counts", payload)
        self.assertIn("observed_event_kinds", first_result)
        self.assertIn("observed_actions", first_result)
        self.assertIn("audit_summary", first_result)
        self.assertIn("audit_trace", first_result)
        self.assertIn("event_kind_counts", first_result["audit_summary"])
        self.assertIn("source_counts", first_result["audit_summary"])
        self.assertIn("tool_name_counts", first_result["audit_summary"])
        self.assertIn("event_operation", first_result["audit_trace"][0])

    def test_langgraph_eval_trace_links_side_effects_to_tool_context(self) -> None:
        summary = run_official_adapter_eval_suite("langgraph")
        adapter = get_official_adapter("langgraph")
        workflow_result = require_named_eval_result(
            summary.to_dict(),
            adapter.eval_expectations,
            "workflow_shell_then_http",
        )

        command_trace = require_eval_trace(
            workflow_result,
            event_kind="command",
        )
        http_trace = require_eval_trace(
            workflow_result,
            event_kind="http_request",
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
        summary = run_official_adapter_eval_suite("langgraph")
        adapter = get_official_adapter("langgraph")
        workflow_result = require_named_eval_result(
            summary.to_dict(),
            adapter.eval_expectations,
            "log_only_workflow",
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
        summary = run_official_adapter_eval_suite("langgraph")
        adapter = get_official_adapter("langgraph")
        workflow_result = require_named_eval_result(
            summary.to_dict(),
            adapter.eval_expectations,
            "workflow_shell_then_file_then_http",
        )

        self.assertEqual(
            workflow_result["observed_event_kinds"],
            workflow_result["expected_event_kinds"],
        )
        self.assertEqual(
            workflow_result["observed_actions"],
            workflow_result["expected_action_sequence"],
        )
