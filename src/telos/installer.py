"""Agent pack install/uninstall logic."""

from __future__ import annotations

import shutil
import tomllib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import tomli_w

from telos.config import get_config_dir, get_data_dir


@dataclass
class InstallResult:
    """Summary of an agent installation."""

    agent_name: str
    skill_count: int
    install_path: Path


def read_agent_toml(pack_dir: Path) -> dict:
    """Read agent.toml from a pack directory.

    Applies defaults for missing fields.
    Raises FileNotFoundError if agent.toml doesn't exist.
    """
    agent_file = pack_dir / "agent.toml"
    if not agent_file.exists():
        raise FileNotFoundError(f"No agent.toml found in {pack_dir} — not a valid agent pack.")

    with open(agent_file, "rb") as f:
        data = tomllib.load(f)

    # Apply defaults
    data.setdefault("executor", "claude_code")
    data.setdefault("working_dir", ".")
    data.setdefault("description", "")

    return data


def copy_skills(src_dir: Path, dest_dir: Path) -> int:
    """Copy .md skill files from src to dest.

    Creates dest_dir if needed. Ignores non-.md files.
    Returns the number of files copied.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    if not src_dir.exists():
        return 0
    for path in sorted(src_dir.glob("*.md")):
        shutil.copy2(path, dest_dir / path.name)
        count += 1
    return count


def register_agent(
    registry_path: Path,
    agent_name: str,
    source_path: str,
    skill_count: int,
) -> None:
    """Register an agent in the registry.toml."""
    data: dict = {"agents": {}}
    if registry_path.exists():
        with open(registry_path, "rb") as f:
            data = tomllib.load(f)
        if "agents" not in data:
            data["agents"] = {}

    data["agents"][agent_name] = {
        "source_path": source_path,
        "skill_count": skill_count,
        "install_date": datetime.now(timezone.utc).isoformat(),
    }

    registry_path.parent.mkdir(parents=True, exist_ok=True)
    with open(registry_path, "wb") as f:
        tomli_w.dump(data, f)


def unregister_agent(registry_path: Path, agent_name: str) -> None:
    """Remove an agent from registry.toml."""
    if not registry_path.exists():
        return

    with open(registry_path, "rb") as f:
        data = tomllib.load(f)

    if "agents" in data and agent_name in data["agents"]:
        del data["agents"][agent_name]

    with open(registry_path, "wb") as f:
        tomli_w.dump(data, f)


def merge_agent_config(
    config_path: Path,
    agent_name: str,
    description: str,
    working_dir: str,
) -> None:
    """Add or update an agent stanza in agents.toml."""
    data: dict = {}
    if config_path.exists():
        with open(config_path, "rb") as f:
            data = tomllib.load(f)

    if "agents" not in data:
        data["agents"] = {}

    data["agents"][agent_name] = {
        "mode": "installed",
        "description": description,
        "working_dir": working_dir,
        "executor": "claude_code",
    }

    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "wb") as f:
        tomli_w.dump(data, f)


def remove_agent_config(config_path: Path, agent_name: str) -> None:
    """Remove an agent stanza from agents.toml."""
    if not config_path.exists():
        return

    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    if "agents" in data and agent_name in data["agents"]:
        del data["agents"][agent_name]

    with open(config_path, "wb") as f:
        tomli_w.dump(data, f)


def install_agent(pack_dir: Path) -> InstallResult:
    """Install an agent pack: copy skills, register, merge config.

    Returns an InstallResult summary.
    """
    metadata = read_agent_toml(pack_dir)
    agent_name = metadata["name"]

    data_dir = get_data_dir()
    config_dir = get_config_dir()

    # Copy skills
    skills_src = pack_dir / "skills"
    skills_dest = data_dir / "agents" / agent_name / "skills"
    skill_count = copy_skills(skills_src, skills_dest)

    # Register in registry
    registry_path = data_dir / "registry.toml"
    register_agent(registry_path, agent_name, str(pack_dir), skill_count)

    # Merge into agents.toml
    config_path = config_dir / "agents.toml"
    merge_agent_config(
        config_path,
        agent_name,
        metadata["description"],
        metadata["working_dir"],
    )

    return InstallResult(
        agent_name=agent_name,
        skill_count=skill_count,
        install_path=skills_dest,
    )


def uninstall_agent(agent_name: str) -> None:
    """Uninstall an agent: remove skills dir, registry entry, and config stanza.

    Raises ValueError for linked agents or nonexistent agents.
    """
    config_dir = get_config_dir()
    data_dir = get_data_dir()
    config_path = config_dir / "agents.toml"

    # Check agent exists and is not linked
    if config_path.exists():
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
        agents = data.get("agents", {})
        if agent_name not in agents:
            raise ValueError(f"Agent '{agent_name}' not found in agents.toml")
        if agents[agent_name].get("mode") == "linked":
            raise ValueError(
                f"Agent '{agent_name}' is linked, not installed. "
                "Remove it from agents.toml manually."
            )
    else:
        raise ValueError(f"Agent '{agent_name}' not found in agents.toml")

    # Remove skills directory
    agent_dir = data_dir / "agents" / agent_name
    if agent_dir.exists():
        shutil.rmtree(agent_dir)

    # Unregister from registry
    registry_path = data_dir / "registry.toml"
    unregister_agent(registry_path, agent_name)

    # Remove from agents.toml
    remove_agent_config(config_path, agent_name)
