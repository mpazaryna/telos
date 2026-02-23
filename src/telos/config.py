"""Agent configuration loading from ~/.skills/ discovery + agents.toml overrides."""

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


def get_skills_dir() -> Path:
    """Return the skills directory, respecting TELOS_SKILLS_DIR env override."""
    env = os.environ.get("TELOS_SKILLS_DIR")
    if env:
        return Path(env)
    return Path.home() / ".skills"


@dataclass
class Agent:
    """Represents a registered agent with its configuration."""

    name: str
    description: str
    skills_dir: Path | None
    working_dir: Path
    pack_dir: Path | None = None
    executor: str = "claude_code"
    mcp_config: Path | None = None

    def __post_init__(self) -> None:
        # Derive skills_dir and mcp_config from pack_dir
        if self.pack_dir is not None:
            self.pack_dir = self.pack_dir.expanduser()
            if self.skills_dir is None:
                self.skills_dir = self.pack_dir / "skills"
            if self.mcp_config is None:
                candidate = self.pack_dir / "mcp.json"
                if candidate.exists():
                    self.mcp_config = candidate

        # Expand tilde in paths
        if self.skills_dir is not None:
            self.skills_dir = self.skills_dir.expanduser()
        if self.mcp_config is not None:
            self.mcp_config = self.mcp_config.expanduser()
        self.working_dir = self.working_dir.expanduser()


def discover_agents(skills_dir: Path) -> dict[str, Agent]:
    """Scan skills_dir for agent packs.

    Each subdirectory containing skills/*/SKILL.md is treated as an agent.
    Reads optional agent.toml for metadata; infers defaults from directory name.
    """
    agents: dict[str, Agent] = {}
    if not skills_dir.exists():
        return agents

    for entry in sorted(skills_dir.iterdir()):
        if not entry.is_dir():
            continue
        skills_subdir = entry / "skills"
        if not skills_subdir.exists():
            continue
        skill_files = list(skills_subdir.glob("*/SKILL.md"))
        if not skill_files:
            continue

        name = entry.name
        description = ""
        working_dir = Path(f"~/obsidian/telos/{name}")

        # Read optional agent.toml
        agent_toml = entry / "agent.toml"
        if agent_toml.exists():
            with open(agent_toml, "rb") as f:
                data = tomllib.load(f)
            name = data.get("name", name)
            description = data.get("description", "")
            working_dir = Path(data.get("working_dir", str(working_dir)))

        agents[name] = Agent(
            name=name,
            description=description,
            skills_dir=None,  # derived from pack_dir in __post_init__
            working_dir=working_dir,
            pack_dir=entry,
        )

    return agents


def load_config(config_path: Path) -> dict[str, Agent]:
    """Load agent configuration: discover from ~/.skills/ then merge agents.toml overrides.

    Does not require agents.toml to exist — discovery alone is sufficient.
    """
    # Discover from skills dir
    agents = discover_agents(get_skills_dir())

    if config_path.exists():
        with open(config_path, "rb") as f:
            data = tomllib.load(f)

        agents_data = data.get("agents", {})

        for name, cfg in agents_data.items():
            if name in agents:
                # Merge overrides onto discovered agent
                existing = agents[name]
                if "working_dir" in cfg:
                    existing.working_dir = Path(cfg["working_dir"]).expanduser()
                if "description" in cfg:
                    existing.description = cfg["description"]
                if "skills_dir" in cfg:
                    existing.skills_dir = Path(cfg["skills_dir"]).expanduser()
                if "mcp_config" in cfg:
                    existing.mcp_config = Path(cfg["mcp_config"]).expanduser()
            else:
                # Agent from toml only — backward compat
                skills_dir_raw = cfg.get("skills_dir")
                skills_dir = Path(skills_dir_raw) if skills_dir_raw else None
                mcp_config_raw = cfg.get("mcp_config")
                mcp_config = Path(mcp_config_raw) if mcp_config_raw else None

                # Backward compat: mode=installed → derive pack_dir from old data dir
                pack_dir = None
                mode = cfg.get("mode")
                if mode == "installed":
                    old_pack_dir = get_data_dir() / "agents" / name
                    if old_pack_dir.exists():
                        pack_dir = old_pack_dir
                        if skills_dir is None:
                            skills_dir = old_pack_dir / "skills"

                agents[name] = Agent(
                    name=name,
                    description=cfg.get("description", ""),
                    skills_dir=skills_dir,
                    working_dir=Path(cfg.get("working_dir", ".")),
                    pack_dir=pack_dir,
                    executor=cfg.get("executor", "claude_code"),
                    mcp_config=mcp_config,
                )

    return agents
