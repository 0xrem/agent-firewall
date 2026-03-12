import importlib.util
import unittest


LANGGRAPH_AVAILABLE = bool(importlib.util.find_spec("langchain")) and bool(
    importlib.util.find_spec("langgraph")
)


@unittest.skipUnless(LANGGRAPH_AVAILABLE, "LangGraph optional dependencies are not installed.")
class LangGraphEvalTests(unittest.TestCase):
    def test_default_langgraph_eval_suite_passes(self) -> None:
        from agentfirewall.evals import run_langgraph_eval_suite

        summary = run_langgraph_eval_suite()

        self.assertEqual(summary.failed, 0)
        self.assertEqual(summary.total, 6)
        self.assertEqual(summary.status_counts["completed"], 2)
        self.assertEqual(summary.status_counts["blocked"], 2)
        self.assertEqual(summary.status_counts["review_required"], 2)

    def test_langgraph_eval_summary_is_json_friendly(self) -> None:
        from agentfirewall.evals import run_langgraph_eval_suite

        summary = run_langgraph_eval_suite()
        payload = summary.to_dict()

        self.assertEqual(payload["failed"], 0)
        self.assertEqual(payload["unexpected_allows"], 0)
        self.assertEqual(payload["unexpected_blocks"], 0)
        self.assertEqual(payload["results"][0]["name"], "safe_status_tool")
        self.assertIn("observed_actions", payload["results"][0])
