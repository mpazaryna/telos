"""CLI entrypoint for telos."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import click
import typer
import typer.core
from rich.console import Console
from rich.table import Table

from telos.config import Agent, get_config_dir, get_skills_dir, load_config
from telos.executor import execute_skill
from telos.installer import install_agent, uninstall_agent
from telos.router import Skill, discover_skills, route_intent


class DefaultGroup(typer.core.TyperGroup):
    """Typer Group that redirects unrecognized commands to a default 'run' command."""

    def resolve_command(self, ctx: click.Context, args: list[str]):
        try:
            return super().resolve_command(ctx, args)
        except click.UsageError:
            # Not a known subcommand — redirect to the hidden 'run' command
            cmd = self.get_command(ctx, "run")
            if cmd is not None:
                return "run", cmd, args
            raise


app = typer.Typer(
    cls=DefaultGroup,
    help="Personal agent runtime — route natural language to skills, execute via Claude Code",
)
console = Console()
err_console = Console(stderr=True)


def _load_agents_or_exit() -> dict[str, Agent]:
    """Load config or print init hint and exit."""
    config_dir = get_config_dir()
    config_path = config_dir / "agents.toml"

    if not config_path.exists():
        project_config = Path.cwd() / "config" / "agents.toml"
        if project_config.exists():
            config_path = project_config

    # load_config discovers from ~/.skills/ even without agents.toml
    agents = load_config(config_path)

    if not agents:
        err_console.print(
            "[bold red]No agents found.[/bold red] "
            "Run [bold]telos init[/bold] then [bold]telos install <path-to-pack>[/bold] to add agents."
        )
        raise typer.Exit(code=1)

    return agents


def _route_across_agents(
    request: str,
    agents: dict[str, Agent],
    agent_name: str | None = None,
) -> tuple[Agent, Skill] | tuple[None, None]:
    """Find the right agent + skill for a request.

    When agent_name is explicit, only search that agent.
    Otherwise search all agents.
    """
    if agent_name:
        if agent_name not in agents:
            return None, None
        agent = agents[agent_name]
        skills = discover_skills(agent.skills_dir) if agent.skills_dir else []
        matched = route_intent(request, skills) if skills else None
        return (agent, matched) if matched else (None, None)

    for name in sorted(agents):
        agent = agents[name]
        skills = discover_skills(agent.skills_dir) if agent.skills_dir else []
        if not skills:
            continue
        matched = route_intent(request, skills)
        if matched is not None:
            return agent, matched

    return None, None


def _print_skills_table(skills: list[Skill], header: str = "Skills") -> None:
    """Print a table of skills."""
    table = Table(title=header)
    table.add_column("Skill", style="cyan")
    table.add_column("Description", style="white")
    for skill in sorted(skills, key=lambda s: s.name):
        table.add_row(skill.name, skill.description)
    console.print(table)


def _handle_request(
    request: str,
    agent_name: str | None,
    dry_run: bool,
    verbose: bool,
) -> None:
    """Core request handling: load config, route across agents, execute."""
    agents = _load_agents_or_exit()

    if agent_name and agent_name not in agents:
        err_console.print(f"[bold red]Agent '{agent_name}' not found.[/bold red] Available: {', '.join(sorted(agents.keys()))}")
        raise typer.Exit(code=1)

    selected, matched = _route_across_agents(request, agents, agent_name)

    if selected is None or matched is None:
        err_console.print(f"[bold red]No matching skill found for:[/bold red] '{request}'")
        err_console.print()
        # Show all available skills across agents
        all_skills: list[Skill] = []
        for agent in agents.values():
            if agent.skills_dir:
                all_skills.extend(discover_skills(agent.skills_dir))
        if all_skills:
            _print_skills_table(all_skills, header="Available skills:")
        raise typer.Exit(code=1)

    if verbose:
        console.print(f"[dim]Agent:[/dim] {selected.name}")
        console.print(f"[dim]Skills dir:[/dim] {selected.skills_dir}")
        if selected.pack_dir:
            console.print(f"[dim]Pack dir:[/dim] {selected.pack_dir}")
        console.print(f"[dim]Matched skill:[/dim] {matched.name}")

    if dry_run:
        console.print(f"[bold green]Matched:[/bold green] agent={selected.name}, skill={matched.name}")
        return

    env_path = get_config_dir() / ".env"
    execute_skill(
        matched.body,
        working_dir=selected.working_dir,
        env_path=env_path,
        user_request=request,
        mcp_config_path=selected.mcp_config,
        pack_dir=selected.pack_dir,
    )


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent to use"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show matched skill without executing"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show routing details"),
) -> None:
    """Route natural language to skills and execute via Claude Code."""
    # Store options for the hidden 'run' command
    ctx.ensure_object(dict)
    ctx.obj["agent"] = agent
    ctx.obj["dry_run"] = dry_run
    ctx.obj["verbose"] = verbose

    if ctx.invoked_subcommand is None:
        # No subcommand and no flags → launch interactive mode
        if not agent and not dry_run and not verbose:
            from telos.interactive import interactive_mode
            interactive_mode(console, err_console)
        raise typer.Exit()


@app.command(hidden=True)
def run(
    ctx: typer.Context,
    request: str = typer.Argument(help="Natural language request"),
) -> None:
    """Route a natural language request to a skill and execute it."""
    obj = ctx.obj or {}
    _handle_request(
        request=request,
        agent_name=obj.get("agent"),
        dry_run=obj.get("dry_run", False),
        verbose=obj.get("verbose", False),
    )


@app.command()
def list_skills(
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent to list skills for"),
) -> None:
    """List available skills for an agent (or all agents)."""
    agents = _load_agents_or_exit()

    if agent:
        if agent not in agents:
            err_console.print(f"[bold red]Agent '{agent}' not found.[/bold red]")
            raise typer.Exit(code=1)
        selected = agents[agent]
        skills = discover_skills(selected.skills_dir) if selected.skills_dir else []
        if not skills:
            console.print(f"No skills found for agent '{agent}'.")
            return
        _print_skills_table(skills, header=f"Skills for {agent}")
    else:
        for name in sorted(agents):
            a = agents[name]
            skills = discover_skills(a.skills_dir) if a.skills_dir else []
            if skills:
                _print_skills_table(skills, header=f"Skills for {name}")


@app.command()
def agents() -> None:
    """List all registered agents."""
    all_agents = _load_agents_or_exit()

    table = Table(title="Registered Agents")
    table.add_column("Agent", style="cyan")
    table.add_column("Skills", justify="right")
    table.add_column("Pack Dir", style="dim")
    table.add_column("Working Dir", style="dim")

    for name, agent_obj in sorted(all_agents.items()):
        skill_count = 0
        if agent_obj.skills_dir and agent_obj.skills_dir.exists():
            skill_count = len(list(agent_obj.skills_dir.glob("*/SKILL.md")))
        table.add_row(
            name,
            str(skill_count),
            str(agent_obj.pack_dir or "—"),
            str(agent_obj.working_dir),
        )

    console.print(table)


@app.command()
def install(
    path: str = typer.Argument(help="Path to agent pack directory"),
) -> None:
    """Install an agent pack from a local directory."""
    pack_dir = Path(path).resolve()
    if not pack_dir.is_dir():
        err_console.print(f"[bold red]Not a directory:[/bold red] {pack_dir}")
        raise typer.Exit(code=1)

    try:
        result = install_agent(pack_dir)
    except FileNotFoundError as e:
        err_console.print(f"[bold red]{e}[/bold red]")
        raise typer.Exit(code=1)

    console.print(
        f"[bold green]Installed agent '{result.agent_name}' with {result.skill_count} skills[/bold green]"
    )
    console.print(f"[dim]Installed to:[/dim] {result.install_path}")


@app.command()
def uninstall(
    agent_name: str = typer.Argument(help="Name of the agent to uninstall"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Uninstall an agent and remove its skills."""
    if not yes:
        confirm = typer.confirm(f"Remove agent '{agent_name}' and all its skills?")
        if not confirm:
            console.print("Cancelled.")
            raise typer.Exit()

    try:
        uninstall_agent(agent_name)
    except ValueError as e:
        err_console.print(f"[bold red]{e}[/bold red]")
        raise typer.Exit(code=1)

    console.print(f"[bold green]Uninstalled agent '{agent_name}'[/bold green]")


@app.command()
def init() -> None:
    """Create starter config and skills directory."""
    config_dir = get_config_dir()
    skills_dir = get_skills_dir()
    config_path = config_dir / "agents.toml"

    config_dir.mkdir(parents=True, exist_ok=True)
    skills_dir.mkdir(parents=True, exist_ok=True)

    if config_path.exists():
        console.print(
            f"Config already exists at {config_path} — not overwriting."
        )
    else:
        config_path.write_text("""\
# Telos agent configuration
# Agents are discovered automatically from ~/.skills/
# This file is for overrides only (working_dir, etc.)

# Override working_dir for a discovered agent:
# [agents.hackernews]
# working_dir = "~/obsidian/telos/hackernews"

# Legacy linked agent (skills in external directory):
# [agents.kairos]
# description = "Personal productivity"
# skills_dir = "~/vault/.claude/commands"
# working_dir = "~/vault"
""")
        console.print(f"[bold green]Config created at {config_path}[/bold green]")

    console.print(f"[bold green]Skills directory at {skills_dir}[/bold green]")
    console.print("Install packs with [bold]telos install <path-to-pack>[/bold]")


@app.command()
def bot() -> None:
    """Start the Discord bot."""
    from telos.discord_bot import start_bot

    console.print("[bold green]Starting telos Discord bot...[/bold green]")
    start_bot()


if __name__ == "__main__":
    app()
