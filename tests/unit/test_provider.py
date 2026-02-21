"""Unit tests for telos.provider."""

from unittest.mock import MagicMock

from telos.provider import AnthropicProvider, StreamEvent, ToolCall


class TestAnthropicProviderStreamText:
    """Tests for AnthropicProvider.stream_completion with text responses."""

    def _make_provider(self, mock_client):
        provider = AnthropicProvider.__new__(AnthropicProvider)
        provider.client = mock_client
        provider.model = "claude-sonnet-4-6"
        return provider

    def _make_stream(self, text_chunks, final_content=None, stop_reason="end_turn"):
        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)
        mock_stream.text_stream = iter(text_chunks)
        final = MagicMock()
        final.content = final_content or []
        final.stop_reason = stop_reason
        mock_stream.get_final_message.return_value = final
        return mock_stream

    def test_yields_text_events(self):
        mock_client = MagicMock()
        mock_stream = self._make_stream(["Hello", " world"])
        mock_client.messages.stream.return_value = mock_stream
        provider = self._make_provider(mock_client)

        events = list(
            provider.stream_completion("system", [{"role": "user", "content": "hi"}])
        )

        text_events = [e for e in events if e.type == "text"]
        assert len(text_events) == 2
        assert text_events[0].text == "Hello"
        assert text_events[1].text == " world"

    def test_yields_done_event(self):
        mock_client = MagicMock()
        mock_stream = self._make_stream(["ok"], stop_reason="end_turn")
        mock_client.messages.stream.return_value = mock_stream
        provider = self._make_provider(mock_client)

        events = list(
            provider.stream_completion("sys", [{"role": "user", "content": "hi"}])
        )

        done = [e for e in events if e.type == "done"]
        assert len(done) == 1
        assert done[0].stop_reason == "end_turn"

    def test_passes_model_and_params(self):
        mock_client = MagicMock()
        mock_stream = self._make_stream([])
        mock_client.messages.stream.return_value = mock_stream
        provider = self._make_provider(mock_client)

        list(
            provider.stream_completion(
                "system prompt",
                [{"role": "user", "content": "hello"}],
                max_tokens=1024,
            )
        )

        mock_client.messages.stream.assert_called_once()
        kwargs = mock_client.messages.stream.call_args[1]
        assert kwargs["model"] == "claude-sonnet-4-6"
        assert kwargs["max_tokens"] == 1024
        assert kwargs["system"] == "system prompt"
        assert "tools" not in kwargs


class TestAnthropicProviderStreamToolCalls:
    """Tests for AnthropicProvider.stream_completion with tool_use responses."""

    def _make_provider(self, mock_client):
        provider = AnthropicProvider.__new__(AnthropicProvider)
        provider.client = mock_client
        provider.model = "claude-sonnet-4-6"
        return provider

    def test_yields_tool_call_events(self):
        mock_client = MagicMock()
        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.id = "tool_1"
        tool_block.name = "get_tasks"
        tool_block.input = {"status": "active"}

        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)
        mock_stream.text_stream = iter([])
        final = MagicMock()
        final.content = [tool_block]
        final.stop_reason = "tool_use"
        mock_stream.get_final_message.return_value = final
        mock_client.messages.stream.return_value = mock_stream

        provider = self._make_provider(mock_client)
        from telos.provider import ToolDefinition

        tools = [
            ToolDefinition(
                name="get_tasks",
                description="Get tasks",
                input_schema={"type": "object"},
            )
        ]

        events = list(
            provider.stream_completion(
                "sys", [{"role": "user", "content": "hi"}], tools=tools
            )
        )

        tool_events = [e for e in events if e.type == "tool_call"]
        assert len(tool_events) == 1
        assert tool_events[0].tool_call.name == "get_tasks"
        assert tool_events[0].tool_call.arguments == {"status": "active"}

        done = [e for e in events if e.type == "done"]
        assert done[0].stop_reason == "tool_use"

    def test_tools_converted_to_api_format(self):
        mock_client = MagicMock()
        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)
        mock_stream.text_stream = iter([])
        final = MagicMock()
        final.content = []
        final.stop_reason = "end_turn"
        mock_stream.get_final_message.return_value = final
        mock_client.messages.stream.return_value = mock_stream

        provider = self._make_provider(mock_client)
        from telos.provider import ToolDefinition

        tools = [
            ToolDefinition(
                name="search",
                description="Search items",
                input_schema={"type": "object", "properties": {"q": {"type": "string"}}},
            )
        ]

        list(
            provider.stream_completion(
                "sys", [{"role": "user", "content": "hi"}], tools=tools
            )
        )

        kwargs = mock_client.messages.stream.call_args[1]
        assert "tools" in kwargs
        assert kwargs["tools"][0]["name"] == "search"
        assert kwargs["tools"][0]["description"] == "Search items"
