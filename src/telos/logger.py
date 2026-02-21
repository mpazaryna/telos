"""Per-day JSONL logging for skill executions."""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path


def _log_dir() -> Path:
    """Return the log directory, respecting TELOS_DATA_DIR."""
    from telos.config import get_data_dir

    return get_data_dir() / "logs"


def _log_path() -> Path:
    """Return today's log file path."""
    today = datetime.now().strftime("%Y-%m-%d")
    return _log_dir() / f"{today}.jsonl"


def _append(entry: dict) -> None:
    """Append a JSON line to today's log file."""
    path = _log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def log_skill_start(provider: str, model: str, has_mcp: bool) -> dict:
    """Log the start of a skill execution. Returns context dict for log_skill_end."""
    entry = {
        "ts": datetime.now().astimezone().isoformat(),
        "event": "skill_start",
        "provider": provider,
        "model": model,
        "has_mcp": has_mcp,
    }
    _append(entry)
    return {"start_time": time.monotonic(), "tool_calls": 0, "rounds": 0}


def log_tool_call(name: str, is_error: bool) -> None:
    """Log a tool call event."""
    _append({
        "ts": datetime.now().astimezone().isoformat(),
        "event": "tool_call",
        "tool": name,
        "is_error": is_error,
    })


def log_skill_end(
    ctx: dict,
    messages: list[dict],
    error: str | None = None,
) -> None:
    """Log the end of a skill execution with duration and conversation."""
    duration = time.monotonic() - ctx["start_time"]
    _append({
        "ts": datetime.now().astimezone().isoformat(),
        "event": "skill_end",
        "duration_s": round(duration, 2),
        "rounds": ctx["rounds"],
        "tool_calls": ctx["tool_calls"],
        "error": error,
        "messages": messages,
    })
