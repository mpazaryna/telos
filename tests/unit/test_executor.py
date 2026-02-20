"""Unit tests for telos.executor."""

import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from telos.executor import build_command, load_env, resolve_working_dir, execute_skill


class TestBuildCommand:
    """Tests for build_command."""

    def test_builds_claude_command(self):
        cmd = build_command("# Kickoff\nDo the thing")
        assert cmd == ["claude", "-p", "# Kickoff\nDo the thing"]

    def test_preserves_multiline_body(self):
        body = "# Kickoff\n\nLine 1\nLine 2\nLine 3"
        cmd = build_command(body)
        assert cmd[2] == body

    def test_appends_user_request(self):
        cmd = build_command("# Skill body", user_request="write a note about the meeting")
        assert "User request: write a note about the meeting" in cmd[2]
        assert cmd[2].startswith("# Skill body")

    def test_no_user_request_omits_section(self):
        cmd = build_command("# Skill body")
        assert "User request" not in cmd[2]


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


class TestExecuteSkill:
    """Tests for execute_skill."""

    @patch("telos.executor.subprocess.run")
    def test_subprocess_called_with_correct_args(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0)
        execute_skill("# Kickoff\nDo the thing", working_dir=tmp_path)
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["claude", "-p", "# Kickoff\nDo the thing"]
        assert call_args[1]["cwd"] == tmp_path

    @patch("telos.executor.subprocess.run")
    def test_inherits_stdio(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0)
        execute_skill("body", working_dir=tmp_path)
        call_kwargs = mock_run.call_args[1]
        # Should NOT have capture_output=True
        assert call_kwargs.get("capture_output") is not True

    @patch("telos.executor.subprocess.run")
    def test_claude_not_found_raises_error(self, mock_run, tmp_path):
        mock_run.side_effect = FileNotFoundError()
        with pytest.raises(SystemExit) as exc_info:
            execute_skill("body", working_dir=tmp_path)

    @patch("telos.executor.subprocess.run")
    def test_nonzero_exit_raises_error(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=1)
        with pytest.raises(SystemExit):
            execute_skill("body", working_dir=tmp_path)

    @patch("telos.executor.subprocess.run")
    def test_env_passed_to_subprocess(self, mock_run, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("CUSTOM=value\n")
        mock_run.return_value = MagicMock(returncode=0)

        execute_skill("body", working_dir=tmp_path, env_path=env_file)

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["env"]["CUSTOM"] == "value"
