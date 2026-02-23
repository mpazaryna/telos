"""Integration tests: full pipeline config -> router -> executor."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from telos.config import load_config
from telos.executor import execute_skill
from telos.provider import StreamEvent
from telos.router import discover_skills, route_intent


class TestFullPipeline:
    """Integration: load config, discover skills, route, execute."""

    def _setup_full(self, tmp_path, monkeypatch):
        skills_dir = tmp_path / "skills_home"
        monkeypatch.setenv("TELOS_SKILLS_DIR", str(skills_dir))

        pack = skills_dir / "kairos"
        skills = pack / "skills"
        (skills / "kickoff").mkdir(parents=True)
        (skills / "kickoff" / "SKILL.md").write_text(
            "---\ndescription: Morning orientation\n---\n# Kickoff\nStart the day"
        )
        (pack / "agent.toml").write_text(f'name = "kairos"\ndescription = "Personal productivity"\nworking_dir = "{tmp_path}"\n')

        config = tmp_path / "agents.toml"
        config.write_text("")  # empty — discovery handles everything
        return config

    def _mock_provider(self):
        mock_provider = MagicMock()
        mock_provider.stream_completion.return_value = iter(
            [
                StreamEvent(type="text", text="Done."),
                StreamEvent(type="done", stop_reason="end_turn"),
            ]
        )
        return mock_provider

    @patch("telos.executor._create_provider")
    def test_full_pipeline_keyword_match(self, mock_create, tmp_path, monkeypatch):
        mock_create.return_value = self._mock_provider()
        config = self._setup_full(tmp_path, monkeypatch)
        agents = load_config(config)
        agent = agents["kairos"]
        skills = discover_skills(agent.skills_dir)
        result = route_intent("run kickoff", skills)
        assert result is not None
        execute_skill(result.body, working_dir=agent.working_dir, pack_dir=agent.pack_dir)
        mock_create.assert_called_once()

    @patch("telos.executor._create_provider")
    def test_full_pipeline_api_match(self, mock_create, tmp_path, monkeypatch):
        mock_create.return_value = self._mock_provider()
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="kickoff")]
        mock_client.messages.create.return_value = mock_response
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        config = self._setup_full(tmp_path, monkeypatch)
        agents = load_config(config)
        agent = agents["kairos"]
        skills = discover_skills(agent.skills_dir)
        result = route_intent("let's start the day", skills, client=mock_client)
        assert result is not None
        execute_skill(result.body, working_dir=agent.working_dir, pack_dir=agent.pack_dir)
        mock_create.assert_called_once()

    @patch("telos.executor._create_provider")
    def test_full_pipeline_with_env(self, mock_create, tmp_path, monkeypatch):
        mock_create.return_value = self._mock_provider()
        env_file = tmp_path / ".env"
        env_file.write_text("ANTHROPIC_API_KEY=test123\nCLICKUP_API_KEY=test123\n")

        config = self._setup_full(tmp_path, monkeypatch)
        agents = load_config(config)
        agent = agents["kairos"]
        skills = discover_skills(agent.skills_dir)
        result = route_intent("run kickoff", skills)
        assert result is not None
        execute_skill(result.body, working_dir=agent.working_dir, env_path=env_file, pack_dir=agent.pack_dir)

        env_arg = mock_create.call_args[0][0]
        assert env_arg["CLICKUP_API_KEY"] == "test123"

    @patch("telos.executor._create_provider")
    def test_user_request_included_in_prompt(self, mock_create, tmp_path, monkeypatch):
        """The user's original request must be appended to the skill body
        so the model has full context (e.g. 'write an interstitial about X')."""
        mock_provider = self._mock_provider()
        mock_create.return_value = mock_provider
        config = self._setup_full(tmp_path, monkeypatch)
        agents = load_config(config)
        agent = agents["kairos"]
        skills = discover_skills(agent.skills_dir)
        user_input = "run kickoff and focus on the API refactor"
        result = route_intent(user_input, skills)
        assert result is not None
        execute_skill(result.body, working_dir=agent.working_dir, user_request=user_input, pack_dir=agent.pack_dir)

        mock_provider.stream_completion.assert_called_once()
        call_args = mock_provider.stream_completion.call_args
        messages = call_args[0][1]
        prompt = messages[0]["content"]
        # Skill body is present
        assert "# Kickoff" in prompt
        # User request is appended
        assert "run kickoff and focus on the API refactor" in prompt

    @patch("telos.executor._create_provider")
    def test_full_pipeline_with_mcp_config(self, mock_create, tmp_path, monkeypatch):
        """Full pipeline with mcp_config: load config -> route -> execute_skill
        dispatches to MCP execution path."""
        mock_provider = MagicMock()
        mock_provider.stream_completion.return_value = iter(
            [
                StreamEvent(type="text", text="Done."),
                StreamEvent(type="done", stop_reason="end_turn"),
            ]
        )
        mock_create.return_value = mock_provider

        # Create mcp.json in the agent's data dir
        mcp_json = tmp_path / "mcp.json"
        mcp_json.write_text('{"mcpServers": {}}')

        config = self._setup_full(tmp_path, monkeypatch)
        agents = load_config(config)
        agent = agents["kairos"]
        skills = discover_skills(agent.skills_dir)
        result = route_intent("run kickoff", skills)
        assert result is not None

        # Mock the MCP execution path since we don't have real MCP servers
        with patch("telos.executor._execute_with_mcp") as mock_mcp:
            execute_skill(
                result.body,
                working_dir=agent.working_dir,
                mcp_config_path=mcp_json,
                pack_dir=agent.pack_dir,
            )
            mock_mcp.assert_called_once()
