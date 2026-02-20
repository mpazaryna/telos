"""Unit tests for telos.config."""

import os
from pathlib import Path

import pytest

from telos.config import Agent, load_config, get_config_dir, get_data_dir


class TestAgent:
    """Tests for the Agent dataclass."""

    def test_create_agent_all_fields(self):
        agent = Agent(
            name="kairos",
            mode="linked",
            description="Personal productivity",
            skills_dir=Path("/vault/.claude/commands"),
            working_dir=Path("/vault"),
            executor="claude_code",
        )
        assert agent.name == "kairos"
        assert agent.mode == "linked"
        assert agent.description == "Personal productivity"
        assert agent.skills_dir == Path("/vault/.claude/commands")
        assert agent.working_dir == Path("/vault")
        assert agent.executor == "claude_code"

    def test_agent_executor_defaults_to_claude_code(self):
        agent = Agent(
            name="test",
            mode="installed",
            description="Test agent",
            skills_dir=Path("/tmp/skills"),
            working_dir=Path("."),
        )
        assert agent.executor == "claude_code"

    def test_linked_mode_requires_explicit_skills_dir(self):
        """Linked agents must have skills_dir set explicitly in config."""
        with pytest.raises(ValueError, match="skills_dir"):
            Agent(
                name="kairos",
                mode="linked",
                description="Test",
                skills_dir=None,
                working_dir=Path("/vault"),
            )

    def test_installed_mode_derives_skills_dir(self):
        """Installed agents derive skills_dir from name + data dir."""
        agent = Agent(
            name="gmail",
            mode="installed",
            description="Gmail agent",
            skills_dir=None,
            working_dir=Path("."),
        )
        assert agent.skills_dir == Path.home() / ".local/share/telos/agents/gmail/skills"

    def test_installed_mode_derives_skills_dir_with_custom_data_dir(self, monkeypatch, tmp_path):
        monkeypatch.setenv("TELOS_DATA_DIR", str(tmp_path))
        agent = Agent(
            name="gmail",
            mode="installed",
            description="Gmail agent",
            skills_dir=None,
            working_dir=Path("."),
        )
        assert agent.skills_dir == tmp_path / "agents/gmail/skills"

    def test_path_expansion_tilde(self):
        agent = Agent(
            name="kairos",
            mode="linked",
            description="Test",
            skills_dir=Path("~/vault/.claude/commands"),
            working_dir=Path("~/vault"),
        )
        assert "~" not in str(agent.skills_dir)
        assert agent.skills_dir == Path.home() / "vault/.claude/commands"
        assert agent.working_dir == Path.home() / "vault"

    def test_mcp_config_stored_and_expanded(self):
        """Agent with mcp_config set → path stored and expanded."""
        agent = Agent(
            name="clickup",
            mode="linked",
            description="ClickUp",
            skills_dir=Path("/tmp/skills"),
            working_dir=Path("."),
            mcp_config=Path("~/myconfig/mcp.json"),
        )
        assert agent.mcp_config is not None
        assert "~" not in str(agent.mcp_config)
        assert agent.mcp_config == Path.home() / "myconfig/mcp.json"

    def test_installed_agent_derives_mcp_config(self, monkeypatch, tmp_path):
        """Installed agent with mcp.json in data dir → derives path automatically."""
        monkeypatch.setenv("TELOS_DATA_DIR", str(tmp_path))
        mcp_path = tmp_path / "agents" / "clickup" / "mcp.json"
        mcp_path.parent.mkdir(parents=True)
        mcp_path.write_text('{}')

        agent = Agent(
            name="clickup",
            mode="installed",
            description="ClickUp",
            skills_dir=None,
            working_dir=Path("."),
        )
        assert agent.mcp_config == mcp_path

    def test_mcp_config_defaults_to_none(self):
        """Agent without mcp_config → field is None."""
        agent = Agent(
            name="kairos",
            mode="linked",
            description="Test",
            skills_dir=Path("/tmp/skills"),
            working_dir=Path("."),
        )
        assert agent.mcp_config is None


class TestLoadConfig:
    """Tests for load_config."""

    def test_load_agents_from_toml(self, tmp_path):
        config = tmp_path / "agents.toml"
        config.write_text("""\
[defaults]
default_agent = "kairos"

[agents.kairos]
mode = "linked"
description = "Personal productivity"
skills_dir = "/vault/.claude/commands"
working_dir = "/vault"
executor = "claude_code"
""")
        agents, default_agent = load_config(config)
        assert default_agent == "kairos"
        assert "kairos" in agents
        assert agents["kairos"].name == "kairos"
        assert agents["kairos"].mode == "linked"

    def test_missing_config_raises_filenotfounderror(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path / "nonexistent.toml")

    def test_multiple_agents_loaded(self, tmp_path):
        config = tmp_path / "agents.toml"
        config.write_text("""\
[defaults]
default_agent = "kairos"

[agents.kairos]
mode = "linked"
description = "Personal productivity"
skills_dir = "/vault/.claude/commands"
working_dir = "/vault"

[agents.gmail]
mode = "installed"
description = "Gmail"
working_dir = "."
""")
        agents, default_agent = load_config(config)
        assert len(agents) == 2
        assert "kairos" in agents
        assert "gmail" in agents
        assert agents["gmail"].mode == "installed"

    def test_default_agent_validation(self, tmp_path):
        config = tmp_path / "agents.toml"
        config.write_text("""\
[defaults]
default_agent = "nonexistent"

[agents.kairos]
mode = "linked"
description = "Test"
skills_dir = "/vault"
working_dir = "/vault"
""")
        with pytest.raises(ValueError, match="nonexistent"):
            load_config(config)

    def test_fallback_to_project_root_config(self, tmp_path, monkeypatch):
        """When config_path is None and XDG location doesn't exist, fall back to project root."""
        monkeypatch.setenv("TELOS_CONFIG_DIR", str(tmp_path / "xdg"))
        # No file at XDG location
        project_config = tmp_path / "project" / "config" / "agents.toml"
        project_config.parent.mkdir(parents=True)
        project_config.write_text("""\
[defaults]
default_agent = "test"

[agents.test]
mode = "installed"
description = "Test"
working_dir = "."
""")
        agents, default_agent = load_config(project_config)
        assert "test" in agents


class TestDirectoryHelpers:
    """Tests for get_config_dir and get_data_dir."""

    def test_config_dir_default(self, monkeypatch):
        monkeypatch.delenv("TELOS_CONFIG_DIR", raising=False)
        assert get_config_dir() == Path.home() / ".config/telos"

    def test_config_dir_env_override(self, monkeypatch, tmp_path):
        monkeypatch.setenv("TELOS_CONFIG_DIR", str(tmp_path / "custom"))
        assert get_config_dir() == tmp_path / "custom"

    def test_data_dir_default(self, monkeypatch):
        monkeypatch.delenv("TELOS_DATA_DIR", raising=False)
        assert get_data_dir() == Path.home() / ".local/share/telos"

    def test_data_dir_env_override(self, monkeypatch, tmp_path):
        monkeypatch.setenv("TELOS_DATA_DIR", str(tmp_path / "data"))
        assert get_data_dir() == tmp_path / "data"
