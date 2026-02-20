"""Agent configuration loading from agents.toml."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


def get_config_dir() -> Path:
    """Return the telos config directory, respecting TELOS_CONFIG_DIR env override."""
    env = os.environ.get("TELOS_CONFIG_DIR")
    if env:
        return Path(env)
    return Path.home() / ".config/telos"


def get_data_dir() -> Path:
    """Return the telos data directory, respecting TELOS_DATA_DIR env override."""
    env = os.environ.get("TELOS_DATA_DIR")
    if env:
        return Path(env)
    return Path.home() / ".local/share/telos"


@dataclass
class Agent:
    """Represents a registered agent with its configuration."""

    name: str
    mode: str
    description: str
    skills_dir: Path | None
    working_dir: Path
    executor: str = "claude_code"

    def __post_init__(self) -> None:
        # Validate linked mode requires skills_dir
        if self.mode == "linked" and self.skills_dir is None:
            raise ValueError(f"Agent '{self.name}': linked mode requires explicit skills_dir")

        # Derive skills_dir for installed mode
        if self.mode == "installed" and self.skills_dir is None:
            self.skills_dir = get_data_dir() / f"agents/{self.name}/skills"

        # Expand tilde in paths
        if self.skills_dir is not None:
            self.skills_dir = self.skills_dir.expanduser()
        self.working_dir = self.working_dir.expanduser()


def load_config(config_path: Path) -> tuple[dict[str, Agent], str]:
    """Load agents.toml and return (agents_dict, default_agent_name).

    Raises FileNotFoundError if config_path does not exist.
    Raises ValueError if default_agent references a nonexistent agent.
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    default_agent = data.get("defaults", {}).get("default_agent", "")
    agents_data = data.get("agents", {})

    agents: dict[str, Agent] = {}
    for name, cfg in agents_data.items():
        skills_dir_raw = cfg.get("skills_dir")
        skills_dir = Path(skills_dir_raw) if skills_dir_raw else None
        agents[name] = Agent(
            name=name,
            mode=cfg["mode"],
            description=cfg.get("description", ""),
            skills_dir=skills_dir,
            working_dir=Path(cfg.get("working_dir", ".")),
            executor=cfg.get("executor", "claude_code"),
        )

    if default_agent and default_agent not in agents:
        raise ValueError(
            f"Default agent '{default_agent}' not found in agents: {list(agents.keys())}"
        )

    return agents, default_agent
