"""Unit tests for telos.executor."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from telos.executor import (
    BUILTIN_TOOLS,
    _build_prompt,
    _execute_builtin_tool,
    execute_skill,
    load_env,
    resolve_working_dir,
)
from telos.provider import StreamEvent


class TestBuildPrompt:
    """Tests for _build_prompt."""

    def test_basic_prompt(self):
        result = _build_prompt("# Kickoff\nDo the thing")
        assert result.startswith("# Kickoff\nDo the thing")
        assert "Current date/time:" in result

    def test_preserves_multiline_body(self):
        body = "# Kickoff\n\nLine 1\nLine 2\nLine 3"
        result = _build_prompt(body)
        assert result.startswith(body)

    def test_appends_user_request(self):
        result = _build_prompt("# Skill body", user_request="write a note about the meeting")
        assert "User request: write a note about the meeting" in result
        assert result.startswith("# Skill body")

    def test_no_user_request_omits_section(self):
        result = _build_prompt("# Skill body")
        assert "User request" not in result

    def test_includes_timestamp(self):
        result = _build_prompt("# Skill body")
        assert "Current date/time:" in result


class TestLoadEnv:
    """Tests for load_env."""

    def test_loads_key_value_pairs(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("CLICKUP_API_KEY=xxxx\nOTHER_KEY=yyyy\n")
        result = load_env(env_file)
        assert result["CLICKUP_API_KEY"] == "xxxx"
        assert result["OTHER_KEY"] == "yyyy"

    def test_ignores_comments(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("# This is a comment\nKEY=value\n")
        result = load_env(env_file)
        assert "# This is a comment" not in result
        assert result["KEY"] == "value"

    def test_ignores_empty_lines(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("KEY1=val1\n\n\nKEY2=val2\n")
        result = load_env(env_file)
        assert result["KEY1"] == "val1"
        assert result["KEY2"] == "val2"

    def test_strips_quotes(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text('KEY1="quoted"\nKEY2=\'single\'\n')
        result = load_env(env_file)
        assert result["KEY1"] == "quoted"
        assert result["KEY2"] == "single"

    def test_merges_with_os_environ(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("CUSTOM_KEY=custom_value\n")
        result = load_env(env_file)
        # Should contain the .env values
        assert result["CUSTOM_KEY"] == "custom_value"
        # Should also contain inherited os.environ values
        assert "PATH" in result

    def test_missing_env_file_returns_os_environ(self, tmp_path):
        result = load_env(tmp_path / "nonexistent.env")
        assert "PATH" in result
        assert result == dict(os.environ)

    def test_env_file_overrides_os_environ(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MY_VAR", "original")
        env_file = tmp_path / ".env"
        env_file.write_text("MY_VAR=overridden\n")
        result = load_env(env_file)
        assert result["MY_VAR"] == "overridden"


class TestResolveWorkingDir:
    """Tests for resolve_working_dir."""

    def test_dot_resolves_to_cwd(self):
        result = resolve_working_dir(Path("."))
        assert result == Path.cwd()

    def test_absolute_path_unchanged(self, tmp_path):
        result = resolve_working_dir(tmp_path)
        assert result == tmp_path

    def test_tilde_expansion(self):
        result = resolve_working_dir(Path("~/Documents"))
        assert "~" not in str(result)
        assert result == Path.home() / "Documents"


class TestBuiltinTools:
    """Tests for _execute_builtin_tool."""

    def test_write_file_creates_file(self, tmp_path):
        result = _execute_builtin_tool(
            "write_file", {"path": "test.md", "content": "hello"}, tmp_path
        )
        assert not result.is_error
        assert (tmp_path / "test.md").read_text() == "hello"

    def test_write_file_creates_parent_dirs(self, tmp_path):
        result = _execute_builtin_tool(
            "write_file",
            {"path": "sub/dir/test.md", "content": "nested"},
            tmp_path,
        )
        assert not result.is_error
        assert (tmp_path / "sub/dir/test.md").read_text() == "nested"

    def test_read_file(self, tmp_path):
        (tmp_path / "data.txt").write_text("file content")
        result = _execute_builtin_tool("read_file", {"path": "data.txt"}, tmp_path)
        assert not result.is_error
        assert result.content == "file content"

    def test_read_file_not_found(self, tmp_path):
        result = _execute_builtin_tool("read_file", {"path": "missing.txt"}, tmp_path)
        assert result.is_error

    def test_list_directory(self, tmp_path):
        (tmp_path / "a.txt").touch()
        (tmp_path / "b.txt").touch()
        result = _execute_builtin_tool("list_directory", {"path": "."}, tmp_path)
        assert not result.is_error
        assert "a.txt" in result.content
        assert "b.txt" in result.content

    def test_unknown_tool(self, tmp_path):
        result = _execute_builtin_tool("nope", {}, tmp_path)
        assert result.is_error
        assert "Unknown tool" in result.content

    def test_builtin_tools_list(self):
        assert len(BUILTIN_TOOLS) == 4
        names = {t.name for t in BUILTIN_TOOLS}
        assert names == {"write_file", "read_file", "list_directory", "fetch_url"}


class TestExecuteSkill:
    """Tests for execute_skill with mocked provider."""

    @patch("telos.executor._create_provider")
    def test_streams_text_to_stdout(self, mock_create, tmp_path, capsys, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        mock_provider = MagicMock()
        mock_provider.stream_completion.return_value = iter(
            [
                StreamEvent(type="text", text="Hello"),
                StreamEvent(type="text", text=" world"),
                StreamEvent(type="done", stop_reason="end_turn"),
            ]
        )
        mock_create.return_value = mock_provider

        execute_skill("# Kickoff\nDo the thing", working_dir=tmp_path)

        captured = capsys.readouterr()
        assert "Hello world" in captured.out

    @patch("telos.executor._create_provider")
    def test_provider_receives_builtin_tools(self, mock_create, tmp_path, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        mock_provider = MagicMock()
        mock_provider.stream_completion.return_value = iter(
            [StreamEvent(type="done", stop_reason="end_turn")]
        )
        mock_create.return_value = mock_provider

        execute_skill("body", working_dir=tmp_path)

        call_args = mock_provider.stream_completion.call_args
        tools_arg = call_args[1].get("tools") or (call_args[0][2] if len(call_args[0]) > 2 else None)
        assert tools_arg is not None
        assert len(tools_arg) == 4

    @patch("telos.executor._create_provider")
    def test_provider_called_with_prompt(self, mock_create, tmp_path, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        mock_provider = MagicMock()
        mock_provider.stream_completion.return_value = iter(
            [StreamEvent(type="done", stop_reason="end_turn")]
        )
        mock_create.return_value = mock_provider

        execute_skill(
            "# Skill body",
            working_dir=tmp_path,
            user_request="do something",
        )

        mock_provider.stream_completion.assert_called_once()
        call_args = mock_provider.stream_completion.call_args
        messages = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("messages")
        prompt = messages[0]["content"]
        assert "# Skill body" in prompt
        assert "User request: do something" in prompt

    @patch("telos.executor._create_provider")
    def test_env_passed_to_provider(self, mock_create, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("ANTHROPIC_API_KEY=test-key\nCUSTOM=value\n")
        mock_provider = MagicMock()
        mock_provider.stream_completion.return_value = iter(
            [StreamEvent(type="done", stop_reason="end_turn")]
        )
        mock_create.return_value = mock_provider

        execute_skill("body", working_dir=tmp_path, env_path=env_file)

        mock_create.assert_called_once()
        env_arg = mock_create.call_args[0][0]
        assert env_arg["CUSTOM"] == "value"

    def test_missing_api_key_raises_exit(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        env_file = tmp_path / ".env"
        env_file.write_text("OTHER_KEY=value\n")

        with pytest.raises(SystemExit):
            execute_skill("body", working_dir=tmp_path, env_path=env_file)
