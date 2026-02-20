"""Unit tests for telos.router."""

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from telos.router import Skill, discover_skills, keyword_match, api_route, route_intent


class TestSkill:
    """Tests for the Skill dataclass."""

    def test_create_skill(self):
        skill = Skill(name="kickoff", description="Morning orientation", body="# Kickoff\nDo stuff")
        assert skill.name == "kickoff"
        assert skill.description == "Morning orientation"
        assert skill.body == "# Kickoff\nDo stuff"


class TestDiscoverSkills:
    """Tests for discover_skills."""

    def test_discovers_skill_subdirs(self, tmp_path):
        (tmp_path / "kickoff").mkdir()
        (tmp_path / "kickoff" / "SKILL.md").write_text("---\ndescription: Morning orientation\n---\n# Kickoff\nBody")
        (tmp_path / "shutdown").mkdir()
        (tmp_path / "shutdown" / "SKILL.md").write_text("---\ndescription: End of day\n---\n# Shutdown\nBody")
        skills = discover_skills(tmp_path)
        assert len(skills) == 2
        names = {s.name for s in skills}
        assert names == {"kickoff", "shutdown"}

    def test_ignores_non_skill_dirs(self, tmp_path):
        (tmp_path / "kickoff").mkdir()
        (tmp_path / "kickoff" / "SKILL.md").write_text("---\ndescription: Test\n---\nBody")
        (tmp_path / "README.txt").write_text("Not a skill")
        (tmp_path / ".DS_Store").write_text("junk")
        skills = discover_skills(tmp_path)
        assert len(skills) == 1
        assert skills[0].name == "kickoff"

    def test_extracts_frontmatter_description(self, tmp_path):
        (tmp_path / "kickoff").mkdir()
        (tmp_path / "kickoff" / "SKILL.md").write_text(
            "---\ndescription: Quick morning orientation. Surface what matters, set focus.\n---\n# Kickoff"
        )
        skills = discover_skills(tmp_path)
        assert skills[0].description == "Quick morning orientation. Surface what matters, set focus."

    def test_missing_description_uses_placeholder(self, tmp_path, capsys):
        (tmp_path / "experimental").mkdir()
        (tmp_path / "experimental" / "SKILL.md").write_text("---\ntags: test\n---\n# Experimental\nBody")
        skills = discover_skills(tmp_path)
        assert skills[0].description == "(no description)"

    def test_missing_frontmatter_entirely(self, tmp_path):
        (tmp_path / "simple").mkdir()
        (tmp_path / "simple" / "SKILL.md").write_text("# Simple\nJust a body")
        skills = discover_skills(tmp_path)
        assert skills[0].description == "(no description)"
        assert "# Simple\nJust a body" in skills[0].body

    def test_body_extracted_without_frontmatter(self, tmp_path):
        (tmp_path / "kickoff").mkdir()
        (tmp_path / "kickoff" / "SKILL.md").write_text("---\ndescription: Test\n---\n# Kickoff\nDo the thing")
        skills = discover_skills(tmp_path)
        assert skills[0].body.strip() == "# Kickoff\nDo the thing"

    def test_empty_directory_returns_no_skills(self, tmp_path):
        skills = discover_skills(tmp_path)
        assert skills == []


class TestKeywordMatch:
    """Tests for keyword_match."""

    def test_exact_match(self):
        skills = [Skill("kickoff", "Test", "body")]
        result = keyword_match("kickoff", skills)
        assert result is not None
        assert result.name == "kickoff"

    def test_partial_match(self):
        skills = [Skill("kickoff", "Test", "body")]
        result = keyword_match("run daily kickoff", skills)
        assert result is not None
        assert result.name == "kickoff"

    def test_case_insensitive(self):
        skills = [Skill("kickoff", "Test", "body")]
        result = keyword_match("Run KICKOFF now", skills)
        assert result is not None
        assert result.name == "kickoff"

    def test_longest_match_first(self):
        skills = [
            Skill("weekly", "Short", "body"),
            Skill("weekly-summary", "Long", "body"),
        ]
        result = keyword_match("generate weekly-summary report", skills)
        assert result is not None
        assert result.name == "weekly-summary"

    def test_no_match_returns_none(self):
        skills = [Skill("kickoff", "Test", "body")]
        result = keyword_match("order me a pizza", skills)
        assert result is None


class TestApiRoute:
    """Tests for api_route."""

    def test_correct_api_payload(self, monkeypatch):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="kickoff")]
        mock_client.messages.create.return_value = mock_response

        skills = [Skill("kickoff", "Morning orientation", "body")]
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        result = api_route("let's start the day", skills, client=mock_client)

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-sonnet-4-6"
        assert call_kwargs["max_tokens"] == 64
        assert result is not None
        assert result.name == "kickoff"

    def test_returns_none_when_api_says_none(self, monkeypatch):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="NONE")]
        mock_client.messages.create.return_value = mock_response

        skills = [Skill("kickoff", "Test", "body")]
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        result = api_route("order a pizza", skills, client=mock_client)
        assert result is None

    def test_no_api_key_returns_none(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        skills = [Skill("kickoff", "Test", "body")]
        result = api_route("start the day", skills)
        assert result is None

    def test_system_prompt_instructs_skill_name_only(self, monkeypatch):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="kickoff")]
        mock_client.messages.create.return_value = mock_response

        skills = [Skill("kickoff", "Morning orientation", "body")]
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        api_route("start the day", skills, client=mock_client)

        call_kwargs = mock_client.messages.create.call_args[1]
        system = call_kwargs["system"]
        assert "NONE" in system
        assert "skill name" in system.lower() or "skill" in system.lower()


class TestRouteIntent:
    """Tests for route_intent."""

    def test_keyword_match_shortcircuits_api(self, monkeypatch):
        mock_client = MagicMock()
        skills = [Skill("kickoff", "Test", "body")]
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        result = route_intent("run kickoff", skills, client=mock_client)

        assert result is not None
        assert result.name == "kickoff"
        mock_client.messages.create.assert_not_called()

    def test_falls_through_to_api_when_no_keyword(self, monkeypatch):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="shutdown")]
        mock_client.messages.create.return_value = mock_response

        skills = [Skill("shutdown", "End of day", "body")]
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        result = route_intent("let's wrap up for the day", skills, client=mock_client)

        assert result is not None
        assert result.name == "shutdown"
        mock_client.messages.create.assert_called_once()

    def test_no_match_returns_none(self, monkeypatch):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="NONE")]
        mock_client.messages.create.return_value = mock_response

        skills = [Skill("kickoff", "Test", "body")]
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        result = route_intent("order pizza", skills, client=mock_client)
        assert result is None
