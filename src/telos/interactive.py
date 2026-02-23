"""Simple interactive mode using Rich prompts."""

from __future__ import annotations

import sys

from rich.console import Console
from rich.table import Table

from telos.config import Agent, get_config_dir, load_config


def _load_agents() -> dict[str, Agent] | None:
    """Try to load agents config. Returns None if not configured."""
    config_dir = get_config_dir()
    config_path = config_dir / "agents.toml"
    try:
        agents = load_config(config_path)
        if not agents:
            return None
        return agents
    except (FileNotFoundError, ValueError):
        return None


def _prompt(message: str, choices: list[str]) -> str | None:
    """Print numbered choices and read selection from stdin.

    Returns the selected choice string, or None on quit/empty input.
    """
    for i, choice in enumerate(choices, 1):
        print(f"  {i}. {choice}")
    print()
    try:
        raw = input(f"{message} ").strip()
    except (EOFError, KeyboardInterrupt):
        return None
    if not raw or raw.lower() == "q":
        return None
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(choices):
            return choices[idx]
    except ValueError:
        # Try matching by name
        for choice in choices:
            if raw.lower() == choice.lower():
                return choice
    return None


def interactive_mode(console: Console, err_console: Console) -> None:
    """Run the interactive agent/skill browser."""
    if not sys.stdin.isatty():
        return

    agents = _load_agents()
    if agents is None:
        err_console.print(
            "[bold red]No agents found.[/bold red] "
            "Run [bold]telos init[/bold] then [bold]telos install[/bold] to add agents."
        )
        return

    from telos.router import discover_skills

    # Show agents table
    table = Table(title="Agents")
    table.add_column("#", style="dim", width=3)
    table.add_column("Agent", style="cyan")
    table.add_column("Skills", justify="right")
    table.add_column("Description", style="dim")

    agent_names = sorted(agents.keys())
    for i, name in enumerate(agent_names, 1):
        agent = agents[name]
        skill_count = 0
        if agent.skills_dir and agent.skills_dir.exists():
            skill_count = len(list(agent.skills_dir.glob("*/SKILL.md")))
        table.add_row(str(i), name, str(skill_count), agent.description)

    console.print()
    console.print(table)
    console.print()

    selected_name = _prompt("Select agent (number or name, q to quit):", agent_names)
    if selected_name is None:
        return

    agent = agents[selected_name]
    skills = discover_skills(agent.skills_dir) if agent.skills_dir else []

    if not skills:
        err_console.print(f"[bold red]No skills found for '{selected_name}'.[/bold red]")
        return

    # Show skills table
    skill_table = Table(title=f"Skills — {selected_name}")
    skill_table.add_column("#", style="dim", width=3)
    skill_table.add_column("Skill", style="cyan")
    skill_table.add_column("Description", style="dim")

    skill_names = [s.name for s in skills]
    for i, skill in enumerate(skills, 1):
        skill_table.add_row(str(i), skill.name, skill.description)

    console.print()
    console.print(skill_table)
    console.print()

    selected_skill = _prompt("Select skill (number or name, q to quit):", skill_names)
    if selected_skill is None:
        return

    matched = next((s for s in skills if s.name == selected_skill), None)
    if matched is None:
        return

    console.print()
    console.print(f"[bold green]Matched:[/bold green] agent={selected_name}, skill={matched.name}")
    console.print()

    try:
        raw = input("Run? (y = execute, d = dry run, q = quit) ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return

    if raw == "d":
        console.print(f"[dim]Dry run — would execute skill '{matched.name}' on agent '{selected_name}'[/dim]")
    elif raw == "y":
        from telos.executor import execute_skill

        env_path = get_config_dir() / ".env"
        execute_skill(
            matched.body,
            working_dir=agent.working_dir,
            env_path=env_path,
            mcp_config_path=agent.mcp_config,
            pack_dir=agent.pack_dir,
        )
    else:
        return
