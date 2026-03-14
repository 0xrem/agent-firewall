import unittest

from agentfirewall.integrations import AdapterCapability, AdapterSupportLevel
from agentfirewall.runtime_support import (
    RuntimeSupportKind,
    export_preview_runtime_inventory,
    export_runtime_support_inventory,
    export_runtime_support_matrix,
    get_generic_preview_runtime_spec,
    get_preview_runtime,
    list_preview_runtimes,
    run_preview_runtime_eval_suite,
    validate_preview_runtime_eval_expectations,
)


class RuntimeSupportInventoryTests(unittest.TestCase):
    def test_generic_preview_runtime_declares_experimental_support_contract(self) -> None:
        spec = get_generic_preview_runtime_spec()

        self.assertEqual(spec.name, "generic_wrappers")
        self.assertEqual(spec.module, "agentfirewall.generic")
        self.assertEqual(spec.support_level, AdapterSupportLevel.EXPERIMENTAL)
        self.assertFalse(spec.supports(AdapterCapability.PROMPT_INSPECTION))
        self.assertTrue(spec.supports(AdapterCapability.TOOL_CALL_INTERCEPTION))
        self.assertTrue(spec.supports(AdapterCapability.SHELL_ENFORCEMENT))
        self.assertTrue(spec.supports(AdapterCapability.FILE_READ_ENFORCEMENT))
        self.assertTrue(spec.supports(AdapterCapability.FILE_WRITE_ENFORCEMENT))
        self.assertTrue(spec.supports(AdapterCapability.HTTP_ENFORCEMENT))
        self.assertTrue(spec.supports(AdapterCapability.RUNTIME_CONTEXT_CORRELATION))
        self.assertTrue(spec.supports(AdapterCapability.REVIEW_SEMANTICS))
        self.assertTrue(spec.supports(AdapterCapability.LOG_ONLY_SEMANTICS))

    def test_preview_runtime_inventory_exports_eval_evidence(self) -> None:
        runtimes = list_preview_runtimes()
        inventory = export_preview_runtime_inventory()

        self.assertEqual(tuple(runtime.name for runtime in runtimes), ("generic_wrappers",))
        self.assertEqual(len(inventory), 1)
        self.assertEqual(inventory[0]["name"], "generic_wrappers")
        self.assertEqual(inventory[0]["kind"], RuntimeSupportKind.PREVIEW_RUNTIME.value)
        self.assertTrue(inventory[0]["has_eval_suite"])
        self.assertTrue(inventory[0]["has_eval_expectations"])
        self.assertEqual(
            inventory[0]["eval_runner"],
            "agentfirewall.evals:run_generic_eval_suite",
        )

    def test_combined_runtime_support_inventory_distinguishes_official_and_preview_paths(
        self,
    ) -> None:
        inventory = export_runtime_support_inventory()
        names = {item["name"]: item for item in inventory}

        self.assertEqual(set(names), {"langgraph", "generic_wrappers"})
        self.assertEqual(
            names["langgraph"]["kind"],
            RuntimeSupportKind.OFFICIAL_ADAPTER.value,
        )
        self.assertEqual(
            names["generic_wrappers"]["kind"],
            RuntimeSupportKind.PREVIEW_RUNTIME.value,
        )

    def test_combined_runtime_support_matrix_carries_kind_and_capabilities(self) -> None:
        matrix = export_runtime_support_matrix()
        names = {row["name"]: row for row in matrix}

        self.assertEqual(set(names), {"langgraph", "generic_wrappers"})
        self.assertEqual(names["langgraph"]["kind"], "official_adapter")
        self.assertEqual(names["generic_wrappers"]["kind"], "preview_runtime")
        self.assertEqual(names["generic_wrappers"]["prompt_inspection"], "not_supported")
        self.assertEqual(
            names["generic_wrappers"]["tool_call_interception"],
            "supported",
        )
        self.assertEqual(
            names["generic_wrappers"]["runtime_context_correlation"],
            "supported",
        )

    def test_preview_runtime_registry_can_run_generic_eval_suite(self) -> None:
        summary = run_preview_runtime_eval_suite("generic_wrappers")

        self.assertEqual(summary.failed, 0)
        self.assertEqual(summary.total, 7)

    def test_preview_runtime_registry_validates_generic_eval_expectations(self) -> None:
        report = validate_preview_runtime_eval_expectations("generic_wrappers")

        self.assertTrue(report.ok, msg=report.to_dict())

    def test_preview_runtime_record_exposes_named_eval_aliases(self) -> None:
        runtime = get_preview_runtime("generic_wrappers")

        self.assertEqual(runtime.spec, get_generic_preview_runtime_spec())
        self.assertTrue(runtime.has_eval_suite())
        self.assertTrue(runtime.has_eval_expectations())
        self.assertEqual(
            runtime.eval_expectations.case_name("blocked_http"),
            "guarded_http_blocks_untrusted_host",
        )
