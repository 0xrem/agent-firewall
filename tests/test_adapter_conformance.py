import importlib.util
import unittest

from agentfirewall.integrations import (
    AdapterCapability,
    AdapterSupportLevel,
    OFFICIAL_ADAPTER_CAPABILITY_ORDER,
    capability_support_map,
    export_official_adapter_matrix,
    get_official_adapter_spec,
    get_langgraph_adapter_spec,
    list_official_adapter_specs,
    validate_eval_summary,
)
from agentfirewall.runtime_context import (
    REQUIRED_RUNTIME_CONTEXT_FIELDS,
    SIDE_EFFECT_RUNTIME_EVENT_KINDS,
    build_tool_runtime_context,
    missing_runtime_context_fields,
)


LANGGRAPH_AVAILABLE = bool(importlib.util.find_spec("langchain")) and bool(
    importlib.util.find_spec("langgraph")
)


class AdapterContractTests(unittest.TestCase):
    def test_official_adapter_registry_lists_langgraph(self) -> None:
        specs = list_official_adapter_specs()

        self.assertEqual(tuple(spec.name for spec in specs), ("langgraph",))
        self.assertEqual(get_official_adapter_spec("langgraph"), get_langgraph_adapter_spec())

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

    def test_capability_support_map_tracks_standard_matrix_order(self) -> None:
        spec = get_langgraph_adapter_spec()

        support_map = capability_support_map(spec)

        self.assertEqual(
            tuple(support_map.keys()),
            tuple(capability.value for capability in OFFICIAL_ADAPTER_CAPABILITY_ORDER),
        )
        self.assertTrue(all(value == "supported" for value in support_map.values()))

    def test_export_official_adapter_matrix_returns_machine_readable_rows(self) -> None:
        matrix = export_official_adapter_matrix()

        self.assertEqual(len(matrix), 1)
        self.assertEqual(matrix[0]["name"], "langgraph")
        self.assertEqual(matrix[0]["module"], "agentfirewall.langgraph")
        self.assertEqual(matrix[0]["support_level"], "supported")
        self.assertEqual(matrix[0]["prompt_inspection"], "supported")
        self.assertEqual(matrix[0]["log_only_semantics"], "supported")

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

    def test_build_tool_runtime_context_normalizes_required_fields(self) -> None:
        context = build_tool_runtime_context(
            runtime="langgraph",
            tool_name="shell",
            tool_call_id="call_123",
            tool_event_source="langgraph.tool",
            trace_id="trace_1",
            empty_field="",
        )

        self.assertEqual(
            context,
            {
                "runtime": "langgraph",
                "tool_name": "shell",
                "tool_call_id": "call_123",
                "tool_event_source": "langgraph.tool",
                "trace_id": "trace_1",
            },
        )

    def test_runtime_context_contract_event_kinds_match_side_effect_surfaces(self) -> None:
        self.assertEqual(
            SIDE_EFFECT_RUNTIME_EVENT_KINDS,
            ("command", "file_access", "http_request"),
        )


@unittest.skipUnless(LANGGRAPH_AVAILABLE, "LangGraph optional dependencies are not installed.")
class LangGraphConformanceTests(unittest.TestCase):
    def test_langgraph_eval_suite_still_passes_under_adapter_contract(self) -> None:
        from agentfirewall.evals import run_langgraph_eval_suite

        summary = run_langgraph_eval_suite()

        self.assertEqual(summary.failed, 0)
        self.assertEqual(summary.total, 19)

    def test_langgraph_eval_summary_passes_reusable_conformance_validator(self) -> None:
        from agentfirewall.evals import run_langgraph_eval_suite

        spec = get_langgraph_adapter_spec()
        report = validate_eval_summary(run_langgraph_eval_suite().to_dict(), spec)

        self.assertTrue(report.ok, msg=report.to_dict())

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

    def test_langgraph_eval_trace_includes_event_operation_for_file_access(self) -> None:
        from agentfirewall.evals import run_langgraph_eval_suite

        summary = run_langgraph_eval_suite().to_dict()
        write_case = next(
            result for result in summary["results"]
            if result["name"] == "guarded_file_write_allows_safe_path"
        )
        file_trace = next(
            item for item in write_case["audit_trace"]
            if item["event_kind"] == "file_access"
        )

        self.assertEqual(file_trace["event_operation"], "write")

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
