"""Integration tests: config loading -> skill discovery -> routing."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from telos.config import load_config
from telos.router import discover_skills, route_intent


class TestConfigToRouter:
    """Integration: load config, discover skills, route intent."""

    def _setup_agent(self, tmp_path):
        """Create a config and skills directory for testing."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "kickoff").mkdir()
        (skills_dir / "kickoff" / "SKILL.md").write_text("---\ndescription: Morning orientation\n---\n# Kickoff\nStart the day")
        (skills_dir / "shutdown").mkdir()
        (skills_dir / "shutdown" / "SKILL.md").write_text("---\ndescription: End of day wrap-up\n---\n# Shutdown\nWrap up")

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

    def test_load_config_then_discover_skills(self, tmp_path):
        config = self._setup_agent(tmp_path)
        agents, default_agent = load_config(config)
        agent = agents[default_agent]
        skills = discover_skills(agent.skills_dir)
        assert len(skills) == 2

    def test_keyword_routing_end_to_end(self, tmp_path):
        config = self._setup_agent(tmp_path)
        agents, default_agent = load_config(config)
        agent = agents[default_agent]
        skills = discover_skills(agent.skills_dir)
        result = route_intent("run kickoff", skills)
        assert result is not None
        assert result.name == "kickoff"

    def test_api_routing_end_to_end(self, tmp_path, monkeypatch):
        config = self._setup_agent(tmp_path)
        agents, default_agent = load_config(config)
        agent = agents[default_agent]
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
        config = self._setup_agent(tmp_path)
        agents, default_agent = load_config(config)
        agent = agents[default_agent]
        skills = discover_skills(agent.skills_dir)

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="NONE")]
        mock_client.messages.create.return_value = mock_response
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        result = route_intent("order pizza", skills, client=mock_client)
        assert result is None
