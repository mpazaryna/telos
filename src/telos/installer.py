"""Agent pack install/uninstall logic — targets ~/.skills/."""

from __future__ import annotations

import shutil
import tomllib
from dataclasses import dataclass
from pathlib import Path

from telos.config import get_skills_dir


@dataclass
class InstallResult:
    """Summary of an agent installation."""

    agent_name: str
    skill_count: int
    install_path: Path


def read_agent_toml(pack_dir: Path) -> dict:
    """Read agent.toml from a pack directory.

    agent.toml is optional — infers name from directory, applies defaults.
    """
    agent_file = pack_dir / "agent.toml"
    data: dict = {}
    if agent_file.exists():
        with open(agent_file, "rb") as f:
            data = tomllib.load(f)

    # Infer name from directory if not in toml
    data.setdefault("name", pack_dir.name)
    data.setdefault("executor", "claude_code")
    data.setdefault("working_dir", f"~/obsidian/telos/{data['name']}")
    data.setdefault("description", "")

    return data


def install_agent(pack_dir: Path) -> InstallResult:
    """Install an agent pack: copy entire directory to ~/.skills/<name>/.

    Returns an InstallResult summary.
    """
    metadata = read_agent_toml(pack_dir)
    agent_name = metadata["name"]

    skills_dir = get_skills_dir()
    dest = skills_dir / agent_name

    # Remove existing installation if present
    if dest.exists():
        shutil.rmtree(dest)

    skills_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(pack_dir, dest)

    # Count skills
    skills_subdir = dest / "skills"
    skill_count = len(list(skills_subdir.glob("*/SKILL.md"))) if skills_subdir.exists() else 0

    return InstallResult(
        agent_name=agent_name,
        skill_count=skill_count,
        install_path=dest,
    )


def uninstall_agent(agent_name: str) -> None:
    """Uninstall an agent: remove its directory from ~/.skills/.

    Raises ValueError if agent directory doesn't exist.
    """
    skills_dir = get_skills_dir()
    agent_dir = skills_dir / agent_name

    if not agent_dir.exists():
        raise ValueError(f"Agent '{agent_name}' not found in {skills_dir}")

    shutil.rmtree(agent_dir)
