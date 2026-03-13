from types import SimpleNamespace
import unittest

from agentfirewall.integrations.langgraph import LangGraphEventTranslator
from agentfirewall.runtime_context import current_runtime_context


class LangGraphEventTranslatorTests(unittest.TestCase):
    def test_prompt_event_extracts_latest_user_message(self) -> None:
        translator = LangGraphEventTranslator(source="langgraph")
        state = {
            "messages": [
                SimpleNamespace(type="assistant", content="How can I help?"),
                SimpleNamespace(
                    type="human",
                    content=[
                        {"text": "Check repository status"},
                    ],
                ),
            ],
        }

        event = translator.prompt_event(state)

        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.kind.value, "prompt")
        self.assertEqual(event.operation, "inspect")
        self.assertEqual(event.payload["text"], "Check repository status")
        self.assertEqual(event.source, "langgraph.prompt")

    def test_prompt_event_returns_none_without_latest_user_text(self) -> None:
        translator = LangGraphEventTranslator(source="langgraph")
        state = {
            "messages": [
                SimpleNamespace(type="assistant", content="Still thinking"),
            ],
        }

        event = translator.prompt_event(state)

        self.assertIsNone(event)

    def test_tool_event_normalizes_tool_payload_and_call_id(self) -> None:
        translator = LangGraphEventTranslator(source="langgraph")

        event = translator.tool_event(
            {
                "name": "shell",
                "id": "call_123",
                "args": {"command": "ls -la"},
            }
        )

        self.assertEqual(event.kind.value, "tool_call")
        self.assertEqual(event.operation, "dispatch")
        self.assertEqual(event.payload["name"], "shell")
        self.assertEqual(event.payload["kwargs"]["command"], "ls -la")
        self.assertEqual(event.payload["arguments"]["command"], "ls -la")
        self.assertEqual(event.payload["tool_call_id"], "call_123")
        self.assertEqual(event.source, "langgraph.tool")

    def test_tool_runtime_metadata_uses_shared_contract_fields(self) -> None:
        translator = LangGraphEventTranslator(source="langgraph")

        metadata = translator.tool_runtime_metadata(
            {
                "name": "http_request",
                "id": "call_http_1",
            }
        )

        self.assertEqual(
            metadata,
            {
                "runtime": "langgraph",
                "tool_name": "http_request",
                "tool_call_id": "call_http_1",
                "tool_event_source": "langgraph.tool",
            },
        )

    def test_tool_execution_context_applies_and_resets_runtime_context(self) -> None:
        translator = LangGraphEventTranslator(source="langgraph")

        self.assertEqual(current_runtime_context(), {})
        with translator.tool_execution_context({"name": "shell", "id": "call_shell_1"}):
            self.assertEqual(
                current_runtime_context(),
                {
                    "runtime": "langgraph",
                    "tool_name": "shell",
                    "tool_call_id": "call_shell_1",
                    "tool_event_source": "langgraph.tool",
                },
            )
        self.assertEqual(current_runtime_context(), {})

    def test_tool_execution_context_is_noop_without_tool_name_or_call_id(self) -> None:
        translator = LangGraphEventTranslator(source="langgraph")

        with translator.tool_execution_context({}):
            self.assertEqual(current_runtime_context(), {})
