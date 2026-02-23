"""Unit tests for telos.config."""

import os
from pathlib import Path

import pytest

from telos.config import Agent, load_config, get_config_dir, get_data_dir, get_skills_dir, discover_agents


class TestAgent:
    """Tests for the Agent dataclass."""

    def test_create_agent_all_fields(self):
        agent = Agent(
            name="kairos",
            description="Personal productivity",
            skills_dir=Path("/vault/.claude/commands"),
            working_dir=Path("/vault"),
            executor="claude_code",
        )
        assert agent.name == "kairos"
        assert agent.description == "Personal productivity"
        assert agent.skills_dir == Path("/vault/.claude/commands")
        assert agent.working_dir == Path("/vault")
        assert agent.executor == "claude_code"

    def test_agent_executor_defaults_to_claude_code(self):
        agent = Agent(
            name="test",
            description="Test agent",
            skills_dir=Path("/tmp/skills"),
            working_dir=Path("."),
        )
        assert agent.executor == "claude_code"

    def test_pack_dir_derives_skills_dir(self, tmp_path):
        """Agent with pack_dir set → skills_dir derived from pack_dir/skills."""
        pack = tmp_path / "myagent"
        pack.mkdir()
        agent = Agent(
            name="myagent",
            description="Test",
            skills_dir=None,
            working_dir=Path("."),
            pack_dir=pack,
        )
        assert agent.skills_dir == pack / "skills"

    def test_pack_dir_derives_mcp_config(self, tmp_path):
        """Agent with pack_dir and mcp.json present → mcp_config derived."""
        pack = tmp_path / "clickup"
        pack.mkdir()
        mcp_path = pack / "mcp.json"
        mcp_path.write_text('{}')

        agent = Agent(
            name="clickup",
            description="ClickUp",
            skills_dir=None,
            working_dir=Path("."),
            pack_dir=pack,
        )
        assert agent.mcp_config == mcp_path

    def test_pack_dir_no_mcp_json(self, tmp_path):
        """Agent with pack_dir but no mcp.json → mcp_config is None."""
        pack = tmp_path / "hackernews"
        pack.mkdir()

        agent = Agent(
            name="hackernews",
            description="HN",
            skills_dir=None,
            working_dir=Path("."),
            pack_dir=pack,
        )
        assert agent.mcp_config is None

    def test_explicit_skills_dir_not_overridden_by_pack_dir(self, tmp_path):
        """When both skills_dir and pack_dir are set, skills_dir is kept."""
        pack = tmp_path / "myagent"
        pack.mkdir()
        explicit = tmp_path / "explicit_skills"

        agent = Agent(
            name="myagent",
            description="Test",
            skills_dir=explicit,
            working_dir=Path("."),
            pack_dir=pack,
        )
        assert agent.skills_dir == explicit

    def test_path_expansion_tilde(self):
        agent = Agent(
            name="kairos",
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
            description="ClickUp",
            skills_dir=Path("/tmp/skills"),
            working_dir=Path("."),
            mcp_config=Path("~/myconfig/mcp.json"),
        )
        assert agent.mcp_config is not None
        assert "~" not in str(agent.mcp_config)
        assert agent.mcp_config == Path.home() / "myconfig/mcp.json"

    def test_mcp_config_defaults_to_none(self):
        """Agent without mcp_config → field is None."""
        agent = Agent(
            name="kairos",
            description="Test",
            skills_dir=Path("/tmp/skills"),
            working_dir=Path("."),
        )
        assert agent.mcp_config is None

    def test_pack_dir_defaults_to_none(self):
        """Agent without pack_dir → field is None."""
        agent = Agent(
            name="kairos",
            description="Test",
            skills_dir=Path("/tmp/skills"),
            working_dir=Path("."),
        )
        assert agent.pack_dir is None


class TestDiscoverAgents:
    """Tests for discover_agents."""

    def test_discovers_agent_with_skills(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TELOS_SKILLS_DIR", str(tmp_path))
        pack = tmp_path / "hackernews"
        (pack / "skills" / "frontpage").mkdir(parents=True)
        (pack / "skills" / "frontpage" / "SKILL.md").write_text("---\ndescription: HN\n---\nBody")

        agents = discover_agents(tmp_path)
        assert "hackernews" in agents
        assert agents["hackernews"].pack_dir == pack
        assert agents["hackernews"].skills_dir == pack / "skills"

    def test_reads_agent_toml_metadata(self, tmp_path):
        pack = tmp_path / "hn-pack"
        (pack / "skills" / "frontpage").mkdir(parents=True)
        (pack / "skills" / "frontpage" / "SKILL.md").write_text("Body")
        (pack / "agent.toml").write_text('name = "hackernews"\ndescription = "HN frontpage"\nworking_dir = "~/custom/dir"\n')

        agents = discover_agents(tmp_path)
        assert "hackernews" in agents
        assert agents["hackernews"].description == "HN frontpage"
        assert agents["hackernews"].working_dir == Path.home() / "custom/dir"

    def test_infers_name_from_directory(self, tmp_path):
        pack = tmp_path / "my-agent"
        (pack / "skills" / "task").mkdir(parents=True)
        (pack / "skills" / "task" / "SKILL.md").write_text("Body")
        # No agent.toml

        agents = discover_agents(tmp_path)
        assert "my-agent" in agents

    def test_skips_dirs_without_skills(self, tmp_path):
        (tmp_path / "empty-dir").mkdir()
        (tmp_path / "no-skills" / "skills").mkdir(parents=True)
        # skills dir exists but no SKILL.md inside

        agents = discover_agents(tmp_path)
        assert len(agents) == 0

    def test_discovers_mcp_config(self, tmp_path):
        pack = tmp_path / "clickup"
        (pack / "skills" / "standup").mkdir(parents=True)
        (pack / "skills" / "standup" / "SKILL.md").write_text("Body")
        (pack / "mcp.json").write_text('{}')

        agents = discover_agents(tmp_path)
        assert agents["clickup"].mcp_config == pack / "mcp.json"

    def test_nonexistent_dir_returns_empty(self, tmp_path):
        agents = discover_agents(tmp_path / "nonexistent")
        assert agents == {}

    def test_default_working_dir(self, tmp_path):
        pack = tmp_path / "hackernews"
        (pack / "skills" / "frontpage").mkdir(parents=True)
        (pack / "skills" / "frontpage" / "SKILL.md").write_text("Body")

        agents = discover_agents(tmp_path)
        assert agents["hackernews"].working_dir == Path.home() / "obsidian/telos/hackernews"


class TestLoadConfig:
    """Tests for load_config."""

    def test_load_agents_from_toml_with_discovery(self, tmp_path, monkeypatch):
        """agents.toml overrides are merged with discovered agents."""
        skills_dir = tmp_path / "skills"
        monkeypatch.setenv("TELOS_SKILLS_DIR", str(skills_dir))

        # Set up discovered agent
        pack = skills_dir / "hackernews"
        (pack / "skills" / "frontpage").mkdir(parents=True)
        (pack / "skills" / "frontpage" / "SKILL.md").write_text("Body")
        (pack / "agent.toml").write_text('name = "hackernews"\ndescription = "HN"\nworking_dir = "~/obsidian/telos/hackernews"\n')

        config = tmp_path / "agents.toml"
        config.write_text("""\
[agents.hackernews]
working_dir = "~/custom/output"
""")
        agents = load_config(config)
        assert "hackernews" in agents
        # working_dir overridden by toml
        assert agents["hackernews"].working_dir == Path.home() / "custom/output"

    def test_toml_only_agents_still_work(self, tmp_path, monkeypatch):
        """Agents defined only in toml (not discovered) are still loaded."""
        monkeypatch.setenv("TELOS_SKILLS_DIR", str(tmp_path / "empty_skills"))

        config = tmp_path / "agents.toml"
        config.write_text("""\
[agents.kairos]
description = "Personal productivity"
skills_dir = "/vault/.claude/commands"
working_dir = "/vault"
""")
        agents = load_config(config)
        assert "kairos" in agents
        assert agents["kairos"].skills_dir == Path("/vault/.claude/commands")

    def test_missing_config_uses_discovery_only(self, tmp_path, monkeypatch):
        """When agents.toml doesn't exist, discovery alone works."""
        skills_dir = tmp_path / "skills"
        monkeypatch.setenv("TELOS_SKILLS_DIR", str(skills_dir))

        pack = skills_dir / "hackernews"
        (pack / "skills" / "frontpage").mkdir(parents=True)
        (pack / "skills" / "frontpage" / "SKILL.md").write_text("Body")

        agents = load_config(tmp_path / "nonexistent.toml")
        assert "hackernews" in agents

    def test_backward_compat_installed_mode(self, tmp_path, monkeypatch):
        """Old mode=installed entries derive pack_dir from data dir."""
        monkeypatch.setenv("TELOS_SKILLS_DIR", str(tmp_path / "empty_skills"))
        monkeypatch.setenv("TELOS_DATA_DIR", str(tmp_path / "data"))

        # Set up old-style installed agent
        old_dir = tmp_path / "data" / "agents" / "gmail"
        (old_dir / "skills" / "check").mkdir(parents=True)
        (old_dir / "skills" / "check" / "SKILL.md").write_text("Body")

        config = tmp_path / "agents.toml"
        config.write_text("""\
[agents.gmail]
mode = "installed"
description = "Gmail"
working_dir = "."
""")
        agents = load_config(config)
        assert "gmail" in agents
        assert agents["gmail"].pack_dir == old_dir
        assert agents["gmail"].skills_dir == old_dir / "skills"

    def test_multiple_agents_loaded(self, tmp_path, monkeypatch):
        skills_dir = tmp_path / "skills"
        monkeypatch.setenv("TELOS_SKILLS_DIR", str(skills_dir))

        # Two discovered agents
        for name in ("hackernews", "arxiv"):
            pack = skills_dir / name
            (pack / "skills" / "main").mkdir(parents=True)
            (pack / "skills" / "main" / "SKILL.md").write_text("Body")

        agents = load_config(tmp_path / "nonexistent.toml")
        assert len(agents) == 2
        assert "hackernews" in agents
        assert "arxiv" in agents

    def test_ignores_default_agent_in_toml(self, tmp_path, monkeypatch):
        """default_agent in toml is silently ignored."""
        skills_dir = tmp_path / "skills"
        monkeypatch.setenv("TELOS_SKILLS_DIR", str(skills_dir))

        pack = skills_dir / "hackernews"
        (pack / "skills" / "frontpage").mkdir(parents=True)
        (pack / "skills" / "frontpage" / "SKILL.md").write_text("Body")

        config = tmp_path / "agents.toml"
        config.write_text("""\
[defaults]
default_agent = "hackernews"
""")
        # Should not raise, just returns agents
        agents = load_config(config)
        assert "hackernews" in agents


class TestDirectoryHelpers:
    """Tests for get_config_dir, get_data_dir, and get_skills_dir."""

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

    def test_skills_dir_default(self, monkeypatch):
        monkeypatch.delenv("TELOS_SKILLS_DIR", raising=False)
        assert get_skills_dir() == Path.home() / ".skills"

    def test_skills_dir_env_override(self, monkeypatch, tmp_path):
        monkeypatch.setenv("TELOS_SKILLS_DIR", str(tmp_path / "my_skills"))
        assert get_skills_dir() == tmp_path / "my_skills"
