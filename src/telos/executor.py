"""Claude Code subprocess execution."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from rich.console import Console

console = Console(stderr=True)


def build_command(skill_body: str, user_request: str | None = None) -> list[str]:
    """Build the claude CLI command from skill body and optional user request."""
    prompt = skill_body
    if user_request:
        prompt = f"{skill_body}\n\n---\nUser request: {user_request}"
    return ["claude", "-p", prompt]


def load_env(env_path: Path) -> dict[str, str]:
    """Load .env file and merge with os.environ.

    Supports KEY=VALUE, comments (#), empty lines, and quoted values.
    .env values override os.environ.
    Returns os.environ copy if file doesn't exist.
    """
    env = dict(os.environ)

    if not env_path.exists():
        return env

    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        # Strip surrounding quotes
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        env[key] = value

    return env


def resolve_working_dir(working_dir: Path) -> Path:
    """Resolve working directory: expand tilde, resolve '.' to cwd."""
    expanded = working_dir.expanduser()
    if str(working_dir) == ".":
        return Path.cwd()
    return expanded


def execute_skill(
    skill_body: str,
    working_dir: Path,
    env_path: Path | None = None,
    user_request: str | None = None,
) -> None:
    """Execute a skill via Claude Code subprocess.

    Inherits stdin/stdout/stderr for interactive use.
    Raises SystemExit on errors.
    """
    cmd = build_command(skill_body, user_request=user_request)
    cwd = resolve_working_dir(working_dir)

    env = None
    if env_path is not None:
        env = load_env(env_path)
    else:
        env = dict(os.environ)

    # Allow Claude Code to launch even from within a Claude Code session
    env.pop("CLAUDECODE", None)

    try:
        result = subprocess.run(cmd, cwd=cwd, env=env)
    except FileNotFoundError:
        console.print(
            "[bold red]Claude Code not found.[/bold red] "
            "Install with: npm install -g @anthropic-ai/claude-code"
        )
        raise SystemExit(1)

    if result.returncode != 0:
        console.print(f"[bold red]Claude Code exited with code {result.returncode}[/bold red]")
        raise SystemExit(result.returncode)
