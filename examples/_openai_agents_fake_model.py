"""Local fake-model helpers for offline OpenAI Agents examples."""

from __future__ import annotations

import json

from agents.items import ModelResponse
from agents.models.interface import Model
from agents.usage import Usage
from openai.types.responses import (
    ResponseFunctionToolCall,
    ResponseOutputMessage,
    ResponseOutputText,
)


class SequentialFakeModel(Model):
    """Return a fixed sequence of responses for local examples."""

    def __init__(self, outputs: list[ModelResponse]) -> None:
        self.outputs = list(outputs)
        self.calls = 0

    async def get_response(
        self,
        system_instructions,
        input,
        model_settings,
        tools,
        output_schema,
        handoffs,
        tracing,
        *,
        previous_response_id,
        conversation_id,
        prompt,
    ):
        output = self.outputs[self.calls]
        self.calls += 1
        return output

    def stream_response(self, *args, **kwargs):
        raise NotImplementedError


def tool_call_output(*, call_id: str, name: str, arguments: dict[str, object]) -> ModelResponse:
    return ModelResponse(
        output=[
            ResponseFunctionToolCall(
                arguments=json.dumps(arguments),
                call_id=call_id,
                name=name,
                type="function_call",
            )
        ],
        usage=Usage(),
        response_id=f"resp_{call_id}",
    )


def final_text_output(text: str) -> ModelResponse:
    return ModelResponse(
        output=[
            ResponseOutputMessage(
                id="msg_final",
                content=[
                    ResponseOutputText(
                        annotations=[],
                        text=text,
                        type="output_text",
                    )
                ],
                role="assistant",
                status="completed",
                type="message",
            )
        ],
        usage=Usage(),
        response_id="resp_final",
    )


def build_fake_model(
    *,
    tool_calls: list[dict[str, object]] | None = None,
    final_text: str = "done",
) -> SequentialFakeModel:
    outputs = [
        tool_call_output(
            call_id=str(tool_call["id"]),
            name=str(tool_call["name"]),
            arguments=dict(tool_call.get("args", {})),
        )
        for tool_call in (tool_calls or [])
    ]
    outputs.append(final_text_output(final_text))
    return SequentialFakeModel(outputs)
