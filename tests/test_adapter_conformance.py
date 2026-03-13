import importlib.util
import unittest

from agentfirewall.integrations import (
    AdapterCapability,
    AdapterSupportLevel,
    get_langgraph_adapter_spec,
)
from agentfirewall.runtime_context import (
    REQUIRED_RUNTIME_CONTEXT_FIELDS,
    missing_runtime_context_fields,
)


LANGGRAPH_AVAILABLE = bool(importlib.util.find_spec("langchain")) and bool(
    importlib.util.find_spec("langgraph")
)


class AdapterContractTests(unittest.TestCase):
    def test_langgraph_adapter_declares_supported_capabilities(self) -> None:
        spec = get_langgraph_adapter_spec()

        self.assertEqual(spec.name, "langgraph")
        self.assertEqual(spec.module, "agentfirewall.langgraph")
        self.assertEqual(spec.support_level, AdapterSupportLevel.SUPPORTED)
        self.assertEqual(
            spec.required_runtime_context_fields,
            REQUIRED_RUNTIME_CONTEXT_FIELDS,
        )
        self.assertTrue(spec.supports(AdapterCapability.PROMPT_INSPECTION))
        self.assertTrue(spec.supports(AdapterCapability.TOOL_CALL_INTERCEPTION))
        self.assertTrue(spec.supports(AdapterCapability.SHELL_ENFORCEMENT))
        self.assertTrue(spec.supports(AdapterCapability.FILE_READ_ENFORCEMENT))
        self.assertTrue(spec.supports(AdapterCapability.FILE_WRITE_ENFORCEMENT))
        self.assertTrue(spec.supports(AdapterCapability.HTTP_ENFORCEMENT))
        self.assertTrue(spec.supports(AdapterCapability.RUNTIME_CONTEXT_CORRELATION))
        self.assertTrue(spec.supports(AdapterCapability.REVIEW_SEMANTICS))
        self.assertTrue(spec.supports(AdapterCapability.LOG_ONLY_SEMANTICS))

    def test_missing_runtime_context_fields_reports_contract_gaps(self) -> None:
        self.assertEqual(
            missing_runtime_context_fields({"runtime": "langgraph"}),
            ("tool_name", "tool_call_id", "tool_event_source"),
        )
        self.assertEqual(
            missing_runtime_context_fields(
                {
                    "runtime": "langgraph",
                    "tool_name": "shell",
                    "tool_call_id": "call_1",
                    "tool_event_source": "langgraph.tool",
                }
            ),
            (),
        )


@unittest.skipUnless(LANGGRAPH_AVAILABLE, "LangGraph optional dependencies are not installed.")
class LangGraphConformanceTests(unittest.TestCase):
    def test_langgraph_eval_suite_still_passes_under_adapter_contract(self) -> None:
        from agentfirewall.evals import run_langgraph_eval_suite

        summary = run_langgraph_eval_suite()

        self.assertEqual(summary.failed, 0)
        self.assertEqual(summary.total, 17)

    def test_langgraph_side_effect_traces_include_required_runtime_context(self) -> None:
        from agentfirewall.evals import run_langgraph_eval_suite

        spec = get_langgraph_adapter_spec()
        summary = run_langgraph_eval_suite()

        for result in summary.to_dict()["results"]:
            for trace in result["audit_trace"]:
                if trace["event_kind"] not in {"command", "file_access", "http_request"}:
                    continue
                missing = missing_runtime_context_fields(
                    trace["runtime_context"],
                    required_fields=spec.required_runtime_context_fields,
                )
                self.assertEqual(
                    missing,
                    (),
                    msg=(
                        f"{result['name']} emitted {trace['event_kind']} without "
                        f"required runtime_context fields: {missing}"
                    ),
                )

    def test_langgraph_review_and_log_only_semantics_match_contract(self) -> None:
        from agentfirewall.evals import run_langgraph_eval_suite

        spec = get_langgraph_adapter_spec()
        summary = run_langgraph_eval_suite().to_dict()

        if spec.supports(AdapterCapability.REVIEW_SEMANTICS):
            review_case = next(
                result for result in summary["results"]
                if result["name"] == "shell_tool_review_without_handler"
            )
            self.assertEqual(review_case["status"], "review_required")
            self.assertEqual(review_case["observed_final_action"], "review")

        if spec.supports(AdapterCapability.LOG_ONLY_SEMANTICS):
            log_only_case = next(
                result for result in summary["results"]
                if result["name"] == "log_only_shell_then_blocked_http"
            )
            self.assertEqual(log_only_case["status"], "completed")
            self.assertEqual(log_only_case["observed_final_action"], "log")

            original_actions = [
                item["decision_metadata"].get("original_action")
                for item in log_only_case["audit_trace"]
                if item["action"] == "log"
            ]
            self.assertIn("review", original_actions)
            self.assertIn("block", original_actions)
