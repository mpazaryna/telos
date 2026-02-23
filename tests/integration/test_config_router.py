"""Integration tests: config loading -> skill discovery -> routing."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from telos.config import load_config
from telos.router import discover_skills, route_intent


class TestConfigToRouter:
    """Integration: load config, discover skills, route intent."""

    def _setup_agent(self, tmp_path, monkeypatch):
        """Create a skills dir and config for testing."""
        skills_dir = tmp_path / "skills_home"
        monkeypatch.setenv("TELOS_SKILLS_DIR", str(skills_dir))

        # Set up agent pack at ~/.skills/kairos/
        pack = skills_dir / "kairos"
        skills = pack / "skills"
        (skills / "kickoff").mkdir(parents=True)
        (skills / "kickoff" / "SKILL.md").write_text("---\ndescription: Morning orientation\n---\n# Kickoff\nStart the day")
        (skills / "shutdown").mkdir()
        (skills / "shutdown" / "SKILL.md").write_text("---\ndescription: End of day wrap-up\n---\n# Shutdown\nWrap up")
        (pack / "agent.toml").write_text(f'name = "kairos"\ndescription = "Personal productivity"\nworking_dir = "{tmp_path}"\n')

        config = tmp_path / "agents.toml"
        config.write_text("")  # empty — discovery handles everything
        return config

    def test_load_config_then_discover_skills(self, tmp_path, monkeypatch):
        config = self._setup_agent(tmp_path, monkeypatch)
        agents = load_config(config)
        agent = agents["kairos"]
        skills = discover_skills(agent.skills_dir)
        assert len(skills) == 2

    def test_keyword_routing_end_to_end(self, tmp_path, monkeypatch):
        config = self._setup_agent(tmp_path, monkeypatch)
        agents = load_config(config)
        agent = agents["kairos"]
        skills = discover_skills(agent.skills_dir)
        result = route_intent("run kickoff", skills)
        assert result is not None
        assert result.name == "kickoff"

    def test_api_routing_end_to_end(self, tmp_path, monkeypatch):
        config = self._setup_agent(tmp_path, monkeypatch)
        agents = load_config(config)
        agent = agents["kairos"]
        skills = discover_skills(agent.skills_dir)

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="shutdown")]
        mock_client.messages.create.return_value = mock_response
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        result = route_intent("let's wrap up for the day", skills, client=mock_client)
        assert result is not None
        assert result.name == "shutdown"

    def test_no_match_end_to_end(self, tmp_path, monkeypatch):
        config = self._setup_agent(tmp_path, monkeypatch)
        agents = load_config(config)
        agent = agents["kairos"]
        skills = discover_skills(agent.skills_dir)

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="NONE")]
        mock_client.messages.create.return_value = mock_response
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        result = route_intent("order pizza", skills, client=mock_client)
        assert result is None
