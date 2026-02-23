"""Skill execution via direct Anthropic API calls."""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console

from telos.logger import log_skill_end, log_skill_start, log_tool_call
from telos.provider import AnthropicProvider, OllamaProvider, StreamEvent, ToolDefinition, ToolResult

console = Console(stderr=True)

BUILTIN_TOOLS = [
    ToolDefinition(
        name="write_file",
        description="Write content to a file. Creates parent directories if needed.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path (relative to working directory)"},
                "content": {"type": "string", "description": "Content to write"},
            },
            "required": ["path", "content"],
        },
    ),
    ToolDefinition(
        name="read_file",
        description="Read the contents of a file.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path (relative to working directory)"},
            },
            "required": ["path"],
        },
    ),
    ToolDefinition(
        name="list_directory",
        description="List files and subdirectories in a directory.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path (relative to working directory, default '.')"},
            },
        },
    ),
    ToolDefinition(
        name="fetch_url",
        description="Fetch content from a URL. Returns the response body as text.",
        input_schema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to fetch"},
            },
            "required": ["url"],
        },
    ),
    ToolDefinition(
        name="run_command",
        description="Run a shell command and return its output. The command runs in the agent's working directory. Use for running scripts, git commands, system utilities, etc. Timeout is 60 seconds.",
        input_schema={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The shell command to execute"},
            },
            "required": ["command"],
        },
    ),
]


def _execute_builtin_tool(name: str, arguments: dict, cwd: Path, command_cwd: Path | None = None) -> ToolResult:
    """Execute a built-in file system tool.

    File tools (write_file, read_file, list_directory) resolve relative to ``cwd``.
    ``run_command`` uses ``command_cwd`` when set (pack directory for companion scripts),
    falling back to ``cwd``.
    """
    try:
        if name == "write_file":
            target = (cwd / arguments["path"]).resolve()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(arguments["content"])
            return ToolResult(tool_call_id="", content=f"Wrote {target}")
        elif name == "read_file":
            target = (cwd / arguments["path"]).resolve()
            return ToolResult(tool_call_id="", content=target.read_text())
        elif name == "list_directory":
            target = (cwd / arguments.get("path", ".")).resolve()
            entries = sorted(p.name for p in target.iterdir())
            return ToolResult(tool_call_id="", content="\n".join(entries))
        elif name == "fetch_url":
            import urllib.request

            req = urllib.request.Request(
                arguments["url"],
                headers={"User-Agent": "telos/0.1"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                return ToolResult(tool_call_id="", content=resp.read().decode())
        elif name == "run_command":
            import subprocess

            run_cwd = command_cwd if command_cwd is not None else cwd
            result = subprocess.run(
                arguments["command"],
                shell=True,
                cwd=str(run_cwd),
                capture_output=True,
                text=True,
                timeout=60,
            )
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]\n{result.stderr}"
            if result.returncode != 0:
                output += f"\n[exit code: {result.returncode}]"
            return ToolResult(tool_call_id="", content=output or "(no output)", is_error=result.returncode != 0)
        else:
            return ToolResult(tool_call_id="", content=f"Unknown tool: {name}", is_error=True)
    except Exception as e:
        return ToolResult(tool_call_id="", content=str(e), is_error=True)


def _build_prompt(
    skill_body: str,
    user_request: str | None = None,
) -> str:
    """Build the prompt string from skill body and optional user request."""
    now = datetime.now().astimezone()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S %Z")
    prompt = f"{skill_body}\n\n---\nCurrent date/time: {timestamp}"
    if user_request:
        prompt += f"\nUser request: {user_request}"
    return prompt


def _create_provider(env: dict[str, str]) -> AnthropicProvider | OllamaProvider:
    """Create a provider from environment variables.

    TELOS_PROVIDER selects the backend: "anthropic" (default) or "ollama".
    TELOS_MODEL overrides the model name.
    OLLAMA_BASE_URL overrides the Ollama endpoint (default: http://localhost:11434/v1).
    """
    provider_type = env.get("TELOS_PROVIDER", "anthropic")

    if provider_type == "ollama":
        model = env.get("TELOS_MODEL", "llama3.1")
        base_url = env.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        return OllamaProvider(model=model, base_url=base_url)

    # Default: Anthropic
    api_key = env.get("ANTHROPIC_API_KEY")
    if not api_key:
        console.print(
            "[bold red]ANTHROPIC_API_KEY not set.[/bold red] "
            "Add it to ~/.config/telos/.env"
        )
        raise SystemExit(1)
    model = env.get("TELOS_MODEL", "claude-haiku-4-5")
    return AnthropicProvider(api_key=api_key, model=model)


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


def _execute_simple(provider: AnthropicProvider | OllamaProvider, prompt: str, cwd: Path, log_ctx: dict, command_cwd: Path | None = None) -> None:
    """Execute a skill with built-in file system tools."""
    system = "Follow the instructions carefully and provide a helpful response. Use the available tools to read and write files as needed."
    messages: list[dict] = [{"role": "user", "content": prompt}]
    tools = BUILTIN_TOOLS

    for _round in range(20):
        log_ctx["rounds"] = _round + 1
        text_parts: list[str] = []
        tool_calls: list = []

        try:
            events = provider.stream_completion(system, messages, tools=tools)
            for event in events:
                if event.type == "text" and event.text:
                    sys.stdout.write(event.text)
                    sys.stdout.flush()
                    text_parts.append(event.text)
                elif event.type == "tool_call" and event.tool_call:
                    tool_calls.append(event.tool_call)
        except Exception:
            if tools:
                # Model doesn't support tools — retry without
                tools = None
                system = "Follow the instructions carefully and provide a helpful response."
                continue
            raise

        if not tool_calls:
            break

        # Build assistant message with text + tool_use blocks
        assistant_content: list[dict] = []
        if text_parts:
            assistant_content.append({"type": "text", "text": "".join(text_parts)})
        for tc in tool_calls:
            assistant_content.append(
                {
                    "type": "tool_use",
                    "id": tc.id,
                    "name": tc.name,
                    "input": tc.arguments,
                }
            )
        messages.append({"role": "assistant", "content": assistant_content})

        # Execute tools and build results
        tool_results: list[dict] = []
        for tc in tool_calls:
            result = _execute_builtin_tool(tc.name, tc.arguments, cwd, command_cwd=command_cwd)
            log_ctx["tool_calls"] += 1
            log_tool_call(tc.name, result.is_error)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "content": result.content,
                    "is_error": result.is_error,
                }
            )
        messages.append({"role": "user", "content": tool_results})

    sys.stdout.write("\n")
    sys.stdout.flush()
    log_skill_end(log_ctx, messages)


async def _execute_with_mcp(
    provider: AnthropicProvider,
    prompt: str,
    mcp_config_path: Path,
    env: dict[str, str],
    log_ctx: dict,
    cwd: Path,
    command_cwd: Path | None = None,
) -> None:
    """Execute a skill with MCP tools + built-in file tools."""
    from telos.mcp_client import connect_mcp_servers

    builtin_names = {t.name for t in BUILTIN_TOOLS}

    async with connect_mcp_servers(mcp_config_path, env) as mcp_ctx:
        system = "Follow the instructions carefully and provide a helpful response. Use the available tools as needed."
        messages: list[dict] = [{"role": "user", "content": prompt}]
        tools = list(BUILTIN_TOOLS) + mcp_ctx.tools

        for _round in range(20):
            log_ctx["rounds"] = _round + 1
            text_parts: list[str] = []
            tool_calls: list = []

            for event in provider.stream_completion(system, messages, tools=tools):
                if event.type == "text" and event.text:
                    sys.stdout.write(event.text)
                    sys.stdout.flush()
                    text_parts.append(event.text)
                elif event.type == "tool_call" and event.tool_call:
                    tool_calls.append(event.tool_call)

            if not tool_calls:
                break

            # Build assistant message with text + tool_use blocks
            assistant_content: list[dict] = []
            if text_parts:
                assistant_content.append({"type": "text", "text": "".join(text_parts)})
            for tc in tool_calls:
                assistant_content.append(
                    {
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.arguments,
                    }
                )
            messages.append({"role": "assistant", "content": assistant_content})

            # Execute tools and build results
            tool_results: list[dict] = []
            for tc in tool_calls:
                if tc.name in builtin_names:
                    result = _execute_builtin_tool(tc.name, tc.arguments, cwd, command_cwd=command_cwd)
                else:
                    result = await mcp_ctx.call_tool(tc.name, tc.arguments)
                log_ctx["tool_calls"] += 1
                log_tool_call(tc.name, result.is_error)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tc.id,
                        "content": result.content,
                        "is_error": result.is_error,
                    }
                )
            messages.append({"role": "user", "content": tool_results})

    sys.stdout.write("\n")
    sys.stdout.flush()
    log_skill_end(log_ctx, messages)


def execute_skill(
    skill_body: str,
    working_dir: Path,
    env_path: Path | None = None,
    user_request: str | None = None,
    mcp_config_path: Path | None = None,
    pack_dir: Path | None = None,
) -> None:
    """Execute a skill via direct API call.

    File tools resolve relative to ``working_dir`` (output directory).
    ``run_command`` uses ``pack_dir`` when set (for companion scripts),
    falling back to ``working_dir``.

    Streams output to stdout.
    Raises SystemExit on errors.
    """
    cwd = resolve_working_dir(working_dir)
    command_cwd = pack_dir if pack_dir is not None else None

    if env_path is not None:
        env = load_env(env_path)
    else:
        env = dict(os.environ)

    provider = _create_provider(env)
    prompt = _build_prompt(skill_body, user_request=user_request)

    provider_name = type(provider).__name__.removesuffix("Provider").lower()
    log_ctx = log_skill_start(provider_name, provider.model, has_mcp=mcp_config_path is not None)

    try:
        if mcp_config_path is not None:
            asyncio.run(_execute_with_mcp(provider, prompt, mcp_config_path, env, log_ctx, cwd, command_cwd=command_cwd))
        else:
            _execute_simple(provider, prompt, cwd, log_ctx, command_cwd=command_cwd)
    except Exception as e:
        log_skill_end(log_ctx, [], error=str(e))
        raise
