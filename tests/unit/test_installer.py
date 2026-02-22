"""Unit tests for telos.installer."""

import os
from pathlib import Path

import pytest
import tomli_w
import tomllib

from telos.installer import (
    read_agent_toml,
    copy_skills,
    copy_mcp_config,
    register_agent,
    unregister_agent,
    merge_agent_config,
    remove_agent_config,
    install_agent,
    uninstall_agent,
    InstallResult,
)


class TestReadAgentToml:
    """Tests for read_agent_toml."""

    def test_reads_valid_agent_toml(self, tmp_path):
        agent_toml = tmp_path / "agent.toml"
        agent_toml.write_text('name = "gmail"\ndescription = "Gmail agent"\nworking_dir = "."\n')
        result = read_agent_toml(tmp_path)
        assert result["name"] == "gmail"
        assert result["description"] == "Gmail agent"

    def test_missing_agent_toml_raises_error(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="agent.toml"):
            read_agent_toml(tmp_path)

    def test_defaults_applied(self, tmp_path):
        agent_toml = tmp_path / "agent.toml"
        agent_toml.write_text('name = "gmail"\n')
        result = read_agent_toml(tmp_path)
        assert result["executor"] == "claude_code"
        assert result["working_dir"] == "~/obsidian/telos/gmail"

    def test_description_defaults_to_empty(self, tmp_path):
        agent_toml = tmp_path / "agent.toml"
        agent_toml.write_text('name = "gmail"\n')
        result = read_agent_toml(tmp_path)
        assert result["description"] == ""


class TestCopySkills:
    """Tests for copy_skills."""

    def test_copies_skill_subdirs(self, tmp_path):
        src = tmp_path / "pack" / "skills"
        src.mkdir(parents=True)
        (src / "check-email").mkdir()
        (src / "check-email" / "SKILL.md").write_text("---\ndescription: Check\n---\nBody")
        (src / "send-reply").mkdir()
        (src / "send-reply" / "SKILL.md").write_text("---\ndescription: Send\n---\nBody")

        dest = tmp_path / "installed"
        count = copy_skills(src, dest)
        assert count == 2
        assert (dest / "check-email" / "SKILL.md").exists()
        assert (dest / "send-reply" / "SKILL.md").exists()

    def test_creates_dest_dirs(self, tmp_path):
        src = tmp_path / "pack" / "skills"
        src.mkdir(parents=True)
        (src / "skill").mkdir()
        (src / "skill" / "SKILL.md").write_text("Body")

        dest = tmp_path / "deep" / "nested" / "dest"
        copy_skills(src, dest)
        assert dest.exists()

    def test_ignores_non_skill_dirs(self, tmp_path):
        src = tmp_path / "pack" / "skills"
        src.mkdir(parents=True)
        (src / "skill").mkdir()
        (src / "skill" / "SKILL.md").write_text("Body")
        (src / "README.txt").write_text("Not a skill")
        (src / ".DS_Store").write_text("junk")

        dest = tmp_path / "installed"
        count = copy_skills(src, dest)
        assert count == 1
        assert not (dest / "README.txt").exists()

    def test_returns_zero_for_empty_skills(self, tmp_path):
        src = tmp_path / "pack" / "skills"
        src.mkdir(parents=True)
        dest = tmp_path / "installed"
        count = copy_skills(src, dest)
        assert count == 0


class TestRegisterAgent:
    """Tests for register_agent and unregister_agent."""

    def test_registers_new_agent(self, tmp_path):
        registry_path = tmp_path / "registry.toml"
        register_agent(registry_path, "gmail", str(tmp_path / "pack"), 3)
        assert registry_path.exists()
        with open(registry_path, "rb") as f:
            data = tomllib.load(f)
        assert "gmail" in data["agents"]
        assert data["agents"]["gmail"]["skill_count"] == 3

    def test_updates_existing_agent(self, tmp_path):
        registry_path = tmp_path / "registry.toml"
        register_agent(registry_path, "gmail", "/old/path", 2)
        register_agent(registry_path, "gmail", "/new/path", 5)
        with open(registry_path, "rb") as f:
            data = tomllib.load(f)
        assert data["agents"]["gmail"]["source_path"] == "/new/path"
        assert data["agents"]["gmail"]["skill_count"] == 5

    def test_unregister_agent(self, tmp_path):
        registry_path = tmp_path / "registry.toml"
        register_agent(registry_path, "gmail", "/path", 3)
        unregister_agent(registry_path, "gmail")
        with open(registry_path, "rb") as f:
            data = tomllib.load(f)
        assert "gmail" not in data["agents"]

    def test_creates_registry_if_missing(self, tmp_path):
        registry_path = tmp_path / "registry.toml"
        assert not registry_path.exists()
        register_agent(registry_path, "gmail", "/path", 1)
        assert registry_path.exists()

    def test_register_includes_metadata(self, tmp_path):
        registry_path = tmp_path / "registry.toml"
        register_agent(registry_path, "gmail", "/path", 3)
        with open(registry_path, "rb") as f:
            data = tomllib.load(f)
        agent = data["agents"]["gmail"]
        assert "install_date" in agent
        assert "source_path" in agent
        assert "skill_count" in agent


class TestMergeAgentConfig:
    """Tests for merge_agent_config and remove_agent_config."""

    def test_adds_agent_stanza(self, tmp_path):
        config_path = tmp_path / "agents.toml"
        config_path.write_text('[defaults]\ndefault_agent = "kairos"\n\n[agents.kairos]\nmode = "linked"\ndescription = "Test"\nskills_dir = "/vault"\nworking_dir = "/vault"\n')
        merge_agent_config(config_path, "gmail", "Gmail agent", ".")
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
        assert "gmail" in data["agents"]
        assert data["agents"]["gmail"]["mode"] == "installed"

    def test_preserves_existing_agents(self, tmp_path):
        config_path = tmp_path / "agents.toml"
        config_path.write_text('[defaults]\ndefault_agent = "kairos"\n\n[agents.kairos]\nmode = "linked"\ndescription = "Test"\nskills_dir = "/vault"\nworking_dir = "/vault"\n')
        merge_agent_config(config_path, "gmail", "Gmail agent", ".")
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
        assert "kairos" in data["agents"]
        assert "gmail" in data["agents"]

    def test_overwrites_existing_agent(self, tmp_path):
        config_path = tmp_path / "agents.toml"
        config_path.write_text('[defaults]\ndefault_agent = "kairos"\n\n[agents.gmail]\nmode = "installed"\ndescription = "Old"\nworking_dir = "."\n')
        merge_agent_config(config_path, "gmail", "New description", ".")
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
        assert data["agents"]["gmail"]["description"] == "New description"

    def test_creates_config_if_missing(self, tmp_path):
        config_path = tmp_path / "agents.toml"
        assert not config_path.exists()
        merge_agent_config(config_path, "gmail", "Gmail agent", ".")
        assert config_path.exists()
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
        assert "gmail" in data["agents"]

    def test_remove_agent_config(self, tmp_path):
        config_path = tmp_path / "agents.toml"
        config_path.write_text('[defaults]\ndefault_agent = "kairos"\n\n[agents.kairos]\nmode = "linked"\ndescription = "Test"\nskills_dir = "/vault"\nworking_dir = "/vault"\n\n[agents.gmail]\nmode = "installed"\ndescription = "Gmail"\nworking_dir = "."\n')
        remove_agent_config(config_path, "gmail")
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
        assert "gmail" not in data["agents"]
        assert "kairos" in data["agents"]


class TestUninstallAgent:
    """Tests for uninstall_agent."""

    def test_uninstall_removes_dir_and_config(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TELOS_DATA_DIR", str(tmp_path / "data"))
        monkeypatch.setenv("TELOS_CONFIG_DIR", str(tmp_path / "config"))

        # Set up installed agent
        skills_dir = tmp_path / "data" / "agents" / "gmail" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "check.md").write_text("body")

        registry = tmp_path / "data" / "registry.toml"
        register_agent(registry, "gmail", "/path", 1)

        config_path = tmp_path / "config" / "agents.toml"
        config_path.parent.mkdir(parents=True)
        config_path.write_text('[agents.gmail]\nmode = "installed"\ndescription = "Gmail"\nworking_dir = "."\n')

        uninstall_agent("gmail")
        assert not skills_dir.parent.exists()

    def test_uninstall_blocks_linked_agents(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TELOS_CONFIG_DIR", str(tmp_path / "config"))
        config_path = tmp_path / "config" / "agents.toml"
        config_path.parent.mkdir(parents=True)
        config_path.write_text('[agents.kairos]\nmode = "linked"\ndescription = "Test"\nskills_dir = "/vault"\nworking_dir = "/vault"\n')

        with pytest.raises(ValueError, match="linked"):
            uninstall_agent("kairos")

    def test_uninstall_nonexistent_raises_error(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TELOS_CONFIG_DIR", str(tmp_path / "config"))
        config_path = tmp_path / "config" / "agents.toml"
        config_path.parent.mkdir(parents=True)
        config_path.write_text('[defaults]\ndefault_agent = "kairos"\n')

        with pytest.raises(ValueError, match="not found"):
            uninstall_agent("nonexistent")


class TestInstallAgent:
    """Tests for install_agent orchestration."""

    def test_full_install_returns_summary(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TELOS_DATA_DIR", str(tmp_path / "data"))
        monkeypatch.setenv("TELOS_CONFIG_DIR", str(tmp_path / "config"))

        # Create pack
        pack_dir = tmp_path / "gmail-pack"
        pack_dir.mkdir()
        (pack_dir / "agent.toml").write_text('name = "gmail"\ndescription = "Gmail agent"\nworking_dir = "."\n')
        skills_src = pack_dir / "skills"
        skills_src.mkdir()
        (skills_src / "check").mkdir()
        (skills_src / "check" / "SKILL.md").write_text("---\ndescription: Check\n---\nBody")
        (skills_src / "send").mkdir()
        (skills_src / "send" / "SKILL.md").write_text("---\ndescription: Send\n---\nBody")

        result = install_agent(pack_dir)

        assert isinstance(result, InstallResult)
        assert result.agent_name == "gmail"
        assert result.skill_count == 2
        assert (tmp_path / "data" / "agents" / "gmail" / "skills" / "check" / "SKILL.md").exists()

    def test_install_creates_all_required_files(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TELOS_DATA_DIR", str(tmp_path / "data"))
        monkeypatch.setenv("TELOS_CONFIG_DIR", str(tmp_path / "config"))

        pack_dir = tmp_path / "gmail-pack"
        pack_dir.mkdir()
        (pack_dir / "agent.toml").write_text('name = "gmail"\ndescription = "Gmail"\nworking_dir = "."\n')
        skills_src = pack_dir / "skills"
        skills_src.mkdir()
        (skills_src / "check").mkdir()
        (skills_src / "check" / "SKILL.md").write_text("Body")

        install_agent(pack_dir)

        # Verify all outputs
        assert (tmp_path / "data" / "agents" / "gmail" / "skills" / "check" / "SKILL.md").exists()
        assert (tmp_path / "data" / "registry.toml").exists()
        assert (tmp_path / "config" / "agents.toml").exists()

    def test_install_with_mcp_json_copies_file(self, tmp_path, monkeypatch):
        """install_agent with mcp.json present → file ends up in installed agent dir."""
        monkeypatch.setenv("TELOS_DATA_DIR", str(tmp_path / "data"))
        monkeypatch.setenv("TELOS_CONFIG_DIR", str(tmp_path / "config"))

        pack_dir = tmp_path / "clickup-pack"
        pack_dir.mkdir()
        (pack_dir / "agent.toml").write_text('name = "clickup"\ndescription = "ClickUp"\nworking_dir = "."\n')
        skills_src = pack_dir / "skills"
        skills_src.mkdir()
        (skills_src / "standup").mkdir()
        (skills_src / "standup" / "SKILL.md").write_text("Body")
        (pack_dir / "mcp.json").write_text('{"mcpServers": {}}')

        result = install_agent(pack_dir)

        mcp_dest = tmp_path / "data" / "agents" / "clickup" / "mcp.json"
        assert mcp_dest.exists()
        assert mcp_dest.read_text() == '{"mcpServers": {}}'


class TestCopyMcpConfig:
    """Tests for copy_mcp_config."""

    def test_copies_mcp_json(self, tmp_path):
        """copy_mcp_config copies mcp.json from pack to install dir."""
        pack_dir = tmp_path / "pack"
        pack_dir.mkdir()
        (pack_dir / "mcp.json").write_text('{"mcpServers": {"test": {}}}')

        dest_dir = tmp_path / "installed"
        dest_dir.mkdir()

        result = copy_mcp_config(pack_dir, dest_dir)
        assert result is True
        assert (dest_dir / "mcp.json").exists()
        assert (dest_dir / "mcp.json").read_text() == '{"mcpServers": {"test": {}}}'

    def test_no_mcp_json_returns_false(self, tmp_path):
        """copy_mcp_config when no mcp.json exists → returns False, no error."""
        pack_dir = tmp_path / "pack"
        pack_dir.mkdir()

        dest_dir = tmp_path / "installed"
        dest_dir.mkdir()

        result = copy_mcp_config(pack_dir, dest_dir)
        assert result is False
        assert not (dest_dir / "mcp.json").exists()
