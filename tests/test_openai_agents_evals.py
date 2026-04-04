import importlib.util
import unittest

from agentfirewall.evals import (
    load_openai_agents_eval_cases,
    run_openai_agents_eval_case,
    run_openai_agents_eval_suite,
)


OPENAI_AGENTS_AVAILABLE = bool(importlib.util.find_spec("agents"))


@unittest.skipUnless(
    OPENAI_AGENTS_AVAILABLE,
    "OpenAI Agents optional dependencies are not installed.",
)
class OpenAIAgentsEvalTests(unittest.TestCase):
    def test_packaged_openai_eval_suite_matches_all_cases(self) -> None:
        summary = run_openai_agents_eval_suite()

        self.assertEqual(summary.total, 11)
        self.assertEqual(summary.passed, 11)
        self.assertEqual(summary.failed, 0)

    def test_nested_side_effect_case_preserves_runtime_context(self) -> None:
        cases = {
            case.name: case
            for case in load_openai_agents_eval_cases()
        }

        result = run_openai_agents_eval_case(cases["nested_side_effects"])

        self.assertTrue(result.matched, msg=result.detail)
        http_entry = next(
            entry
            for entry in result.audit_trace
            if entry["event_kind"] == "http_request"
        )
        self.assertEqual(
            http_entry["runtime_context"],
            {
                "runtime": "openai_agents",
                "tool_name": "http_request",
                "tool_call_id": "call_http",
                "tool_event_source": "openai_agents.tool",
            },
        )

    def test_reviewed_shell_case_captures_review_then_command(self) -> None:
        cases = {
            case.name: case
            for case in load_openai_agents_eval_cases()
        }

        result = run_openai_agents_eval_case(cases["shell_tool_approved"])

        self.assertTrue(result.matched, msg=result.detail)
        self.assertEqual(
            result.observed_actions,
            ["allow", "review", "allow", "allow"],
        )
        self.assertEqual(
            result.observed_event_kinds,
            ["prompt", "tool_call", "tool_call", "command"],
        )

    def test_repo_triage_workflow_preserves_file_and_http_steps(self) -> None:
        cases = {
            case.name: case
            for case in load_openai_agents_eval_cases()
        }

        result = run_openai_agents_eval_case(
            cases["workflow_shell_approved_then_safe_file_then_trusted_http"]
        )

        self.assertTrue(result.matched, msg=result.detail)
        self.assertEqual(
            result.observed_event_kinds,
            ["prompt", "tool_call", "tool_call", "command", "tool_call", "file_access", "tool_call", "http_request"],
        )
        http_entry = next(
            entry
            for entry in result.audit_trace
            if entry["event_kind"] == "http_request"
        )
        self.assertEqual(
            http_entry["runtime_context"],
            {
                "runtime": "openai_agents",
                "tool_name": "http_request",
                "tool_call_id": "call_http_triage",
                "tool_event_source": "openai_agents.tool",
            },
        )
