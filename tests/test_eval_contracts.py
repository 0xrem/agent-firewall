import unittest

from agentfirewall.evals import (
    EvalSuiteExpectations,
    require_eval_trace,
    require_named_eval_result,
    validate_eval_summary_against_expectations,
)


class EvalContractTests(unittest.TestCase):
    def test_validate_eval_summary_against_expectations_accepts_matching_payload(self) -> None:
        expectations = EvalSuiteExpectations(
            total=1,
            status_counts={"completed": 1},
            task_counts={"operations_check": 1},
            named_cases={"safe_status_tool": "safe_status_tool"},
        )
        payload = {
            "total": 1,
            "failed": 0,
            "unexpected_allows": 0,
            "unexpected_blocks": 0,
            "unexpected_reviews": 0,
            "status_counts": {"completed": 1},
            "task_counts": {"operations_check": 1},
            "results": [
                {
                    "name": "safe_status_tool",
                    "audit_trace": [
                        {
                            "event_kind": "prompt",
                            "event_operation": "inspect",
                            "action": "allow",
                        }
                    ],
                }
            ],
        }

        report = validate_eval_summary_against_expectations(payload, expectations)

        self.assertTrue(report.ok, msg=report.to_dict())

    def test_validate_eval_summary_against_expectations_reports_mismatches(self) -> None:
        expectations = EvalSuiteExpectations(
            total=2,
            status_counts={"completed": 2},
            named_cases={"safe_status_tool": "safe_status_tool"},
        )
        payload = {
            "total": 1,
            "failed": 1,
            "unexpected_allows": 1,
            "unexpected_blocks": 0,
            "unexpected_reviews": 0,
            "status_counts": {"completed": 1},
            "task_counts": {},
            "results": [],
        }

        report = validate_eval_summary_against_expectations(payload, expectations)

        self.assertFalse(report.ok)
        self.assertTrue(any(issue.check == "total" for issue in report.issues))
        self.assertTrue(any(issue.check == "failed" for issue in report.issues))
        self.assertTrue(any(issue.check == "named_cases" for issue in report.issues))

    def test_named_result_and_trace_helpers_resolve_aliases(self) -> None:
        expectations = EvalSuiteExpectations(
            total=1,
            named_cases={"safe_file_write": "guarded_file_write_allows_safe_path"},
        )
        payload = {
            "results": [
                {
                    "name": "guarded_file_write_allows_safe_path",
                    "audit_trace": [
                        {
                            "event_kind": "file_access",
                            "event_operation": "write",
                            "action": "allow",
                        }
                    ],
                }
            ],
        }

        result = require_named_eval_result(payload, expectations, "safe_file_write")
        trace = require_eval_trace(
            result,
            event_kind="file_access",
            event_operation="write",
        )

        self.assertEqual(result["name"], "guarded_file_write_allows_safe_path")
        self.assertEqual(trace["action"], "allow")
