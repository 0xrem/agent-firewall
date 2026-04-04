import unittest

from agentfirewall.evals import (
    require_eval_result,
    require_eval_trace,
    run_generic_eval_suite,
)


class GenericEvalSuiteTests(unittest.TestCase):
    def test_generic_eval_suite_matches_expected_release_shape(self) -> None:
        summary = run_generic_eval_suite()
        payload = summary.to_dict()

        self.assertEqual(payload["total"], 9)
        self.assertEqual(payload["failed"], 0)
        self.assertEqual(payload["unexpected_allows"], 0)
        self.assertEqual(payload["unexpected_blocks"], 0)
        self.assertEqual(payload["unexpected_reviews"], 0)
        self.assertEqual(
            payload["status_counts"],
            {
                "blocked": 3,
                "completed": 5,
                "review_required": 1,
            },
        )

    def test_generic_eval_suite_preserves_nested_runtime_context(self) -> None:
        payload = run_generic_eval_suite().to_dict()

        shell_result = require_eval_result(payload, "shell_tool_approved")
        shell_trace = require_eval_trace(
            shell_result,
            event_kind="command",
            event_operation="execute",
        )
        self.assertEqual(
            shell_trace["runtime_context"],
            {
                "runtime": "generic",
                "tool_name": "shell",
                "tool_call_id": "call_eval_shell",
                "tool_event_source": "generic.tool",
            },
        )

        http_result = require_eval_result(
            payload,
            "guarded_http_blocks_untrusted_host",
        )
        http_trace = require_eval_trace(
            http_result,
            event_kind="http_request",
            event_operation="POST",
        )
        self.assertEqual(
            http_trace["runtime_context"],
            {
                "runtime": "generic",
                "tool_name": "http_request",
                "tool_call_id": "call_eval_http_request",
                "tool_event_source": "generic.tool",
            },
        )

    def test_generic_eval_suite_covers_log_only_and_file_write_paths(self) -> None:
        payload = run_generic_eval_suite().to_dict()

        log_only_result = require_eval_result(payload, "log_only_shell_then_blocked_http")
        self.assertEqual(
            log_only_result["observed_actions"],
            ["log", "allow", "allow", "log"],
        )

        write_result = require_eval_result(
            payload,
            "guarded_file_write_blocks_sensitive_path",
        )
        write_trace = require_eval_trace(
            write_result,
            event_kind="file_access",
            event_operation="write",
        )
        self.assertEqual(
            write_trace["runtime_context"],
            {
                "runtime": "generic",
                "tool_name": "write_file",
                "tool_call_id": "call_eval_write_file",
                "tool_event_source": "generic.tool",
            },
        )

    def test_generic_eval_suite_covers_repo_triage_workflow(self) -> None:
        payload = run_generic_eval_suite().to_dict()

        workflow_result = require_eval_result(
            payload,
            "workflow_shell_approved_then_safe_file_then_trusted_http",
        )
        self.assertEqual(
            workflow_result["observed_actions"],
            ["review", "allow", "allow", "allow", "allow", "allow", "allow"],
        )
        http_trace = require_eval_trace(
            workflow_result,
            event_kind="http_request",
            event_operation="GET",
        )
        self.assertEqual(
            http_trace["runtime_context"],
            {
                "runtime": "generic",
                "tool_name": "http_request",
                "tool_call_id": "call_eval_http_request",
                "tool_event_source": "generic.tool",
            },
        )
