"""Provider protocol and Anthropic implementation for LLM streaming."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generator, Protocol


@dataclass
class ToolDefinition:
    """A tool available to the model."""

    name: str
    description: str
    input_schema: dict


@dataclass
class ToolCall:
    """A tool call requested by the model."""

    id: str
    name: str
    arguments: dict


@dataclass
class ToolResult:
    """Result of executing a tool call."""

    tool_call_id: str
    content: str
    is_error: bool = False


@dataclass
class StreamEvent:
    """A streaming event from the provider."""

    type: str  # "text" | "tool_call" | "done"
    text: str | None = None
    tool_call: ToolCall | None = None
    stop_reason: str | None = None


class Provider(Protocol):
    """Protocol for LLM providers. Implementations must yield StreamEvents."""

    def stream_completion(
        self,
        system: str,
        messages: list[dict],
        tools: list[ToolDefinition] | None = None,
        max_tokens: int = 16384,
    ) -> Generator[StreamEvent, None, None]: ...


class AnthropicProvider:
    """Anthropic API provider using the official SDK."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        import anthropic

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def stream_completion(
        self,
        system: str,
        messages: list[dict],
        tools: list[ToolDefinition] | None = None,
        max_tokens: int = 16384,
    ) -> Generator[StreamEvent, None, None]:
        kwargs: dict = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.input_schema,
                }
                for t in tools
            ]

        with self.client.messages.stream(**kwargs) as stream:
            for text_chunk in stream.text_stream:
                yield StreamEvent(type="text", text=text_chunk)

            final = stream.get_final_message()
            for block in final.content:
                if block.type == "tool_use":
                    yield StreamEvent(
                        type="tool_call",
                        tool_call=ToolCall(
                            id=block.id,
                            name=block.name,
                            arguments=block.input,
                        ),
                    )
            yield StreamEvent(type="done", stop_reason=final.stop_reason)


class OllamaProvider:
    """Ollama provider using the OpenAI-compatible API."""

    def __init__(self, model: str = "llama3.1", base_url: str = "http://localhost:11434/v1"):
        from openai import OpenAI

        self.client = OpenAI(base_url=base_url, api_key="ollama")
        self.model = model

    @staticmethod
    def _convert_messages(system: str, messages: list[dict]) -> list[dict]:
        """Convert Anthropic-format messages to OpenAI format."""
        import json as _json

        oai_messages: list[dict] = [{"role": "system", "content": system}]
        for msg in messages:
            # Assistant message with tool_use blocks (Anthropic format)
            if msg["role"] == "assistant" and isinstance(msg.get("content"), list):
                tool_calls = []
                text = ""
                for block in msg["content"]:
                    if block.get("type") == "tool_use":
                        tool_calls.append(
                            {
                                "id": block["id"],
                                "type": "function",
                                "function": {
                                    "name": block["name"],
                                    "arguments": _json.dumps(block["input"]),
                                },
                            }
                        )
                    elif block.get("type") == "text":
                        text = block["text"]
                oai_msg: dict = {"role": "assistant", "content": text or None}
                if tool_calls:
                    oai_msg["tool_calls"] = tool_calls
                oai_messages.append(oai_msg)
            # User message with tool_result blocks (Anthropic format)
            elif msg["role"] == "user" and isinstance(msg.get("content"), list):
                for block in msg["content"]:
                    if block.get("type") == "tool_result":
                        oai_messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": block["tool_use_id"],
                                "content": str(block.get("content", "")),
                            }
                        )
            else:
                oai_messages.append(msg)
        return oai_messages

    def stream_completion(
        self,
        system: str,
        messages: list[dict],
        tools: list[ToolDefinition] | None = None,
        max_tokens: int = 16384,
    ) -> Generator[StreamEvent, None, None]:
        oai_messages = self._convert_messages(system, messages)

        kwargs: dict = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": oai_messages,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.input_schema,
                    },
                }
                for t in tools
            ]

        tool_calls_accum: dict[int, dict] = {}
        stop_reason = "stop"

        stream = self.client.chat.completions.create(**kwargs)
        for chunk in stream:
            choice = chunk.choices[0] if chunk.choices else None
            if choice is None:
                continue
            delta = choice.delta

            if delta and delta.content:
                yield StreamEvent(type="text", text=delta.content)

            if delta and delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    if idx not in tool_calls_accum:
                        tool_calls_accum[idx] = {
                            "id": tc_delta.id or "",
                            "name": "",
                            "arguments": "",
                        }
                    if tc_delta.id:
                        tool_calls_accum[idx]["id"] = tc_delta.id
                    if tc_delta.function and tc_delta.function.name:
                        tool_calls_accum[idx]["name"] = tc_delta.function.name
                    if tc_delta.function and tc_delta.function.arguments:
                        tool_calls_accum[idx]["arguments"] += tc_delta.function.arguments

            if choice.finish_reason:
                stop_reason = choice.finish_reason

        import json

        for tc_data in tool_calls_accum.values():
            try:
                args = json.loads(tc_data["arguments"]) if tc_data["arguments"] else {}
            except json.JSONDecodeError:
                args = {}
            yield StreamEvent(
                type="tool_call",
                tool_call=ToolCall(
                    id=tc_data["id"],
                    name=tc_data["name"],
                    arguments=args,
                ),
            )

        yield StreamEvent(type="done", stop_reason=stop_reason)
