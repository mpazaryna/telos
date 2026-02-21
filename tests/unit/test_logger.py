"""Unit tests for telos.logger."""

import json
import time
from pathlib import Path
from unittest.mock import patch

from telos.logger import _append, log_skill_end, log_skill_start, log_tool_call


class TestAppend:
    """Tests for _append."""

    def test_creates_log_dir_and_file(self, tmp_path):
        log_file = tmp_path / "logs" / "2026-02-21.jsonl"
        with patch("telos.logger._log_path", return_value=log_file):
            _append({"event": "test"})
        assert log_file.exists()
        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 1
        assert json.loads(lines[0])["event"] == "test"

    def test_appends_multiple_entries(self, tmp_path):
        log_file = tmp_path / "test.jsonl"
        with patch("telos.logger._log_path", return_value=log_file):
            _append({"event": "first"})
            _append({"event": "second"})
        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["event"] == "first"
        assert json.loads(lines[1])["event"] == "second"


class TestLogSkillStart:
    """Tests for log_skill_start."""

    def test_returns_context_dict(self, tmp_path):
        log_file = tmp_path / "test.jsonl"
        with patch("telos.logger._log_path", return_value=log_file):
            ctx = log_skill_start("anthropic", "claude-haiku-4-5", has_mcp=False)
        assert "start_time" in ctx
        assert ctx["tool_calls"] == 0
        assert ctx["rounds"] == 0

    def test_writes_start_event(self, tmp_path):
        log_file = tmp_path / "test.jsonl"
        with patch("telos.logger._log_path", return_value=log_file):
            log_skill_start("anthropic", "claude-haiku-4-5", has_mcp=True)
        entry = json.loads(log_file.read_text().strip())
        assert entry["event"] == "skill_start"
        assert entry["provider"] == "anthropic"
        assert entry["model"] == "claude-haiku-4-5"
        assert entry["has_mcp"] is True
        assert "ts" in entry


class TestLogToolCall:
    """Tests for log_tool_call."""

    def test_writes_tool_call_event(self, tmp_path):
        log_file = tmp_path / "test.jsonl"
        with patch("telos.logger._log_path", return_value=log_file):
            log_tool_call("fetch_url", is_error=False)
        entry = json.loads(log_file.read_text().strip())
        assert entry["event"] == "tool_call"
        assert entry["tool"] == "fetch_url"
        assert entry["is_error"] is False

    def test_logs_error_tool_call(self, tmp_path):
        log_file = tmp_path / "test.jsonl"
        with patch("telos.logger._log_path", return_value=log_file):
            log_tool_call("read_file", is_error=True)
        entry = json.loads(log_file.read_text().strip())
        assert entry["is_error"] is True


class TestLogSkillEnd:
    """Tests for log_skill_end."""

    def test_writes_end_event_with_duration(self, tmp_path):
        log_file = tmp_path / "test.jsonl"
        ctx = {"start_time": time.monotonic() - 1.5, "tool_calls": 3, "rounds": 2}
        messages = [{"role": "user", "content": "test prompt"}]
        with patch("telos.logger._log_path", return_value=log_file):
            log_skill_end(ctx, messages)
        entry = json.loads(log_file.read_text().strip())
        assert entry["event"] == "skill_end"
        assert entry["duration_s"] >= 1.0
        assert entry["rounds"] == 2
        assert entry["tool_calls"] == 3
        assert entry["error"] is None
        assert entry["messages"] == messages

    def test_logs_error(self, tmp_path):
        log_file = tmp_path / "test.jsonl"
        ctx = {"start_time": time.monotonic(), "tool_calls": 0, "rounds": 1}
        with patch("telos.logger._log_path", return_value=log_file):
            log_skill_end(ctx, [], error="API timeout")
        entry = json.loads(log_file.read_text().strip())
        assert entry["error"] == "API timeout"


class TestLogFilePath:
    """Tests for per-day log file naming."""

    def test_uses_today_date(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TELOS_DATA_DIR", str(tmp_path))
        from telos.logger import _log_path

        path = _log_path()
        assert path.parent == tmp_path / "logs"
        # Filename matches YYYY-MM-DD.jsonl pattern
        assert path.suffix == ".jsonl"
        assert len(path.stem) == 10  # YYYY-MM-DD
