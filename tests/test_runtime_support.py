import json
from pathlib import Path
import tempfile
import unittest

from agentfirewall.integrations import AdapterCapability, AdapterSupportLevel
from agentfirewall.integrations.openai_agents import get_openai_agents_adapter_spec
from agentfirewall.runtime_support import (
    RuntimeSupportKind,
    collect_preview_runtime_evidence,
    export_preview_runtime_inventory,
    export_runtime_support_manifest,
    export_runtime_support_inventory,
    export_runtime_support_matrix,
    get_generic_preview_runtime_spec,
    get_preview_runtime,
    list_preview_runtimes,
    run_preview_runtime_eval_suite,
    validate_preview_runtime_eval_expectations,
    write_runtime_support_manifest,
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

        self.assertEqual(
            tuple(runtime.name for runtime in runtimes),
            ("generic_wrappers", "openai_agents"),
        )
        names = {item["name"]: item for item in inventory}
        self.assertEqual(set(names), {"generic_wrappers", "openai_agents"})
        self.assertEqual(
            names["generic_wrappers"]["kind"],
            RuntimeSupportKind.PREVIEW_RUNTIME.value,
        )
        self.assertEqual(
            names["openai_agents"]["kind"],
            RuntimeSupportKind.PREVIEW_RUNTIME.value,
        )
        self.assertTrue(names["generic_wrappers"]["has_eval_suite"])
        self.assertTrue(names["openai_agents"]["has_eval_suite"])
        self.assertTrue(names["generic_wrappers"]["has_eval_expectations"])
        self.assertTrue(names["openai_agents"]["has_eval_expectations"])
        self.assertEqual(
            names["generic_wrappers"]["eval_runner"],
            "agentfirewall.evals:run_generic_eval_suite",
        )
        self.assertEqual(
            names["openai_agents"]["eval_runner"],
            "agentfirewall.evals:run_openai_agents_eval_suite",
        )

    def test_combined_runtime_support_inventory_distinguishes_official_and_preview_paths(
        self,
    ) -> None:
        inventory = export_runtime_support_inventory()
        names = {item["name"]: item for item in inventory}

        self.assertEqual(set(names), {"langgraph", "generic_wrappers", "openai_agents"})
        self.assertEqual(
            names["langgraph"]["kind"],
            RuntimeSupportKind.OFFICIAL_ADAPTER.value,
        )
        self.assertEqual(
            names["generic_wrappers"]["kind"],
            RuntimeSupportKind.PREVIEW_RUNTIME.value,
        )
        self.assertEqual(
            names["openai_agents"]["kind"],
            RuntimeSupportKind.PREVIEW_RUNTIME.value,
        )

    def test_combined_runtime_support_matrix_carries_kind_and_capabilities(self) -> None:
        matrix = export_runtime_support_matrix()
        names = {row["name"]: row for row in matrix}

        self.assertEqual(set(names), {"langgraph", "generic_wrappers", "openai_agents"})
        self.assertEqual(names["langgraph"]["kind"], "official_adapter")
        self.assertEqual(names["generic_wrappers"]["kind"], "preview_runtime")
        self.assertEqual(names["openai_agents"]["kind"], "preview_runtime")
        self.assertEqual(names["generic_wrappers"]["prompt_inspection"], "not_supported")
        self.assertEqual(
            names["generic_wrappers"]["tool_call_interception"],
            "supported",
        )
        self.assertEqual(
            names["generic_wrappers"]["runtime_context_correlation"],
            "supported",
        )
        self.assertEqual(names["openai_agents"]["prompt_inspection"], "supported")
        self.assertEqual(names["openai_agents"]["tool_call_interception"], "supported")
        self.assertEqual(
            names["openai_agents"]["shell_enforcement"],
            "not_supported",
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

    def test_openai_preview_runtime_reuses_openai_adapter_spec(self) -> None:
        runtime = get_preview_runtime("openai_agents")

        self.assertEqual(runtime.spec, get_openai_agents_adapter_spec())
        self.assertEqual(runtime.spec.support_level, AdapterSupportLevel.EXPERIMENTAL)
        self.assertTrue(runtime.spec.supports(AdapterCapability.PROMPT_INSPECTION))
        self.assertTrue(runtime.spec.supports(AdapterCapability.TOOL_CALL_INTERCEPTION))
        self.assertTrue(runtime.spec.supports(AdapterCapability.RUNTIME_CONTEXT_CORRELATION))
        self.assertTrue(runtime.spec.supports(AdapterCapability.REVIEW_SEMANTICS))
        self.assertTrue(runtime.spec.supports(AdapterCapability.LOG_ONLY_SEMANTICS))
        self.assertFalse(runtime.spec.supports(AdapterCapability.SHELL_ENFORCEMENT))

    def test_runtime_support_manifest_exports_inventory_matrix_and_preview_evidence(self) -> None:
        manifest = export_runtime_support_manifest(include_evidence=True)

        self.assertEqual(manifest["schema_version"], 1)
        self.assertIn("generated_at", manifest)
        inventory = {item["name"]: item for item in manifest["inventory"]}
        self.assertEqual(
            set(inventory),
            {"langgraph", "generic_wrappers", "openai_agents"},
        )
        matrix = {item["name"]: item for item in manifest["matrix"]}
        self.assertEqual(
            set(matrix),
            {"langgraph", "generic_wrappers", "openai_agents"},
        )
        evidence = manifest["evidence"]
        preview = {item["name"]: item for item in evidence["preview_runtimes"]}
        self.assertIn("generic_wrappers", preview)
        self.assertIn("openai_agents", preview)
        self.assertTrue(preview["generic_wrappers"]["evaluated"])
        self.assertTrue(preview["generic_wrappers"]["ok"])
        self.assertEqual(preview["generic_wrappers"]["summary"]["total"], 7)
        self.assertIn("named_cases", preview["generic_wrappers"]["summary"])
        self.assertEqual(
            preview["generic_wrappers"]["summary"]["named_cases"]["blocked_http"]["status"],
            "blocked",
        )
        self.assertIn("conformance", preview["generic_wrappers"])
        self.assertIn("eval_expectations", preview["generic_wrappers"])

    def test_collect_preview_runtime_evidence_returns_openai_summary_when_available(self) -> None:
        evidence = collect_preview_runtime_evidence("openai_agents")

        self.assertEqual(evidence["name"], "openai_agents")
        self.assertEqual(
            evidence["kind"],
            RuntimeSupportKind.PREVIEW_RUNTIME.value,
        )
        if evidence["evaluated"]:
            self.assertTrue(evidence["ok"])
            self.assertEqual(evidence["summary"]["total"], 9)
            self.assertEqual(
                evidence["summary"]["status_counts"]["review_required"],
                2,
            )
            self.assertEqual(
                evidence["summary"]["named_cases"]["prompt_review"]["status"],
                "review_required",
            )
        else:
            self.assertIn("error", evidence)

    def test_write_runtime_support_manifest_writes_json_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "runtime-support.json"

            written = write_runtime_support_manifest(path, include_evidence=False)

            self.assertEqual(written, path)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], 1)
            self.assertIn("inventory", payload)
            self.assertIn("matrix", payload)
