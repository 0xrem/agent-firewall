import json
from pathlib import Path
import tempfile
import unittest

from agentfirewall.integrations import AdapterCapability, AdapterSupportLevel
from agentfirewall.runtime_support import (
    RuntimeSupportKind,
    collect_official_adapter_evidence,
    collect_preview_runtime_evidence,
    export_preview_runtime_inventory,
    export_runtime_support_manifest,
    export_runtime_support_inventory,
    export_runtime_support_matrix,
    get_generic_preview_runtime_spec,
    get_mcp_client_preview_runtime_spec,
    get_mcp_server_preview_runtime_spec,
    get_openai_agents_preview_runtime_spec,
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
        self.assertFalse(spec.supports(AdapterCapability.RESOURCE_READ_INTERCEPTION))
        self.assertTrue(spec.supports(AdapterCapability.RUNTIME_CONTEXT_CORRELATION))
        self.assertTrue(spec.supports(AdapterCapability.REVIEW_SEMANTICS))
        self.assertTrue(spec.supports(AdapterCapability.LOG_ONLY_SEMANTICS))

    def test_mcp_preview_runtimes_declare_resource_interception_as_preview_only(self) -> None:
        client = get_mcp_client_preview_runtime_spec()
        server = get_mcp_server_preview_runtime_spec()

        self.assertEqual(client.support_level, AdapterSupportLevel.EXPERIMENTAL)
        self.assertEqual(server.support_level, AdapterSupportLevel.EXPERIMENTAL)
        self.assertTrue(client.supports(AdapterCapability.RESOURCE_READ_INTERCEPTION))
        self.assertTrue(server.supports(AdapterCapability.RESOURCE_READ_INTERCEPTION))
        self.assertFalse(client.supports(AdapterCapability.PROMPT_INSPECTION))
        self.assertFalse(server.supports(AdapterCapability.PROMPT_INSPECTION))

    def test_preview_runtime_inventory_exports_eval_evidence(self) -> None:
        runtimes = list_preview_runtimes()
        inventory = export_preview_runtime_inventory()

        self.assertEqual(
            tuple(runtime.name for runtime in runtimes),
            ("generic_wrappers", "mcp_client", "mcp_server"),
        )
        names = {item["name"]: item for item in inventory}
        self.assertEqual(set(names), {"generic_wrappers", "mcp_client", "mcp_server"})
        self.assertEqual(
            names["generic_wrappers"]["kind"],
            RuntimeSupportKind.PREVIEW_RUNTIME.value,
        )
        self.assertTrue(names["generic_wrappers"]["has_eval_suite"])
        self.assertTrue(names["generic_wrappers"]["has_eval_expectations"])
        self.assertEqual(
            names["generic_wrappers"]["eval_runner"],
            "agentfirewall.evals:run_generic_eval_suite",
        )
        self.assertEqual(
            names["mcp_client"]["eval_runner"],
            "agentfirewall.evals:run_mcp_client_eval_suite",
        )
        self.assertEqual(
            names["mcp_server"]["eval_runner"],
            "agentfirewall.evals:run_mcp_server_eval_suite",
        )

    def test_combined_runtime_support_inventory_distinguishes_official_and_preview_paths(
        self,
    ) -> None:
        inventory = export_runtime_support_inventory()
        names = {item["name"]: item for item in inventory}

        self.assertEqual(
            set(names),
            {"langgraph", "generic_wrappers", "mcp_client", "mcp_server", "openai_agents"},
        )
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
            RuntimeSupportKind.OFFICIAL_ADAPTER.value,
        )

    def test_combined_runtime_support_matrix_carries_kind_and_capabilities(self) -> None:
        matrix = export_runtime_support_matrix()
        names = {row["name"]: row for row in matrix}

        self.assertEqual(
            set(names),
            {"langgraph", "generic_wrappers", "mcp_client", "mcp_server", "openai_agents"},
        )
        self.assertEqual(names["langgraph"]["kind"], "official_adapter")
        self.assertEqual(names["generic_wrappers"]["kind"], "preview_runtime")
        self.assertEqual(names["mcp_client"]["kind"], "preview_runtime")
        self.assertEqual(names["mcp_server"]["kind"], "preview_runtime")
        self.assertEqual(names["openai_agents"]["kind"], "official_adapter")
        self.assertEqual(names["generic_wrappers"]["prompt_inspection"], "not_supported")
        self.assertEqual(
            names["generic_wrappers"]["tool_call_interception"],
            "supported",
        )
        self.assertEqual(
            names["generic_wrappers"]["resource_read_interception"],
            "not_supported",
        )
        self.assertEqual(
            names["mcp_client"]["resource_read_interception"],
            "supported",
        )
        self.assertEqual(
            names["mcp_server"]["resource_read_interception"],
            "supported",
        )
        self.assertEqual(
            names["generic_wrappers"]["runtime_context_correlation"],
            "supported",
        )
        self.assertEqual(names["openai_agents"]["prompt_inspection"], "supported")
        self.assertEqual(names["openai_agents"]["tool_call_interception"], "supported")
        self.assertEqual(
            names["openai_agents"]["resource_read_interception"],
            "not_supported",
        )
        self.assertEqual(
            names["openai_agents"]["shell_enforcement"],
            "supported",
        )
        self.assertEqual(names["openai_agents"]["file_read_enforcement"], "supported")
        self.assertEqual(names["openai_agents"]["file_write_enforcement"], "supported")
        self.assertEqual(names["openai_agents"]["http_enforcement"], "supported")

    def test_preview_runtime_registry_can_run_generic_eval_suite(self) -> None:
        summary = run_preview_runtime_eval_suite("generic_wrappers")

        self.assertEqual(summary.failed, 0)
        self.assertEqual(summary.total, 9)

    def test_preview_runtime_registry_can_run_mcp_preview_eval_suites(self) -> None:
        client = run_preview_runtime_eval_suite("mcp_client")
        server = run_preview_runtime_eval_suite("mcp_server")

        self.assertEqual(client.failed, 0)
        self.assertEqual(client.total, 8)
        self.assertEqual(server.failed, 0)
        self.assertEqual(server.total, 6)

    def test_preview_runtime_registry_validates_generic_eval_expectations(self) -> None:
        report = validate_preview_runtime_eval_expectations("generic_wrappers")

        self.assertTrue(report.ok, msg=report.to_dict())

    def test_preview_runtime_registry_validates_mcp_eval_expectations(self) -> None:
        self.assertTrue(
            validate_preview_runtime_eval_expectations("mcp_client").ok
        )
        self.assertTrue(
            validate_preview_runtime_eval_expectations("mcp_server").ok
        )

    def test_preview_runtime_record_exposes_named_eval_aliases(self) -> None:
        runtime = get_preview_runtime("generic_wrappers")

        self.assertEqual(runtime.spec, get_generic_preview_runtime_spec())
        self.assertTrue(runtime.has_eval_suite())
        self.assertTrue(runtime.has_eval_expectations())
        self.assertEqual(
            runtime.eval_expectations.case_name("blocked_http"),
            "guarded_http_blocks_untrusted_host",
        )

    def test_openai_agents_support_contract_is_kept_as_compatibility_shim(self) -> None:
        spec = get_openai_agents_preview_runtime_spec()

        self.assertEqual(spec.name, "openai_agents")
        self.assertEqual(spec.support_level, AdapterSupportLevel.SUPPORTED)
        self.assertTrue(spec.supports(AdapterCapability.PROMPT_INSPECTION))
        self.assertTrue(spec.supports(AdapterCapability.TOOL_CALL_INTERCEPTION))
        self.assertTrue(spec.supports(AdapterCapability.SHELL_ENFORCEMENT))
        self.assertTrue(spec.supports(AdapterCapability.FILE_READ_ENFORCEMENT))
        self.assertTrue(spec.supports(AdapterCapability.FILE_WRITE_ENFORCEMENT))
        self.assertTrue(spec.supports(AdapterCapability.HTTP_ENFORCEMENT))
        self.assertFalse(spec.supports(AdapterCapability.RESOURCE_READ_INTERCEPTION))
        self.assertTrue(spec.supports(AdapterCapability.RUNTIME_CONTEXT_CORRELATION))
        self.assertTrue(spec.supports(AdapterCapability.REVIEW_SEMANTICS))
        self.assertTrue(spec.supports(AdapterCapability.LOG_ONLY_SEMANTICS))

    def test_openai_agents_is_no_longer_listed_as_preview_runtime(self) -> None:
        with self.assertRaises(KeyError):
            get_preview_runtime("openai_agents")

    def test_runtime_support_manifest_exports_inventory_matrix_and_preview_evidence(self) -> None:
        manifest = export_runtime_support_manifest(include_evidence=True)

        self.assertEqual(manifest["schema_version"], 1)
        self.assertIn("generated_at", manifest)
        inventory = {item["name"]: item for item in manifest["inventory"]}
        self.assertEqual(
            set(inventory),
            {"langgraph", "generic_wrappers", "mcp_client", "mcp_server", "openai_agents"},
        )
        matrix = {item["name"]: item for item in manifest["matrix"]}
        self.assertEqual(
            set(matrix),
            {"langgraph", "generic_wrappers", "mcp_client", "mcp_server", "openai_agents"},
        )
        evidence = manifest["evidence"]
        official = {item["name"]: item for item in evidence["official_adapters"]}
        self.assertEqual(set(official), {"langgraph", "openai_agents"})
        preview = {item["name"]: item for item in evidence["preview_runtimes"]}
        self.assertIn("generic_wrappers", preview)
        self.assertIn("mcp_client", preview)
        self.assertIn("mcp_server", preview)
        self.assertTrue(preview["generic_wrappers"]["evaluated"])
        self.assertTrue(preview["generic_wrappers"]["ok"])
        self.assertEqual(preview["generic_wrappers"]["summary"]["total"], 9)
        self.assertEqual(preview["mcp_client"]["summary"]["total"], 8)
        self.assertEqual(preview["mcp_server"]["summary"]["total"], 6)
        self.assertIn("named_cases", preview["generic_wrappers"]["summary"])
        self.assertEqual(
            preview["generic_wrappers"]["summary"]["named_cases"]["blocked_http"]["status"],
            "blocked",
        )
        self.assertIn("conformance", preview["generic_wrappers"])
        self.assertIn("eval_expectations", preview["generic_wrappers"])

    def test_collect_official_adapter_evidence_returns_openai_summary_when_available(self) -> None:
        evidence = collect_official_adapter_evidence("openai_agents")

        self.assertEqual(evidence["name"], "openai_agents")
        self.assertEqual(
            evidence["kind"],
            RuntimeSupportKind.OFFICIAL_ADAPTER.value,
        )
        if evidence["evaluated"]:
            self.assertTrue(evidence["ok"])
            self.assertEqual(evidence["summary"]["total"], 11)
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
