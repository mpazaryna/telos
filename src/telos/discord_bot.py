"""Discord bot frontend for telos."""

from __future__ import annotations

import asyncio
import io
import re
import sys
from pathlib import Path

import discord

from telos.config import get_config_dir, load_config
from telos.executor import execute_skill, load_env
from telos.router import discover_skills, route_intent

CHANNEL_NAME = "telos"

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Serialize skill execution — one at a time, stdout capture is safe.
_execution_lock = asyncio.Lock()


def _resolve_skill(request: str, agents: dict, agent_name: str | None):
    """Find the right agent + skill for a request.

    When agent_name is explicit, only search that agent.
    Otherwise search all agents.
    Returns (agent, matched_skill) or (None, None).
    """
    if agent_name:
        if agent_name not in agents:
            return None, None
        agent = agents[agent_name]
        skills = discover_skills(agent.skills_dir)
        return agent, route_intent(request, skills) if skills else None

    for name in sorted(agents):
        agent = agents[name]
        skills = discover_skills(agent.skills_dir) if agent.skills_dir else []
        if not skills:
            continue
        matched = route_intent(request, skills)
        if matched is not None:
            return agent, matched

    return None, None


def _run_skill(request: str, agent_name: str | None = None) -> str:
    """Run a telos skill and capture stdout output."""
    config_path = get_config_dir() / "agents.toml"
    agents = load_config(config_path)

    if agent_name and agent_name not in agents:
        available = ", ".join(agents.keys())
        return f"Agent '{agent_name}' not found. Available: {available}"

    agent, matched = _resolve_skill(request, agents, agent_name)
    if agent is None or matched is None:
        all_skills = []
        for a in agents.values():
            skills = discover_skills(a.skills_dir)
            all_skills.extend(f"{a.name}:{s.name}" for s in skills)
        skill_list = ", ".join(sorted(all_skills))
        return f"No matching skill for: '{request}'\nAvailable: {skill_list}"

    env_path = get_config_dir() / ".env"

    # Capture stdout — execute_skill streams text via sys.stdout.write()
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        execute_skill(
            matched.body,
            working_dir=agent.working_dir,
            env_path=env_path,
            user_request=request,
            mcp_config_path=agent.mcp_config,
            pack_dir=agent.pack_dir,
        )
    finally:
        sys.stdout = old_stdout

    return buf.getvalue().strip()


def _chunk_message(text: str, limit: int = 1900) -> list[str]:
    """Split text into chunks that fit Discord's 2000-char message limit."""
    if len(text) <= limit:
        return [text]

    chunks = []
    while text:
        if len(text) <= limit:
            chunks.append(text)
            break
        # Try to split at a newline
        split = text.rfind("\n", 0, limit)
        if split == -1:
            split = limit
        chunks.append(text[:split])
        text = text[split:].lstrip("\n")
    return chunks


@client.event
async def on_ready():
    print(f"telos bot connected as {client.user}")


@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    # Only respond in the #telos channel
    if message.channel.name != CHANNEL_NAME:
        return

    text = message.content.strip()
    if not text:
        return

    # Parse optional --agent flag: "--agent hackernews frontpage"
    agent_name = None
    agent_match = re.match(r"--agent\s+(\S+)\s+(.*)", text, re.DOTALL)
    if agent_match:
        agent_name = agent_match.group(1)
        text = agent_match.group(2).strip()

    async with _execution_lock:
        async with message.channel.typing():
            try:
                result = await asyncio.to_thread(_run_skill, text, agent_name)
            except Exception as e:
                result = f"Error: {e}"

    if not result:
        result = "(no output)"

    for chunk in _chunk_message(result):
        await message.channel.send(chunk)


def start_bot() -> None:
    """Load token from .env and start the Discord bot."""
    env_path = get_config_dir() / ".env"
    env = load_env(env_path)

    token = env.get("DISCORD_BOT_TOKEN")
    if not token:
        print("DISCORD_BOT_TOKEN not set in ~/.config/telos/.env")
        sys.exit(1)

    client.run(token, log_handler=None)
