"""Unit tests for telos.installer."""

import os
from pathlib import Path

import pytest

from telos.installer import (
    read_agent_toml,
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

    def test_missing_agent_toml_infers_name(self, tmp_path):
        """Without agent.toml, name is inferred from directory."""
        result = read_agent_toml(tmp_path)
        assert result["name"] == tmp_path.name

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

    def test_no_agent_toml_defaults(self, tmp_path):
        """Without agent.toml, all defaults are applied."""
        result = read_agent_toml(tmp_path)
        assert result["executor"] == "claude_code"
        assert result["description"] == ""
        assert result["working_dir"] == f"~/obsidian/telos/{tmp_path.name}"


class TestInstallAgent:
    """Tests for install_agent — copies entire pack to skills dir."""

    def test_full_install_returns_summary(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TELOS_SKILLS_DIR", str(tmp_path / "skills"))

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
        assert result.install_path == tmp_path / "skills" / "gmail"

    def test_install_copies_entire_pack(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TELOS_SKILLS_DIR", str(tmp_path / "skills"))

        pack_dir = tmp_path / "gmail-pack"
        pack_dir.mkdir()
        (pack_dir / "agent.toml").write_text('name = "gmail"\ndescription = "Gmail"\nworking_dir = "."\n')
        skills_src = pack_dir / "skills"
        skills_src.mkdir()
        (skills_src / "check").mkdir()
        (skills_src / "check" / "SKILL.md").write_text("Body")
        # Add scripts
        scripts = pack_dir / "scripts"
        scripts.mkdir()
        (scripts / "helper.sh").write_text("#!/bin/sh\necho hi")

        install_agent(pack_dir)

        dest = tmp_path / "skills" / "gmail"
        assert (dest / "skills" / "check" / "SKILL.md").exists()
        assert (dest / "scripts" / "helper.sh").exists()
        assert (dest / "agent.toml").exists()

    def test_install_with_mcp_json(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TELOS_SKILLS_DIR", str(tmp_path / "skills"))

        pack_dir = tmp_path / "clickup-pack"
        pack_dir.mkdir()
        (pack_dir / "agent.toml").write_text('name = "clickup"\ndescription = "ClickUp"\nworking_dir = "."\n')
        skills_src = pack_dir / "skills"
        skills_src.mkdir()
        (skills_src / "standup").mkdir()
        (skills_src / "standup" / "SKILL.md").write_text("Body")
        (pack_dir / "mcp.json").write_text('{"mcpServers": {}}')

        install_agent(pack_dir)

        dest = tmp_path / "skills" / "clickup"
        assert (dest / "mcp.json").exists()
        assert (dest / "mcp.json").read_text() == '{"mcpServers": {}}'

    def test_install_without_agent_toml(self, tmp_path, monkeypatch):
        """Install works without agent.toml — infers name from directory."""
        monkeypatch.setenv("TELOS_SKILLS_DIR", str(tmp_path / "skills"))

        pack_dir = tmp_path / "my-agent"
        pack_dir.mkdir()
        skills_src = pack_dir / "skills"
        skills_src.mkdir()
        (skills_src / "task").mkdir()
        (skills_src / "task" / "SKILL.md").write_text("Body")

        result = install_agent(pack_dir)
        assert result.agent_name == "my-agent"
        assert result.skill_count == 1

    def test_reinstall_overwrites(self, tmp_path, monkeypatch):
        """Installing over existing agent replaces it."""
        monkeypatch.setenv("TELOS_SKILLS_DIR", str(tmp_path / "skills"))

        pack_dir = tmp_path / "test-pack"
        pack_dir.mkdir()
        (pack_dir / "agent.toml").write_text('name = "test"\ndescription = "v1"\n')
        (pack_dir / "skills").mkdir()
        (pack_dir / "skills" / "a").mkdir()
        (pack_dir / "skills" / "a" / "SKILL.md").write_text("v1")

        install_agent(pack_dir)

        # Update and reinstall
        (pack_dir / "agent.toml").write_text('name = "test"\ndescription = "v2"\n')
        (pack_dir / "skills" / "a" / "SKILL.md").write_text("v2")

        result = install_agent(pack_dir)
        assert result.agent_name == "test"
        dest = tmp_path / "skills" / "test"
        assert (dest / "skills" / "a" / "SKILL.md").read_text() == "v2"


class TestUninstallAgent:
    """Tests for uninstall_agent."""

    def test_uninstall_removes_dir(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TELOS_SKILLS_DIR", str(tmp_path / "skills"))

        # Set up installed agent
        agent_dir = tmp_path / "skills" / "gmail"
        (agent_dir / "skills" / "check").mkdir(parents=True)
        (agent_dir / "skills" / "check" / "SKILL.md").write_text("Body")

        uninstall_agent("gmail")
        assert not agent_dir.exists()

    def test_uninstall_nonexistent_raises_error(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TELOS_SKILLS_DIR", str(tmp_path / "skills"))
        (tmp_path / "skills").mkdir(parents=True)

        with pytest.raises(ValueError, match="not found"):
            uninstall_agent("nonexistent")
