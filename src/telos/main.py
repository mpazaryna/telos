"""CLI entrypoint for telos."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import click
import typer
import typer.core
from rich.console import Console
from rich.table import Table

from telos.config import Agent, get_config_dir, get_data_dir, load_config
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


def _load_agents_or_exit() -> tuple[dict[str, Agent], str]:
    """Load config or print init hint and exit."""
    config_dir = get_config_dir()
    config_path = config_dir / "agents.toml"

    if not config_path.exists():
        project_config = Path.cwd() / "config" / "agents.toml"
        if project_config.exists():
            config_path = project_config
        else:
            err_console.print(
                "[bold red]No agents.toml found.[/bold red] "
                "Run [bold]telos init[/bold] to create one."
            )
            raise typer.Exit(code=1)

    try:
        return load_config(config_path)
    except FileNotFoundError:
        err_console.print(
            "[bold red]No agents.toml found.[/bold red] "
            "Run [bold]telos init[/bold] to create one."
        )
        raise typer.Exit(code=1)


def _resolve_agent(agents: dict[str, Agent], default_agent: str, agent_name: str | None) -> Agent:
    """Resolve which agent to use."""
    name = agent_name or default_agent
    if not name:
        err_console.print("[bold red]No default agent configured and no --agent flag provided.[/bold red]")
        raise typer.Exit(code=1)
    if name not in agents:
        err_console.print(f"[bold red]Agent '{name}' not found.[/bold red] Available: {', '.join(agents.keys())}")
        raise typer.Exit(code=1)
    return agents[name]


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
    """Core request handling: load config, route, execute."""
    agents, default_agent = _load_agents_or_exit()
    selected = _resolve_agent(agents, default_agent, agent_name)
    skills = discover_skills(selected.skills_dir)

    if not skills:
        err_console.print(f"[bold red]No skills found for agent '{selected.name}'.[/bold red]")
        raise typer.Exit(code=1)

    if verbose:
        console.print(f"[dim]Agent:[/dim] {selected.name}")
        console.print(f"[dim]Skills dir:[/dim] {selected.skills_dir}")

    matched = route_intent(request, skills)

    if matched is None:
        err_console.print(f"[bold red]No matching skill found for:[/bold red] '{request}'")
        err_console.print()
        _print_skills_table(skills, header="Available skills:")
        raise typer.Exit(code=1)

    if verbose:
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
    )


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent to use (overrides default)"),
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
    """List available skills for an agent."""
    agents, default_agent = _load_agents_or_exit()
    selected = _resolve_agent(agents, default_agent, agent)
    skills = discover_skills(selected.skills_dir)

    if not skills:
        console.print(f"No skills found for agent '{selected.name}'.")
        return

    _print_skills_table(skills, header=f"Skills for {selected.name}")


@app.command()
def agents() -> None:
    """List all registered agents."""
    all_agents, default_agent = _load_agents_or_exit()

    table = Table(title="Registered Agents")
    table.add_column("Agent", style="cyan")
    table.add_column("Mode", style="yellow")
    table.add_column("Skills", justify="right")
    table.add_column("Working Dir", style="dim")

    for name, agent_obj in sorted(all_agents.items()):
        skill_count = 0
        if agent_obj.skills_dir and agent_obj.skills_dir.exists():
            skill_count = len(list(agent_obj.skills_dir.glob("*/SKILL.md")))
        default_marker = " *" if name == default_agent else ""
        table.add_row(
            f"{name}{default_marker}",
            agent_obj.mode,
            str(skill_count),
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
    console.print(f"[dim]Skills at:[/dim] {result.install_path}")


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
    """Create starter config at the telos config directory."""
    config_dir = get_config_dir()
    data_dir = get_data_dir()
    config_path = config_dir / "agents.toml"

    if config_path.exists():
        console.print(
            f"Config already exists at {config_path} — not overwriting."
        )
        return

    config_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "agents").mkdir(parents=True, exist_ok=True)

    config_path.write_text("""\
# Telos agent configuration
# See: telos agents --help

[defaults]
default_agent = ""

# Example linked agent:
# [agents.kairos]
# mode = "linked"
# description = "Personal productivity"
# skills_dir = "~/Documents/ObsidianVault/.claude/commands"
# working_dir = "~/Documents/ObsidianVault"
# executor = "claude_code"

# Installed agents are added automatically via `telos install`
""")

    console.print(f"[bold green]Config created at {config_path}[/bold green]")
    console.print("Edit it to register your agents, then run [bold]telos agents[/bold] to verify.")


if __name__ == "__main__":
    app()
