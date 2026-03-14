import importlib.util
import unittest

from agentfirewall.evals import (
    require_eval_trace,
    require_named_eval_result,
)
from agentfirewall.integrations import (
    AdapterCapability,
    AdapterSupportLevel,
    OFFICIAL_ADAPTER_CAPABILITY_ORDER,
    capability_support_map,
    export_official_adapter_inventory,
    get_official_adapter,
    export_official_adapter_matrix,
    get_official_adapter_spec,
    get_langgraph_adapter_spec,
    get_openai_agents_adapter_spec,
    list_official_adapters,
    list_official_adapter_specs,
    run_official_adapter_eval_suite,
    validate_eval_summary,
    validate_official_adapter_conformance,
    validate_official_adapter_eval_expectations,
    validate_official_adapter_release_gate,
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
OPENAI_AGENTS_AVAILABLE = bool(importlib.util.find_spec("agents"))


class AdapterContractTests(unittest.TestCase):
    def test_official_adapter_registry_lists_langgraph_and_openai_agents(self) -> None:
        specs = list_official_adapter_specs()

        self.assertEqual(
            tuple(spec.name for spec in specs),
            ("langgraph", "openai_agents"),
        )
        self.assertEqual(get_official_adapter_spec("langgraph"), get_langgraph_adapter_spec())
        self.assertEqual(
            get_official_adapter_spec("openai_agents"),
            get_openai_agents_adapter_spec(),
        )
        self.assertEqual(
            tuple(adapter.name for adapter in list_official_adapters()),
            ("langgraph", "openai_agents"),
        )

    def test_official_adapter_inventory_exports_eval_evidence_entrypoint(self) -> None:
        inventory = export_official_adapter_inventory()

        self.assertEqual(len(inventory), 2)
        rows = {item["name"]: item for item in inventory}
        self.assertEqual(set(rows), {"langgraph", "openai_agents"})
        self.assertTrue(rows["langgraph"]["has_eval_suite"])
        self.assertTrue(rows["langgraph"]["has_eval_expectations"])
        self.assertEqual(
            rows["langgraph"]["eval_runner"],
            "agentfirewall.evals:run_langgraph_eval_suite",
        )
        self.assertTrue(rows["openai_agents"]["has_eval_suite"])
        self.assertTrue(rows["openai_agents"]["has_eval_expectations"])
        self.assertEqual(
            rows["openai_agents"]["eval_runner"],
            "agentfirewall.evals:run_openai_agents_eval_suite",
        )

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

    def test_openai_agents_adapter_declares_supported_capabilities(self) -> None:
        spec = get_openai_agents_adapter_spec()

        self.assertEqual(spec.name, "openai_agents")
        self.assertEqual(spec.module, "agentfirewall.openai_agents")
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

        self.assertEqual(len(matrix), 2)
        rows = {row["name"]: row for row in matrix}
        self.assertEqual(set(rows), {"langgraph", "openai_agents"})
        self.assertEqual(rows["langgraph"]["module"], "agentfirewall.langgraph")
        self.assertEqual(rows["openai_agents"]["module"], "agentfirewall.openai_agents")
        self.assertEqual(rows["langgraph"]["support_level"], "supported")
        self.assertEqual(rows["openai_agents"]["support_level"], "supported")
        self.assertEqual(rows["langgraph"]["prompt_inspection"], "supported")
        self.assertEqual(rows["openai_agents"]["prompt_inspection"], "supported")
        self.assertEqual(rows["langgraph"]["log_only_semantics"], "supported")
        self.assertEqual(rows["openai_agents"]["log_only_semantics"], "supported")

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
    def test_official_adapter_registry_can_run_langgraph_eval_suite(self) -> None:
        summary = run_official_adapter_eval_suite("langgraph")

        self.assertEqual(summary.failed, 0)
        self.assertEqual(summary.total, 19)

    def test_official_adapter_registry_can_validate_langgraph_conformance(self) -> None:
        report = validate_official_adapter_conformance("langgraph")

        self.assertTrue(report.ok, msg=report.to_dict())

    def test_official_adapter_registry_can_validate_langgraph_eval_expectations(self) -> None:
        report = validate_official_adapter_eval_expectations("langgraph")

        self.assertTrue(report.ok, msg=report.to_dict())

    def test_official_adapter_registry_can_validate_langgraph_release_gate(self) -> None:
        report = validate_official_adapter_release_gate("langgraph")

        self.assertTrue(report.ok, msg=report.to_dict())
        self.assertTrue(report.conformance.ok)
        self.assertIsNotNone(report.eval_expectations)
        self.assertTrue(report.eval_expectations.ok)

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

    def test_official_adapter_record_matches_langgraph_contract(self) -> None:
        adapter = get_official_adapter("langgraph")

        self.assertEqual(adapter.spec, get_langgraph_adapter_spec())
        self.assertTrue(adapter.has_eval_suite())
        self.assertTrue(adapter.has_eval_expectations())
        self.assertEqual(
            adapter.resolve_eval_case_alias("log_only_workflow"),
            "log_only_shell_then_blocked_http",
        )

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
        summary = run_official_adapter_eval_suite("langgraph").to_dict()
        adapter = get_official_adapter("langgraph")
        write_case = require_named_eval_result(
            summary,
            adapter.eval_expectations,
            "safe_file_write",
        )
        file_trace = require_eval_trace(
            write_case,
            event_kind="file_access",
            event_operation="write",
        )

        self.assertEqual(file_trace["event_operation"], "write")

    def test_langgraph_review_and_log_only_semantics_match_contract(self) -> None:
        spec = get_langgraph_adapter_spec()
        summary = run_official_adapter_eval_suite("langgraph").to_dict()
        adapter = get_official_adapter("langgraph")

        if spec.supports(AdapterCapability.REVIEW_SEMANTICS):
            review_case = require_named_eval_result(
                summary,
                adapter.eval_expectations,
                "review_required_tool",
            )
            self.assertEqual(review_case["status"], "review_required")
            self.assertEqual(review_case["observed_final_action"], "review")

        if spec.supports(AdapterCapability.LOG_ONLY_SEMANTICS):
            log_only_case = require_named_eval_result(
                summary,
                adapter.eval_expectations,
                "log_only_workflow",
            )
            self.assertEqual(log_only_case["status"], "completed")

            original_actions = [
                item["decision_metadata"].get("original_action")
                for item in log_only_case["audit_trace"]
                if item["action"] == "log"
            ]
            self.assertIn("review", original_actions)
            self.assertIn("block", original_actions)


@unittest.skipUnless(
    OPENAI_AGENTS_AVAILABLE,
    "OpenAI Agents optional dependencies are not installed.",
)
class OpenAIAgentsConformanceTests(unittest.TestCase):
    def test_official_adapter_registry_can_run_openai_agents_eval_suite(self) -> None:
        summary = run_official_adapter_eval_suite("openai_agents")

        self.assertEqual(summary.failed, 0)
        self.assertEqual(summary.total, 9)

    def test_official_adapter_registry_can_validate_openai_agents_conformance(self) -> None:
        report = validate_official_adapter_conformance("openai_agents")

        self.assertTrue(report.ok, msg=report.to_dict())

    def test_official_adapter_registry_can_validate_openai_agents_eval_expectations(self) -> None:
        report = validate_official_adapter_eval_expectations("openai_agents")

        self.assertTrue(report.ok, msg=report.to_dict())

    def test_official_adapter_registry_can_validate_openai_agents_release_gate(self) -> None:
        report = validate_official_adapter_release_gate("openai_agents")

        self.assertTrue(report.ok, msg=report.to_dict())
        self.assertTrue(report.conformance.ok)
        self.assertIsNotNone(report.eval_expectations)
        self.assertTrue(report.eval_expectations.ok)

    def test_openai_agents_eval_summary_passes_reusable_conformance_validator(self) -> None:
        from agentfirewall.evals import run_openai_agents_eval_suite

        spec = get_openai_agents_adapter_spec()
        report = validate_eval_summary(run_openai_agents_eval_suite().to_dict(), spec)

        self.assertTrue(report.ok, msg=report.to_dict())

    def test_official_adapter_record_matches_openai_agents_contract(self) -> None:
        adapter = get_official_adapter("openai_agents")

        self.assertEqual(adapter.spec, get_openai_agents_adapter_spec())
        self.assertTrue(adapter.has_eval_suite())
        self.assertTrue(adapter.has_eval_expectations())
        self.assertEqual(
            adapter.resolve_eval_case_alias("nested_side_effects"),
            "nested_side_effects",
        )

    def test_openai_agents_side_effect_traces_include_required_runtime_context(self) -> None:
        from agentfirewall.evals import run_openai_agents_eval_suite

        spec = get_openai_agents_adapter_spec()
        summary = run_openai_agents_eval_suite()

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

    def test_openai_agents_eval_trace_includes_file_write_event(self) -> None:
        summary = run_official_adapter_eval_suite("openai_agents").to_dict()
        adapter = get_official_adapter("openai_agents")
        workflow_case = require_named_eval_result(
            summary,
            adapter.eval_expectations,
            "nested_side_effects",
        )
        file_trace = require_eval_trace(
            workflow_case,
            event_kind="file_access",
            event_operation="write",
        )

        self.assertEqual(file_trace["event_operation"], "write")

    def test_openai_agents_review_and_log_only_semantics_match_contract(self) -> None:
        spec = get_openai_agents_adapter_spec()
        summary = run_official_adapter_eval_suite("openai_agents").to_dict()
        adapter = get_official_adapter("openai_agents")

        if spec.supports(AdapterCapability.REVIEW_SEMANTICS):
            review_case = require_named_eval_result(
                summary,
                adapter.eval_expectations,
                "shell_review",
            )
            self.assertEqual(review_case["status"], "review_required")
            self.assertEqual(review_case["observed_final_action"], "review")

        if spec.supports(AdapterCapability.LOG_ONLY_SEMANTICS):
            log_only_case = require_named_eval_result(
                summary,
                adapter.eval_expectations,
                "log_only_workflow",
            )
            self.assertEqual(log_only_case["status"], "completed")

            original_actions = [
                item["decision_metadata"].get("original_action")
                for item in log_only_case["audit_trace"]
                if item["action"] == "log"
            ]
            self.assertIn("review", original_actions)
