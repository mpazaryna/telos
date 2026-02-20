"""Integration tests: full pipeline config -> router -> executor."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from telos.config import load_config
from telos.router import discover_skills, route_intent
from telos.executor import execute_skill


class TestFullPipeline:
    """Integration: load config, discover skills, route, execute."""

    def _setup_full(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "kickoff").mkdir()
        (skills_dir / "kickoff" / "SKILL.md").write_text(
            "---\ndescription: Morning orientation\n---\n# Kickoff\nStart the day"
        )
        config = tmp_path / "agents.toml"
        config.write_text(f"""\
[defaults]
default_agent = "kairos"

[agents.kairos]
mode = "linked"
description = "Personal productivity"
skills_dir = "{skills_dir}"
working_dir = "{tmp_path}"
""")
        return config

    @patch("telos.executor.subprocess.run")
    def test_full_pipeline_keyword_match(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0)
        config = self._setup_full(tmp_path)
        agents, default_agent = load_config(config)
        agent = agents[default_agent]
        skills = discover_skills(agent.skills_dir)
        result = route_intent("run kickoff", skills)
        assert result is not None
        execute_skill(result.body, working_dir=agent.working_dir)
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "claude"
        assert "# Kickoff" in cmd[2]

    @patch("telos.executor.subprocess.run")
    def test_full_pipeline_api_match(self, mock_run, tmp_path, monkeypatch):
        mock_run.return_value = MagicMock(returncode=0)
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="kickoff")]
        mock_client.messages.create.return_value = mock_response
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        config = self._setup_full(tmp_path)
        agents, default_agent = load_config(config)
        agent = agents[default_agent]
        skills = discover_skills(agent.skills_dir)
        result = route_intent("let's start the day", skills, client=mock_client)
        assert result is not None
        execute_skill(result.body, working_dir=agent.working_dir)
        mock_run.assert_called_once()

    @patch("telos.executor.subprocess.run")
    def test_full_pipeline_with_env(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0)
        env_file = tmp_path / ".env"
        env_file.write_text("CLICKUP_API_KEY=test123\n")

        config = self._setup_full(tmp_path)
        agents, default_agent = load_config(config)
        agent = agents[default_agent]
        skills = discover_skills(agent.skills_dir)
        result = route_intent("run kickoff", skills)
        assert result is not None
        execute_skill(result.body, working_dir=agent.working_dir, env_path=env_file)

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["env"]["CLICKUP_API_KEY"] == "test123"

    @patch("telos.executor.subprocess.run")
    def test_user_request_included_in_prompt(self, mock_run, tmp_path):
        """The user's original request must be appended to the skill body
        so Claude Code has full context (e.g. 'write an interstitial about X')."""
        mock_run.return_value = MagicMock(returncode=0)
        config = self._setup_full(tmp_path)
        agents, default_agent = load_config(config)
        agent = agents[default_agent]
        skills = discover_skills(agent.skills_dir)
        user_input = "run kickoff and focus on the API refactor"
        result = route_intent(user_input, skills)
        assert result is not None
        execute_skill(result.body, working_dir=agent.working_dir, user_request=user_input)
        cmd = mock_run.call_args[0][0]
        # Skill body is present
        assert "# Kickoff" in cmd[2]
        # User request is appended
        assert "run kickoff and focus on the API refactor" in cmd[2]

    @patch("telos.executor.subprocess.run")
    def test_full_pipeline_with_mcp_config(self, mock_run, tmp_path):
        """Full pipeline with mcp_config: load config → route → execute_skill
        receives mcp_config_path → subprocess command includes --mcp-config."""
        mock_run.return_value = MagicMock(returncode=0)

        # Create mcp.json in the agent's data dir
        mcp_json = tmp_path / "mcp.json"
        mcp_json.write_text('{"mcpServers": {}}')

        config = self._setup_full(tmp_path)
        agents, default_agent = load_config(config)
        agent = agents[default_agent]
        skills = discover_skills(agent.skills_dir)
        result = route_intent("run kickoff", skills)
        assert result is not None

        execute_skill(
            result.body,
            working_dir=agent.working_dir,
            mcp_config_path=mcp_json,
        )

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "--mcp-config" in cmd
        idx = cmd.index("--mcp-config")
        assert cmd[idx + 1] == str(mcp_json)
